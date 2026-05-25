from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QIcon
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMainWindow

from daily_report.config.paths import get_installed_share_root
from daily_report.gui.assets import find_app_icon_path
from daily_report.gui.bridge import PythonBridge
from daily_report.gui.services.gui_service import GuiService


class WebMainWindow(QMainWindow):
    def __init__(self, service: GuiService | None = None):
        super().__init__()
        self.setWindowTitle("Daily Reporter")
        icon_path = find_app_icon_path(128)
        if icon_path:
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1365, 820)

        self.view = QWebEngineView(self)
        self.setCentralWidget(self.view)

        self.bridge = PythonBridge(service)
        self.channel = QWebChannel(self.view.page())
        self.channel.registerObject("pyBridge", self.bridge)
        self.view.page().setWebChannel(self.channel)

        self.load_frontend()

    def load_frontend(self) -> None:
        dev_url = os.getenv("DAILY_REPORT_WEB_DEV_SERVER") or os.getenv("VITE_DEV_SERVER_URL")
        if dev_url:
            self.view.load(QUrl(dev_url))
            return

        index = self._frontend_index()
        if index.exists():
            self.view.load(QUrl.fromLocalFile(str(index)))
            return

        self.view.setHtml(self._missing_frontend_html(index), QUrl.fromLocalFile(str(index.parent)))

    @staticmethod
    def _frontend_index() -> Path:
        gui_dir = Path(__file__).resolve().parent
        repo_root = gui_dir.parents[2]
        env_dist = os.getenv("DAILY_REPORT_FRONTEND_DIST")
        candidates = [
            Path(env_dist) / "index.html" if env_dist else None,
            Path.cwd() / "frontend" / "dist" / "index.html",
            repo_root / "frontend" / "dist" / "index.html",
            get_installed_share_root() / "frontend" / "dist" / "index.html",
        ]
        for candidate in candidates:
            if candidate and candidate.exists():
                return candidate
        return Path.cwd() / "frontend" / "dist" / "index.html"

    @staticmethod
    def _missing_frontend_html(index: Path) -> str:
        return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>Daily Reporter</title>
  <style>
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #f5f7fb;
      color: #172033;
      font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    }}
    .panel {{
      width: min(680px, calc(100vw - 48px));
      padding: 32px;
      border: 1px solid #dbe3ef;
      border-radius: 18px;
      background: #fff;
      box-shadow: 0 18px 48px rgba(15, 23, 42, .08);
    }}
    h1 {{ margin: 0 0 12px; font-size: 24px; }}
    p {{ line-height: 1.8; color: #526179; }}
    code {{
      display: block;
      margin-top: 12px;
      padding: 12px 14px;
      border-radius: 10px;
      background: #f1f5f9;
      color: #0f172a;
      white-space: pre-wrap;
    }}
  </style>
</head>
<body>
  <main class="panel">
    <h1>Vue 前端构建产物不存在</h1>
    <p>未找到 <strong>{index}</strong>。请先构建 Web UI，然后重新执行 <strong>daily-report gui</strong>。</p>
    <code>cd frontend
npm install
npm run build
daily-report gui</code>
    <p>开发时也可以设置 DAILY_REPORT_WEB_DEV_SERVER，例如 http://localhost:5173。</p>
  </main>
</body>
</html>
"""
