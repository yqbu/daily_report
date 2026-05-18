from __future__ import annotations

import os
import subprocess
import sys
import time
import logging
from contextlib import AbstractContextManager
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from PySide6.QtWidgets import QApplication

from daily_report.gui.services.gui_service import GuiService


logger = logging.getLogger(__name__)


class ViteDevServer(AbstractContextManager["ViteDevServer"]):
    def __init__(self, *, port: int = 5173, timeout_seconds: int = 45):
        self.port = port
        self.timeout_seconds = timeout_seconds
        self.url = f"http://127.0.0.1:{port}"
        self.process: subprocess.Popen | None = None
        self.frontend_dir = Path(__file__).resolve().parents[3] / "frontend"

    def __enter__(self) -> "ViteDevServer":
        self._ensure_frontend_ready()
        if self._is_ready():
            logger.info("Using existing Vite dev server: %s", self.url)
            return self

        npm = "npm.cmd" if os.name == "nt" else "npm"
        logger.info("Starting Vite dev server: %s", self.url)
        self.process = subprocess.Popen(
            [npm, "run", "dev", "--", "--port", str(self.port), "--strictPort"],
            cwd=self.frontend_dir,
        )
        self._wait_until_ready()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self.process is None:
            return
        if self.process.poll() is not None:
            return
        logger.info("Stopping Vite dev server")
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

    def _ensure_frontend_ready(self) -> None:
        package_json = self.frontend_dir / "package.json"
        node_modules = self.frontend_dir / "node_modules"
        if not package_json.exists():
            raise RuntimeError(f"frontend/package.json not found: {package_json}")
        if not node_modules.exists():
            raise RuntimeError("frontend/node_modules not found. Run: cd frontend && npm install")

    def _wait_until_ready(self) -> None:
        deadline = time.time() + self.timeout_seconds
        while time.time() < deadline:
            if self.process is not None and self.process.poll() is not None:
                raise RuntimeError(f"Vite dev server exited with code {self.process.returncode}")
            if self._is_ready():
                logger.info("Vite dev server ready: %s", self.url)
                return
            time.sleep(0.4)
        raise RuntimeError(f"Timed out waiting for Vite dev server: {self.url}")

    def _is_ready(self) -> bool:
        try:
            with urlopen(self.url, timeout=0.8) as response:
                return 200 <= response.status < 500
        except URLError:
            return False
        except OSError:
            return False


def run_gui(
    *,
    dev: bool = False,
    dev_port: int = 5173,
    remote_debugging_port: int | None = None,
) -> int:
    if remote_debugging_port is not None:
        os.environ.setdefault("QTWEBENGINE_REMOTE_DEBUGGING", str(remote_debugging_port))

    if dev:
        with ViteDevServer(port=dev_port) as server:
            os.environ["DAILY_REPORT_WEB_DEV_SERVER"] = server.url
            return _run_qt_app()

    return _run_qt_app()


def _run_qt_app() -> int:
    from daily_report.gui.web_window import WebMainWindow

    app = QApplication.instance() or QApplication(sys.argv)
    window = WebMainWindow(GuiService())
    window.show()
    return app.exec()
