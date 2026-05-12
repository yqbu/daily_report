from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional, Protocol

from daily_report.storage.database import SqliteConnectionFactory
from daily_report.storage.repositories import ClipboardEntryRepository


class ClipboardEntryStateLike(Protocol):
    id: Optional[int]
    date: str
    first_seen_at: datetime
    last_seen_at: datetime
    content: str
    content_preview: str
    content_hash: str
    char_count: int
    is_sensitive: bool
    sensitivity_reason: Optional[str]
    is_selected: bool


class RepositoryClipboardEntryStore:
    """
    ClipboardCollector 使用的 store 适配器。

    和 RepositoryForegroundSessionStore 保持一致：
    - collector 不直接写 SQL；
    - store 懒加载 SQLite connection；
    - connection 在 collector 所在线程中创建和关闭。
    """

    def __init__(self, connection_factory: SqliteConnectionFactory):
        self.connection_factory = connection_factory
        self._conn: Optional[sqlite3.Connection] = None
        self._repository: Optional[ClipboardEntryRepository] = None

    def _get_repository(self) -> ClipboardEntryRepository:
        if self._repository is None:
            self._conn = self.connection_factory.open()
            self._repository = ClipboardEntryRepository(self._conn)

        return self._repository

    def save_entry(self, entry: ClipboardEntryStateLike) -> int:
        repository = self._get_repository()

        return repository.upsert_entry(
            date=entry.date,
            first_seen_at=entry.first_seen_at,
            last_seen_at=entry.last_seen_at,
            content=entry.content,
            content_preview=entry.content_preview,
            content_hash=entry.content_hash,
            char_count=entry.char_count,
            is_sensitive=entry.is_sensitive,
            sensitivity_reason=entry.sensitivity_reason,
            is_selected=entry.is_selected,
        )

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            self._repository = None