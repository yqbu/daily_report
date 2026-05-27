from __future__ import annotations

import json
import threading
import time
import logging
from pathlib import Path

from daily_report.collector.collector_manager import CollectorManager
from daily_report.config.local_settings import LocalSettings, load_local_settings
from daily_report.storage.database import create_connection, default_db_path, init_database, SqliteConnectionFactory

from daily_report.service.single_instance import SingleInstanceError, SingleInstanceLock
from daily_report.service.cleanup_service import cleanup_database, cleanup_logs

from daily_report.collector.app_session_collector import ForegroundCollector
from daily_report.storage.storage_adapter.app_session_store import RepositoryForegroundSessionStore

from daily_report.collector.clipboard_collector import ClipboardCollector
from daily_report.storage.storage_adapter.clipboard_store import RepositoryClipboardEntryStore

from daily_report.collector.edge_history_collector import EdgeHistoryCollector
from daily_report.storage.storage_adapter.edge_history_store import RepositoryEdgeHistoryEntryStore

from daily_report.collector.ai_prompt_receiver import AiPromptReceiver
from daily_report.storage.storage_adapter.ai_prompt_store import RepositoryAiPromptEntryStore


logger = logging.getLogger(__name__)


class RuntimeSettingsProvider:
    def __init__(self, refresh_interval_sec: float = 1.0) -> None:
        self.refresh_interval_sec = refresh_interval_sec
        self._settings: LocalSettings | None = None
        self._loaded_at = 0.0
        self._lock = threading.Lock()

    def get(self) -> LocalSettings:
        now = time.monotonic()
        if self._settings is not None and now - self._loaded_at < self.refresh_interval_sec:
            return self._settings

        with self._lock:
            now = time.monotonic()
            if self._settings is None or now - self._loaded_at >= self.refresh_interval_sec:
                self._settings = load_local_settings()
                self._loaded_at = now
            return self._settings


class DailyReportService:

    def __init__(self) -> None:
        self.db_path = default_db_path()
        self.connection_factory = SqliteConnectionFactory(self.db_path)
        self.manager = CollectorManager(self.connection_factory)
        self.settings_provider = RuntimeSettingsProvider()
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
        settings = self.settings_provider.get()

        foreground_store = RepositoryForegroundSessionStore(connection_factory=self.connection_factory)
        foreground_collector = ForegroundCollector(
            store=foreground_store,
            poll_interval_sec=float(settings.collector.foreground_poll_interval_sec),
            idle_threshold_sec=180,
            split_on_title_change=True,
            min_title_change_interval_sec=2.0,
            flush_interval_sec=10.0,
            enabled_getter=lambda: self.settings_provider.get().collector.foreground_enabled,
            poll_interval_getter=lambda: float(
                self.settings_provider.get().collector.foreground_poll_interval_sec
            ),
        )
        self.manager.add('foreground', foreground_collector)

        clipboard_store = RepositoryClipboardEntryStore(connection_factory=self.connection_factory)
        clipboard_collector = ClipboardCollector(
            store=clipboard_store,
            poll_interval_sec=1.0,
            min_text_chars=2,
            max_text_chars=10_000,
            preview_chars=160,
            sensitive_unselected_by_default=settings.privacy.sensitive_unselected_by_default,
            sensitive_keywords=settings.privacy.sensitive_keywords,
            clipboard_preview_only=settings.privacy.clipboard_preview_only,
            enabled_getter=lambda: self.settings_provider.get().collector.clipboard_enabled,
            sensitive_unselected_getter=lambda: (
                self.settings_provider.get().privacy.sensitive_unselected_by_default
            ),
            sensitive_keywords_getter=lambda: self.settings_provider.get().privacy.sensitive_keywords,
            clipboard_preview_only_getter=lambda: self.settings_provider.get().privacy.clipboard_preview_only,
        )
        self.manager.add('clipboard', clipboard_collector)

        edge_store = RepositoryEdgeHistoryEntryStore(connection_factory=self.connection_factory)
        edge_collector = EdgeHistoryCollector(
            store=edge_store,
            poll_interval_sec=float(settings.collector.edge_sync_interval_min * 60),
            initial_lookback_hours=24,
            max_rows_per_profile=500,
            enabled_getter=lambda: self.settings_provider.get().collector.edge_history_enabled,
            poll_interval_getter=lambda: float(
                self.settings_provider.get().collector.edge_sync_interval_min * 60
            ),
        )
        self.manager.add('edge_history', edge_collector)

        ai_prompt_store = RepositoryAiPromptEntryStore(connection_factory=self.connection_factory)
        ai_prompt_receiver = AiPromptReceiver(
            store=ai_prompt_store,
            host='127.0.0.1',
            port=8765,
            endpoint='/api/ai-prompt',
            sensitive_unselected_by_default=settings.privacy.sensitive_unselected_by_default,
            sensitive_keywords=settings.privacy.sensitive_keywords,
            enabled_getter=lambda: self.settings_provider.get().collector.ai_prompt_enabled,
            sensitive_unselected_getter=lambda: (
                self.settings_provider.get().privacy.sensitive_unselected_by_default
            ),
            sensitive_keywords_getter=lambda: self.settings_provider.get().privacy.sensitive_keywords,
        )
        self.manager.add('ai_prompt', ai_prompt_receiver)

    def cleanup_runtime_data(self) -> None:
        settings = load_local_settings()
        conn = create_connection(self.db_path)
        try:
            cleanup_database(
                conn,
                retention_days=settings.logging.retention_days,
                report_retention_days=90,
                vacuum=False,
            )
        finally:
            conn.close()

        cleanup_logs(
            self.db_path.parent.parent / 'logs',
            retention_days=settings.logging.retention_days,
        )

    def start_cleanup_worker(self) -> None:
        thread = threading.Thread(
            target=self._cleanup_loop,
            name='CleanupWorker',
            daemon=True,
        )
        thread.start()

    def start_status_json_worker(self) -> None:
        thread = threading.Thread(
            target=self._status_json_loop,
            name='StatusJsonWorker',
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

    def _status_json_loop(self) -> None:
        while True:
            try:
                self.write_status_json()
            except Exception:
                logger.exception('Failed to write YASB status JSON.')

            time.sleep(5)

    def write_status_json(self) -> None:
        settings = self.settings_provider.get()
        raw_path = str(settings.yasb.status_json_path or '').strip()
        if not raw_path:
            return

        from daily_report.yasb_bridge.usage_status import build_status_payload

        status_path = Path(raw_path).expanduser()
        status_path.parent.mkdir(parents=True, exist_ok=True)
        payload = build_status_payload()
        tmp_path = status_path.with_name(f'.{status_path.name}.tmp')
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        tmp_path.replace(status_path)

    def run(self) -> None:
        try:
            with SingleInstanceLock(
                self.lock_path,
                app_name='daily-report collector',
            ):
                self.setup_database()
                self.cleanup_runtime_data()
                self.start_cleanup_worker()
                self.start_status_json_worker()
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
