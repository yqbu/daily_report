from __future__ import annotations

import traceback
from typing import Callable

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot


class FunctionWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, func: Callable, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        try:
            self.finished.emit(self.func(*self.args, **self.kwargs))
        except Exception as exc:
            self.failed.emit(f"{exc}\n\n{traceback.format_exc()}")


class ResultDispatcher(QObject):
    def __init__(
        self,
        on_success: Callable[[object], None],
        on_error: Callable[[str], None],
        cleanup: Callable[[], None],
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.on_success = on_success
        self.on_error = on_error
        self.cleanup = cleanup

    @Slot(object)
    def handle_success(self, result: object) -> None:
        try:
            self.on_success(result)
        finally:
            self.cleanup()

    @Slot(str)
    def handle_error(self, message: str) -> None:
        try:
            self.on_error(message)
        finally:
            self.cleanup()


def run_in_thread(parent, func: Callable, on_success: Callable[[object], None], on_error: Callable[[str], None], *args, **kwargs) -> None:
    thread = QThread(parent)
    worker = FunctionWorker(func, *args, **kwargs)
    worker.moveToThread(thread)

    def cleanup() -> None:
        thread.quit()
        thread.wait()
        thread.deleteLater()
        dispatcher.deleteLater()
        if hasattr(parent, "_threads"):
            try:
                parent._threads.remove(thread)
            except ValueError:
                pass

    dispatcher = ResultDispatcher(on_success, on_error, cleanup, parent)

    thread.started.connect(worker.run)
    worker.finished.connect(dispatcher.handle_success, Qt.ConnectionType.QueuedConnection)
    worker.failed.connect(dispatcher.handle_error, Qt.ConnectionType.QueuedConnection)
    worker.finished.connect(worker.deleteLater)
    worker.failed.connect(worker.deleteLater)
    if not hasattr(parent, "_threads"):
        parent._threads = []
    parent._threads.append(thread)
    thread._worker = worker
    thread._dispatcher = dispatcher
    thread.start()
