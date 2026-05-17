from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextBrowser, QVBoxLayout, QWidget

from daily_report.gui.data_provider import GuiDataProvider, MaterialRow
from daily_report.gui.widgets import Card, PageHeader, checkbox_item, make_table, normal_item


class MaterialReviewPage(QWidget):
    def __init__(self, provider: GuiDataProvider):
        super().__init__()
        self.provider = provider
        self.rows: list[MaterialRow] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(14)
        root.addWidget(PageHeader("素材确认中心", "勾选需要进入日报生成的素材，疑似敏感内容默认不选中"))

        filters = QHBoxLayout()
        filters.addWidget(QLabel("数据类型："))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["全部", "应用记录", "剪贴板", "浏览记录", "AI 提问"])
        self.type_combo.currentTextChanged.connect(self.apply_filters)
        filters.addWidget(self.type_combo)
        self.hide_sensitive = QCheckBox("隐藏疑似敏感内容")
        self.hide_sensitive.stateChanged.connect(self.apply_filters)
        filters.addWidget(self.hide_sensitive)
        filters.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索内容、来源或关键词")
        self.search.textChanged.connect(self.apply_filters)
        self.search.setFixedWidth(260)
        filters.addWidget(self.search)
        root.addLayout(filters)

        content = QHBoxLayout()
        left = QVBoxLayout()
        self.table = make_table(["选中", "时间", "类型", "内容预览", "来源", "敏感"])
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        left.addWidget(self.table, 1)

        self.detail = QTextBrowser()
        self.detail.setMinimumHeight(110)
        left.addWidget(self.detail)
        content.addLayout(left, 1)
        root.addLayout(content, 1)

        buttons = QHBoxLayout()
        refresh = QPushButton("刷新")
        refresh.clicked.connect(self.refresh)
        buttons.addWidget(refresh)
        buttons.addStretch()
        root.addLayout(buttons)
        self.refresh()

    def refresh(self) -> None:
        self.rows = self.provider.list_materials()
        self.apply_filters()

    def apply_filters(self) -> None:
        source_type = self.type_combo.currentText()
        keyword = self.search.text().strip().lower()
        hide_sensitive = self.hide_sensitive.isChecked()
        rows = self.rows
        if source_type != "全部":
            rows = [r for r in rows if r.source_type == source_type]
        if keyword:
            rows = [r for r in rows if keyword in (r.preview + r.source + r.source_type).lower()]
        if hide_sensitive:
            rows = [r for r in rows if not r.sensitive]
        self.fill(rows)

    def fill(self, rows: list[MaterialRow]) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, checkbox_item(row.selected, row.key))
            self.table.setItem(r, 1, normal_item(row.time))
            self.table.setItem(r, 2, normal_item(row.source_type))
            self.table.setItem(r, 3, normal_item(row.preview, sensitive=row.sensitive))
            self.table.setItem(r, 4, normal_item(row.source))
            self.table.setItem(r, 5, normal_item("是" if row.sensitive else "否", sensitive=row.sensitive))
        self.table.blockSignals(False)
        self.table.resizeRowsToContents()

    def on_item_changed(self, item) -> None:
        if item.column() != 0:
            return
        key = item.data(Qt.UserRole)
        if key:
            self.provider.update_material_selected(key, item.checkState() == Qt.Checked)

    def on_selection_changed(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        values = [self.table.item(row, c).text() if self.table.item(row, c) else "" for c in range(self.table.columnCount())]
        self.detail.setPlainText(
            f"时间：{values[1]}\n类型：{values[2]}\n来源：{values[4]}\n敏感：{values[5]}\n内容：{values[3]}"
        )
