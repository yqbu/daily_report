from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import date as date_cls
from datetime import datetime
from pathlib import Path
from typing import Any

from daily_report.config.local_settings import get_model_api_key, load_local_settings
from daily_report.reporter.deepseek_client import ChatMessage, DeepSeekClient
from daily_report.reporter.prompt_builder import ReportMaterialBundle, build_prompt_from_materials
from daily_report.service.material_service import MaterialService
from daily_report.storage.database import (
    SqliteConnectionFactory,
    create_connection,
    default_db_path,
    init_database,
)
from daily_report.storage.storage_adapter.report_store import ReportStore, SaveReportCommand

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeneratedReport:
    report_id: int
    prompt_text: str
    report_markdown: str
    material_snapshot_json: str = ''
    created_at: str = ''


class ReportService:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path is not None else default_db_path()
        self.connection_factory = SqliteConnectionFactory(self.db_path)
        self.material_service = MaterialService(self.db_path)

    def ensure_database(self) -> None:
        conn = create_connection(self.db_path)
        try:
            init_database(conn)
        finally:
            conn.close()

    def build_bundle(self, target_date: str | None = None) -> ReportMaterialBundle:
        day = target_date or date_cls.today().isoformat()
        stats = self._build_day_stats(day)
        materials = self.material_service.build_materials(day, include_sensitive=False)
        return ReportMaterialBundle(
            date=day,
            total_time=str(stats.get('total_time', '0m')),
            active_time=str(stats.get('active_time', '0m')),
            top_apps=[],
            app_sessions=[m.summary for m in materials if m.source_type == 'app'],
            clipboard_items=[m.evidence for m in materials if m.source_type == 'clipboard'],
            browser_items=[m.summary for m in materials if m.source_type == 'browser'],
            ai_prompts=[m.summary for m in materials if m.source_type == 'ai_prompt'],
            browser_events=[m.summary for m in materials if m.source_type == 'browser_event'],
        )

    def build_prompt(
        self,
        target_date: str | None = None,
        *,
        template_name: str = 'daily_standard',
        max_chars: int | None = None,
        extra_requirements: str | None = None,
        output_focus: list[str] | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        self.ensure_database()
        settings = load_local_settings()
        day = target_date or date_cls.today().isoformat()
        materials = self.material_service.build_materials(day, include_sensitive=False)
        stats = self._build_day_stats(day)
        stats.update(self.material_service.count_selected_sources(day, include_sensitive=False))
        return build_prompt_from_materials(
            date=day,
            materials=materials,
            stats=stats,
            template_name=template_name,
            max_chars=max_chars or settings.model.max_prompt_chars,
            extra_requirements=extra_requirements,
            output_focus=output_focus,
            options=options,
        )

    def generate_report(
        self,
        target_date: str | None = None,
        *,
        api_key: str | None = None,
        save: bool = True,
        template_name: str = 'daily_standard',
        prompt_text: str | None = None,
        extra_requirements: str | None = None,
        output_focus: list[str] | None = None,
        options: dict[str, Any] | None = None,
    ) -> GeneratedReport:
        self.ensure_database()
        settings = load_local_settings()
        day = target_date or date_cls.today().isoformat()
        prompt = prompt_text or self.build_prompt(
            day,
            template_name=template_name,
            max_chars=settings.model.max_prompt_chars,
            extra_requirements=extra_requirements,
            output_focus=output_focus,
            options=options,
        )

        resolved_api_key = api_key or get_model_api_key(settings)
        if not resolved_api_key:
            raise ValueError(
                'API key is missing. Pass --api-key, set DAILY_REPORT_API_KEY / '
                'DEEPSEEK_API_KEY / OPENAI_API_KEY, or save model.api_key in settings.'
            )

        try:
            client = DeepSeekClient(
                api_key=resolved_api_key,
                model_name=settings.model.model_name,
                base_url=settings.model.base_url,
                temperature=settings.model.temperature,
                timeout_seconds=settings.model.timeout_seconds,
            )
            markdown = client.chat(
                [
                    ChatMessage(role='system', content='你是一名严谨的工作日报写作助手。'),
                    ChatMessage(role='user', content=prompt),
                ]
            ).strip()
        except Exception:
            logger.exception('Model call failed while generating daily report.')
            raise

        if not markdown:
            raise RuntimeError('Model returned an empty report. Nothing was saved.')

        report_id = -1
        material_snapshot_json = ''
        if save:
            snapshot = self.material_service.build_snapshot(day, include_sensitive=False)
            stats = self._build_day_stats(day)
            source_counts = self.material_service.count_selected_sources(day, include_sensitive=False)
            material_snapshot_json = json.dumps(snapshot, ensure_ascii=False)
            report_id = ReportStore(self.connection_factory).save(
                SaveReportCommand(
                    date=day,
                    report_type='daily',
                    template_name=template_name,
                    model_provider=settings.model.provider,
                    model_name=settings.model.model_name,
                    prompt_text=prompt,
                    report_markdown=markdown,
                    material_snapshot_json=material_snapshot_json,
                    material_summary=self._build_material_summary(day, snapshot),
                    source_counts={**source_counts, **stats},
                )
            )

        return GeneratedReport(
            report_id=report_id,
            prompt_text=prompt,
            report_markdown=markdown,
            material_snapshot_json=material_snapshot_json,
            created_at=datetime.now().isoformat(timespec='seconds'),
        )

    def save_report(
        self,
        *,
        target_date: str,
        template_name: str,
        prompt_text: str,
        report_markdown: str,
        material_snapshot_json: str | None = None,
    ) -> int:
        self.ensure_database()
        settings = load_local_settings()
        day = target_date or date_cls.today().isoformat()
        snapshot = material_snapshot_json or json.dumps(
            self.material_service.build_snapshot(day, include_sensitive=False),
            ensure_ascii=False,
        )
        source_counts = self.material_service.count_selected_sources(day, include_sensitive=False)
        stats = self._build_day_stats(day)
        return ReportStore(self.connection_factory).save(
            SaveReportCommand(
                date=day,
                report_type='daily',
                template_name=template_name,
                model_provider=settings.model.provider,
                model_name=settings.model.model_name,
                prompt_text=prompt_text,
                report_markdown=report_markdown,
                material_snapshot_json=snapshot,
                material_summary=self._build_material_summary(day, {'source_counts': source_counts}),
                source_counts={**source_counts, **stats},
            )
        )

    def get_latest_report(self, target_date: str | None = None):
        self.ensure_database()
        day = target_date or date_cls.today().isoformat()
        return ReportStore(self.connection_factory).latest_by_date(day)

    def get_report_detail(self, report_id: int):
        self.ensure_database()
        return ReportStore(self.connection_factory).get_by_id(report_id)

    def list_reports(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ):
        self.ensure_database()
        return ReportStore(self.connection_factory).list_reports(start_date=start_date, end_date=end_date)

    def delete_report(self, report_id: int) -> None:
        self.ensure_database()
        ReportStore(self.connection_factory).delete(report_id)

    def _build_day_stats(self, day: str) -> dict[str, Any]:
        self.ensure_database()
        conn = create_connection(self.db_path)
        try:
            total = conn.execute(
                """
                SELECT
                    COALESCE(SUM(a.duration_sec), 0) AS total_duration_sec,
                    COALESCE(SUM(a.active_duration_sec), 0) AS total_active_duration_sec
                FROM app_sessions a
                LEFT JOIN app_profiles p ON p.app_key = LOWER(TRIM(a.process_name))
                WHERE a.date = ?
                  AND a.is_deleted = 0
                  AND COALESCE(p.track_enabled, 1) = 1
                """,
                (day,),
            ).fetchone()
        finally:
            conn.close()
        total_sec = float(total['total_duration_sec'] if total else 0)
        active_sec = float(total['total_active_duration_sec'] if total else 0)
        return {
            'total_time_sec': total_sec,
            'active_time_sec': active_sec,
            'total_time': _fmt_seconds(total_sec),
            'active_time': _fmt_seconds(active_sec),
        }

    @staticmethod
    def _build_material_summary(day: str, snapshot: dict[str, Any]) -> str:
        counts = snapshot.get('source_counts') if isinstance(snapshot, dict) else {}
        if not isinstance(counts, dict):
            counts = {}
        return (
            f"date={day}; app={counts.get('app', 0)}; browser={counts.get('browser', 0)}; "
            f"clipboard={counts.get('clipboard', 0)}; ai_prompt={counts.get('ai_prompt', 0)}; "
            f"browser_event={counts.get('browser_event', 0)}"
        )


def _fmt_seconds(sec: int | float | None) -> str:
    seconds = int(sec or 0)
    hours, rem = divmod(seconds, 3600)
    minutes, _ = divmod(rem, 60)
    if hours:
        return f'{hours}h{minutes:02d}m'
    return f'{minutes}m'


def generated_report_to_dict(result: GeneratedReport) -> dict[str, Any]:
    return asdict(result)
