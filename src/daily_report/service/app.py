from __future__ import annotations

import threading
import time
import logging

from daily_report.service.collector_manager import CollectorManager
from daily_report.storage.database import create_connection, default_db_path, init_database, SqliteConnectionFactory

from daily_report.service.single_instance import SingleInstanceError, SingleInstanceLock
from daily_report.service.cleanup import cleanup_database, cleanup_logs

from daily_report.collector.foreground_collector import ForegroundCollector
from daily_report.storage.storage_adapter.foreground_store import RepositoryForegroundSessionStore

from daily_report.collector.clipboard_collector import ClipboardCollector
from daily_report.storage.storage_adapter.clipboard_store import RepositoryClipboardEntryStore


logger = logging.getLogger(__name__)


class DailyReportService:

    def __init__(self) -> None:
        self.db_path = default_db_path()
        self.manager = CollectorManager()
        self.connection_factory = SqliteConnectionFactory(self.db_path)
        # self._connections = []

        self.lock_path = self.db_path.parent / 'daily_report_collector.lock'

    def setup_database(self) -> None:
        logger.info('SQLite database path: %s', self.db_path)

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

        self.manager.add('foreground', foreground_collector)

        clipboard_store = RepositoryClipboardEntryStore(
            connection_factory=self.connection_factory
        )

        clipboard_collector = ClipboardCollector(
            store=clipboard_store,
            poll_interval_sec=1.0,
            min_text_chars=2,
            max_text_chars=10_000,
            preview_chars=160,
        )

        self.manager.add('clipboard', clipboard_collector)

        # 后续继续加：
        # edge_history_collector = EdgeHistoryCollector(...)
        # self.manager.add('edge_history', edge_history_collector)
        #
        # ai_prompt_receiver = AiPromptReceiver(...)
        # self.manager.add('ai_prompt_receiver', ai_prompt_receiver)

    def cleanup_runtime_data(self) -> None:
        conn = create_connection(self.db_path)
        try:
            cleanup_database(
                conn,
                retention_days=7,
                report_retention_days=90,
                vacuum=False,
            )
        finally:
            conn.close()

        cleanup_logs(
            self.db_path.parent.parent / 'logs',
            retention_days=7,
        )

    def start_cleanup_worker(self) -> None:
        thread = threading.Thread(
            target=self._cleanup_loop,
            name='CleanupWorker',
            daemon=True,
        )
        thread.start()

    def _cleanup_loop(self) -> None:
        while True:
            try:
                self.cleanup_runtime_data()
            except Exception:
                logger.exception('Runtime cleanup failed')

            # 每 12 小时清理一次
            time.sleep(24 * 60 * 60)

    def run(self) -> None:
        try:
            with SingleInstanceLock(
                self.lock_path,
                app_name='daily-report collector',
            ):
                self.setup_database()
                self.cleanup_runtime_data()
                self.start_cleanup_worker()
                self.setup_collectors()
                self.manager.start_all()
                self.manager.wait_forever()

        except SingleInstanceError as exc:
            logger.warning('%s', exc)
            return

    # def close(self) -> None:
    #     for conn in self._connections:
    #         try:
    #             conn.close()
    #         except Exception:
    #             logger.exception('Failed to close database connection.')