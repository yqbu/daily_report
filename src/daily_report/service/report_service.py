from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_cls

from daily_report.config.local_settings import load_local_settings
from daily_report.reporter.deepseek_client import ChatMessage, DeepSeekClient
from daily_report.reporter.prompt_builder import ReportMaterialBundle, build_daily_report_prompt
from daily_report.storage.repositories.report_repository import DailyReportRepository
from daily_report.storage.database import create_connection, default_db_path
from daily_report.yasb_bridge.usage_status import fmt_seconds


@dataclass(frozen=True)
class GeneratedReport:
    report_id: int
    prompt_text: str
    report_markdown: str


class ReportService:
    def __init__(self, db_path=None):
        self.db_path = db_path or default_db_path()

    def build_bundle(self, target_date: str | None = None) -> ReportMaterialBundle:
        day = target_date or date_cls.today().isoformat()
        conn = create_connection(self.db_path)
        try:
            total = conn.execute(
                """
                SELECT COALESCE(SUM(duration_sec), 0) AS total_duration_sec,
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
                total_time=fmt_seconds(total["total_duration_sec"] if total else 0),
                active_time=fmt_seconds(total["total_active_duration_sec"] if total else 0),
                top_apps=[
                    f"{r['app_name']} {fmt_seconds(r['active_sec'])}（{r['session_count']} 次）"
                    for r in top_rows
                ],
                app_sessions=[
                    f"{r['start_time'][11:16] if r['start_time'] else ''}-{r['end_time'][11:16] if r['end_time'] else ''} "
                    f"{r['app_name']}：{r['window_title'] or ''}（{fmt_seconds(r['active_duration_sec'])}）"
                    for r in app_rows
                ],
                clipboard_items=[
                    f"{r['last_seen_at'][11:16] if r['last_seen_at'] else ''} {r['content_preview']}"
                    for r in clip_rows
                ],
                browser_items=[
                    self._format_browser_item(r) for r in browser_rows
                ],
                ai_prompts=[
                    f"{r['timestamp'][11:16] if r['timestamp'] else ''} {r['platform']}：{r['prompt_preview']}"
                    for r in ai_rows
                ],
            )
        finally:
            conn.close()

    def build_prompt(self, target_date: str | None = None, *, max_chars: int | None = None) -> str:
        settings = load_local_settings()
        bundle = self.build_bundle(target_date)
        return build_daily_report_prompt(bundle, max_chars=max_chars or settings.model.max_prompt_chars)

    def generate_report(self, target_date: str | None = None, *, api_key: str | None = None) -> GeneratedReport:
        settings = load_local_settings()
        day = target_date or date_cls.today().isoformat()
        prompt = self.build_prompt(day, max_chars=settings.model.max_prompt_chars)
        client = DeepSeekClient(
            api_key=api_key or settings.model.api_key,
            model_name=settings.model.model_name,
            base_url=settings.model.base_url,
            temperature=settings.model.temperature,
        )
        markdown = client.chat(
            [
                ChatMessage(role="system", content="你是一名严谨的工作日报写作助手。"),
                ChatMessage(role="user", content=prompt),
            ]
        )
        conn = create_connection(self.db_path)
        try:
            repo = DailyReportRepository(conn)
            report_id = repo.save_report(
                date=day,
                model_name=settings.model.model_name,
                prompt_text=prompt,
                report_markdown=markdown,
            )
        finally:
            conn.close()
        return GeneratedReport(report_id=report_id, prompt_text=prompt, report_markdown=markdown)

    @staticmethod
    def _safe_select(conn, sql: str, params: tuple) -> list:
        try:
            return list(conn.execute(sql, params).fetchall())
        except Exception:
            return []

    @staticmethod
    def _format_browser_item(row) -> str:
        time_part = row["visit_time"][11:16] if row["visit_time"] else ""
        if row["is_search"]:
            return f"{time_part} 搜索 {row['search_engine'] or ''}：{row['search_query'] or ''}"
        title = row["title"] or row["domain"] or ""
        return f"{time_part} {row['domain'] or ''}：{title}"