from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from typing import Optional


class AiPromptEntryRepository:
    """
    ai_prompt_entries 表的数据访问层。

    注意：
    - dedupe_key 在 receiver 中生成，用于避免 keydown/click/submit 重复触发；
    - ON CONFLICT 时不覆盖 is_selected，避免覆盖 GUI 中的人工勾选结果。
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._lock = threading.RLock()

    def upsert_entry(
        self,
        *,
        date: str,
        timestamp: datetime,
        platform: str,
        conversation_url: str,
        page_title: str,
        prompt_text: str,
        prompt_preview: str,
        prompt_hash: str,
        dedupe_key: str,
        char_count: int,
        is_sensitive: bool,
        sensitivity_reason: Optional[str],
        is_selected: bool,
        client_event_id: Optional[str],
        source: str,
    ) -> int:
        now = datetime.now().isoformat(timespec='seconds')

        with self._lock:
            self.conn.execute(
                """
                INSERT INTO ai_prompt_entries (
                    date,
                    timestamp,
                    platform,
                    conversation_url,
                    page_title,
                    prompt_text,
                    prompt_preview,
                    prompt_hash,
                    dedupe_key,
                    char_count,
                    is_sensitive,
                    sensitivity_reason,
                    is_selected,
                    is_deleted,
                    client_event_id,
                    source,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
                ON CONFLICT(dedupe_key)
                DO UPDATE SET
                    timestamp = excluded.timestamp,
                    page_title = excluded.page_title,
                    prompt_preview = excluded.prompt_preview,
                    char_count = excluded.char_count,
                    is_sensitive = excluded.is_sensitive,
                    sensitivity_reason = excluded.sensitivity_reason,
                    client_event_id = excluded.client_event_id,
                    source = excluded.source,
                    updated_at = excluded.updated_at
                """,
                (
                    date,
                    timestamp.isoformat(timespec='seconds'),
                    platform,
                    conversation_url,
                    page_title,
                    prompt_text,
                    prompt_preview,
                    prompt_hash,
                    dedupe_key,
                    int(char_count),
                    int(is_sensitive),
                    sensitivity_reason,
                    int(is_selected),
                    client_event_id,
                    source,
                    now,
                    now,
                ),
            )

            row = self.conn.execute(
                """
                SELECT id
                FROM ai_prompt_entries
                WHERE dedupe_key = ?
                """,
                (dedupe_key,),
            ).fetchone()

            self.conn.commit()

            if row is None:
                raise RuntimeError(f'Failed to fetch ai prompt entry id: {dedupe_key}')
            return int(row['id'])

    def list_today_entries(self, date: str) -> list[sqlite3.Row]:
        with self._lock:
            cursor = self.conn.execute(
                """
                SELECT *
                FROM ai_prompt_entries
                WHERE date = ?
                  AND is_deleted = 0
                ORDER BY timestamp DESC
                """,
                (date,),
            )
            return list(cursor.fetchall())

    def update_selected(self, entry_id: int, is_selected: bool) -> None:
        now = datetime.now().isoformat(timespec='seconds')

        with self._lock:
            self.conn.execute(
                """
                UPDATE ai_prompt_entries
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
                UPDATE ai_prompt_entries
                SET is_deleted = 1,
                    updated_at = ?
                WHERE id = ?
                """,
                (now, int(entry_id)),
            )
            self.conn.commit()
