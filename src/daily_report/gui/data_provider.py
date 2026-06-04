from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date as date_cls
from pathlib import Path
from typing import Any

from daily_report.storage.database import create_connection, default_db_path, init_database
from daily_report.yasb_bridge.collector_status import build_collector_status_payload
from daily_report.yasb_bridge.usage_status import fmt_seconds


@dataclass(frozen=True)
class MaterialRow:
    key: str
    selected: bool
    time: str
    source_type: str
    preview: str
    source: str
    sensitive: bool


def _app_session_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    display_name = str(data.pop("display_app_name", "") or "").strip()
    if display_name:
        data["app_name"] = display_name
    return data


class GuiDataProvider:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path is not None else default_db_path()
        self.ensure_database()

    def ensure_database(self) -> None:
        conn = create_connection(self.db_path)
        try:
            init_database(conn)
        finally:
            conn.close()

    def connect(self) -> sqlite3.Connection:
        return create_connection(self.db_path)

    @staticmethod
    def today() -> str:
        return date_cls.today().isoformat()

    def status(self, day: str | None = None) -> dict[str, Any]:
        payload = build_collector_status_payload()
        payload["date"] = day or self.today()
        return payload

    def dashboard(self, day: str | None = None) -> dict[str, Any]:
        day = day or self.today()
        conn = self.connect()
        try:
            total = conn.execute(
                """
                SELECT COALESCE(SUM(a.duration_sec), 0) AS total_duration_sec,
                       COALESCE(SUM(a.active_duration_sec), 0) AS total_active_duration_sec,
                       COUNT(a.id) AS session_count
                FROM app_sessions a
                LEFT JOIN app_profiles p ON p.app_key = LOWER(TRIM(a.process_name))
                WHERE a.date = ?
                  AND a.is_deleted = 0
                  AND COALESCE(p.track_enabled, 1) = 1
                """,
                (day,),
            ).fetchone()
            top = conn.execute(
                """
                SELECT COALESCE(NULLIF(p.display_name, ''), a.app_name) AS app_name,
                       SUM(a.active_duration_sec) AS active_sec,
                       COUNT(*) AS session_count
                FROM app_sessions a
                LEFT JOIN app_profiles p ON p.app_key = LOWER(TRIM(a.process_name))
                WHERE a.date = ?
                  AND a.is_deleted = 0
                  AND COALESCE(p.track_enabled, 1) = 1
                GROUP BY COALESCE(NULLIF(p.display_name, ''), a.app_name)
                ORDER BY active_sec DESC
                LIMIT 5
                """,
                (day,),
            ).fetchall()
            sessions = self._list_app_sessions_from_connection(conn, day)
            return {
                "date": day,
                "active_time": fmt_seconds(total["total_active_duration_sec"] if total else 0),
                "total_time": fmt_seconds(total["total_duration_sec"] if total else 0),
                "app_session_count": int(total["session_count"] if total else 0),
                "clipboard_count": self._count(conn, "clipboard_entries", day),
                "browser_count": self._count(conn, "browser_history_entries", day),
                "ai_prompt_count": self._count(conn, "ai_prompt_entries", day),
                "browser_event_count": self._count(conn, "browser_events", day),
                "top_apps": [
                    {
                        "name": row["app_name"],
                        "seconds": float(row["active_sec"] or 0),
                        "session_count": int(row["session_count"] or 0),
                    }
                    for row in top
                ],
                "sessions": sessions,
            }
        finally:
            conn.close()

    def list_app_sessions(
        self,
        day: str | None = None,
        *,
        app_name: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        include_excluded: bool = False,
    ) -> list[dict[str, Any]]:
        day = day or self.today()
        conn = self.connect()
        try:
            return self._list_app_sessions_from_connection(
                conn,
                day,
                app_name=app_name,
                limit=limit,
                offset=offset,
                include_excluded=include_excluded,
            )
        finally:
            conn.close()

    @staticmethod
    def _list_app_sessions_from_connection(
        conn: sqlite3.Connection,
        day: str,
        *,
        app_name: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        include_excluded: bool = False,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT a.*,
                   COALESCE(NULLIF(p.display_name, ''), a.app_name) AS display_app_name
            FROM app_sessions a
            LEFT JOIN app_profiles p ON p.app_key = LOWER(TRIM(a.process_name))
            WHERE a.date = ?
              AND a.is_deleted = 0
        """
        params: list[Any] = [day]
        if app_name and app_name != "全部":
            sql += " AND COALESCE(NULLIF(p.display_name, ''), a.app_name) = ?"
            params.append(app_name)
        if not include_excluded:
            sql += " AND COALESCE(p.track_enabled, 1) = 1"
        sql += " ORDER BY a.start_time ASC"
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([int(limit), int(offset)])

        rows = conn.execute(sql, tuple(params)).fetchall()
        return [_app_session_dict(r) for r in rows]

    def count_app_sessions(
        self,
        day: str | None = None,
        *,
        app_name: str | None = None,
        include_excluded: bool = False,
    ) -> int:
        day = day or self.today()
        sql = """
            SELECT COUNT(*) AS n
            FROM app_sessions a
            LEFT JOIN app_profiles p ON p.app_key = LOWER(TRIM(a.process_name))
            WHERE a.date = ?
              AND a.is_deleted = 0
        """
        params: list[Any] = [day]
        if app_name and app_name != "全部":
            sql += " AND COALESCE(NULLIF(p.display_name, ''), a.app_name) = ?"
            params.append(app_name)
        if not include_excluded:
            sql += " AND COALESCE(p.track_enabled, 1) = 1"
        conn = self.connect()
        try:
            row = conn.execute(sql, tuple(params)).fetchone()
            return int(row["n"] if row else 0)
        finally:
            conn.close()

    def count_app_sessions_by_date(self, days: list[str]) -> dict[str, int]:
        unique_days = list(dict.fromkeys(day for day in days if day))
        if not unique_days:
            return {}

        placeholders = ", ".join("?" for _ in unique_days)
        sql = f"""
            SELECT a.date, COUNT(a.id) AS n
            FROM app_sessions a
            LEFT JOIN app_profiles p ON p.app_key = LOWER(TRIM(a.process_name))
            WHERE a.date IN ({placeholders})
              AND a.is_deleted = 0
              AND COALESCE(p.track_enabled, 1) = 1
            GROUP BY a.date
        """
        conn = self.connect()
        try:
            counts = {day: 0 for day in unique_days}
            for row in conn.execute(sql, tuple(unique_days)).fetchall():
                counts[str(row["date"])] = int(row["n"] or 0)
            return counts
        finally:
            conn.close()

    def list_app_names(self, day: str | None = None) -> list[str]:
        day = day or self.today()
        conn = self.connect()
        try:
            rows = conn.execute(
                """
                SELECT DISTINCT COALESCE(NULLIF(p.display_name, ''), a.app_name) AS app_name
                FROM app_sessions a
                LEFT JOIN app_profiles p ON p.app_key = LOWER(TRIM(a.process_name))
                WHERE a.date = ?
                  AND a.is_deleted = 0
                  AND COALESCE(p.track_enabled, 1) = 1
                  AND COALESCE(NULLIF(p.display_name, ''), a.app_name) IS NOT NULL
                  AND COALESCE(NULLIF(p.display_name, ''), a.app_name) != ''
                ORDER BY app_name ASC
                """,
                (day,),
            ).fetchall()
            return [str(r["app_name"]) for r in rows]
        finally:
            conn.close()

    def list_clipboard_entries(
        self,
        day: str | None = None,
        *,
        keyword: str = "",
        hide_sensitive: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        day = day or self.today()
        sql = """
            SELECT *
            FROM clipboard_entries
            WHERE date = ? AND is_deleted = 0
        """
        params: list[Any] = [day]
        if hide_sensitive:
            sql += " AND is_sensitive = 0"
        sql, params = self._append_keyword_filter(
            sql,
            params,
            keyword,
            ["content", "content_preview", "sensitivity_reason"],
        )
        sql += " ORDER BY last_seen_at DESC, id DESC"
        sql, params = self._append_limit(sql, params, limit, offset)
        return self._fetch_dicts(sql, tuple(params))

    def count_clipboard_entries(
        self,
        day: str | None = None,
        *,
        keyword: str = "",
        hide_sensitive: bool = False,
    ) -> int:
        day = day or self.today()
        sql = """
            SELECT COUNT(*) AS n
            FROM clipboard_entries
            WHERE date = ? AND is_deleted = 0
        """
        params: list[Any] = [day]
        if hide_sensitive:
            sql += " AND is_sensitive = 0"
        sql, params = self._append_keyword_filter(
            sql,
            params,
            keyword,
            ["content", "content_preview", "sensitivity_reason"],
        )
        return self._fetch_count(sql, tuple(params))

    def list_browser_history_entries(
        self,
        day: str | None = None,
        *,
        keyword: str = "",
        domain: str | None = None,
        mode: str = "全部",
        hide_noise: bool = True,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        day = day or self.today()
        sql = """
            SELECT *
            FROM browser_history_entries
            WHERE date = ? AND is_deleted = 0
        """
        params: list[Any] = [day]
        if hide_noise:
            sql += " AND is_noise = 0"
        if domain and domain != "全部":
            sql += " AND domain = ?"
            params.append(domain)
        if mode == "搜索":
            sql += " AND is_search = 1"
        elif mode == "普通访问":
            sql += " AND is_search = 0"
        sql, params = self._append_keyword_filter(
            sql,
            params,
            keyword,
            ["title", "url", "domain", "search_engine", "search_query", "profile_name"],
        )
        sql += " ORDER BY visit_time DESC, id DESC"
        sql, params = self._append_limit(sql, params, limit, offset)
        return self._fetch_dicts(sql, tuple(params))

    def count_browser_history_entries(
        self,
        day: str | None = None,
        *,
        keyword: str = "",
        domain: str | None = None,
        mode: str = "全部",
        hide_noise: bool = True,
    ) -> int:
        day = day or self.today()
        sql = """
            SELECT COUNT(*) AS n
            FROM browser_history_entries
            WHERE date = ? AND is_deleted = 0
        """
        params: list[Any] = [day]
        if hide_noise:
            sql += " AND is_noise = 0"
        if domain and domain != "全部":
            sql += " AND domain = ?"
            params.append(domain)
        if mode == "搜索":
            sql += " AND is_search = 1"
        elif mode == "普通访问":
            sql += " AND is_search = 0"
        sql, params = self._append_keyword_filter(
            sql,
            params,
            keyword,
            ["title", "url", "domain", "search_engine", "search_query", "profile_name"],
        )
        return self._fetch_count(sql, tuple(params))

    def list_browser_domains(self, day: str | None = None) -> list[str]:
        day = day or self.today()
        conn = self.connect()
        try:
            rows = conn.execute(
                """
                SELECT DISTINCT domain
                FROM browser_history_entries
                WHERE date = ? AND is_deleted = 0 AND domain IS NOT NULL AND domain != ''
                ORDER BY domain ASC
                """,
                (day,),
            ).fetchall()
            return [str(r["domain"]) for r in rows]
        finally:
            conn.close()

    def list_ai_prompt_entries(
        self,
        day: str | None = None,
        *,
        keyword: str = "",
        platform: str | None = None,
        hide_sensitive: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        day = day or self.today()
        sql = """
            SELECT *
            FROM ai_prompt_entries
            WHERE date = ? AND is_deleted = 0
        """
        params: list[Any] = [day]
        if platform and platform != "全部":
            sql += " AND platform = ?"
            params.append(platform)
        if hide_sensitive:
            sql += " AND is_sensitive = 0"
        sql, params = self._append_keyword_filter(
            sql,
            params,
            keyword,
            ["platform", "page_title", "prompt_text", "prompt_preview", "conversation_url", "source"],
        )
        sql += " ORDER BY timestamp DESC, id DESC"
        sql, params = self._append_limit(sql, params, limit, offset)
        return self._fetch_dicts(sql, tuple(params))

    def count_ai_prompt_entries(
        self,
        day: str | None = None,
        *,
        keyword: str = "",
        platform: str | None = None,
        hide_sensitive: bool = False,
    ) -> int:
        day = day or self.today()
        sql = """
            SELECT COUNT(*) AS n
            FROM ai_prompt_entries
            WHERE date = ? AND is_deleted = 0
        """
        params: list[Any] = [day]
        if platform and platform != "全部":
            sql += " AND platform = ?"
            params.append(platform)
        if hide_sensitive:
            sql += " AND is_sensitive = 0"
        sql, params = self._append_keyword_filter(
            sql,
            params,
            keyword,
            ["platform", "page_title", "prompt_text", "prompt_preview", "conversation_url", "source"],
        )
        return self._fetch_count(sql, tuple(params))

    def list_ai_platforms(self, day: str | None = None) -> list[str]:
        day = day or self.today()
        conn = self.connect()
        try:
            rows = conn.execute(
                """
                SELECT DISTINCT platform
                FROM ai_prompt_entries
                WHERE date = ? AND is_deleted = 0 AND platform IS NOT NULL AND platform != ''
                ORDER BY platform ASC
                """,
                (day,),
            ).fetchall()
            return [str(r["platform"]) for r in rows]
        finally:
            conn.close()

    def list_daily_reports(
        self,
        *,
        day: str | None = None,
        keyword: str = "",
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT *
            FROM daily_reports
            WHERE 1 = 1
        """
        params: list[Any] = []
        if day:
            sql += " AND date = ?"
            params.append(day)
        sql, params = self._append_keyword_filter(
            sql,
            params,
            keyword,
            ["model_name", "prompt_text", "report_markdown", "material_summary", "source_counts_json"],
        )
        sql += " ORDER BY created_at DESC, id DESC"
        sql, params = self._append_limit(sql, params, limit, offset)
        return self._fetch_dicts(sql, tuple(params))

    def count_daily_reports(self, *, day: str | None = None, keyword: str = "") -> int:
        sql = """
            SELECT COUNT(*) AS n
            FROM daily_reports
            WHERE 1 = 1
        """
        params: list[Any] = []
        if day:
            sql += " AND date = ?"
            params.append(day)
        sql, params = self._append_keyword_filter(
            sql,
            params,
            keyword,
            ["model_name", "prompt_text", "report_markdown", "material_summary", "source_counts_json"],
        )
        return self._fetch_count(sql, tuple(params))

    def get_daily_report(self, report_id: int) -> dict[str, Any] | None:
        rows = self._fetch_dicts(
            """
            SELECT *
            FROM daily_reports
            WHERE id = ?
            """,
            (int(report_id),),
        )
        return rows[0] if rows else None

    def list_materials(self, day: str | None = None) -> list[MaterialRow]:
        day = day or self.today()
        conn = self.connect()
        try:
            rows: list[MaterialRow] = []
            for r in conn.execute(
                """
                SELECT id, is_selected, start_time, app_name, window_title, is_active
                FROM app_sessions
                WHERE date = ?
                ORDER BY start_time DESC
                """,
                (day,),
            ).fetchall():
                rows.append(
                    MaterialRow(
                        key=f"app_sessions:{r['id']}",
                        selected=bool(r["is_selected"]),
                        time=self._time_part(r["start_time"]),
                        source_type="应用记录",
                        preview=f"{r['app_name']} - {r['window_title'] or ''}",
                        source=r["app_name"],
                        sensitive=False,
                    )
                )
            for r in self._safe_fetchall(
                conn,
                """
                SELECT id, is_selected, last_seen_at, content_preview, is_sensitive
                FROM clipboard_entries
                WHERE date = ? AND is_deleted = 0
                ORDER BY last_seen_at DESC
                """,
                (day,),
            ):
                rows.append(
                    MaterialRow(
                        key=f"clipboard_entries:{r['id']}",
                        selected=bool(r["is_selected"]),
                        time=self._time_part(r["last_seen_at"]),
                        source_type="剪贴板",
                        preview=r["content_preview"],
                        source="剪贴板",
                        sensitive=bool(r["is_sensitive"]),
                    )
                )
            for r in self._safe_fetchall(
                conn,
                """
                SELECT id, is_selected, visit_time, title, domain, is_search, search_engine, search_query
                FROM browser_history_entries
                WHERE date = ? AND is_deleted = 0 AND is_noise = 0
                ORDER BY visit_time DESC
                """,
                (day,),
            ):
                preview = f"搜索：{r['search_query']}" if r["is_search"] else (r["title"] or r["domain"] or "")
                source = r["search_engine"] if r["is_search"] else (r["domain"] or "Edge")
                rows.append(
                    MaterialRow(
                        key=f"browser_history_entries:{r['id']}",
                        selected=bool(r["is_selected"]),
                        time=self._time_part(r["visit_time"]),
                        source_type="浏览记录",
                        preview=preview,
                        source=source or "Edge",
                        sensitive=False,
                    )
                )
            for r in self._safe_fetchall(
                conn,
                """
                SELECT id, is_selected, timestamp, platform, prompt_preview, is_sensitive
                FROM ai_prompt_entries
                WHERE date = ? AND is_deleted = 0
                ORDER BY timestamp DESC
                """,
                (day,),
            ):
                rows.append(
                    MaterialRow(
                        key=f"ai_prompt_entries:{r['id']}",
                        selected=bool(r["is_selected"]),
                        time=self._time_part(r["timestamp"]),
                        source_type="AI 提问",
                        preview=r["prompt_preview"],
                        source=r["platform"],
                        sensitive=bool(r["is_sensitive"]),
                    )
                )
            for r in self._safe_fetchall(
                conn,
                """
                SELECT id, is_selected, timestamp, event_type, title, domain, search_query, content_preview, is_sensitive
                FROM browser_events
                WHERE date = ? AND is_deleted = 0
                ORDER BY timestamp DESC
                """,
                (day,),
            ):
                preview = r["search_query"] or r["content_preview"] or r["title"] or r["domain"] or r["event_type"]
                rows.append(
                    MaterialRow(
                        key=f"browser_events:{r['id']}",
                        selected=bool(r["is_selected"]),
                        time=self._time_part(r["timestamp"]),
                        source_type="浏览器事件",
                        preview=preview,
                        source=r["domain"] or "Edge",
                        sensitive=bool(r["is_sensitive"]),
                    )
                )
            rows.sort(key=lambda x: x.time, reverse=True)
            return rows
        finally:
            conn.close()

    def update_material_selected(self, key: str, selected: bool) -> None:
        table, id_text = key.split(":", 1)
        if table not in {"app_sessions", "clipboard_entries", "browser_history_entries", "ai_prompt_entries", "browser_events"}:
            raise ValueError(f"Unsupported material table: {table}")
        conn = self.connect()
        try:
            conn.execute(
                f"UPDATE {table} SET is_selected = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (1 if selected else 0, int(id_text)),
            )
            conn.commit()
        finally:
            conn.close()

    def soft_delete_material(self, key: str) -> None:
        table, id_text = key.split(":", 1)
        if table not in {"clipboard_entries", "browser_history_entries", "ai_prompt_entries", "browser_events"}:
            raise ValueError(f"Unsupported soft delete table: {table}")
        conn = self.connect()
        try:
            conn.execute(
                f"UPDATE {table} SET is_deleted = 1, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (int(id_text),),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _time_part(value: str | None) -> str:
        if not value:
            return ""
        return value[11:19] if len(value) >= 19 else value

    @staticmethod
    def _safe_fetchall(conn: sqlite3.Connection, sql: str, params: tuple) -> list[sqlite3.Row]:
        try:
            return list(conn.execute(sql, params).fetchall())
        except sqlite3.Error:
            return []

    @staticmethod
    def _count(conn: sqlite3.Connection, table: str, day: str) -> int:
        try:
            deleted_clause = " AND is_deleted = 0" if table in {
                "clipboard_entries",
                "browser_history_entries",
                "ai_prompt_entries",
                "browser_events",
            } else ""
            row = conn.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE date = ?{deleted_clause}", (day,)).fetchone()
            return int(row["n"] if row else 0)
        except sqlite3.Error:
            return 0

    @staticmethod
    def _append_keyword_filter(
        sql: str,
        params: list[Any],
        keyword: str,
        columns: list[str],
    ) -> tuple[str, list[Any]]:
        keyword = keyword.strip()
        if not keyword:
            return sql, params
        like = f"%{keyword}%"
        sql += " AND (" + " OR ".join(f"{column} LIKE ?" for column in columns) + ")"
        params.extend([like] * len(columns))
        return sql, params

    @staticmethod
    def _append_limit(
        sql: str,
        params: list[Any],
        limit: int | None,
        offset: int,
    ) -> tuple[str, list[Any]]:
        if limit is None:
            return sql, params
        sql += " LIMIT ? OFFSET ?"
        params.extend([int(limit), int(offset)])
        return sql, params

    def _fetch_dicts(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        conn = self.connect()
        try:
            return [dict(row) for row in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    def _fetch_count(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        conn = self.connect()
        try:
            row = conn.execute(sql, params).fetchone()
            return int(row["n"] if row else 0)
        finally:
            conn.close()
