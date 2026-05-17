from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from daily_report.gui.data_provider import GuiDataProvider
from daily_report.gui.widgets import PageHeader, SmartDateEdit, checkbox_item, fmt_seconds, make_table, normal_item


class AppSessionsPage(QWidget):
    PAGE_SIZE = 100

    def __init__(self, provider: GuiDataProvider):
        super().__init__()
        self.provider = provider
        self.offset = 0
        self.total = 0
        self.loading = False
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(14)
        root.addWidget(PageHeader("应用使用记录", "查看前台窗口 session、使用时长和活跃状态"))

        filters = QHBoxLayout()
        filters.addWidget(QLabel("日期："))
        self.date_edit = SmartDateEdit()
        self.date_edit.setDate(date.today())
        self.date_edit.dateChanged.connect(self.refresh)
        filters.addWidget(self.date_edit)
        filters.addWidget(QLabel("应用："))
        self.app_combo = QComboBox()
        self.app_combo.addItem("全部")
        self.app_combo.currentTextChanged.connect(self.refresh)
        filters.addWidget(self.app_combo)
        filters.addStretch()
        refresh = QPushButton("刷新")
        refresh.clicked.connect(self.refresh)
        filters.addWidget(refresh)
        root.addLayout(filters)

        self.table = make_table(["选中", "开始时间", "结束时间", "应用名称", "进程名", "窗口标题", "时长", "活跃"])
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.verticalScrollBar().valueChanged.connect(self._maybe_load_more)
        root.addWidget(self.table, 1)
        self.count_label = QLabel()
        self.count_label.setObjectName("MutedText")
        root.addWidget(self.count_label)
        self.refresh()

    def refresh(self) -> None:
        self.refresh_app_names()
        self.offset = 0
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self.table.blockSignals(False)
        self.total = self.provider.count_app_sessions(self.day, app_name=self.current_app)
        self.load_more()

    def refresh_app_names(self) -> None:
        day = self.date_edit.date().toString("yyyy-MM-dd")
        current = self.app_combo.currentText()
        app_names = self.provider.list_app_names(day)
        self.app_combo.blockSignals(True)
        self.app_combo.clear()
        self.app_combo.addItem("全部")
        self.app_combo.addItems(app_names)
        self.app_combo.setCurrentText(current if current in ["全部", *app_names] else "全部")
        self.app_combo.blockSignals(False)

    def load_more(self) -> None:
        if self.loading or self.offset >= self.total:
            self.update_count()
            return
        self.loading = True
        rows = self.provider.list_app_sessions(
            self.day,
            app_name=self.current_app,
            limit=self.PAGE_SIZE,
            offset=self.offset,
        )
        self.table.blockSignals(True)
        for row in rows:
            self.append_row(row)
        self.table.blockSignals(False)
        self.offset += len(rows)
        self.loading = False
        self.table.resizeRowsToContents()
        self.update_count()

    def append_row(self, row: dict) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)
        key = f"app_sessions:{row['id']}"
        self.table.setItem(r, 0, checkbox_item(bool(row.get("is_selected")), key))
        self.table.setItem(r, 1, normal_item(str(row.get("start_time", ""))[11:19]))
        self.table.setItem(r, 2, normal_item(str(row.get("end_time", ""))[11:19]))
        self.table.setItem(r, 3, normal_item(row.get("app_name", "")))
        self.table.setItem(r, 4, normal_item(row.get("process_name", "")))
        self.table.setItem(r, 5, normal_item(row.get("window_title", "")))
        self.table.setItem(r, 6, normal_item(fmt_seconds(row.get("active_duration_sec"))))
        self.table.setItem(r, 7, normal_item("是" if row.get("is_active") else "否"))

    def _maybe_load_more(self, value: int) -> None:
        bar = self.table.verticalScrollBar()
        if value >= bar.maximum() - 2:
            self.load_more()

    def _on_item_changed(self, item) -> None:
        if item.column() != 0:
            return
        key = item.data(Qt.UserRole)
        if key:
            self.provider.update_material_selected(key, item.checkState() == Qt.Checked)

    def update_count(self) -> None:
        self.count_label.setText(f"已加载 {self.table.rowCount()} / {self.total} 条")

    @property
    def day(self) -> str:
        return self.date_edit.date().toString("yyyy-MM-dd")

    @property
    def current_app(self) -> str:
        return self.app_combo.currentText()
