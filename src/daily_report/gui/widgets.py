from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont
from PySide6.QtWidgets import (
    QFrame, QHeaderView, QLabel, QPushButton, QSizePolicy, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget
)


@dataclass(frozen=True)
class UsageItem:
    name: str
    seconds: float
    percent: int = 0


def fmt_seconds(sec: int | float | None) -> str:
    sec = int(sec or 0)
    h, rem = divmod(sec, 3600)
    m, _ = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m"
    return f"{m}m"


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("card", True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)


class MetricCard(Card):
    def __init__(self, title: str, value: str, delta: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        title_label = QLabel(title)
        title_label.setObjectName("MutedText")
        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 28px; font-weight: 800; color: #1d4ed8;")
        delta_label = QLabel(delta)
        delta_label.setStyleSheet("font-size: 12px; color: #16a34a; font-weight: 600;")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(delta_label)


class PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str | None = None):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        layout.addWidget(title_label)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("MutedText")
            layout.addWidget(subtitle_label)


class UsageBarChart(Card):
    def __init__(self, data: list[UsageItem] | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.data = data or []
        self.setMinimumHeight(260)

    def set_data(self, data: list[UsageItem]) -> None:
        self.data = data
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(18, 16, -18, -16)
        painter.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        painter.setPen(QColor("#111827"))
        painter.drawText(rect.left(), rect.top() + 12, "Top 应用（按活跃时长）")
        if not self.data:
            painter.setFont(QFont("Microsoft YaHei", 10))
            painter.setPen(QColor("#6b7280"))
            painter.drawText(rect, Qt.AlignCenter, "暂无数据，请先运行 daily-report run")
            return
        max_seconds = max(item.seconds for item in self.data) or 1
        start_y, row_h, label_w, bar_h = rect.top() + 48, 34, 92, 11
        for i, item in enumerate(self.data):
            y = start_y + i * row_h
            painter.setFont(QFont("Microsoft YaHei", 9))
            painter.setPen(QColor("#111827"))
            painter.drawText(rect.left(), y + 11, item.name)
            bar_x = rect.left() + label_w
            bar_w = rect.width() - label_w - 86
            current_w = int(bar_w * item.seconds / max_seconds)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#eef2ff"))
            painter.drawRoundedRect(bar_x, y, bar_w, bar_h, 5, 5)
            painter.setBrush(QColor("#2563eb"))
            painter.drawRoundedRect(bar_x, y, current_w, bar_h, 5, 5)
            painter.setPen(QColor("#374151"))
            painter.drawText(bar_x + bar_w + 12, y + 11, fmt_seconds(item.seconds))


class TimelineWidget(Card):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.active_slots: set[int] = set()
        self.setMinimumHeight(148)

    def set_slots_from_sessions(self, sessions: list[dict]) -> None:
        # 简化实现：用 session 开始小时映射到 48 个半小时块。
        slots: set[int] = set()
        for row in sessions:
            start = str(row.get("start_time", ""))
            end = str(row.get("end_time", ""))
            try:
                sh, sm = int(start[11:13]), int(start[14:16])
                eh, em = int(end[11:13]), int(end[14:16])
            except Exception:
                continue
            a = min(47, max(0, sh * 2 + (1 if sm >= 30 else 0)))
            b = min(47, max(a, eh * 2 + (1 if em >= 30 else 0)))
            slots.update(range(a, b + 1))
        self.active_slots = slots
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(18, 16, -18, -16)
        painter.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        painter.setPen(QColor("#111827"))
        painter.drawText(rect.left(), rect.top() + 12, "今日时间分布（活跃 / 空闲）")
        blocks, gap = 48, 3
        block_w = max(4, int((rect.width() - gap * (blocks - 1)) / blocks))
        x, y, h = rect.left(), rect.top() + 45, 24
        for i in range(blocks):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#2563eb") if i in self.active_slots else QColor("#d1d5db"))
            painter.drawRoundedRect(x, y, block_w, h, 3, 3)
            x += block_w + gap
        painter.setFont(QFont("Microsoft YaHei", 8))
        painter.setPen(QColor("#6b7280"))
        for label, pos in [("00:00", 0), ("06:00", 12), ("12:00", 24), ("18:00", 36), ("24:00", 47)]:
            lx = rect.left() + int((rect.width() - 36) * pos / 47)
            painter.drawText(lx, y + h + 22, label)


def make_table(columns: list[str]) -> QTableWidget:
    table = QTableWidget(0, len(columns))
    table.setHorizontalHeaderLabels(columns)
    table.verticalHeader().setVisible(False)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setShowGrid(False)
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    table.setMinimumHeight(260)
    return table


def checkbox_item(checked: bool, key: str | None = None) -> QTableWidgetItem:
    item = QTableWidgetItem()
    item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
    item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
    if key:
        item.setData(Qt.UserRole, key)
    return item


def normal_item(text: str, *, sensitive: bool = False) -> QTableWidgetItem:
    item = QTableWidgetItem(text or "")
    item.setToolTip(text or "")
    if sensitive:
        item.setForeground(QBrush(QColor("#dc2626")))
    return item
