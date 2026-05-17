from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_cls
from pathlib import Path
from typing import Any

from daily_report.config.local_settings import get_model_api_key, load_local_settings
from daily_report.reporter.deepseek_client import ChatMessage, DeepSeekClient
from daily_report.reporter.prompt_builder import ReportMaterialBundle, build_daily_report_prompt
from daily_report.storage.database import (
    SqliteConnectionFactory,
    create_connection,
    default_db_path,
    init_database,
)
from daily_report.storage.storage_adapter.report_store import ReportStore, SaveReportCommand
from daily_report.yasb_bridge.usage_status import fmt_seconds


@dataclass(frozen=True)
class GeneratedReport:
    report_id: int
    prompt_text: str
    report_markdown: str


class ReportService:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path is not None else default_db_path()
        self.connection_factory = SqliteConnectionFactory(self.db_path)

    def ensure_database(self) -> None:
        conn = create_connection(self.db_path)
        try:
            init_database(conn)
        finally:
            conn.close()

    def build_bundle(self, target_date: str | None = None) -> ReportMaterialBundle:
        self.ensure_database()
        day = target_date or date_cls.today().isoformat()
        conn = create_connection(self.db_path)
        try:
            total = conn.execute(
                """
                SELECT
                    COALESCE(SUM(duration_sec), 0) AS total_duration_sec,
                    COALESCE(SUM(active_duration_sec), 0) AS total_active_duration_sec
                FROM app_sessions
                WHERE date = ?
                """,
                (day,),
            ).fetchone()

            top_rows = conn.execute(
                """
                SELECT app_name, SUM(active_duration_sec) AS active_sec, COUNT(*) AS session_count
                FROM app_sessions
                WHERE date = ?
                GROUP BY app_name
                ORDER BY active_sec DESC
                LIMIT 5
                """,
                (day,),
            ).fetchall()

            app_rows = conn.execute(
                """
                SELECT app_name, window_title, start_time, end_time, active_duration_sec
                FROM app_sessions
                WHERE date = ? AND is_selected = 1
                ORDER BY start_time ASC
                LIMIT 80
                """,
                (day,),
            ).fetchall()

            clip_rows = self._safe_select(
                conn,
                """
                SELECT content_preview, last_seen_at, is_sensitive
                FROM clipboard_entries
                WHERE date = ? AND is_selected = 1 AND is_deleted = 0
                ORDER BY last_seen_at DESC
                LIMIT 60
                """,
                (day,),
            )

            browser_rows = self._safe_select(
                conn,
                """
                SELECT title, domain, is_search, search_engine, search_query, visit_time
                FROM browser_history_entries
                WHERE date = ? AND is_selected = 1 AND is_deleted = 0 AND is_noise = 0
                ORDER BY visit_time DESC
                LIMIT 80
                """,
                (day,),
            )

            ai_rows = self._safe_select(
                conn,
                """
                SELECT platform, prompt_preview, timestamp
                FROM ai_prompt_entries
                WHERE date = ? AND is_selected = 1 AND is_deleted = 0
                ORDER BY timestamp DESC
                LIMIT 80
                """,
                (day,),
            )

            return ReportMaterialBundle(
                date=day,
                total_time=fmt_seconds(total['total_duration_sec'] if total else 0),
                active_time=fmt_seconds(total['total_active_duration_sec'] if total else 0),
                top_apps=[
                    f"{r['app_name']} {fmt_seconds(r['active_sec'])}（{r['session_count']} 次）"
                    for r in top_rows
                ],
                app_sessions=[
                    f"{self._hhmm(r['start_time'])}-{self._hhmm(r['end_time'])} "
                    f"{r['app_name']}：{r['window_title'] or ''}（{fmt_seconds(r['active_duration_sec'])}）"
                    for r in app_rows
                ],
                clipboard_items=[
                    f"{self._hhmm(r['last_seen_at'])} {r['content_preview']}"
                    for r in clip_rows
                ],
                browser_items=[self._format_browser_item(r) for r in browser_rows],
                ai_prompts=[
                    f"{self._hhmm(r['timestamp'])} {r['platform']}：{r['prompt_preview']}"
                    for r in ai_rows
                ],
            )
        finally:
            conn.close()

    def build_prompt(self, target_date: str | None = None, *, max_chars: int | None = None) -> str:
        settings = load_local_settings()
        bundle = self.build_bundle(target_date)
        return build_daily_report_prompt(bundle, max_chars=max_chars or settings.model.max_prompt_chars)

    def generate_report(
        self,
        target_date: str | None = None,
        *,
        api_key: str | None = None,
        save: bool = True,
    ) -> GeneratedReport:
        settings = load_local_settings()
        day = target_date or date_cls.today().isoformat()
        prompt = self.build_prompt(day, max_chars=settings.model.max_prompt_chars)

        client = DeepSeekClient(
            api_key=api_key or get_model_api_key(settings),
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
        )

        report_id = -1
        if save:
            store = ReportStore(self.connection_factory)
            report_id = store.save(
                SaveReportCommand(
                    date=day,
                    model_name=settings.model.model_name,
                    prompt_text=prompt,
                    report_markdown=markdown,
                    material_summary=self._build_material_summary(day),
                    source_counts=self._build_source_counts(day),
                )
            )
        return GeneratedReport(report_id=report_id, prompt_text=prompt, report_markdown=markdown)

    def get_latest_report(self, target_date: str | None = None):
        self.ensure_database()
        day = target_date or date_cls.today().isoformat()
        return ReportStore(self.connection_factory).latest_by_date(day)

    def _build_material_summary(self, day: str) -> str:
        bundle = self.build_bundle(day)
        return (
            f'active_time={bundle.active_time}; '
            f'top_apps={len(bundle.top_apps)}; '
            f'app_sessions={len(bundle.app_sessions)}; '
            f'clipboard={len(bundle.clipboard_items)}; '
            f'browser={len(bundle.browser_items)}; '
            f'ai_prompts={len(bundle.ai_prompts)}'
        )

    def _build_source_counts(self, day: str) -> dict[str, Any]:
        bundle = self.build_bundle(day)
        return {
            'date': day,
            'top_apps': len(bundle.top_apps),
            'app_sessions': len(bundle.app_sessions),
            'clipboard_items': len(bundle.clipboard_items),
            'browser_items': len(bundle.browser_items),
            'ai_prompts': len(bundle.ai_prompts),
        }

    @staticmethod
    def _safe_select(conn, sql: str, params: tuple) -> list:
        try:
            return list(conn.execute(sql, params).fetchall())
        except Exception:
            return []

    @staticmethod
    def _hhmm(value: str | None) -> str:
        if not value:
            return ''
        if len(value) >= 16 and value[10] in {' ', 'T'}:
            return value[11:16]
        return value[:5]

    @classmethod
    def _format_browser_item(cls, row) -> str:
        time_part = cls._hhmm(row['visit_time'])
        if row['is_search']:
            return f"{time_part} 搜索 {row['search_engine'] or ''}：{row['search_query'] or ''}"
        title = row['title'] or row['domain'] or ''
        return f"{time_part} {row['domain'] or ''}：{title}"
