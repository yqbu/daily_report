from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional, Protocol

from daily_report.storage.database import SqliteConnectionFactory
from daily_report.storage.repositories import BrowserHistoryEntryRepository


class EdgeHistoryEntryStateLike(Protocol):
    id: Optional[int]
    date: str

    browser: str
    profile_name: str

    visit_id: int
    visit_time: datetime
    visit_time_chrome: int

    title: str
    url: str
    domain: str

    transition: Optional[int]
    visit_duration_sec: float

    is_search: bool
    search_engine: Optional[str]
    search_query: Optional[str]

    is_noise: bool
    is_selected: bool


class RepositoryEdgeHistoryEntryStore:
    """
    EdgeHistoryCollector 使用的 store 适配器

    与 foreground_store / clipboard_store 保持一致
    - collector 不直接写 SQL
    - store 懒加载 SQLite connection
    - connection 在 collector 所在线程中创建和关闭
    """

    def __init__(self, connection_factory: SqliteConnectionFactory):
        self.connection_factory = connection_factory
        self._conn: Optional[sqlite3.Connection] = None
        self._repository: Optional[BrowserHistoryEntryRepository] = None

    def _get_repository(self) -> BrowserHistoryEntryRepository:
        if self._repository is None:
            self._conn = self.connection_factory.open()
            self._repository = BrowserHistoryEntryRepository(self._conn)

        return self._repository

    def save_entry(self, entry: EdgeHistoryEntryStateLike) -> int:
        repository = self._get_repository()

        return repository.upsert_entry(
            date=entry.date,
            browser=entry.browser,
            profile_name=entry.profile_name,
            visit_id=entry.visit_id,
            visit_time=entry.visit_time,
            visit_time_chrome=entry.visit_time_chrome,
            title=entry.title,
            url=entry.url,
            domain=entry.domain,
            transition=entry.transition,
            visit_duration_sec=entry.visit_duration_sec,
            is_search=entry.is_search,
            search_engine=entry.search_engine,
            search_query=entry.search_query,
            is_noise=entry.is_noise,
            is_selected=entry.is_selected,
        )

    def get_latest_visit_time_chrome(
        self,
        browser: str,
        profile_name: str,
    ) -> Optional[int]:
        repository = self._get_repository()

        return repository.get_latest_visit_time_chrome(
            browser=browser,
            profile_name=profile_name,
        )

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()

        self._conn = None
        self._repository = None