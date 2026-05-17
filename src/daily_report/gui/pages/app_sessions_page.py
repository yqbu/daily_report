from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDateEdit, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from daily_report.gui.data_provider import GuiDataProvider
from daily_report.gui.widgets import PageHeader, checkbox_item, fmt_seconds, make_table, normal_item


class AppSessionsPage(QWidget):
    def __init__(self, provider: GuiDataProvider):
        super().__init__()
        self.provider = provider
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(14)
        root.addWidget(PageHeader("应用使用记录", "查看前台窗口 session、使用时长和活跃状态"))

        filters = QHBoxLayout()
        filters.addWidget(QLabel("日期："))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(date.today())
        filters.addWidget(self.date_edit)
        filters.addWidget(QLabel("应用："))
        self.app_combo = QComboBox()
        self.app_combo.addItem("全部")
        filters.addWidget(self.app_combo)
        filters.addStretch()
        refresh = QPushButton("刷新")
        refresh.clicked.connect(self.refresh)
        filters.addWidget(refresh)
        root.addLayout(filters)

        self.table = make_table(["选中", "开始时间", "结束时间", "应用名称", "进程名", "窗口标题", "时长", "活跃"])
        root.addWidget(self.table, 1)
        self.refresh()

    def refresh(self) -> None:
        day = self.date_edit.date().toString("yyyy-MM-dd")
        rows = self.provider.list_app_sessions(day)
        app_names = sorted({r.get("app_name") for r in rows if r.get("app_name")})
        current = self.app_combo.currentText()
        self.app_combo.blockSignals(True)
        self.app_combo.clear()
        self.app_combo.addItem("全部")
        self.app_combo.addItems(app_names)
        self.app_combo.setCurrentText(current if current in ["全部", *app_names] else "全部")
        self.app_combo.blockSignals(False)
        if self.app_combo.currentText() != "全部":
            rows = [r for r in rows if r.get("app_name") == self.app_combo.currentText()]
        self.table.setRowCount(0)
        for row in rows:
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
        self.table.resizeRowsToContents()
        self.table.itemChanged.connect(self._on_item_changed)

    def _on_item_changed(self, item) -> None:
        if item.column() != 0:
            return
        key = item.data(Qt.UserRole)
        if key:
            self.provider.update_material_selected(key, item.checkState() == Qt.Checked)
