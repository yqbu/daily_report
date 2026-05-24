from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import date as date_cls
from pathlib import Path
from typing import Any

from daily_report.service.material_service import MaterialService
from daily_report.storage.database import create_connection, default_db_path, init_database
from daily_report.storage.repositories.collector_state_repository import CollectorStateRepository
from daily_report.yasb_bridge.collector_status import build_collector_status_payload


class OverviewService:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path is not None else default_db_path()
        self.material_service = MaterialService(self.db_path)

    def get_overview(self, date: str | None = None) -> dict[str, Any]:
        day = date or date_cls.today().isoformat()
        conn = create_connection(self.db_path)
        try:
            init_database(conn)
            active_time_sec, total_time_sec, app_session_count = self._app_totals(conn, day)
            browser_count = self._count(
                conn,
                "SELECT COUNT(*) AS n FROM browser_history_entries WHERE date = ? AND is_deleted = 0",
                (day,),
            )
            clipboard_count = self._count(
                conn,
                "SELECT COUNT(*) AS n FROM clipboard_entries WHERE date = ? AND is_deleted = 0",
                (day,),
            )
            ai_prompt_count = self._count(
                conn,
                "SELECT COUNT(*) AS n FROM ai_prompt_entries WHERE date = ? AND is_deleted = 0",
                (day,),
            )
            selected_material_count = self._selected_count(conn, day)
            sensitive_count = self._sensitive_count(conn, day)
            top_apps = self._top_apps(conn, day)
            hourly_activity = self._hourly_activity(conn, day)
            collector_payload = self._collector_payload(conn)
            report_status = '已生成' if self._latest_report_exists(conn, day) else '未生成'
        finally:
            conn.close()

        category_distribution = self._category_distribution(day)
        source_distribution = [
            {'source_type': 'app', 'count': app_session_count},
            {'source_type': 'browser', 'count': browser_count},
            {'source_type': 'clipboard', 'count': clipboard_count},
            {'source_type': 'ai_prompt', 'count': ai_prompt_count},
        ]

        return {
            'date': day,
            'collector_status': collector_payload.get('collector_status', 'unknown'),
            'collector_status_label': collector_payload.get('collector_status_label', ''),
            'collector_states': collector_payload.get('collector_states', []),
            'active_time_sec': active_time_sec,
            'total_time_sec': total_time_sec,
            'active_time': _fmt_seconds(active_time_sec),
            'total_time': _fmt_seconds(total_time_sec),
            'app_session_count': app_session_count,
            'browser_count': browser_count,
            'clipboard_count': clipboard_count,
            'ai_prompt_count': ai_prompt_count,
            'selected_material_count': selected_material_count,
            'sensitive_count': sensitive_count,
            'report_status': report_status,
            'top_apps': top_apps,
            'source_distribution': source_distribution,
            'category_distribution': category_distribution,
            'hourly_activity': hourly_activity,
        }

    def _collector_payload(self, conn: sqlite3.Connection) -> dict[str, Any]:
        try:
            payload = build_collector_status_payload()
        except Exception:
            payload = {'collector_status': 'unknown', 'collector_status_label': '未知'}
        try:
            payload['collector_states'] = CollectorStateRepository(conn).list_states()
        except sqlite3.Error:
            payload['collector_states'] = []
        return payload

    @staticmethod
    def _app_totals(conn: sqlite3.Connection, day: str) -> tuple[int, int, int]:
        try:
            row = conn.execute(
                """
                SELECT
                    COALESCE(SUM(active_duration_sec), 0) AS active_sec,
                    COALESCE(SUM(duration_sec), 0) AS total_sec,
                    COUNT(*) AS n
                FROM app_sessions
                WHERE date = ? AND is_deleted = 0
                """,
                (day,),
            ).fetchone()
        except sqlite3.Error:
            return 0, 0, 0
        return (
            int(row['active_sec'] if row else 0),
            int(row['total_sec'] if row else 0),
            int(row['n'] if row else 0),
        )

    @staticmethod
    def _top_apps(conn: sqlite3.Connection, day: str) -> list[dict[str, Any]]:
        try:
            rows = conn.execute(
                """
                SELECT app_name, SUM(active_duration_sec) AS seconds, COUNT(*) AS session_count
                FROM app_sessions
                WHERE date = ? AND is_deleted = 0
                GROUP BY app_name
                ORDER BY seconds DESC
                LIMIT 8
                """,
                (day,),
            ).fetchall()
        except sqlite3.Error:
            return []
        return [
            {
                'name': str(row['app_name'] or ''),
                'app_name': str(row['app_name'] or ''),
                'seconds': int(row['seconds'] or 0),
                'session_count': int(row['session_count'] or 0),
            }
            for row in rows
        ]

    @staticmethod
    def _hourly_activity(conn: sqlite3.Connection, day: str) -> list[dict[str, Any]]:
        slots = [{'hour': hour, 'label': f'{hour:02d}:00', 'active_sec': 0} for hour in range(24)]
        try:
            rows = conn.execute(
                """
                SELECT start_time, active_duration_sec, duration_sec
                FROM app_sessions
                WHERE date = ? AND is_deleted = 0
                """,
                (day,),
            ).fetchall()
        except sqlite3.Error:
            return slots
        for row in rows:
            start = str(row['start_time'] or '')
            try:
                hour = int(start[11:13])
            except ValueError:
                continue
            if 0 <= hour < 24:
                slots[hour]['active_sec'] += int(row['active_duration_sec'] or row['duration_sec'] or 0)
        return slots

    def _category_distribution(self, day: str) -> list[dict[str, Any]]:
        counter = Counter(material.category for material in self.material_service.build_materials(day))
        return [{'category': category, 'count': count} for category, count in counter.most_common()]

    @staticmethod
    def _selected_count(conn: sqlite3.Connection, day: str) -> int:
        queries = (
            "SELECT COUNT(*) AS n FROM app_sessions WHERE date = ? AND is_selected = 1 AND is_deleted = 0",
            "SELECT COUNT(*) AS n FROM browser_history_entries WHERE date = ? AND is_selected = 1 AND is_deleted = 0",
            "SELECT COUNT(*) AS n FROM clipboard_entries WHERE date = ? AND is_selected = 1 AND is_deleted = 0",
            "SELECT COUNT(*) AS n FROM ai_prompt_entries WHERE date = ? AND is_selected = 1 AND is_deleted = 0",
        )
        return sum(OverviewService._count(conn, sql, (day,)) for sql in queries)

    @staticmethod
    def _sensitive_count(conn: sqlite3.Connection, day: str) -> int:
        queries = (
            "SELECT COUNT(*) AS n FROM clipboard_entries WHERE date = ? AND is_sensitive = 1 AND is_deleted = 0",
            "SELECT COUNT(*) AS n FROM ai_prompt_entries WHERE date = ? AND is_sensitive = 1 AND is_deleted = 0",
        )
        return sum(OverviewService._count(conn, sql, (day,)) for sql in queries)

    @staticmethod
    def _latest_report_exists(conn: sqlite3.Connection, day: str) -> bool:
        try:
            row = conn.execute(
                "SELECT 1 FROM daily_reports WHERE date = ? LIMIT 1",
                (day,),
            ).fetchone()
        except sqlite3.Error:
            return False
        return row is not None

    @staticmethod
    def _count(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...]) -> int:
        try:
            row = conn.execute(sql, params).fetchone()
        except sqlite3.Error:
            return 0
        return int(row['n'] if row else 0)


def _fmt_seconds(sec: int | float | None) -> str:
    seconds = int(sec or 0)
    hours, rem = divmod(seconds, 3600)
    minutes, _ = divmod(rem, 60)
    if hours:
        return f'{hours}h{minutes:02d}m'
    return f'{minutes}m'
