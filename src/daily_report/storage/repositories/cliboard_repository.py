from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from typing import Optional


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
                    f'Failed to fetch clipboard entry id: {date}, {content_hash}'
                )

            return int(row['id'])

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
