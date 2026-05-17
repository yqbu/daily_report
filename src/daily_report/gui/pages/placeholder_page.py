from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from daily_report.gui.widgets import Card, PageHeader


class PlaceholderPage(QWidget):
    def __init__(self, title: str, description: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 24)
        layout.addWidget(PageHeader(title, description))
        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        label = QLabel("该页面可复用素材确认中心的表格样式，接入对应 repository 后展示真实数据。")
        label.setObjectName("MutedText")
        label.setWordWrap(True)
        card_layout.addWidget(label)
        layout.addWidget(card)
        layout.addStretch()
