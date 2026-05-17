from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from daily_report.config.local_settings import load_local_settings
from daily_report.gui.data_provider import GuiDataProvider
from daily_report.gui.widgets import Card, PageHeader, checkbox_item, make_table, normal_item


class ClipboardPage(QWidget):
    PAGE_SIZE = 100

    def __init__(self, provider: GuiDataProvider):
        super().__init__()
        self.provider = provider
        self.offset = 0
        self.total = 0
        self.loading = False
        self.rows_by_key: dict[str, dict] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(14)
        root.addWidget(PageHeader("剪贴板记录", "查看复制文本记录，支持脱敏预览、人工勾选和详情查看"))

        filters = QHBoxLayout()
        filters.addWidget(QLabel("日期："))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(date.today())
        self.date_edit.dateChanged.connect(self.refresh)
        filters.addWidget(self.date_edit)

        self.hide_sensitive = QCheckBox("隐藏敏感内容")
        self.hide_sensitive.setChecked(load_local_settings().privacy.hide_sensitive_by_default)
        self.hide_sensitive.stateChanged.connect(self.refresh)
        filters.addWidget(self.hide_sensitive)

        filters.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索内容、预览或敏感原因")
        self.search.setFixedWidth(280)
        self.search.returnPressed.connect(self.refresh)
        filters.addWidget(self.search)

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh)
        filters.addWidget(refresh_btn)
        root.addLayout(filters)

        self.table = make_table(["选中", "首次出现", "最近出现", "内容预览", "字符数", "复制次数", "敏感", "原因"])
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.table.verticalScrollBar().valueChanged.connect(self.maybe_load_more)
        root.addWidget(self.table, 1)

        detail_card = Card()
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(16, 14, 16, 14)
        detail_layout.setSpacing(10)
        detail_title = QLabel("详情")
        detail_title.setObjectName("SectionTitle")
        detail_layout.addWidget(detail_title)
        self.detail = QTextBrowser()
        self.detail.setMinimumHeight(120)
        detail_layout.addWidget(self.detail)
        root.addWidget(detail_card)

        actions = QHBoxLayout()
        self.count_label = QLabel()
        self.count_label.setObjectName("MutedText")
        actions.addWidget(self.count_label)
        actions.addStretch()
        copy_btn = QPushButton("复制内容")
        copy_btn.clicked.connect(self.copy_selected_content)
        actions.addWidget(copy_btn)
        delete_btn = QPushButton("删除记录")
        delete_btn.setProperty("danger", True)
        delete_btn.clicked.connect(self.delete_selected)
        actions.addWidget(delete_btn)
        root.addLayout(actions)

        self.refresh()

    def refresh(self) -> None:
        self.offset = 0
        self.rows_by_key.clear()
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self.table.blockSignals(False)
        self.detail.setPlainText("选择一条剪贴板记录后，这里会显示完整内容和敏感性判断。")
        self.total = self.provider.count_clipboard_entries(
            self.day,
            keyword=self.search.text(),
            hide_sensitive=self.hide_sensitive.isChecked(),
        )
        self.load_more()

    def load_more(self) -> None:
        if self.loading or self.offset >= self.total:
            self.update_count()
            return
        self.loading = True
        rows = self.provider.list_clipboard_entries(
            self.day,
            keyword=self.search.text(),
            hide_sensitive=self.hide_sensitive.isChecked(),
            limit=self.PAGE_SIZE,
            offset=self.offset,
        )
        self.table.blockSignals(True)
        for row in rows:
            self.append_row(row)
        self.table.blockSignals(False)
        self.offset += len(rows)
        self.loading = False
        self.update_count()

    def append_row(self, row: dict) -> None:
        key = f"clipboard_entries:{row['id']}"
        self.rows_by_key[key] = row
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, checkbox_item(bool(row.get("is_selected")), key))
        self.table.setItem(r, 1, normal_item(self.time_part(row.get("first_seen_at"))))
        self.table.setItem(r, 2, normal_item(self.time_part(row.get("last_seen_at"))))
        self.table.setItem(r, 3, normal_item(row.get("content_preview", ""), sensitive=bool(row.get("is_sensitive"))))
        self.table.setItem(r, 4, normal_item(str(row.get("char_count", 0))))
        self.table.setItem(r, 5, normal_item(str(row.get("seen_count", 0))))
        self.table.setItem(r, 6, normal_item("是" if row.get("is_sensitive") else "否", sensitive=bool(row.get("is_sensitive"))))
        self.table.setItem(r, 7, normal_item(row.get("sensitivity_reason", "") or ""))

    def maybe_load_more(self, value: int) -> None:
        bar = self.table.verticalScrollBar()
        if value >= bar.maximum() - 2:
            self.load_more()

    def on_item_changed(self, item) -> None:
        if item.column() != 0:
            return
        key = item.data(Qt.UserRole)
        if key:
            self.provider.update_material_selected(key, item.checkState() == Qt.Checked)

    def on_selection_changed(self) -> None:
        row = self.current_row()
        if not row:
            return
        self.detail.setPlainText(
            f"首次出现：{row.get('first_seen_at', '')}\n"
            f"最近出现：{row.get('last_seen_at', '')}\n"
            f"复制次数：{row.get('seen_count', 0)}\n"
            f"字符数：{row.get('char_count', 0)}\n"
            f"敏感：{'是' if row.get('is_sensitive') else '否'}\n"
            f"原因：{row.get('sensitivity_reason') or '-'}\n\n"
            f"{row.get('content', '')}"
        )

    def copy_selected_content(self) -> None:
        row = self.current_row()
        if not row:
            QMessageBox.information(self, "未选择记录", "请先选择一条剪贴板记录。")
            return
        QApplication.clipboard().setText(row.get("content", ""))
        QMessageBox.information(self, "已复制", "剪贴板记录内容已复制。")

    def delete_selected(self) -> None:
        key = self.current_key()
        if not key:
            QMessageBox.information(self, "未选择记录", "请先选择一条剪贴板记录。")
            return
        if QMessageBox.question(self, "确认删除", "确定要删除选中的剪贴板记录吗？") != QMessageBox.StandardButton.Yes:
            return
        self.provider.soft_delete_material(key)
        self.refresh()

    def current_key(self) -> str | None:
        selected = self.table.selectedItems()
        if not selected:
            return None
        item = self.table.item(selected[0].row(), 0)
        return item.data(Qt.UserRole) if item else None

    def current_row(self) -> dict | None:
        key = self.current_key()
        return self.rows_by_key.get(key) if key else None

    def update_count(self) -> None:
        self.count_label.setText(f"已加载 {self.table.rowCount()} / {self.total} 条")

    @property
    def day(self) -> str:
        return self.date_edit.date().toString("yyyy-MM-dd")

    @staticmethod
    def time_part(value: str | None) -> str:
        return str(value or "")[11:19] if value and len(str(value)) >= 19 else str(value or "")
