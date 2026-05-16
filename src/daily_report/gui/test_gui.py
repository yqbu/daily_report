"""
Daily Reporter PySide6 UI Prototype
-----------------------------------
一个单文件可运行的 PySide6 前端原型，用于复刻“智能日报生成工具”的桌面端界面效果。

安装: 
    pip install PySide6

运行: 
    python daily_reporter_pyside6_mockup.py

说明: 
    1. 当前版本使用模拟数据，不依赖 SQLite、DeepSeek API 或后台采集服务。
    2. 后续可将 MockDataProvider 替换为 repository/service 层。
    3. 为了减少依赖，图表使用 QWidget 自绘，没有使用 QtCharts。
"""

from __future__ import annotations

import os
import sys
import pathlib
from dataclasses import dataclass
from datetime import date
from typing import Callable, Iterable

import PySide6
pyside6_dir = pathlib.Path(PySide6.__file__).parent
os.add_dll_directory(str(pyside6_dir))

from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


# -----------------------------------------------------------------------------
# Mock data
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class AppUsage:
    name: str
    seconds: int
    percent: int


@dataclass(frozen=True)
class ActivityRecord:
    selected: bool
    time: str
    source_type: str
    preview: str
    source: str
    sensitive: bool


@dataclass(frozen=True)
class AppSessionRecord:
    selected: bool
    start: str
    end: str
    app: str
    process: str
    title: str
    duration: str
    active: bool


class MockDataProvider:
    """临时模拟数据源。

    后续接入真实数据时，可以将这些方法替换为 SQLite repository 查询: 
        - list_top_apps(date)
        - list_activity_records(date)
        - list_app_sessions(date)
        - build_report_summary(date)
    """

    @staticmethod
    def top_apps() -> list[AppUsage]:
        return [
            AppUsage("VSCode", 7800, 37),
            AppUsage("Edge", 5700, 27),
            AppUsage("WeCom", 2520, 12),
            AppUsage("PyCharm", 2100, 10),
            AppUsage("Terminal", 1860, 9),
        ]

    @staticmethod
    def activity_records() -> list[ActivityRecord]:
        return [
            ActivityRecord(True, "09:31:22", "应用记录", "VSCode - main.py", "VSCode", False),
            ActivityRecord(True, "10:12:45", "AI 提问", "Edge 扩展如何捕获 ChatGPT 的问题发送事件", "ChatGPT", False),
            ActivityRecord(False, "10:55:11", "剪贴板", "sk-xxxxxxxxxxxxxxxxxxxxxxxx", "剪贴板", True),
            ActivityRecord(True, "11:20:33", "浏览记录", "PySide6 QSplitter 使用示例和文档", "Edge", False),
            ActivityRecord(True, "14:08:22", "AI 提问", "前台应用采集如何组织 collector 与 manager", "DeepSeek", False),
            ActivityRecord(True, "15:16:05", "应用记录", "PyCharm - daily_reporter 项目", "PyCharm", False),
        ]

    @staticmethod
    def app_sessions() -> list[AppSessionRecord]:
        return [
            AppSessionRecord(True, "09:00:12", "09:42:33", "VSCode", "Code.exe", "daily_reporter/main.py - Visual Studio Code", "42m 21s", True),
            AppSessionRecord(True, "09:42:33", "10:03:15", "Edge", "msedge.exe", "ChatGPT - 智能日报", "20m 42s", True),
            AppSessionRecord(False, "10:03:15", "10:16:08", "Explorer", "explorer.exe", "Downloads", "12m 53s", False),
            AppSessionRecord(True, "10:16:08", "11:20:44", "VSCode", "Code.exe", "app_session_collector.py - Visual Studio Code", "1h 04m", True),
            AppSessionRecord(True, "11:20:44", "11:32:10", "WeCom", "WeCom.exe", "项目组 - 工作群", "11m 26s", True),
        ]

    @staticmethod
    def report_markdown() -> str:
        return """# 今日日报（2026-05-13）

## 一、今日工作内容

1. 完成前台应用采集模块的界面展示与数据确认入口设计。
2. 实现 Edge 历史记录读取与搜索关键词提取方案梳理。
3. 开发 AI 提问捕获的 Edge 扩展原型设计，明确只记录用户问题。
4. 完成素材汇总与日报生成页面的初步实现。

## 二、问题与处理

1. Edge 历史数据库在使用时可能被占用，已通过复制副本读取规避。
2. 剪贴板内容敏感性较高，已增加敏感识别和人工确认流程。

## 三、明日计划

1. 将 GUI 中的模拟数据替换为 SQLite 查询结果。
2. 接入 DeepSeek API，完成 Markdown 日报生成闭环。
3. 增加 YASB status.json 输出和快捷入口。"""

    @staticmethod
    def report_summary() -> str:
        return """活跃时间: 5h 42m

Top 应用: 
- VSCode 2h 10m
- Edge 1h 35m
- WeCom 42m
- PyCharm 35m

AI 提问: 18 条
浏览记录: 64 条
剪贴板: 32 条

重点素材: 
- 前台应用采集 collector / manager 组织方式
- Edge 历史记录读取与噪声过滤
- ChatGPT / DeepSeek 提问记录 Edge 扩展
- YASB CustomWidget 状态联动"""


# -----------------------------------------------------------------------------
# Theme
# -----------------------------------------------------------------------------


APP_QSS = """
* {
    font-family: "Microsoft YaHei", "Segoe UI", Arial;
    font-size: 13px;
    color: #1f2937;
}

QMainWindow {
    background: #f5f7fb;
}

#RootFrame {
    background: #f5f7fb;
}

#Sidebar {
    background: #ffffff;
    border-right: 1px solid #e5e7eb;
}

#SidebarTitle {
    font-size: 14px;
    font-weight: 700;
    color: #111827;
}

#SidebarSubtitle {
    color: #6b7280;
    font-size: 11px;
}

QPushButton[nav="true"] {
    border: none;
    text-align: left;
    padding: 10px 14px;
    border-radius: 8px;
    background: transparent;
    color: #374151;
}

QPushButton[nav="true"]:hover {
    background: #eff6ff;
    color: #1d4ed8;
}

QPushButton[nav="true"][active="true"] {
    background: #3b82f6;
    color: white;
    font-weight: 600;
}

QPushButton {
    border: 1px solid #d1d5db;
    background: #ffffff;
    border-radius: 7px;
    padding: 8px 14px;
}

QPushButton:hover {
    background: #f3f4f6;
}

QPushButton[primary="true"] {
    border: 1px solid #2563eb;
    background: #2563eb;
    color: white;
    font-weight: 600;
}

QPushButton[primary="true"]:hover {
    background: #1d4ed8;
}

QFrame[card="true"], QGroupBox {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
}

QGroupBox {
    margin-top: 12px;
    padding: 14px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 5px;
}

QLineEdit, QComboBox, QDateEdit, QSpinBox, QTextEdit, QTextBrowser {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 7px;
    padding: 7px 9px;
}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QTextEdit:focus {
    border: 1px solid #3b82f6;
}

QTableWidget {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    gridline-color: #eef2f7;
    selection-background-color: #eff6ff;
    selection-color: #111827;
}

QHeaderView::section {
    background: #f9fafb;
    border: none;
    border-bottom: 1px solid #e5e7eb;
    padding: 8px;
    font-weight: 600;
    color: #374151;
}

QTableWidget::item {
    padding: 8px;
}

#PageTitle {
    font-size: 24px;
    font-weight: 800;
    color: #111827;
}

#SectionTitle {
    font-size: 15px;
    font-weight: 700;
    color: #111827;
}

#MutedText {
    color: #6b7280;
}

#StatusGood {
    color: #16a34a;
    font-weight: 600;
}

#SensitiveText {
    color: #dc2626;
    font-weight: 600;
}
"""


# -----------------------------------------------------------------------------
# Shared widgets
# -----------------------------------------------------------------------------


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
    def __init__(self, data: list[AppUsage], parent: QWidget | None = None):
        super().__init__(parent)
        self.data = data
        self.setMinimumHeight(260)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(18, 16, -18, -16)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        painter.setFont(title_font)
        painter.setPen(QColor("#111827"))
        painter.drawText(rect.left(), rect.top() + 12, "Top 应用（按使用时长）")

        if not self.data:
            return

        max_seconds = max(item.seconds for item in self.data)
        start_y = rect.top() + 48
        row_h = 34
        label_w = 92
        bar_h = 11
        bar_color = QColor("#2563eb")
        bg_color = QColor("#eef2ff")

        painter.setFont(QFont("Microsoft YaHei", 9))
        for i, item in enumerate(self.data):
            y = start_y + i * row_h
            painter.setPen(QColor("#111827"))
            painter.drawText(rect.left(), y + 11, item.name)

            bar_x = rect.left() + label_w
            bar_w = rect.width() - label_w - 80
            current_w = int(bar_w * item.seconds / max_seconds)

            painter.setPen(Qt.NoPen)
            painter.setBrush(bg_color)
            painter.drawRoundedRect(bar_x, y, bar_w, bar_h, 5, 5)
            painter.setBrush(bar_color)
            painter.drawRoundedRect(bar_x, y, current_w, bar_h, 5, 5)

            painter.setPen(QColor("#374151"))
            painter.drawText(bar_x + bar_w + 12, y + 11, seconds_to_label(item.seconds))


class TimelineWidget(Card):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumHeight(148)
        self.active_slots = {3, 4, 8, 9, 10, 13, 14, 15, 17, 18, 23, 30, 31, 32, 34, 35, 40, 41}

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(18, 16, -18, -16)
        painter.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        painter.setPen(QColor("#111827"))
        painter.drawText(rect.left(), rect.top() + 12, "今日时间分布（活跃 / 空闲）")

        blocks = 48
        gap = 3
        block_w = max(4, int((rect.width() - gap * (blocks - 1)) / blocks))
        x = rect.left()
        y = rect.top() + 45
        h = 24

        for i in range(blocks):
            color = QColor("#2563eb") if i in self.active_slots else QColor("#d1d5db")
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(x, y, block_w, h, 3, 3)
            x += block_w + gap

        painter.setFont(QFont("Microsoft YaHei", 8))
        painter.setPen(QColor("#6b7280"))
        for label, pos in [("00:00", 0), ("06:00", 12), ("12:00", 24), ("18:00", 36), ("24:00", 47)]:
            lx = rect.left() + int((rect.width() - 36) * pos / 47)
            painter.drawText(lx, y + h + 22, label)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#2563eb"))
        painter.drawRoundedRect(rect.left(), y + h + 38, 20, 10, 4, 4)
        painter.setPen(QColor("#374151"))
        painter.drawText(rect.left() + 28, y + h + 47, "活跃")

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#d1d5db"))
        painter.drawRoundedRect(rect.left() + 88, y + h + 38, 20, 10, 4, 4)
        painter.setPen(QColor("#374151"))
        painter.drawText(rect.left() + 116, y + h + 47, "空闲")


class DonutChart(Card):
    def __init__(self, data: list[AppUsage], parent: QWidget | None = None):
        super().__init__(parent)
        self.data = data
        self.setMinimumHeight(260)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(18, 16, -18, -16)
        painter.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        painter.setPen(QColor("#111827"))
        painter.drawText(rect.left(), rect.top() + 12, "今日应用分布")

        chart_rect = QRectF(rect.left() + 22, rect.top() + 54, 150, 150)
        colors = ["#2563eb", "#60a5fa", "#93c5fd", "#9ca3af", "#cbd5e1"]
        total = sum(item.seconds for item in self.data)
        start = 90 * 16

        for idx, item in enumerate(self.data):
            span = int(-360 * 16 * item.seconds / total)
            painter.setPen(QPen(QColor(colors[idx % len(colors)]), 26, Qt.SolidLine, Qt.RoundCap))
            painter.drawArc(chart_rect, start, span)
            start += span

        painter.setPen(QColor("#111827"))
        painter.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        painter.drawText(chart_rect, Qt.AlignCenter, "总计\n6h 32m")

        legend_x = rect.left() + 205
        legend_y = rect.top() + 58
        painter.setFont(QFont("Microsoft YaHei", 9))
        for idx, item in enumerate(self.data):
            y = legend_y + idx * 28
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(colors[idx % len(colors)]))
            painter.drawRoundedRect(legend_x, y, 12, 12, 3, 3)
            painter.setPen(QColor("#374151"))
            painter.drawText(
                legend_x + 20,
                y + 11,
                f"{item.name}    {seconds_to_label(item.seconds)} ({item.percent}%)",
            )


class VerticalBarChart(Card):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.values = [0, 5, 8, 22, 55, 70, 45, 62, 30, 15, 52, 68, 40, 12]
        self.setMinimumHeight(260)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(18, 16, -18, -20)
        painter.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        painter.setPen(QColor("#111827"))
        painter.drawText(rect.left(), rect.top() + 12, "活跃时段分布")

        chart = rect.adjusted(4, 46, -8, -24)
        painter.setPen(QPen(QColor("#e5e7eb"), 1))
        for i in range(4):
            y = chart.top() + i * chart.height() / 3
            painter.drawLine(chart.left(), int(y), chart.right(), int(y))

        n = len(self.values)
        gap = 8
        bar_w = max(6, int((chart.width() - gap * (n - 1)) / n))
        max_value = max(self.values)
        x = chart.left()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#2563eb"))
        for value in self.values:
            h = int(chart.height() * value / max_value)
            painter.drawRoundedRect(x, chart.bottom() - h, bar_w, h, 4, 4)
            x += bar_w + gap

        painter.setFont(QFont("Microsoft YaHei", 8))
        painter.setPen(QColor("#6b7280"))
        for text, offset in [("0", 0), ("6", 3), ("12", 7), ("18", 10), ("24", 13)]:
            x = chart.left() + int(offset * (bar_w + gap))
            painter.drawText(x, chart.bottom() + 18, text)


class SettingsGroup(QGroupBox):
    def __init__(self, title: str):
        super().__init__(title)
        self.form = QGridLayout(self)
        self.form.setContentsMargins(12, 18, 12, 12)
        self.form.setHorizontalSpacing(12)
        self.form.setVerticalSpacing(10)


# -----------------------------------------------------------------------------
# Table helpers
# -----------------------------------------------------------------------------


def make_table(columns: list[str]) -> QTableWidget:
    table = QTableWidget(0, len(columns))
    table.setHorizontalHeaderLabels(columns)
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(False)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setShowGrid(False)
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    table.setMinimumHeight(260)
    return table


def checkbox_item(checked: bool) -> QTableWidgetItem:
    item = QTableWidgetItem()
    item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
    item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
    return item


def normal_item(text: str, *, sensitive: bool = False) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setToolTip(text)
    if sensitive:
        item.setForeground(QBrush(QColor("#dc2626")))
    return item


def fill_activity_table(table: QTableWidget, rows: Iterable[ActivityRecord]) -> None:
    table.setRowCount(0)
    for row in rows:
        r = table.rowCount()
        table.insertRow(r)
        table.setItem(r, 0, checkbox_item(row.selected))
        table.setItem(r, 1, normal_item(row.time))
        table.setItem(r, 2, normal_item(row.source_type))
        table.setItem(r, 3, normal_item(row.preview, sensitive=row.sensitive))
        table.setItem(r, 4, normal_item(row.source))
        table.setItem(r, 5, normal_item("是" if row.sensitive else "否", sensitive=row.sensitive))

    table.resizeRowsToContents()


def fill_app_session_table(table: QTableWidget, rows: Iterable[AppSessionRecord]) -> None:
    table.setRowCount(0)
    for row in rows:
        r = table.rowCount()
        table.insertRow(r)
        table.setItem(r, 0, checkbox_item(row.selected))
        table.setItem(r, 1, normal_item(row.start))
        table.setItem(r, 2, normal_item(row.end))
        table.setItem(r, 3, normal_item(row.app))
        table.setItem(r, 4, normal_item(row.process))
        table.setItem(r, 5, normal_item(row.title))
        table.setItem(r, 6, normal_item(row.duration))
        table.setItem(r, 7, normal_item("是" if row.active else "否"))

    table.resizeRowsToContents()


def seconds_to_label(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


# -----------------------------------------------------------------------------
# Pages
# -----------------------------------------------------------------------------


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(16)

        root.addWidget(PageHeader("2026年5月13日 星期三", "今日工作数据总览"))

        metric_row = QHBoxLayout()
        metric_row.setSpacing(12)
        metric_row.addWidget(MetricCard("今日活跃时间", "5h 42m", "较昨日 +12%"))
        metric_row.addWidget(MetricCard("应用记录", "128 条", "较昨日 +8%"))
        metric_row.addWidget(MetricCard("剪贴板", "32 条", "较昨日 -5%"))
        metric_row.addWidget(MetricCard("浏览记录", "64 条", "较昨日 +15%"))
        metric_row.addWidget(MetricCard("AI 提问", "18 条", "较昨日 +20%"))
        root.addLayout(metric_row)

        middle = QHBoxLayout()
        middle.setSpacing(14)
        middle.addWidget(UsageBarChart(MockDataProvider.top_apps()), 5)

        right_col = QVBoxLayout()
        right_col.setSpacing(14)
        right_col.addWidget(TimelineWidget())

        recent = Card()
        recent_layout = QVBoxLayout(recent)
        recent_layout.setContentsMargins(18, 16, 18, 16)
        recent_layout.setSpacing(10)
        recent_title = QLabel("最近活动")
        recent_title.setObjectName("SectionTitle")
        recent_layout.addWidget(recent_title)
        for text in [
            "22:11    ChatGPT    YASB 自定义 Widget 如何渲染和刷新",
            "22:06    Edge       PySide6 QTableView example",
            "21:58    VSCode     app_session_collector.py",
            "20:42    剪贴板      class ForegroundCollector 片段",
            "21:30    WeCom      项目进度同步",
        ]:
            label = QLabel(text)
            label.setObjectName("MutedText")
            recent_layout.addWidget(label)
        right_col.addWidget(recent)
        middle.addLayout(right_col, 5)
        root.addLayout(middle)

        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(QPushButton("刷新数据"))
        bottom.addWidget(QPushButton("暂停采集"))
        generate = QPushButton("生成今日日报")
        generate.setProperty("primary", True)
        bottom.addWidget(generate)
        root.addLayout(bottom)


class MaterialReviewPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(14)

        root.addWidget(PageHeader("素材确认中心", "勾选需要进入日报生成的素材，疑似敏感内容默认不选中"))

        filters = QHBoxLayout()
        filters.addWidget(QLabel("数据类型: "))
        type_combo = QComboBox()
        type_combo.addItems(["全部", "应用记录", "剪贴板", "浏览记录", "AI 提问"])
        filters.addWidget(type_combo)
        sensitive_check = QCheckBox("隐藏疑似敏感内容")
        filters.addWidget(sensitive_check)
        filters.addStretch()
        search = QLineEdit()
        search.setPlaceholderText("搜索内容、来源或关键词")
        search.setFixedWidth(260)
        filters.addWidget(search)
        root.addLayout(filters)

        content = QHBoxLayout()
        left = QVBoxLayout()
        self.table = make_table(["选中", "时间", "类型", "内容预览", "来源", "敏感"])
        fill_activity_table(self.table, MockDataProvider.activity_records())
        left.addWidget(self.table)

        detail = Card()
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(16, 14, 16, 14)
        detail_layout.setSpacing(7)
        detail_title = QLabel("详情预览")
        detail_title.setObjectName("SectionTitle")
        detail_layout.addWidget(detail_title)
        detail_text = QLabel(
            "类型: AI 提问\n"
            "平台: ChatGPT\n"
            "时间: 2026-05-13 14:08:22\n"
            "URL: https://chatgpt.com/c/abc123...\n"
            "内容: 前台应用采集如何组织 collector、manager 与 storage？"
        )
        detail_text.setWordWrap(True)
        detail_layout.addWidget(detail_text)
        left.addWidget(detail)

        content.addLayout(left, 8)

        stats = Card()
        stats.setFixedWidth(220)
        stats_layout = QVBoxLayout(stats)
        stats_layout.setContentsMargins(18, 16, 18, 16)
        stats_layout.setSpacing(12)
        stats_title = QLabel("统计信息")
        stats_title.setObjectName("SectionTitle")
        stats_layout.addWidget(stats_title)
        for k, v in [("已选中", "24 条"), ("总数", "242 条"), ("疑似敏感", "18 条"), ("未选中", "218 条")]:
            row = QHBoxLayout()
            row.addWidget(QLabel(k))
            row.addStretch()
            value = QLabel(v)
            value.setStyleSheet("font-weight: 700;")
            row.addWidget(value)
            stats_layout.addLayout(row)
        stats_layout.addStretch()
        content.addWidget(stats)

        root.addLayout(content)

        buttons = QHBoxLayout()
        buttons.addWidget(QPushButton("全选可用项"))
        buttons.addWidget(QPushButton("取消全选"))
        buttons.addWidget(QPushButton("忽略选中"))
        buttons.addStretch()
        go_report = QPushButton("进入日报生成")
        go_report.setProperty("primary", True)
        buttons.addWidget(go_report)
        root.addLayout(buttons)


class AppSessionsPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(14)

        root.addWidget(PageHeader("应用使用记录", "查看前台窗口 session、使用时长和活跃状态"))

        filters = QHBoxLayout()
        filters.addWidget(QLabel("日期: "))
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDate(date.today())
        filters.addWidget(date_edit)
        filters.addWidget(QLabel("应用: "))
        app_combo = QComboBox()
        app_combo.addItems(["全部", "VSCode", "Edge", "WeCom", "PyCharm", "Terminal"])
        filters.addWidget(app_combo)
        filters.addStretch()
        filters.addWidget(QPushButton("刷新"))
        root.addLayout(filters)

        charts = QHBoxLayout()
        charts.setSpacing(14)
        charts.addWidget(DonutChart(MockDataProvider.top_apps()), 5)
        charts.addWidget(VerticalBarChart(), 5)
        root.addLayout(charts)

        table = make_table(["选中", "开始时间", "结束时间", "应用名称", "进程名", "窗口标题", "时长", "活跃"])
        fill_app_session_table(table, MockDataProvider.app_sessions())
        root.addWidget(table)


class ReportGeneratePage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.addWidget(PageHeader("日报生成", "汇总选中素材，生成结构化 Markdown 日报"), 1)
        header_row.addWidget(QLabel("模板: "))
        template_combo = QComboBox()
        template_combo.addItems(["标准工作日报", "研发进展日报", "问题跟踪日报"])
        template_combo.setFixedWidth(180)
        header_row.addWidget(template_combo)
        manage_button = QPushButton("管理模板")
        header_row.addWidget(manage_button)
        root.addLayout(header_row)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        summary_card = Card()
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(16, 14, 16, 14)
        summary_layout.setSpacing(10)
        summary_title = QLabel("选中素材摘要")
        summary_title.setObjectName("SectionTitle")
        summary_layout.addWidget(summary_title)
        summary = QTextBrowser()
        summary.setPlainText(MockDataProvider.report_summary())
        summary_layout.addWidget(summary)
        summary_layout.addWidget(QPushButton("重新汇总素材"))
        splitter.addWidget(summary_card)

        preview_card = Card()
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(16, 14, 16, 14)
        preview_layout.setSpacing(10)
        preview_title = QLabel("Markdown 预览")
        preview_title.setObjectName("SectionTitle")
        preview_layout.addWidget(preview_title)
        preview = QTextEdit()
        preview.setPlainText(MockDataProvider.report_markdown())
        preview_layout.addWidget(preview)
        splitter.addWidget(preview_card)
        splitter.setSizes([360, 620])
        root.addWidget(splitter, 1)

        prompt_group = QGroupBox("Prompt 预览")
        prompt_layout = QVBoxLayout(prompt_group)
        prompt = QTextEdit()
        prompt.setFixedHeight(92)
        prompt.setPlainText(
            "请根据以下工作素材，生成一份结构化的中文 Markdown 日报，要求条理清晰，重点突出。\n"
            "[活跃时间] 5h42m\n"
            "[Top 应用] VSCode(2h10m), Edge(1h35m), WeCom(42m), PyCharm(35m)\n"
            "[AI 提问] 18 条"
        )
        prompt_layout.addWidget(prompt)
        root.addWidget(prompt_group)

        buttons = QHBoxLayout()
        generate = QPushButton("生成日报")
        generate.setProperty("primary", True)
        buttons.addWidget(generate)
        buttons.addWidget(QPushButton("重新生成"))
        buttons.addStretch()
        buttons.addWidget(QPushButton("复制 Markdown"))
        buttons.addWidget(QPushButton("导出 .md"))
        root.addLayout(buttons)


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(14)

        root.addWidget(PageHeader("设置", "配置采集服务、隐私规则、模型参数与 YASB 联动"))

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        collector = SettingsGroup("采集设置")
        for i, label in enumerate(["前台应用采集", "剪贴板采集", "Edge 历史采集", "AI 提问捕获"]):
            cb = QCheckBox(label)
            cb.setChecked(True)
            collector.form.addWidget(cb, i, 0, 1, 2)
        collector.form.addWidget(QLabel("前台轮询间隔"), 4, 0)
        spin = QSpinBox()
        spin.setRange(1, 60)
        spin.setValue(2)
        spin.setSuffix(" 秒")
        collector.form.addWidget(spin, 4, 1)
        collector.form.addWidget(QLabel("Edge 同步间隔"), 5, 0)
        edge_spin = QSpinBox()
        edge_spin.setRange(1, 60)
        edge_spin.setValue(3)
        edge_spin.setSuffix(" 分钟")
        collector.form.addWidget(edge_spin, 5, 1)
        grid.addWidget(collector, 0, 0)

        privacy = SettingsGroup("隐私设置")
        for i, label in enumerate(["疑似敏感内容默认不选中", "剪贴板只显示预览", "发送模型前必须人工确认"]):
            cb = QCheckBox(label)
            cb.setChecked(True)
            privacy.form.addWidget(cb, i, 0, 1, 2)
        privacy.form.addWidget(QLabel("敏感关键词"), 3, 0)
        keywords = QTextEdit()
        keywords.setFixedHeight(75)
        keywords.setPlainText("password, token, sk-, api_key, 密码, 认证")
        privacy.form.addWidget(keywords, 3, 1)
        grid.addWidget(privacy, 0, 1)

        model = SettingsGroup("模型设置")
        model.form.addWidget(QLabel("DeepSeek API Key"), 0, 0)
        api_key = QLineEdit()
        api_key.setEchoMode(QLineEdit.Password)
        api_key.setText("sk-xxxxxxxxxxxxxxxxxxxxxxxx")
        model.form.addWidget(api_key, 0, 1)
        model.form.addWidget(QLabel("模型名称"), 1, 0)
        model_combo = QComboBox()
        model_combo.addItems(["deepseek-chat", "deepseek-reasoner"])
        model.form.addWidget(model_combo, 1, 1)
        model.form.addWidget(QLabel("最大 Prompt 长度"), 2, 0)
        prompt_len = QSpinBox()
        prompt_len.setRange(1000, 100000)
        prompt_len.setSingleStep(1000)
        prompt_len.setValue(12000)
        model.form.addWidget(prompt_len, 2, 1)
        grid.addWidget(model, 0, 2)

        yasb = SettingsGroup("YASB 联动设置")
        yasb.form.addWidget(QLabel("状态输出文件"), 0, 0)
        status_path = QLineEdit("D:/YASB/status.json")
        yasb.form.addWidget(status_path, 0, 1)
        yasb.form.addWidget(QPushButton("浏览"), 0, 2)
        yasb.form.addWidget(QLabel("CLI 状态命令"), 1, 0)
        command = QLineEdit("daily-reporter status --json")
        yasb.form.addWidget(command, 1, 1)
        yasb.form.addWidget(QPushButton("复制"), 1, 2)
        yasb.form.addWidget(QPushButton("测试输出"), 2, 0)
        yasb.form.addWidget(QPushButton("复制 YASB 配置片段"), 2, 1, 1, 2)
        grid.addWidget(yasb, 1, 0, 1, 2)

        other = SettingsGroup("其他设置")
        other.form.addWidget(QLabel("数据保留天数"), 0, 0)
        keep_days = QSpinBox()
        keep_days.setRange(7, 3650)
        keep_days.setValue(90)
        keep_days.setSuffix(" 天")
        other.form.addWidget(keep_days, 0, 1)
        other.form.addWidget(QLabel("日志级别"), 1, 0)
        log_level = QComboBox()
        log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        log_level.setCurrentText("INFO")
        other.form.addWidget(log_level, 1, 1)
        other.form.addWidget(QLabel("日志目录"), 2, 0)
        log_path = QLineEdit("D:/DailyReporter/logs")
        other.form.addWidget(log_path, 2, 1)
        other.form.addWidget(QPushButton("浏览"), 2, 2)
        grid.addWidget(other, 1, 2)

        root.addLayout(grid)
        root.addStretch()

        buttons = QHBoxLayout()
        save = QPushButton("保存设置")
        save.setProperty("primary", True)
        buttons.addWidget(save)
        buttons.addStretch()
        buttons.addWidget(QPushButton("重启后台服务"))
        buttons.addWidget(QPushButton("打开日志目录"))
        root.addLayout(buttons)


class PlaceholderPage(QWidget):
    def __init__(self, title: str, description: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 24)
        layout.addWidget(PageHeader(title, description))
        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        label = QLabel("该页面可以复用素材确认中心的表格样式，接入对应 repository 后展示真实数据。")
        label.setObjectName("MutedText")
        card_layout.addWidget(label)
        layout.addWidget(card)
        layout.addStretch()


# -----------------------------------------------------------------------------
# Main window
# -----------------------------------------------------------------------------


class SidebarButton(QPushButton):
    def __init__(self, text: str, index: int, on_click: Callable[[int], None]):
        super().__init__(text)
        self.index = index
        self.setCheckable(True)
        self.setProperty("nav", True)
        self.clicked.connect(lambda: on_click(self.index))
        self.setMinimumHeight(40)

    def set_active(self, active: bool) -> None:
        self.setChecked(active)
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Daily Reporter - 智能日报生成工具")
        self.resize(1280, 780)
        self.setMinimumSize(1080, 680)

        root = QFrame()
        root.setObjectName("RootFrame")
        self.setCentralWidget(root)

        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = self._create_sidebar()
        layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.stack.addWidget(DashboardPage())
        self.stack.addWidget(AppSessionsPage())
        self.stack.addWidget(PlaceholderPage("剪贴板", "查看复制文本记录，支持脱敏、预览和人工勾选"))
        self.stack.addWidget(PlaceholderPage("浏览记录", "查看 Edge 历史记录、搜索关键词和噪声过滤结果"))
        self.stack.addWidget(PlaceholderPage("AI 提问", "查看 ChatGPT / DeepSeek 用户提问记录"))
        self.stack.addWidget(MaterialReviewPage())
        self.stack.addWidget(ReportGeneratePage())
        self.stack.addWidget(PlaceholderPage("历史日报", "查看、复制和导出历史生成的 Markdown 日报"))
        self.stack.addWidget(SettingsPage())
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
        items = [
            "今日总览",
            "应用记录",
            "剪贴板",
            "浏览记录",
            "AI 提问",
            "素材确认",
            "日报生成",
            "历史日报",
            "设置",
        ]
        group = QButtonGroup(sidebar)
        group.setExclusive(True)
        for index, text in enumerate(items):
            button = SidebarButton(text, index, self.set_page)
            group.addButton(button)
            self.nav_buttons.append(button)
            layout.addWidget(button)

        layout.addStretch()
        status = QLabel("采集服务: 运行中")
        status.setObjectName("StatusGood")
        version = QLabel("版本: v0.1.0")
        version.setObjectName("MutedText")
        layout.addWidget(status)
        layout.addWidget(version)
        return sidebar

    def set_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for button in self.nav_buttons:
            button.set_active(button.index == index)


# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
