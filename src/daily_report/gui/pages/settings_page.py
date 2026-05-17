from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from daily_report.config.local_settings import LocalSettings, load_local_settings, save_local_settings, get_settings_path
from daily_report.gui.data_provider import GuiDataProvider
from daily_report.gui.widgets import PageHeader
from daily_report.gui.worker import run_in_thread
from daily_report.reporter.deepseek_client import DeepSeekClient


class SettingsGroup(QGroupBox):
    def __init__(self, title: str):
        super().__init__(title)
        self.form = QGridLayout(self)
        self.form.setContentsMargins(12, 18, 12, 12)
        self.form.setHorizontalSpacing(12)
        self.form.setVerticalSpacing(10)


class SettingsPage(QWidget):
    def __init__(self, provider: GuiDataProvider):
        super().__init__()
        self.provider = provider
        self._threads = []
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(14)
        root.addWidget(PageHeader("设置", "配置模型参数、API Key 与 YASB 联动"))

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        model = SettingsGroup("模型设置")
        model.form.addWidget(QLabel("Base URL"), 0, 0)
        self.base_url = QLineEdit()
        model.form.addWidget(self.base_url, 0, 1)
        model.form.addWidget(QLabel("模型名称"), 1, 0)
        self.model_name = QComboBox()
        self.model_name.setEditable(True)
        self.model_name.addItems(["deepseek-chat", "deepseek-reasoner", "deepseek-v4-flash", "deepseek-v4-pro"])
        model.form.addWidget(self.model_name, 1, 1)
        model.form.addWidget(QLabel("API Key"), 2, 0)
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.Password)
        self.api_key.setPlaceholderText("sk-...，也可使用 DEEPSEEK_API_KEY 环境变量")
        model.form.addWidget(self.api_key, 2, 1)
        self.save_key = QCheckBox("保存 API Key 到本地 settings 文件")
        self.save_key.setChecked(True)
        model.form.addWidget(self.save_key, 3, 1)
        model.form.addWidget(QLabel("最大 Prompt 长度"), 4, 0)
        self.max_prompt_chars = QSpinBox()
        self.max_prompt_chars.setRange(1000, 200000)
        self.max_prompt_chars.setSingleStep(1000)
        model.form.addWidget(self.max_prompt_chars, 4, 1)
        model.form.addWidget(QLabel("Temperature"), 5, 0)
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(0.1)
        model.form.addWidget(self.temperature, 5, 1)
        test_btn = QPushButton("测试模型连接")
        test_btn.clicked.connect(self.test_model)
        model.form.addWidget(test_btn, 6, 0)
        save_btn = QPushButton("保存设置")
        save_btn.setProperty("primary", True)
        save_btn.clicked.connect(self.save)
        model.form.addWidget(save_btn, 6, 1)
        grid.addWidget(model, 0, 0)

        yasb = SettingsGroup("YASB 联动")
        yasb.form.addWidget(QLabel("状态命令"), 0, 0)
        self.status_cmd = QLineEdit("daily-report status --json")
        yasb.form.addWidget(self.status_cmd, 0, 1)
        yasb.form.addWidget(QLabel("设置文件"), 1, 0)
        self.settings_path_line = QLineEdit(str(get_settings_path()))
        self.settings_path_line.setReadOnly(True)
        yasb.form.addWidget(self.settings_path_line, 1, 1)
        grid.addWidget(yasb, 0, 1)

        root.addLayout(grid)
        root.addStretch()
        self.load()

    def load(self) -> None:
        settings = load_local_settings()
        self.base_url.setText(settings.model.base_url)
        self.model_name.setCurrentText(settings.model.model_name)
        self.api_key.setText(settings.model.api_key)
        self.max_prompt_chars.setValue(settings.model.max_prompt_chars)
        self.temperature.setValue(settings.model.temperature)
        self.status_cmd.setText(settings.yasb.status_cli_command)

    def current_settings(self) -> LocalSettings:
        settings = load_local_settings()
        settings.model.base_url = self.base_url.text().strip() or "https://api.deepseek.com"
        settings.model.model_name = self.model_name.currentText().strip() or "deepseek-chat"
        settings.model.api_key = self.api_key.text().strip()
        settings.model.max_prompt_chars = self.max_prompt_chars.value()
        settings.model.temperature = self.temperature.value()
        settings.yasb.status_cli_command = self.status_cmd.text().strip() or "daily-report status --json"
        return settings

    def save(self) -> None:
        settings_save_path = get_settings_path()
        save_local_settings(settings=self.current_settings(), path=settings_save_path, save_api_key=self.save_key.isChecked())
        QMessageBox.information(self, "保存成功", f"设置已保存：\n{settings_save_path}")

    def test_model(self) -> None:
        settings = self.current_settings().model

        def call() -> str:
            return DeepSeekClient(
                api_key=settings.api_key,
                model_name=settings.model_name,
                base_url=settings.base_url,
                temperature=settings.temperature,
            ).test()

        def ok(result) -> None:
            QMessageBox.information(self, "测试成功", str(result))

        def fail(message: str) -> None:
            QMessageBox.critical(self, "测试失败", message)

        run_in_thread(self, call, ok, fail)
