from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from daily_report.config.local_settings import (
    LocalSettings,
    get_model_api_key,
    get_settings_path,
    load_local_settings,
    save_local_settings,
)
from daily_report.gui.data_provider import GuiDataProvider
from daily_report.gui.widgets import PageHeader
from daily_report.gui.worker import run_in_thread
from daily_report.reporter.deepseek_client import DeepSeekClient


class SettingsGroup(QGroupBox):
    def __init__(self, title: str):
        super().__init__(title)
        self.form = QGridLayout(self)
        self.form.setContentsMargins(12, 16, 12, 12)
        self.form.setHorizontalSpacing(10)
        self.form.setVerticalSpacing(8)
        self.form.setColumnStretch(1, 1)


class SettingsPage(QWidget):
    def __init__(self, provider: GuiDataProvider):
        super().__init__()
        self.provider = provider
        self._threads = []
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 22)
        root.setSpacing(12)
        root.addWidget(PageHeader("设置", "配置模型、采集、隐私和日志保留策略"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        body.setObjectName("SettingsBody")
        grid = QGridLayout()
        body.setLayout(grid)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        settings_file = SettingsGroup("设置文件")
        settings_file.setMaximumHeight(104)
        settings_file.form.addWidget(QLabel("本地设置文件"), 0, 0)
        self.settings_path = get_settings_path()
        self.settings_path_line = QLineEdit(str(self.settings_path))
        self.settings_path_line.setReadOnly(True)
        self.settings_path_line.setFixedHeight(34)
        settings_file.form.addWidget(self.settings_path_line, 0, 1)
        choose_settings_file = QPushButton("选择文件")
        choose_settings_file.setFixedHeight(34)
        choose_settings_file.clicked.connect(self.choose_settings_file)
        settings_file.form.addWidget(choose_settings_file, 0, 2)
        grid.addWidget(settings_file, 0, 0, 1, 2)

        model = SettingsGroup("模型设置")
        model.form.addWidget(QLabel("模型提供商"), 0, 0)
        self.model_provider = QLineEdit()
        self.model_provider.setPlaceholderText("deepseek")
        model.form.addWidget(self.model_provider, 0, 1)
        model.form.addWidget(QLabel("Base URL"), 1, 0)
        self.base_url = QLineEdit()
        model.form.addWidget(self.base_url, 1, 1)
        model.form.addWidget(QLabel("模型名称"), 2, 0)
        self.model_name = QLineEdit()
        self.model_name.setPlaceholderText("按模型供应商文档填写，例如 deepseek-chat")
        model.form.addWidget(self.model_name, 2, 1)
        model.form.addWidget(QLabel("API Key"), 3, 0)
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.Password)
        self.api_key.setPlaceholderText("sk-...，也可使用 DEEPSEEK_API_KEY 环境变量")
        model.form.addWidget(self.api_key, 3, 1)
        self.save_key = QCheckBox("保存 API Key 到本地 settings 文件")
        self.save_key.setChecked(True)
        model.form.addWidget(self.save_key, 4, 1)
        model.form.addWidget(QLabel("最大 Prompt 长度"), 5, 0)
        self.max_prompt_chars = QSpinBox()
        self.max_prompt_chars.setRange(1000, 200000)
        self.max_prompt_chars.setSingleStep(1000)
        self.max_prompt_chars.setMinimumHeight(34)
        model.form.addWidget(self.max_prompt_chars, 5, 1)
        model.form.addWidget(QLabel("Temperature"), 6, 0)
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setDecimals(2)
        self.temperature.setMinimumHeight(34)
        model.form.addWidget(self.temperature, 6, 1)
        model.form.addWidget(QLabel("请求超时（秒）"), 7, 0)
        self.timeout_seconds = QSpinBox()
        self.timeout_seconds.setRange(5, 300)
        self.timeout_seconds.setSingleStep(5)
        self.timeout_seconds.setMinimumHeight(34)
        model.form.addWidget(self.timeout_seconds, 7, 1)
        self.test_btn = QPushButton("测试模型连接")
        self.test_btn.clicked.connect(self.test_model)
        model.form.addWidget(self.test_btn, 8, 0)
        save_btn = QPushButton("保存设置")
        save_btn.setProperty("primary", True)
        save_btn.clicked.connect(self.save)
        model.form.addWidget(save_btn, 8, 1)
        grid.addWidget(model, 1, 1, 3, 1)

        collector = SettingsGroup("采集设置")
        self.foreground_enabled = QCheckBox("启用前台窗口采集")
        self.clipboard_enabled = QCheckBox("启用剪贴板采集")
        self.edge_history_enabled = QCheckBox("启用 Edge 浏览记录采集")
        self.ai_prompt_enabled = QCheckBox("启用 AI 提问采集")
        collector.form.addWidget(self.foreground_enabled, 0, 0, 1, 2)
        collector.form.addWidget(self.clipboard_enabled, 1, 0, 1, 2)
        collector.form.addWidget(self.edge_history_enabled, 2, 0, 1, 2)
        collector.form.addWidget(self.ai_prompt_enabled, 3, 0, 1, 2)
        collector.form.addWidget(QLabel("前台轮询间隔（秒）"), 4, 0)
        self.foreground_poll_interval_sec = QSpinBox()
        self.foreground_poll_interval_sec.setRange(1, 60)
        self.foreground_poll_interval_sec.setMinimumHeight(34)
        collector.form.addWidget(self.foreground_poll_interval_sec, 4, 1)
        collector.form.addWidget(QLabel("Edge 同步间隔（分钟）"), 5, 0)
        self.edge_sync_interval_min = QSpinBox()
        self.edge_sync_interval_min.setRange(1, 120)
        self.edge_sync_interval_min.setMinimumHeight(34)
        collector.form.addWidget(self.edge_sync_interval_min, 5, 1)
        grid.addWidget(collector, 1, 0)

        privacy = SettingsGroup("隐私与敏感内容")
        self.hide_sensitive_by_default = QCheckBox("默认隐藏敏感内容")
        self.sensitive_unselected_by_default = QCheckBox("敏感内容默认不进入日报")
        self.require_manual_confirm_before_llm = QCheckBox("调用模型前需要人工确认")
        self.clipboard_preview_only = QCheckBox("剪贴板仅保存预览")
        privacy.form.addWidget(self.hide_sensitive_by_default, 0, 0, 1, 2)
        privacy.form.addWidget(self.sensitive_unselected_by_default, 1, 0, 1, 2)
        privacy.form.addWidget(self.require_manual_confirm_before_llm, 2, 0, 1, 2)
        privacy.form.addWidget(self.clipboard_preview_only, 3, 0, 1, 2)
        privacy.form.addWidget(QLabel("敏感关键词"), 4, 0)
        self.sensitive_keywords = QTextEdit()
        self.sensitive_keywords.setPlaceholderText("每行一个关键词，也可以用逗号分隔")
        self.sensitive_keywords.setFixedHeight(96)
        privacy.form.addWidget(self.sensitive_keywords, 4, 1)
        grid.addWidget(privacy, 2, 0)

        logging = SettingsGroup("日志与保留")
        logging.form.addWidget(QLabel("日志级别"), 0, 0)
        self.logging_level = QComboBox()
        self.logging_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        logging.form.addWidget(self.logging_level, 0, 1)
        logging.form.addWidget(QLabel("日志保留天数"), 1, 0)
        self.logging_retention_days = QSpinBox()
        self.logging_retention_days.setRange(1, 3650)
        self.logging_retention_days.setMinimumHeight(34)
        logging.form.addWidget(self.logging_retention_days, 1, 1)
        grid.addWidget(logging, 3, 0)
        grid.setRowStretch(4, 1)

        scroll.setWidget(body)
        root.addWidget(scroll, 1)
        self.load()

    def load(self) -> None:
        settings = load_local_settings()
        self.model_provider.setText(settings.model.provider)
        self.base_url.setText(settings.model.base_url)
        self.model_name.setText(settings.model.model_name)
        self.api_key.setText(settings.model.api_key)
        self.max_prompt_chars.setValue(settings.model.max_prompt_chars)
        self.temperature.setValue(settings.model.temperature)
        self.timeout_seconds.setValue(settings.model.timeout_seconds)
        self.foreground_enabled.setChecked(settings.collector.foreground_enabled)
        self.clipboard_enabled.setChecked(settings.collector.clipboard_enabled)
        self.edge_history_enabled.setChecked(settings.collector.edge_history_enabled)
        self.ai_prompt_enabled.setChecked(settings.collector.ai_prompt_enabled)
        self.foreground_poll_interval_sec.setValue(settings.collector.foreground_poll_interval_sec)
        self.edge_sync_interval_min.setValue(settings.collector.edge_sync_interval_min)
        self.hide_sensitive_by_default.setChecked(settings.privacy.hide_sensitive_by_default)
        self.sensitive_unselected_by_default.setChecked(settings.privacy.sensitive_unselected_by_default)
        self.require_manual_confirm_before_llm.setChecked(settings.privacy.require_manual_confirm_before_llm)
        self.clipboard_preview_only.setChecked(settings.privacy.clipboard_preview_only)
        self.sensitive_keywords.setPlainText("\n".join(settings.privacy.sensitive_keywords))
        self.logging_level.setCurrentText(settings.logging.level)
        self.logging_retention_days.setValue(settings.logging.retention_days)

    def current_settings(self) -> LocalSettings:
        settings = load_local_settings()
        settings.model.provider = self.model_provider.text().strip() or "deepseek"
        settings.model.base_url = self.base_url.text().strip() or "https://api.deepseek.com"
        settings.model.model_name = self.model_name.text().strip() or "deepseek-chat"
        settings.model.api_key = self.api_key.text().strip()
        settings.model.max_prompt_chars = self.max_prompt_chars.value()
        settings.model.temperature = self.temperature.value()
        settings.model.timeout_seconds = self.timeout_seconds.value()
        settings.collector.foreground_enabled = self.foreground_enabled.isChecked()
        settings.collector.clipboard_enabled = self.clipboard_enabled.isChecked()
        settings.collector.edge_history_enabled = self.edge_history_enabled.isChecked()
        settings.collector.ai_prompt_enabled = self.ai_prompt_enabled.isChecked()
        settings.collector.foreground_poll_interval_sec = self.foreground_poll_interval_sec.value()
        settings.collector.edge_sync_interval_min = self.edge_sync_interval_min.value()
        settings.privacy.hide_sensitive_by_default = self.hide_sensitive_by_default.isChecked()
        settings.privacy.sensitive_unselected_by_default = self.sensitive_unselected_by_default.isChecked()
        settings.privacy.require_manual_confirm_before_llm = self.require_manual_confirm_before_llm.isChecked()
        settings.privacy.clipboard_preview_only = self.clipboard_preview_only.isChecked()
        settings.privacy.sensitive_keywords = self.parse_keywords()
        settings.logging.level = self.logging_level.currentText().strip() or "INFO"
        settings.logging.retention_days = self.logging_retention_days.value()
        return settings

    def save(self) -> None:
        settings_save_path = self.settings_path
        save_local_settings(settings=self.current_settings(), path=settings_save_path, save_api_key=self.save_key.isChecked())
        QMessageBox.information(self, "保存成功", f"设置已保存：\n{settings_save_path}")

    def choose_settings_file(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "选择设置文件",
            str(self.settings_path),
            "JSON Files (*.json);;All Files (*)",
        )
        if not filename:
            return
        self.settings_path = Path(filename)
        self.settings_path_line.setText(str(self.settings_path))

    def test_model(self) -> None:
        local_settings = self.current_settings()
        settings = local_settings.model
        self.test_btn.setEnabled(False)
        self.test_btn.setText("测试中...")

        def call() -> str:
            return DeepSeekClient(
                api_key=get_model_api_key(local_settings),
                model_name=settings.model_name,
                base_url=settings.base_url,
                temperature=settings.temperature,
                timeout_seconds=settings.timeout_seconds,
            ).test()

        def ok(result) -> None:
            self.test_btn.setEnabled(True)
            self.test_btn.setText("测试模型连接")
            QMessageBox.information(self, "测试成功", str(result))

        def fail(message: str) -> None:
            self.test_btn.setEnabled(True)
            self.test_btn.setText("测试模型连接")
            QMessageBox.critical(self, "测试失败", message)

        run_in_thread(self, call, ok, fail)

    def parse_keywords(self) -> list[str]:
        raw = self.sensitive_keywords.toPlainText().replace("，", ",").replace("\n", ",")
        return [item.strip() for item in raw.split(",") if item.strip()]
