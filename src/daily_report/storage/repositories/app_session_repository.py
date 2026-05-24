from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from typing import Any


class AppSessionRepository:
    """Repository for foreground application sessions."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._lock = threading.RLock()

    def open_session(
        self,
        *,
        date: str,
        app_name: str,
        process_name: str,
        pid: int | None,
        hwnd: int | None = None,
        exe_path: str | None = None,
        window_title: str,
        start_time: datetime,
        end_time: datetime,
        duration_sec: float = 0.0,
        active_duration_sec: float = 0.0,
        is_active: bool = True,
    ) -> int:
        now = _now()
        with self._lock:
            cursor = self.conn.execute(
                """
                INSERT INTO app_sessions (
                    date, app_name, process_name, pid, hwnd, exe_path, window_title,
                    start_time, end_time, duration_sec, active_duration_sec, is_active,
                    is_selected, is_deleted, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?)
                """,
                (
                    date,
                    app_name,
                    process_name,
                    pid,
                    hwnd,
                    exe_path,
                    window_title,
                    start_time.isoformat(timespec='seconds'),
                    end_time.isoformat(timespec='seconds'),
                    float(duration_sec),
                    float(active_duration_sec),
                    int(is_active),
                    now,
                    now,
                ),
            )
            self.conn.commit()
            return int(cursor.lastrowid)

    def update_session(
        self,
        *,
        session_id: int,
        end_time: datetime,
        duration_sec: float,
        active_duration_sec: float,
        is_active: bool,
    ) -> None:
        with self._lock:
            self.conn.execute(
                """
                UPDATE app_sessions
                SET end_time = ?,
                    duration_sec = ?,
                    active_duration_sec = ?,
                    is_active = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    end_time.isoformat(timespec='seconds'),
                    float(duration_sec),
                    float(active_duration_sec),
                    int(is_active),
                    _now(),
                    int(session_id),
                ),
            )
            self.conn.commit()

    def close_session(
        self,
        *,
        session_id: int,
        end_time: datetime,
        duration_sec: float,
        active_duration_sec: float,
        is_active: bool,
    ) -> None:
        self.update_session(
            session_id=session_id,
            end_time=end_time,
            duration_sec=duration_sec,
            active_duration_sec=active_duration_sec,
            is_active=is_active,
        )

    def list_by_date(
        self,
        date: str,
        filters: dict[str, Any] | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[sqlite3.Row]:
        where, params = self._where_by_date(date, filters)
        params.extend([int(limit), int(offset)])
        with self._lock:
            return list(
                self.conn.execute(
                    f"""
                    SELECT *
                    FROM app_sessions
                    WHERE {where}
                    ORDER BY start_time ASC, id ASC
                    LIMIT ? OFFSET ?
                    """,
                    tuple(params),
                ).fetchall()
            )

    def count_by_date(self, date: str, filters: dict[str, Any] | None = None) -> int:
        where, params = self._where_by_date(date, filters)
        with self._lock:
            row = self.conn.execute(
                f"SELECT COUNT(*) AS n FROM app_sessions WHERE {where}",
                tuple(params),
            ).fetchone()
        return int(row['n'] if row else 0)

    def get_by_id(self, entry_id: int) -> sqlite3.Row | None:
        with self._lock:
            return self.conn.execute(
                "SELECT * FROM app_sessions WHERE id = ?",
                (int(entry_id),),
            ).fetchone()

    def update_selected(self, entry_id: int, selected: bool) -> None:
        with self._lock:
            self.conn.execute(
                """
                UPDATE app_sessions
                SET is_selected = ?, updated_at = ?
                WHERE id = ?
                """,
                (int(selected), _now(), int(entry_id)),
            )
            self.conn.commit()

    def mark_deleted(self, entry_id: int) -> None:
        with self._lock:
            self.conn.execute(
                """
                UPDATE app_sessions
                SET is_deleted = 1, updated_at = ?
                WHERE id = ?
                """,
                (_now(), int(entry_id)),
            )
            self.conn.commit()

    soft_delete = mark_deleted

    def update_annotation(
        self,
        source_type: str,
        source_id: int,
        category: str | None = None,
        note: str | None = None,
        importance: int | None = None,
    ) -> sqlite3.Row:
        from daily_report.storage.repositories.annotation_repository import AnnotationRepository

        return AnnotationRepository(self.conn).update_annotation(
            source_type=source_type,
            source_id=source_id,
            category=category,
            note=note,
            importance=importance,
        )

    def list_today_sessions(self, date: str) -> list[sqlite3.Row]:
        return self.list_by_date(date, {'deleted': False}, limit=100000, offset=0)

    def get_today_top_apps(self, date: str, limit: int = 5) -> list[sqlite3.Row]:
        with self._lock:
            return list(
                self.conn.execute(
                    """
                    SELECT
                        app_name,
                        process_name,
                        SUM(duration_sec) AS total_duration_sec,
                        SUM(active_duration_sec) AS total_active_duration_sec,
                        COUNT(*) AS session_count
                    FROM app_sessions
                    WHERE date = ? AND is_deleted = 0
                    GROUP BY app_name, process_name
                    ORDER BY total_active_duration_sec DESC
                    LIMIT ?
                    """,
                    (date, int(limit)),
                ).fetchall()
            )

    @staticmethod
    def _where_by_date(date: str, filters: dict[str, Any] | None) -> tuple[str, list[Any]]:
        filters = filters or {}
        clauses = ['date = ?']
        params: list[Any] = [date]

        if 'selected' in filters and filters['selected'] is not None:
            clauses.append('is_selected = ?')
            params.append(int(bool(filters['selected'])))
        if 'deleted' in filters and filters['deleted'] is not None:
            clauses.append('is_deleted = ?')
            params.append(int(bool(filters['deleted'])))
        if app_name := str(filters.get('app_name') or '').strip():
            clauses.append('app_name = ?')
            params.append(app_name)
        if keyword := str(filters.get('keyword') or '').strip():
            like = f'%{keyword}%'
            clauses.append('(app_name LIKE ? OR process_name LIKE ? OR window_title LIKE ?)')
            params.extend([like, like, like])

        return ' AND '.join(clauses), params


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')
