from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from daily_report.gui.data_provider import GuiDataProvider
from daily_report.gui.main_window import MainWindow
from daily_report.gui.theme import apply_app_theme


def run_gui() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    apply_app_theme(app)
    provider = GuiDataProvider()
    window = MainWindow(provider)
    window.show()
    return app.exec()
