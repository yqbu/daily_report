from __future__ import annotations

import logging

from daily_report.collector.foreground_collector import ForegroundCollector
from daily_report.service.collector_manager import CollectorManager
from daily_report.storage.database import create_connection, default_db_path, init_database, SqliteConnectionFactory
from daily_report.storage.storage_adapter.foreground_store import RepositoryForegroundSessionStore
from daily_report.storage.repositories import AppSessionRepository

logger = logging.getLogger(__name__)


class DailyReportService:

    def __init__(self) -> None:
        self.db_path = default_db_path()
        self.manager = CollectorManager()
        self.connection_factory = SqliteConnectionFactory(self.db_path)

    def setup_database(self) -> None:
        conn = create_connection(self.db_path)
        try:
            init_database(conn)
        finally:
            conn.close()

    def setup_collectors(self) -> None:
        foreground_store = RepositoryForegroundSessionStore(
            connection_factory=self.connection_factory
        )

        foreground_collector = ForegroundCollector(
            store=foreground_store,
            poll_interval_sec=2.0,
            idle_threshold_sec=180,
            split_on_title_change=True,
            min_title_change_interval_sec=2.0,
            flush_interval_sec=10.0,
        )

        self.manager.add(foreground_collector)

        self.manager.add('foreground', foreground_collector)

        # 后续继续加：
        # clipboard_collector = ClipboardCollector(...)
        # self.manager.add('clipboard', clipboard_collector)
        #
        # edge_history_collector = EdgeHistoryCollector(...)
        # self.manager.add('edge_history', edge_history_collector)
        #
        # ai_prompt_receiver = AiPromptReceiver(...)
        # self.manager.add('ai_prompt_receiver', ai_prompt_receiver)

    def run(self) -> None:
        self.setup_database()
        self.setup_collectors()

        self.manager.start_all()
        self.manager.wait_forever()

    def close(self) -> None:
        for conn in self._connections:
            try:
                conn.close()
            except Exception:
                logger.exception('Failed to close database connection.')