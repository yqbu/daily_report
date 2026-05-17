from __future__ import annotations

from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from daily_report.gui.data_provider import GuiDataProvider
from daily_report.gui.pages.app_sessions_page import AppSessionsPage
from daily_report.gui.pages.dashboard_page import DashboardPage
from daily_report.gui.pages.material_review_page import MaterialReviewPage
from daily_report.gui.pages.placeholder_page import PlaceholderPage
from daily_report.gui.pages.report_generate_page import ReportGeneratePage
from daily_report.gui.pages.settings_page import SettingsPage


class SidebarButton(QPushButton):
    def __init__(self, text: str, index: int, callback):
        super().__init__(text)
        self.index = index
        self.setCheckable(True)
        self.setProperty("nav", True)
        self.clicked.connect(lambda: callback(self.index))
        self.setMinimumHeight(40)

    def set_active(self, active: bool) -> None:
        self.setChecked(active)
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)


class MainWindow(QMainWindow):
    def __init__(self, provider: GuiDataProvider | None = None):
        super().__init__()
        self.provider = provider or GuiDataProvider()
        self.setWindowTitle("Daily Reporter - 智能日报生成工具")
        self.resize(1280, 780)
        self.setMinimumSize(1080, 680)

        root = QFrame()
        root.setObjectName("RootFrame")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._create_sidebar())

        self.stack = QStackedWidget()
        self.stack.addWidget(DashboardPage(self.provider))
        self.stack.addWidget(AppSessionsPage(self.provider))
        self.stack.addWidget(PlaceholderPage("剪贴板", "查看复制文本记录，支持脱敏、预览和人工勾选"))
        self.stack.addWidget(PlaceholderPage("浏览记录", "查看 Edge 历史记录、搜索关键词和噪声过滤结果"))
        self.stack.addWidget(PlaceholderPage("AI 提问", "查看 ChatGPT / DeepSeek 用户提问记录"))
        self.stack.addWidget(MaterialReviewPage(self.provider))
        self.stack.addWidget(ReportGeneratePage(self.provider))
        self.stack.addWidget(PlaceholderPage("历史日报", "查看、复制和导出历史生成的 Markdown 日报"))
        self.stack.addWidget(SettingsPage(self.provider))
        layout.addWidget(self.stack, 1)
        self.set_page(0)

    def _create_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(190)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        title = QLabel("Daily Reporter")
        title.setObjectName("SidebarTitle")
        subtitle = QLabel("智能日报生成工具")
        subtitle.setObjectName("SidebarSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(12)
        self.nav_buttons: list[SidebarButton] = []
        items = ["今日总览", "应用记录", "剪贴板", "浏览记录", "AI 提问", "素材确认", "日报生成", "历史日报", "设置"]
        group = QButtonGroup(sidebar)
        group.setExclusive(True)
        for index, text in enumerate(items):
            button = SidebarButton(text, index, self.set_page)
            group.addButton(button)
            self.nav_buttons.append(button)
            layout.addWidget(button)
        layout.addStretch()
        status = QLabel("采集服务：请运行 daily-report run")
        status.setObjectName("StatusGood")
        version = QLabel("版本：v0.1.0")
        version.setObjectName("MutedText")
        layout.addWidget(status)
        layout.addWidget(version)
        return sidebar

    def set_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for button in self.nav_buttons:
            button.set_active(button.index == index)
        page = self.stack.currentWidget()
        if hasattr(page, "refresh"):
            page.refresh()
        elif hasattr(page, "refresh_summary"):
            page.refresh_summary()
