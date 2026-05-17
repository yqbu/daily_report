from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QMessageBox, QPushButton, QSplitter, QTextBrowser, QTextEdit, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

from daily_report.config.local_settings import load_local_settings
from daily_report.gui.data_provider import GuiDataProvider
from daily_report.gui.widgets import Card, PageHeader
from daily_report.gui.worker import run_in_thread
from daily_report.reporter.prompt_builder import build_material_summary
from daily_report.service.report_service import ReportService


class ReportGeneratePage(QWidget):
    def __init__(self, provider: GuiDataProvider):
        super().__init__()
        self.provider = provider
        self.report_service = ReportService(provider.db_path)
        self._threads = []
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(14)
        root.addWidget(PageHeader("日报生成", "汇总选中素材，调用 DeepSeek 生成结构化 Markdown 日报"))

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        summary_card = Card()
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(16, 14, 16, 14)
        self.summary_text = QTextBrowser()
        summary_layout.addWidget(self.summary_text)
        refresh_summary = QPushButton("重新汇总素材")
        refresh_summary.clicked.connect(self.refresh_summary)
        summary_layout.addWidget(refresh_summary)
        splitter.addWidget(summary_card)

        preview_card = Card()
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(16, 14, 16, 14)
        self.preview_text = QTextEdit()
        preview_layout.addWidget(self.preview_text)
        splitter.addWidget(preview_card)
        splitter.setSizes([360, 680])
        root.addWidget(splitter, 1)

        self.prompt_text = QTextEdit()
        self.prompt_text.setFixedHeight(120)
        root.addWidget(self.prompt_text)

        buttons = QHBoxLayout()
        self.generate_btn = QPushButton("生成日报")
        self.generate_btn.setProperty("primary", True)
        self.generate_btn.clicked.connect(self.generate_report)
        buttons.addWidget(self.generate_btn)
        buttons.addStretch()
        copy_btn = QPushButton("复制 Markdown")
        copy_btn.clicked.connect(self.copy_markdown)
        buttons.addWidget(copy_btn)
        root.addLayout(buttons)
        self.refresh_summary()

    def refresh_summary(self) -> None:
        settings = load_local_settings()
        bundle = self.report_service.build_bundle()
        self.summary_text.setPlainText(build_material_summary(bundle))
        prompt = self.report_service.build_prompt(max_chars=settings.model.max_prompt_chars)
        self.prompt_text.setPlainText(prompt)

    def generate_report(self) -> None:
        if load_local_settings().privacy.require_manual_confirm_before_llm:
            message = "将把已勾选素材汇总后发送给模型生成日报，是否继续？"
            if QMessageBox.question(self, "确认调用模型", message) != QMessageBox.StandardButton.Yes:
                return
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("生成中...")

        def ok(result) -> None:
            self.generate_btn.setEnabled(True)
            self.generate_btn.setText("生成日报")
            self.prompt_text.setPlainText(result.prompt_text)
            self.preview_text.setPlainText(result.report_markdown)
            QMessageBox.information(self, "生成成功", f"日报已保存，ID={result.report_id}")

        def fail(message: str) -> None:
            self.generate_btn.setEnabled(True)
            self.generate_btn.setText("生成日报")
            QMessageBox.critical(self, "生成失败", message)

        run_in_thread(self, self.report_service.generate_report, ok, fail)

    def copy_markdown(self) -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.preview_text.toPlainText())
        QMessageBox.information(self, "已复制", "Markdown 内容已复制到剪贴板。")
