from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional, Protocol

from daily_report.storage.database import SqliteConnectionFactory
from daily_report.storage.repositories import AiPromptEntryRepository


class AiPromptEntryStateLike(Protocol):
    id: Optional[int]
    date: str
    timestamp: datetime
    platform: str
    conversation_url: str
    page_title: str
    prompt_text: str
    prompt_preview: str
    prompt_hash: str
    dedupe_key: str
    char_count: int
    is_sensitive: bool
    sensitivity_reason: Optional[str]
    is_selected: bool
    client_event_id: Optional[str]
    source: str


class RepositoryAiPromptEntryStore:
    """
    AiPromptReceiver 使用的 store 适配器。

    设计与 foreground_store / clipboard_store 一致：
    - receiver 不直接写 SQL；
    - store 懒加载 SQLite connection；
    - connection 在 receiver 所在线程中创建并关闭。
    """

    def __init__(self, connection_factory: SqliteConnectionFactory):
        self.connection_factory = connection_factory
        self._conn: Optional[sqlite3.Connection] = None
        self._repository: Optional[AiPromptEntryRepository] = None

    def _get_repository(self) -> AiPromptEntryRepository:
        if self._repository is None:
            self._conn = self.connection_factory.open()
            self._repository = AiPromptEntryRepository(self._conn)
        return self._repository

    def save_entry(self, entry: AiPromptEntryStateLike) -> int:
        repository = self._get_repository()
        return repository.upsert_entry(
            date=entry.date,
            timestamp=entry.timestamp,
            platform=entry.platform,
            conversation_url=entry.conversation_url,
            page_title=entry.page_title,
            prompt_text=entry.prompt_text,
            prompt_preview=entry.prompt_preview,
            prompt_hash=entry.prompt_hash,
            dedupe_key=entry.dedupe_key,
            char_count=entry.char_count,
            is_sensitive=entry.is_sensitive,
            sensitivity_reason=entry.sensitivity_reason,
            is_selected=entry.is_selected,
            client_event_id=entry.client_event_id,
            source=entry.source,
        )

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
        self._conn = None
        self._repository = None
