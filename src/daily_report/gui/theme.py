APP_QSS = """
* {
    font-family: "Microsoft YaHei", "Segoe UI", Arial;
    font-size: 13px;
    color: #1f2937;
}
QMainWindow, #RootFrame { background: #f4f6fa; }
#Sidebar { background: #ffffff; border-right: 1px solid #e4e7ee; }
#SidebarTitle { font-size: 15px; font-weight: 800; color: #111827; }
#SidebarSubtitle { color: #6b7280; font-size: 11px; }
QPushButton[nav="true"] {
    border: none; text-align: left; padding: 10px 14px; border-radius: 8px;
    background: transparent; color: #374151;
}
QPushButton[nav="true"]:hover { background: #eef5ff; color: #1d4ed8; }
QPushButton[nav="true"][active="true"] { background: #2563eb; color: white; font-weight: 600; }
QPushButton {
    border: 1px solid #cfd6e3; background: #ffffff; border-radius: 7px;
    padding: 8px 14px; min-height: 18px;
}
QPushButton:hover { background: #f5f7fb; border-color: #bac6d8; }
QPushButton:pressed { background: #e9eef7; }
QPushButton:disabled { color: #9ca3af; background: #f3f4f6; border-color: #e5e7eb; }
QPushButton[primary="true"] { border: 1px solid #2563eb; background: #2563eb; color: white; font-weight: 600; }
QPushButton[primary="true"]:hover { background: #1d4ed8; }
QPushButton[danger="true"] { border: 1px solid #fecaca; color: #dc2626; background: #fffafa; }
QPushButton[danger="true"]:hover { background: #fef2f2; border-color: #fca5a5; }
QFrame[card="true"], QGroupBox { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; }
QGroupBox { margin-top: 12px; padding: 14px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #111827; }
QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QTextBrowser {
    background: #ffffff; border: 1px solid #cfd6e3; border-radius: 7px;
    padding: 7px 9px; selection-background-color: #dbeafe; selection-color: #111827;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {
    border: 1px solid #2563eb;
}
QLineEdit[readOnly="true"] { background: #f8fafc; color: #64748b; }
QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox { min-height: 20px; }
QComboBox { padding-right: 28px; }
QComboBox::drop-down {
    subcontrol-origin: padding; subcontrol-position: top right;
    width: 28px; border-left: 1px solid #e2e8f0; border-top-right-radius: 7px; border-bottom-right-radius: 7px;
}
QComboBox QAbstractItemView {
    background: #ffffff; border: 1px solid #cfd6e3; border-radius: 6px;
    padding: 4px; outline: 0px; selection-background-color: #eaf2ff; selection-color: #111827;
}
QSpinBox, QDoubleSpinBox { padding-right: 22px; }
QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border; subcontrol-position: top right;
    width: 20px; border-left: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; border-top-right-radius: 7px;
}
QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border; subcontrol-position: bottom right;
    width: 20px; border-left: 1px solid #e2e8f0; border-bottom-right-radius: 7px;
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
    background: #f8fafc; border: 1px solid #e2e8f0; padding: 8px 14px;
    border-top-left-radius: 7px; border-top-right-radius: 7px; margin-right: 4px;
}
QTabBar::tab:selected { background: #ffffff; color: #1d4ed8; font-weight: 600; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #cbd5e1; border-radius: 5px; min-height: 32px; }
QScrollBar::handle:vertical:hover { background: #94a3b8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #cbd5e1; border-radius: 5px; min-width: 32px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
#PageTitle { font-size: 24px; font-weight: 800; color: #111827; }
#SectionTitle { font-size: 15px; font-weight: 700; color: #111827; }
#MutedText { color: #6b7280; }
#StatusGood { color: #16a34a; font-weight: 600; }
#StatusWarn { color: #d97706; font-weight: 600; }
#SensitiveText { color: #dc2626; font-weight: 600; }
"""
