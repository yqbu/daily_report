from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional, Protocol

from daily_report.storage.database import SqliteConnectionFactory
from daily_report.storage.repositories.app_profile_repository import AppProfileRepository, normalize_app_key
from daily_report.storage.repositories.app_session_repository import AppSessionRepository


class ForegroundSnapshotLike(Protocol):
    process_name: str
    app_name: str
    exe_path: Optional[str]
    window_title: str
    track_enabled: bool


class AppSessionStateLike(Protocol):
    id: Optional[int]
    date: str
    app_name: str
    process_name: str
    pid: int
    hwnd: int
    exe_path: Optional[str]
    window_title: str
    start_time: datetime
    end_time: datetime
    duration_sec: float
    active_duration_sec: float
    is_active: bool
    track_enabled: bool


class RepositoryForegroundSessionStore:
    """
    ForegroundCollector 使用的 store 适配器
    它不直接写 SQL, 而是把 AppSessionState 转换成 AppSessionRepository 所需的字段
    """

    def __init__(self, connection_factory: SqliteConnectionFactory):
        self.connection_factory = connection_factory
        self._conn: Optional[sqlite3.Connection] = None
        self._repository: Optional[AppSessionRepository] = None

    def _get_repository(self) -> AppSessionRepository:
        if self._repository is None:
            # print('Opening SQLite connection for foreground store: %s', self.connection_factory.db_path)
            self._conn = self.connection_factory.open()
            self._repository = AppSessionRepository(self._conn)

        return self._repository

    def prepare_snapshot(self, snapshot: ForegroundSnapshotLike) -> ForegroundSnapshotLike:
        repository = self._get_repository()
        profile = AppProfileRepository(repository.conn).get_profile(
            normalize_app_key(snapshot.process_name, snapshot.exe_path)
        )
        if profile is None:
            return snapshot

        display_name = str(profile.get('display_name') or '').strip()
        if display_name:
            snapshot.app_name = display_name
        if not bool(profile.get('capture_title_enabled', True)):
            snapshot.window_title = ''
        snapshot.track_enabled = bool(profile.get('track_enabled', True))
        return snapshot

    def open_session(self, session: AppSessionStateLike) -> int:
        if not session.track_enabled:
            return 0

        repository = self._get_repository()

        return repository.open_session(
            date=session.date,
            app_name=session.app_name,
            process_name=session.process_name,
            pid=session.pid,
            hwnd=session.hwnd,
            exe_path=session.exe_path,
            window_title=session.window_title,
            start_time=session.start_time,
            end_time=session.end_time,
            duration_sec=session.duration_sec,
            active_duration_sec=session.active_duration_sec,
            is_active=session.is_active,
        )

    def update_session(self, session: AppSessionStateLike) -> None:
        if session.id is None or session.id <= 0:
            return

        repository = self._get_repository()

        repository.update_session(
            session_id=session.id,
            end_time=session.end_time,
            duration_sec=session.duration_sec,
            active_duration_sec=session.active_duration_sec,
            is_active=session.is_active,
        )

    def close_session(self, session: AppSessionStateLike) -> None:
        self.update_session(session)

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            self._repository = None
