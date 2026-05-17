from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from daily_report.gui.data_provider import GuiDataProvider
from daily_report.gui.widgets import Card, PageHeader, SmartDateEdit, checkbox_item, fmt_seconds, make_table, normal_item


class BrowserHistoryPage(QWidget):
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
        root.addWidget(PageHeader("浏览记录", "查看 Edge 历史记录、搜索关键词和噪声过滤结果"))

        filters = QHBoxLayout()
        filters.addWidget(QLabel("日期："))
        self.date_edit = SmartDateEdit()
        self.date_edit.setDate(date.today())
        self.date_edit.dateChanged.connect(self.refresh)
        filters.addWidget(self.date_edit)

        filters.addWidget(QLabel("类型："))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["全部", "搜索", "普通访问"])
        self.mode_combo.currentTextChanged.connect(self.refresh)
        filters.addWidget(self.mode_combo)

        filters.addWidget(QLabel("域名："))
        self.domain_combo = QComboBox()
        self.domain_combo.currentTextChanged.connect(self.refresh)
        filters.addWidget(self.domain_combo)

        self.hide_noise = QCheckBox("隐藏噪声")
        self.hide_noise.setChecked(True)
        self.hide_noise.stateChanged.connect(self.refresh)
        filters.addWidget(self.hide_noise)

        filters.addStretch()
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh)
        filters.addWidget(refresh_btn)
        root.addLayout(filters)

        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        search_row.addWidget(QLabel("搜索："))
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索标题、URL、域名或搜索词")
        self.search.setMinimumWidth(260)
        self.search.returnPressed.connect(self.refresh)
        search_row.addWidget(self.search, 1)
        root.addLayout(search_row)

        self.table = make_table(["选中", "时间", "类型", "标题 / 搜索词", "域名", "浏览器", "Profile", "停留", "噪声"])
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
        copy_url_btn = QPushButton("复制 URL")
        copy_url_btn.clicked.connect(self.copy_selected_url)
        actions.addWidget(copy_url_btn)
        delete_btn = QPushButton("删除记录")
        delete_btn.setProperty("danger", True)
        delete_btn.clicked.connect(self.delete_selected)
        actions.addWidget(delete_btn)
        root.addLayout(actions)

        self.refresh_domains()
        self.refresh()

    def refresh_domains(self) -> None:
        current = self.domain_combo.currentText()
        domains = self.provider.list_browser_domains(self.day)
        self.domain_combo.blockSignals(True)
        self.domain_combo.clear()
        self.domain_combo.addItem("全部")
        self.domain_combo.addItems(domains)
        self.domain_combo.setCurrentText(current if current in ["全部", *domains] else "全部")
        self.domain_combo.blockSignals(False)

    def refresh(self) -> None:
        self.refresh_domains()
        self.offset = 0
        self.rows_by_key.clear()
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self.table.blockSignals(False)
        self.detail.setPlainText("选择一条浏览记录后，这里会显示 URL、标题、搜索信息和采集来源。")
        self.total = self.provider.count_browser_history_entries(
            self.day,
            keyword=self.search.text(),
            domain=self.domain_combo.currentText(),
            mode=self.mode_combo.currentText(),
            hide_noise=self.hide_noise.isChecked(),
        )
        self.load_more()

    def load_more(self) -> None:
        if self.loading or self.offset >= self.total:
            self.update_count()
            return
        self.loading = True
        rows = self.provider.list_browser_history_entries(
            self.day,
            keyword=self.search.text(),
            domain=self.domain_combo.currentText(),
            mode=self.mode_combo.currentText(),
            hide_noise=self.hide_noise.isChecked(),
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
        key = f"browser_history_entries:{row['id']}"
        self.rows_by_key[key] = row
        title = f"{row.get('search_engine') or '搜索'}：{row.get('search_query') or ''}" if row.get("is_search") else row.get("title", "")
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, checkbox_item(bool(row.get("is_selected")), key))
        self.table.setItem(r, 1, normal_item(self.time_part(row.get("visit_time"))))
        self.table.setItem(r, 2, normal_item("搜索" if row.get("is_search") else "访问"))
        self.table.setItem(r, 3, normal_item(title or row.get("url", "")))
        self.table.setItem(r, 4, normal_item(row.get("domain", "") or ""))
        self.table.setItem(r, 5, normal_item(row.get("browser", "") or ""))
        self.table.setItem(r, 6, normal_item(row.get("profile_name", "") or ""))
        self.table.setItem(r, 7, normal_item(fmt_seconds(row.get("visit_duration_sec"))))
        self.table.setItem(r, 8, normal_item("是" if row.get("is_noise") else "否"))

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
        search_text = (
            f"{row.get('search_engine') or ''}：{row.get('search_query') or ''}"
            if row.get("is_search")
            else "-"
        )
        self.detail.setPlainText(
            f"访问时间：{row.get('visit_time', '')}\n"
            f"标题：{row.get('title') or '-'}\n"
            f"URL：{row.get('url') or '-'}\n"
            f"域名：{row.get('domain') or '-'}\n"
            f"搜索：{search_text}\n"
            f"浏览器：{row.get('browser', '')} / {row.get('profile_name', '')}\n"
            f"停留：{fmt_seconds(row.get('visit_duration_sec'))}\n"
            f"噪声：{'是' if row.get('is_noise') else '否'}"
        )

    def copy_selected_url(self) -> None:
        row = self.current_row()
        if not row:
            QMessageBox.information(self, "未选择记录", "请先选择一条浏览记录。")
            return
        QApplication.clipboard().setText(row.get("url", ""))
        QMessageBox.information(self, "已复制", "URL 已复制到剪贴板。")

    def delete_selected(self) -> None:
        key = self.current_key()
        if not key:
            QMessageBox.information(self, "未选择记录", "请先选择一条浏览记录。")
            return
        if QMessageBox.question(self, "确认删除", "确定要删除选中的浏览记录吗？") != QMessageBox.StandardButton.Yes:
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
