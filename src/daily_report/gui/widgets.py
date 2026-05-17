from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QDate, QPoint, QSize, Qt, QRectF, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QBrush, QFont
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget
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
        value_label.setStyleSheet("font-size: 21pt; font-weight: 800; color: #1d4ed8;")
        delta_label = QLabel(delta)
        delta_label.setStyleSheet("font-size: 9pt; color: #16a34a; font-weight: 600;")
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


class MaterialDatePopup(QFrame):
    date_selected = Signal(QDate)

    def __init__(self, selected_date: QDate, max_date: QDate, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("MaterialDatePopup")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.selected_date = selected_date
        self.max_date = max_date
        self.visible_month = QDate(selected_date.year(), selected_date.month(), 1)
        self.day_buttons: list[QPushButton] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(8)
        self.prev_btn = QToolButton()
        self.prev_btn.setObjectName("CalendarNavButton")
        self.prev_btn.setText("‹")
        self.prev_btn.clicked.connect(lambda: self.change_month(-1))
        header.addWidget(self.prev_btn)

        self.title = QLabel()
        self.title.setObjectName("CalendarTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.title, 1)

        self.next_btn = QToolButton()
        self.next_btn.setObjectName("CalendarNavButton")
        self.next_btn.setText("›")
        self.next_btn.clicked.connect(lambda: self.change_month(1))
        header.addWidget(self.next_btn)
        layout.addLayout(header)

        week_row = QGridLayout()
        week_row.setHorizontalSpacing(4)
        for col, name in enumerate(["一", "二", "三", "四", "五", "六", "日"]):
            label = QLabel(name)
            label.setObjectName("CalendarWeekday")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            week_row.addWidget(label, 0, col)
        layout.addLayout(week_row)

        self.days_grid = QGridLayout()
        self.days_grid.setHorizontalSpacing(4)
        self.days_grid.setVerticalSpacing(4)
        for row in range(6):
            for col in range(7):
                button = QPushButton()
                button.setObjectName("CalendarDayButton")
                button.setFixedSize(34, 30)
                button.clicked.connect(self.select_day)
                self.day_buttons.append(button)
                self.days_grid.addWidget(button, row, col)
        layout.addLayout(self.days_grid)

        footer = QHBoxLayout()
        footer.addStretch()
        today_btn = QPushButton("今天")
        today_btn.setObjectName("CalendarTodayButton")
        today_btn.clicked.connect(lambda: self.pick_date(QDate.currentDate()))
        footer.addWidget(today_btn)
        layout.addLayout(footer)

        self.refresh()

    def change_month(self, months: int) -> None:
        next_month = self.visible_month.addMonths(months)
        max_month = QDate(self.max_date.year(), self.max_date.month(), 1)
        if next_month > max_month:
            return
        self.visible_month = next_month
        self.refresh()

    def refresh(self) -> None:
        self.title.setText(self.visible_month.toString("yyyy年 M月"))
        max_month = QDate(self.max_date.year(), self.max_date.month(), 1)
        self.next_btn.setEnabled(self.visible_month < max_month)

        first = self.visible_month
        start_col = first.dayOfWeek() - 1
        days = first.daysInMonth()
        today = QDate.currentDate()

        for index, button in enumerate(self.day_buttons):
            day_number = index - start_col + 1
            valid = 1 <= day_number <= days
            if not valid:
                button.setText("")
                button.setEnabled(False)
                button.setProperty("today", False)
                button.setProperty("selected", False)
                self.repolish(button)
                continue

            date_value = QDate(first.year(), first.month(), day_number)
            button.setText(str(day_number))
            button.date_value = date_value
            button.setEnabled(date_value <= self.max_date)
            button.setProperty("today", date_value == today)
            button.setProperty("selected", date_value == self.selected_date)
            self.repolish(button)

    def select_day(self) -> None:
        button = self.sender()
        if not isinstance(button, QPushButton):
            return
        date_value = getattr(button, "date_value", None)
        if isinstance(date_value, QDate):
            self.pick_date(date_value)

    def pick_date(self, date_value: QDate) -> None:
        if date_value > self.max_date:
            return
        self.selected_date = date_value
        self.date_selected.emit(date_value)
        self.hide()

    @staticmethod
    def repolish(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)


class SmartDateEdit(QWidget):
    dateChanged = Signal(QDate)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._date = QDate.currentDate()
        self._maximum_date = QDate.currentDate()
        self.popup: MaterialDatePopup | None = None

        self.setObjectName("SmartDateEdit")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(220)
        self.setFixedHeight(32)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.line = QLineEdit()
        self.line.setReadOnly(True)
        self.line.setObjectName("SmartDateEditLine")
        layout.addWidget(self.line, 1)

        self.button = QToolButton()
        self.button.setObjectName("SmartDateEditButton")
        self.button.setText("")
        self.button.setIcon(QIcon(str(Path(__file__).with_name("assets") / "chevron-down.svg")))
        self.button.setIconSize(QSize(14, 14))
        self.button.setFixedSize(32, 32)
        self.button.clicked.connect(self.show_calendar)
        layout.addWidget(self.button)
        self.update_text()

    def date(self) -> QDate:
        return self._date

    def setDate(self, date_value: QDate) -> None:
        if date_value > self._maximum_date:
            date_value = self._maximum_date
        if date_value == self._date:
            self.update_text()
            return
        self._date = date_value
        self.update_text()
        self.dateChanged.emit(self._date)

    def setMaximumDate(self, date_value: QDate) -> None:
        self._maximum_date = date_value
        if self._date > self._maximum_date:
            self.setDate(self._maximum_date)

    def maximumDate(self) -> QDate:
        return self._maximum_date

    def update_text(self) -> None:
        self.line.setText(self._date.toString("yyyy-MM-dd"))

    def show_calendar(self) -> None:
        if self.popup is not None:
            self.popup.hide()
            self.popup.deleteLater()
        self.popup = MaterialDatePopup(self._date, self._maximum_date, self)
        self.popup.date_selected.connect(self.setDate)
        pos = self.mapToGlobal(QPoint(0, self.height() + 4))
        self.popup.move(pos)
        self.popup.show()


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
    table.verticalHeader().setDefaultSectionSize(38)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setWordWrap(False)
    table.setShowGrid(False)
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    table.horizontalHeader().setMinimumSectionSize(86)
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
