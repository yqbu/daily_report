from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from typing import Optional


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
