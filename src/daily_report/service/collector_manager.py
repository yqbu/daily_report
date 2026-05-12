from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional

from daily_report.collector.base import Collector

logger = logging.getLogger(__name__)


@dataclass
class ManagedCollector:
    name: str
    collector: Collector
    thread: Optional[threading.Thread] = None


class CollectorManager:
    def __init__(self) -> None:
        self._collectors: list[ManagedCollector] = []
        self._stop_event = threading.Event()

    def add(self, name: str, collector: Collector) -> None:
        self._collectors.append(ManagedCollector(name=name, collector=collector))

    def start_all(self) -> None:
        for item in self._collectors:
            logger.info('Starting collector: %s', item.name)
            item.thread = item.collector.start(blocking=False)

    def stop_all(self) -> None:
        logger.info('Stopping collectors...')

        for item in reversed(self._collectors):
            try:
                logger.info('Stopping collector: %s', item.name)
                item.collector.stop()
            except Exception:
                logger.exception('Failed to stop collector: %s', item.name)

        for item in reversed(self._collectors):
            thread = item.thread
            if thread is not None and thread.is_alive():
                thread.join(timeout=5)

        logger.info('All collectors stopped.')

    def wait_forever(self) -> None:
        try:
            while not self._stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info('KeyboardInterrupt received.')
        finally:
            self.stop_all()