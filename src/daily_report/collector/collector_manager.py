from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional

from daily_report.collector.base_collector import Collector
from daily_report.storage.database import SqliteConnectionFactory
from daily_report.storage.repositories.collector_state_repository import CollectorStateRepository

logger = logging.getLogger(__name__)


@dataclass
class ManagedCollector:
    name: str
    collector: Collector
    thread: Optional[threading.Thread] = None


class CollectorManager:
    def __init__(self, connection_factory: SqliteConnectionFactory | None = None) -> None:
        self._collectors: list[ManagedCollector] = []
        self._stop_event = threading.Event()
        self.connection_factory = connection_factory

    def add(self, name: str, collector: Collector) -> None:
        self._collectors.append(ManagedCollector(name=name, collector=collector))

    def start_all(self) -> None:
        for item in self._collectors:
            try:
                logger.info('Starting collector: %s', item.name)
                item.thread = item.collector.start(blocking=False)
                self._mark_running(item.name)
            except Exception as exc:
                logger.exception('Failed to start collector: %s', item.name)
                self._mark_error(item.name, str(exc))

    def stop_all(self) -> None:
        logger.info('Stopping collectors...')

        for item in reversed(self._collectors):
            try:
                logger.info('Stopping collector: %s', item.name)
                item.collector.stop()
                self._mark_stopped(item.name)
            except Exception:
                logger.exception('Failed to stop collector: %s', item.name)
                self._mark_error(item.name, 'failed to stop')

        for item in reversed(self._collectors):
            thread = item.thread
            if thread is not None and thread.is_alive():
                thread.join(timeout=5)

        logger.info('All collectors stopped.')

    def _mark_running(self, name: str) -> None:
        if self.connection_factory is None:
            return
        try:
            with self.connection_factory.connect() as conn:
                CollectorStateRepository(conn).mark_running(name)
        except Exception:
            logger.debug('Failed to write collector running state: %s', name, exc_info=True)

    def _mark_stopped(self, name: str) -> None:
        if self.connection_factory is None:
            return
        try:
            with self.connection_factory.connect() as conn:
                CollectorStateRepository(conn).mark_stopped(name)
        except Exception:
            logger.debug('Failed to write collector stopped state: %s', name, exc_info=True)

    def _mark_error(self, name: str, message: str) -> None:
        if self.connection_factory is None:
            return
        try:
            with self.connection_factory.connect() as conn:
                CollectorStateRepository(conn).mark_error(name, message)
        except Exception:
            logger.debug('Failed to write collector error state: %s', name, exc_info=True)

    def wait_forever(self) -> None:
        try:
            while not self._stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info('KeyboardInterrupt received.')
        finally:
            self.stop_all()
