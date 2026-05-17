from __future__ import annotations

from pathlib import Path


def _asset_url(name: str) -> str:
    return Path(__file__).with_name("assets").joinpath(name).as_posix()


CHEVRON_DOWN = _asset_url("chevron-down.svg")
CHEVRON_UP = _asset_url("chevron-up.svg")


def _strip_pixel_font_sizes(stylesheet: str) -> str:
    lines = []
    for line in stylesheet.splitlines():
        stripped = line.strip()
        if stripped.startswith("font-size:") and stripped.endswith("px;"):
            continue
        if stripped == "font-size: ;":
            continue
        lines.append(line)
    return "\n".join(lines)


def apply_app_theme(app) -> None:
    from PySide6.QtGui import QFont

    font = QFont("Microsoft YaHei")
    font.setPointSize(10)
    app.setFont(font)

    try:
        from qt_material import build_stylesheet

        app.setStyle("Fusion")
        material_qss = _strip_pixel_font_sizes(build_stylesheet("light_blue.xml") or "")
        app.setStyleSheet(f"{material_qss}\n{APP_QSS}")
    except Exception:
        app.setStyleSheet(APP_QSS)


APP_QSS = """
* {
    font-family: "Microsoft YaHei", "Segoe UI", Arial;
    color: #1f2937;
}
QMainWindow, #RootFrame, QStackedWidget#AppStack, QStackedWidget#AppStack > QWidget { background: #f4f6fa; }
#Sidebar { background: #ffffff; border-right: 1px solid #e4e7ee; }
#SidebarTitle { font-size: 11pt; font-weight: 800; color: #111827; }
#SidebarSubtitle { color: #6b7280; font-size: 8pt; }
QPushButton[nav="true"] {
    border: none; text-align: left; padding: 10px 14px; border-radius: 8px;
    background: transparent; color: #374151;
}
QPushButton[nav="true"]:hover { background: #eef5ff; color: #1d4ed8; }
QPushButton[nav="true"][active="true"] { background: #2563eb; color: white; font-weight: 600; }
QPushButton {
    border: 1px solid #cfd6e3; background: #ffffff; border-radius: 7px;
    padding: 5px 14px; min-height: 22px;
}
QPushButton:hover { background: #f5f7fb; border-color: #bac6d8; }
QPushButton:pressed { background: #e9eef7; }
QPushButton:disabled { color: #9ca3af; background: #f3f4f6; border-color: #e5e7eb; }
QPushButton[primary="true"] { border: 1px solid #2563eb; background: #2563eb; color: white; font-weight: 600; }
QPushButton[primary="true"]:hover { background: #1d4ed8; }
QPushButton[danger="true"] { border: 1px solid #fecaca; color: #dc2626; background: #fffafa; }
QPushButton[danger="true"]:hover { background: #fef2f2; border-color: #fca5a5; }
QScrollArea, QScrollArea > QWidget, QWidget#SettingsBody { background: #f4f6fa; border: none; }
QFrame[card="true"], QGroupBox { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; }
QGroupBox { margin-top: 10px; padding: 12px; font-weight: 600; }
QGroupBox::title {
    subcontrol-origin: margin; left: 12px; padding: 2px 8px;
    color: #111827; background: #ffffff; border-radius: 5px;
}
QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox {
    background: #ffffff; border: 1px solid #cfd6e3; border-radius: 7px;
    min-height: 20px; padding: 5px 9px;
    selection-background-color: #dbeafe; selection-color: #111827;
}
QTextEdit, QTextBrowser, QPlainTextEdit {
    background: #ffffff; border: 1px solid #cfd6e3; border-radius: 7px;
    padding: 4px 7px; selection-background-color: #dbeafe; selection-color: #111827;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #2563eb;
}
QLineEdit[readOnly="true"] { background: #f8fafc; color: #64748b; }
QComboBox, QDateEdit { padding-right: 32px; }
QComboBox::drop-down, QDateEdit::drop-down {
    subcontrol-origin: padding; subcontrol-position: top right;
    width: 32px; border-left: 1px solid #e2e8f0; border-top-right-radius: 7px; border-bottom-right-radius: 7px;
    background: #f8fafc; padding: 0px; margin: 0px;
}
QComboBox::drop-down:hover, QDateEdit::drop-down:hover { background: #eef5ff; }
QComboBox::down-arrow, QDateEdit::down-arrow {
    image: url("__CHEVRON_DOWN__");
    width: 14px; height: 14px; margin: 0px;
}
QComboBox QAbstractItemView {
    background: #ffffff; border: 1px solid #cfd6e3; border-radius: 6px;
    padding: 4px; outline: 0px; selection-background-color: #eaf2ff; selection-color: #111827;
}
QWidget#SmartDateEdit {
    background: #ffffff; border: 1px solid #cfd6e3; border-radius: 7px;
    min-height: 32px; max-height: 32px;
}
QLineEdit#SmartDateEditLine {
    background: transparent; border: none; padding: 5px 10px; color: #1f2937;
    min-height: 20px;
}
QToolButton#SmartDateEditButton {
    background: #f8fafc; border: none; border-left: 1px solid #e2e8f0;
    border-top-right-radius: 7px; border-bottom-right-radius: 7px;
    min-width: 32px; max-width: 32px; min-height: 32px; max-height: 32px;
    padding: 0px; margin: 0px;
}
QToolButton#SmartDateEditButton::menu-indicator { image: none; width: 0px; }
QToolButton#SmartDateEditButton:hover { background: #eef5ff; }
QSpinBox, QDoubleSpinBox { padding-right: 32px; }
QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border; subcontrol-position: top right;
    width: 32px; border-left: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; border-top-right-radius: 7px;
    background: #f8fafc;
}
QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border; subcontrol-position: bottom right;
    width: 32px; border-left: 1px solid #e2e8f0; border-bottom-right-radius: 7px;
    background: #f8fafc;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover { background: #eef5ff; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
    image: url("__CHEVRON_UP__");
    width: 12px; height: 12px;
}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    image: url("__CHEVRON_DOWN__");
    width: 12px; height: 12px;
}
QFrame#MaterialDatePopup {
    background: #ffffff; border: 1px solid #cfd6e3; border-radius: 10px;
}
QLabel#CalendarTitle { font-weight: 700; color: #111827; }
QLabel#CalendarWeekday { color: #64748b; font-weight: 600; }
QToolButton#CalendarNavButton {
    background: #f8fafc; border: 1px solid #d7deea; border-radius: 7px;
    min-width: 30px; min-height: 28px; font-size: 14pt; font-weight: 700;
}
QToolButton#CalendarNavButton:hover { background: #eef5ff; border-color: #bfdbfe; color: #1d4ed8; }
QToolButton#CalendarNavButton:disabled { color: #cbd5e1; background: #f8fafc; border-color: #e2e8f0; }
QPushButton#CalendarDayButton {
    border: none; border-radius: 7px; padding: 0px; min-height: 30px;
    background: transparent; color: #1f2937;
}
QPushButton#CalendarDayButton:hover { background: #eef5ff; color: #1d4ed8; }
QPushButton#CalendarDayButton[today="true"] { color: #2563eb; font-weight: 700; }
QPushButton#CalendarDayButton[selected="true"] { background: #2563eb; color: #ffffff; font-weight: 700; }
QPushButton#CalendarDayButton:disabled { color: #cbd5e1; background: transparent; }
QPushButton#CalendarTodayButton {
    padding: 5px 12px; min-height: 20px; border-radius: 7px;
    background: #eef5ff; color: #1d4ed8; border: 1px solid #bfdbfe;
}
QTableWidget {
    background: #ffffff; alternate-background-color: #f8fafc;
    border: 1px solid #e2e8f0; border-radius: 8px; gridline-color: #eef2f7;
    selection-background-color: #eff6ff; selection-color: #111827;
}
QHeaderView::section {
    background: #f8fafc; border: none; border-bottom: 1px solid #e2e8f0;
    padding: 8px; font-weight: 600; color: #374151;
}
QTableWidget::item { padding: 8px; }
QTabWidget::pane { border: 1px solid #e2e8f0; border-radius: 8px; top: -1px; }
QTabBar::tab {
    background: #f1f5f9; border: 1px solid #dbe3ef; padding: 6px 14px;
    border-top-left-radius: 7px; border-top-right-radius: 7px; margin-right: 4px;
    color: #475569;
}
QTabBar::tab:hover { background: #eaf2ff; color: #1d4ed8; }
QTabBar::tab:selected { background: #ffffff; color: #1d4ed8; font-weight: 600; border-bottom-color: #ffffff; }
QScrollBar:vertical {
    background: rgba(148, 163, 184, 0.10); width: 8px; margin: 2px 1px 2px 1px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: rgba(100, 116, 139, 0.42); border-radius: 4px; min-height: 36px;
}
QScrollBar::handle:vertical:hover { background: rgba(71, 85, 105, 0.62); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: transparent; border: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal {
    background: rgba(148, 163, 184, 0.10); height: 8px; margin: 1px 2px 1px 2px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: rgba(100, 116, 139, 0.42); border-radius: 4px; min-width: 36px;
}
QScrollBar::handle:horizontal:hover { background: rgba(71, 85, 105, 0.62); }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; background: transparent; border: none; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
#PageTitle { font-size: 18pt; font-weight: 800; color: #111827; }
#SectionTitle { font-size: 11pt; font-weight: 700; color: #111827; }
#MutedText { color: #6b7280; }
#StatusGood { color: #16a34a; font-weight: 600; }
#StatusWarn { color: #d97706; font-weight: 600; }
#SensitiveText { color: #dc2626; font-weight: 600; }
"""

APP_QSS = (
    APP_QSS
    .replace("__CHEVRON_DOWN__", CHEVRON_DOWN)
    .replace("__CHEVRON_UP__", CHEVRON_UP)
)
