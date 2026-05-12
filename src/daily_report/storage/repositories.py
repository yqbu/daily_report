from __future__ import annotations

from typing import Optional

import sqlite3
import threading
from datetime import datetime


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


class ClipboardEntryRepository:
    """
    clipboard_entries 表的数据访问层

    注意:
    - 同一天相同 content_hash 只保留一条记录
    - 重复复制时更新 last_seen_at 和 seen_count
    - 不覆盖用户手动修改过的 is_selected
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._lock = threading.RLock()

    def upsert_entry(
        self,
        *,
        date: str,
        first_seen_at: datetime,
        last_seen_at: datetime,
        content: str,
        content_preview: str,
        content_hash: str,
        char_count: int,
        is_sensitive: bool,
        sensitivity_reason: Optional[str],
        is_selected: bool,
    ) -> int:
        now = datetime.now().isoformat(timespec='seconds')

        with self._lock:
            self.conn.execute(
                """
                INSERT INTO clipboard_entries (
                    date,
                    first_seen_at,
                    last_seen_at,
                    content,
                    content_preview,
                    content_hash,
                    char_count,
                    is_sensitive,
                    sensitivity_reason,
                    is_selected,
                    is_deleted,
                    seen_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1, ?, ?)
                ON CONFLICT(date, content_hash)
                DO UPDATE SET
                    last_seen_at = excluded.last_seen_at,
                    seen_count = clipboard_entries.seen_count + 1,
                    updated_at = excluded.updated_at
                """,
                (
                    date,
                    first_seen_at.isoformat(timespec='seconds'),
                    last_seen_at.isoformat(timespec='seconds'),
                    content,
                    content_preview,
                    content_hash,
                    int(char_count),
                    int(is_sensitive),
                    sensitivity_reason,
                    int(is_selected),
                    now,
                    now,
                ),
            )

            row = self.conn.execute(
                """
                SELECT id
                FROM clipboard_entries
                WHERE date = ? AND content_hash = ?
                """,
                (date, content_hash),
            ).fetchone()

            self.conn.commit()

            if row is None:
                raise RuntimeError(
                    f"Failed to fetch clipboard entry id: {date}, {content_hash}"
                )

            return int(row["id"])

    def list_today_entries(self, date: str) -> list[sqlite3.Row]:
        with self._lock:
            cursor = self.conn.execute(
                """
                SELECT *
                FROM clipboard_entries
                WHERE date = ?
                  AND is_deleted = 0
                ORDER BY last_seen_at DESC
                """,
                (date,),
            )
            return list(cursor.fetchall())

    def update_selected(self, entry_id: int, is_selected: bool) -> None:
        now = datetime.now().isoformat(timespec='seconds')

        with self._lock:
            self.conn.execute(
                """
                UPDATE clipboard_entries
                SET is_selected = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (int(is_selected), now, int(entry_id)),
            )
            self.conn.commit()

    def soft_delete(self, entry_id: int) -> None:
        now = datetime.now().isoformat(timespec='seconds')

        with self._lock:
            self.conn.execute(
                """
                UPDATE clipboard_entries
                SET is_deleted = 1,
                    updated_at = ?
                WHERE id = ?
                """,
                (now, int(entry_id)),
            )
            self.conn.commit()


class BrowserHistoryEntryRepository:
    """
    browser_history_entries 表的数据访问层。

    设计要点:
    - visit_id 来自 Edge History 数据库 visits.id
    - 同一个 browser + profile + visit_id 只保存一次
    - 冲突更新时不覆盖 is_selected, 避免覆盖用户在 GUI 中的手动选择
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._lock = threading.RLock()

    def upsert_entry(
        self,
        *,
        date: str,
        browser: str,
        profile_name: str,
        visit_id: int,
        visit_time: datetime,
        visit_time_chrome: int,
        title: str,
        url: str,
        domain: str,
        transition: Optional[int],
        visit_duration_sec: float,
        is_search: bool,
        search_engine: Optional[str],
        search_query: Optional[str],
        is_noise: bool,
        is_selected: bool,
    ) -> int:
        now = datetime.now().isoformat(timespec="seconds")

        with self._lock:
            self.conn.execute(
                """
                INSERT INTO browser_history_entries (
                    date,
                    browser,
                    profile_name,
                    visit_id,
                    visit_time,
                    visit_time_chrome,
                    title,
                    url,
                    domain,
                    transition,
                    visit_duration_sec,
                    is_search,
                    search_engine,
                    search_query,
                    is_noise,
                    is_selected,
                    is_deleted,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                ON CONFLICT(browser, profile_name, visit_id)
                DO UPDATE SET
                    visit_time = excluded.visit_time,
                    visit_time_chrome = excluded.visit_time_chrome,
                    title = excluded.title,
                    url = excluded.url,
                    domain = excluded.domain,
                    transition = excluded.transition,
                    visit_duration_sec = excluded.visit_duration_sec,
                    is_search = excluded.is_search,
                    search_engine = excluded.search_engine,
                    search_query = excluded.search_query,
                    is_noise = excluded.is_noise,
                    updated_at = excluded.updated_at
                """,
                (
                    date,
                    browser,
                    profile_name,
                    int(visit_id),
                    visit_time.isoformat(timespec="seconds"),
                    int(visit_time_chrome),
                    title,
                    url,
                    domain,
                    transition,
                    float(visit_duration_sec),
                    int(is_search),
                    search_engine,
                    search_query,
                    int(is_noise),
                    int(is_selected),
                    now,
                    now,
                ),
            )

            row = self.conn.execute(
                """
                SELECT id
                FROM browser_history_entries
                WHERE browser = ?
                  AND profile_name = ?
                  AND visit_id = ?
                """,
                (browser, profile_name, int(visit_id)),
            ).fetchone()

            self.conn.commit()

            if row is None:
                raise RuntimeError(
                    f"Failed to fetch browser history entry id: "
                    f"{browser}, {profile_name}, {visit_id}"
                )

            return int(row["id"])

    def get_latest_visit_time_chrome(
        self,
        *,
        browser: str,
        profile_name: str,
    ) -> Optional[int]:
        with self._lock:
            row = self.conn.execute(
                """
                SELECT MAX(visit_time_chrome) AS max_visit_time_chrome
                FROM browser_history_entries
                WHERE browser = ?
                  AND profile_name = ?
                """,
                (browser, profile_name),
            ).fetchone()

        if row is None:
            return None

        value = row["max_visit_time_chrome"]
        return int(value) if value is not None else None

    def list_today_entries(self, date: str) -> list[sqlite3.Row]:
        with self._lock:
            cursor = self.conn.execute(
                """
                SELECT *
                FROM browser_history_entries
                WHERE date = ?
                  AND is_deleted = 0
                ORDER BY visit_time DESC
                """,
                (date,),
            )
            return list(cursor.fetchall())

    def update_selected(self, entry_id: int, is_selected: bool) -> None:
        now = datetime.now().isoformat(timespec="seconds")

        with self._lock:
            self.conn.execute(
                """
                UPDATE browser_history_entries
                SET is_selected = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (int(is_selected), now, int(entry_id)),
            )
            self.conn.commit()

    def soft_delete(self, entry_id: int) -> None:
        now = datetime.now().isoformat(timespec="seconds")

        with self._lock:
            self.conn.execute(
                """
                UPDATE browser_history_entries
                SET is_deleted = 1,
                    updated_at = ?
                WHERE id = ?
                """,
                (now, int(entry_id)),
            )
            self.conn.commit()