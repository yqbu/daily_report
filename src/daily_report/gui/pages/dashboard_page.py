from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from daily_report.gui.data_provider import GuiDataProvider
from daily_report.gui.widgets import Card, MetricCard, PageHeader, TimelineWidget, UsageBarChart, UsageItem


class DashboardPage(QWidget):
    def __init__(self, provider: GuiDataProvider):
        super().__init__()
        self.provider = provider
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(16)

        self.header = PageHeader("今日总览", "本地采集数据与工作状态概览")
        root.addWidget(self.header)

        self.metric_row = QHBoxLayout()
        self.metric_row.setSpacing(12)
        root.addLayout(self.metric_row)

        middle = QHBoxLayout()
        middle.setSpacing(14)
        self.usage_chart = UsageBarChart([])
        middle.addWidget(self.usage_chart, 5)

        right_col = QVBoxLayout()
        right_col.setSpacing(14)
        self.timeline = TimelineWidget()
        right_col.addWidget(self.timeline)

        self.recent_card = Card()
        self.recent_layout = QVBoxLayout(self.recent_card)
        self.recent_layout.setContentsMargins(18, 16, 18, 16)
        self.recent_layout.setSpacing(9)
        self.recent_title = QLabel("最近活动")
        self.recent_title.setObjectName("SectionTitle")
        self.recent_layout.addWidget(self.recent_title)
        right_col.addWidget(self.recent_card)
        middle.addLayout(right_col, 5)
        root.addLayout(middle, 1)

        bottom = QHBoxLayout()
        bottom.addStretch()
        refresh = QPushButton("刷新数据")
        refresh.clicked.connect(self.refresh)
        bottom.addWidget(refresh)
        root.addLayout(bottom)
        self.refresh()

    def refresh(self) -> None:
        data = self.provider.dashboard()
        while self.metric_row.count():
            item = self.metric_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.metric_row.addWidget(MetricCard("今日活跃时间", data["active_time"], f"总时长 {data['total_time']}"))
        self.metric_row.addWidget(MetricCard("应用记录", f"{data['app_session_count']} 条", "前台窗口 session"))
        self.metric_row.addWidget(MetricCard("剪贴板", f"{data['clipboard_count']} 条", "文本复制记录"))
        self.metric_row.addWidget(MetricCard("浏览记录", f"{data['browser_count']} 条", "Edge 历史记录"))
        self.metric_row.addWidget(MetricCard("AI 提问", f"{data['ai_prompt_count']} 条", "ChatGPT / DeepSeek"))

        self.usage_chart.set_data([UsageItem(d["name"], d["seconds"]) for d in data["top_apps"]])
        self.timeline.set_slots_from_sessions(data["sessions"])

        # 清空旧最近活动，保留标题。
        while self.recent_layout.count() > 1:
            item = self.recent_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        for row in list(reversed(data["sessions"][-6:])):
            text = f"{str(row.get('start_time', ''))[11:16]}    {row.get('app_name', '')}    {row.get('window_title', '')}"
            label = QLabel(text)
            label.setObjectName("MutedText")
            label.setWordWrap(True)
            self.recent_layout.addWidget(label)
