from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from daily_report.gui.data_provider import GuiDataProvider
from daily_report.gui.widgets import Card, PageHeader, SmartDateEdit, make_table, normal_item


class ReportsHistoryPage(QWidget):
    PAGE_SIZE = 60

    def __init__(self, provider: GuiDataProvider):
        super().__init__()
        self.provider = provider
        self.offset = 0
        self.total = 0
        self.loading = False
        self.rows_by_id: dict[int, dict] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(14)
        root.addWidget(PageHeader("历史日报", "查看、复制和检索已经生成并保存的 Markdown 日报"))

        filters = QHBoxLayout()
        self.date_filter = QCheckBox("按日期过滤")
        self.date_filter.stateChanged.connect(self.refresh)
        filters.addWidget(self.date_filter)
        self.date_edit = SmartDateEdit()
        self.date_edit.setDate(date.today())
        self.date_edit.dateChanged.connect(self.refresh)
        filters.addWidget(self.date_edit)
        filters.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索模型、摘要、Prompt 或日报正文")
        self.search.setFixedWidth(320)
        self.search.returnPressed.connect(self.refresh)
        filters.addWidget(self.search)
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh)
        filters.addWidget(refresh_btn)
        root.addLayout(filters)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        left_card = Card()
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(12, 12, 12, 12)
        self.table = make_table(["ID", "日期", "生成时间", "模型", "素材摘要"])
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.table.verticalScrollBar().valueChanged.connect(self.maybe_load_more)
        left_layout.addWidget(self.table)
        self.count_label = QLabel()
        self.count_label.setObjectName("MutedText")
        left_layout.addWidget(self.count_label)
        splitter.addWidget(left_card)

        right_card = Card()
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(16, 14, 16, 14)
        right_layout.setSpacing(10)
        title = QLabel("日报内容")
        title.setObjectName("SectionTitle")
        right_layout.addWidget(title)
        self.tabs = QTabWidget()
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.prompt_text = QTextEdit()
        self.prompt_text.setReadOnly(True)
        self.meta_text = QTextEdit()
        self.meta_text.setReadOnly(True)
        self.tabs.addTab(self.report_text, "Markdown")
        self.tabs.addTab(self.prompt_text, "Prompt")
        self.tabs.addTab(self.meta_text, "元数据")
        right_layout.addWidget(self.tabs, 1)
        actions = QHBoxLayout()
        actions.addStretch()
        copy_report = QPushButton("复制 Markdown")
        copy_report.clicked.connect(self.copy_report)
        actions.addWidget(copy_report)
        copy_prompt = QPushButton("复制 Prompt")
        copy_prompt.clicked.connect(self.copy_prompt)
        actions.addWidget(copy_prompt)
        right_layout.addLayout(actions)
        splitter.addWidget(right_card)
        splitter.setSizes([420, 680])
        root.addWidget(splitter, 1)

        self.refresh()

    def refresh(self) -> None:
        self.offset = 0
        self.rows_by_id.clear()
        self.table.setRowCount(0)
        self.clear_detail()
        self.total = self.provider.count_daily_reports(day=self.filter_day, keyword=self.search.text())
        self.load_more()

    def load_more(self) -> None:
        if self.loading or self.offset >= self.total:
            self.update_count()
            return
        self.loading = True
        rows = self.provider.list_daily_reports(
            day=self.filter_day,
            keyword=self.search.text(),
            limit=self.PAGE_SIZE,
            offset=self.offset,
        )
        for row in rows:
            self.append_row(row)
        self.offset += len(rows)
        self.loading = False
        self.update_count()

    def append_row(self, row: dict) -> None:
        report_id = int(row["id"])
        self.rows_by_id[report_id] = row
        r = self.table.rowCount()
        self.table.insertRow(r)
        id_item = normal_item(str(report_id))
        id_item.setData(Qt.UserRole, report_id)
        self.table.setItem(r, 0, id_item)
        self.table.setItem(r, 1, normal_item(row.get("date", "")))
        self.table.setItem(r, 2, normal_item(row.get("created_at", "")))
        self.table.setItem(r, 3, normal_item(row.get("model_name", "")))
        self.table.setItem(r, 4, normal_item(row.get("material_summary", "") or ""))

    def maybe_load_more(self, value: int) -> None:
        bar = self.table.verticalScrollBar()
        if value >= bar.maximum() - 2:
            self.load_more()

    def on_selection_changed(self) -> None:
        row = self.current_row()
        if not row:
            return
        self.report_text.setPlainText(row.get("report_markdown", ""))
        self.prompt_text.setPlainText(row.get("prompt_text", ""))
        self.meta_text.setPlainText(
            f"ID：{row.get('id')}\n"
            f"日期：{row.get('date')}\n"
            f"模型：{row.get('model_name')}\n"
            f"生成时间：{row.get('created_at')}\n\n"
            f"素材摘要：\n{row.get('material_summary') or '-'}\n\n"
            f"来源统计：\n{row.get('source_counts_json') or '{}'}"
        )

    def copy_report(self) -> None:
        row = self.current_row()
        if not row:
            QMessageBox.information(self, "未选择日报", "请先选择一条历史日报。")
            return
        QApplication.clipboard().setText(row.get("report_markdown", ""))
        QMessageBox.information(self, "已复制", "日报 Markdown 已复制。")

    def copy_prompt(self) -> None:
        row = self.current_row()
        if not row:
            QMessageBox.information(self, "未选择日报", "请先选择一条历史日报。")
            return
        QApplication.clipboard().setText(row.get("prompt_text", ""))
        QMessageBox.information(self, "已复制", "Prompt 已复制。")

    def current_row(self) -> dict | None:
        selected = self.table.selectedItems()
        if not selected:
            return None
        id_item = self.table.item(selected[0].row(), 0)
        if not id_item:
            return None
        report_id = id_item.data(Qt.UserRole)
        return self.rows_by_id.get(int(report_id)) if report_id is not None else None

    def clear_detail(self) -> None:
        self.report_text.setPlainText("选择左侧一条历史日报后，这里会显示 Markdown 正文。")
        self.prompt_text.clear()
        self.meta_text.clear()

    def update_count(self) -> None:
        self.count_label.setText(f"已加载 {self.table.rowCount()} / {self.total} 条")

    @property
    def filter_day(self) -> str | None:
        if not self.date_filter.isChecked():
            return None
        return self.date_edit.date().toString("yyyy-MM-dd")
