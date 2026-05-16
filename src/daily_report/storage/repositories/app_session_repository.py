from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from typing import Optional


class AppSessionRepository:
    """
    app_sessions 表的数据访问层
    foreground_collector 不直接写 SQL, 而是调用这个类
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._lock = threading.RLock()

    def open_session(
        self,
        *,
        date: str,
        app_name: str,
        process_name: str,
        pid: Optional[int],
        hwnd: Optional[int] = None,
        exe_path: Optional[str] | None,
        window_title: str,
        start_time: datetime,
        end_time: datetime,
        duration_sec: float = 0.0,
        active_duration_sec: float = 0.0,
        is_active: bool = True,
    ) -> int:
        now = datetime.now().isoformat(timespec='seconds')

        with self._lock:
            cursor = self.conn.execute(
                """
                INSERT INTO app_sessions (
                    date,
                    app_name,
                    process_name,
                    pid,
                    hwnd,
                    exe_path,
                    window_title,
                    start_time,
                    end_time,
                    duration_sec,
                    active_duration_sec,
                    is_active,
                    is_selected,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    1,
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
        now = datetime.now().isoformat(timespec='seconds')

        with self._lock:
            self.conn.execute(
                """
                UPDATE app_sessions
                SET
                    end_time = ?,
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
                    now,
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

    def list_today_sessions(self, date: str) -> list[sqlite3.Row]:
        """
        查询某一天的所有应用使用记录
        """
        with self._lock:
            cursor = self.conn.execute(
                """
                SELECT *
                FROM app_sessions
                WHERE date = ?
                ORDER BY start_time ASC
                """,
                (date,),
            )
            return list(cursor.fetchall())

    def get_today_top_apps(self, date: str, limit: int = 5) -> list[sqlite3.Row]:
        """
        统计某一天应用使用 Top N
        """
        with self._lock:
            cursor = self.conn.execute(
                """
                SELECT
                    app_name,
                    process_name,
                    SUM(duration_sec) AS total_duration_sec,
                    SUM(active_duration_sec) AS total_active_duration_sec,
                    COUNT(*) AS session_count
                FROM app_sessions
                WHERE date = ?
                GROUP BY app_name, process_name
                ORDER BY total_active_duration_sec DESC
                LIMIT ?
                """,
                (date, int(limit)),
            )
            return list(cursor.fetchall())
