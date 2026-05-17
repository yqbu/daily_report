APP_QSS = """
* {
    font-family: "Microsoft YaHei", "Segoe UI", Arial;
    font-size: 13px;
    color: #1f2937;
}
QMainWindow, #RootFrame { background: #f5f7fb; }
#Sidebar { background: #ffffff; border-right: 1px solid #e5e7eb; }
#SidebarTitle { font-size: 15px; font-weight: 800; color: #111827; }
#SidebarSubtitle { color: #6b7280; font-size: 11px; }
QPushButton[nav="true"] {
    border: none; text-align: left; padding: 10px 14px; border-radius: 8px;
    background: transparent; color: #374151;
}
QPushButton[nav="true"]:hover { background: #eff6ff; color: #1d4ed8; }
QPushButton[nav="true"][active="true"] { background: #3b82f6; color: white; font-weight: 600; }
QPushButton { border: 1px solid #d1d5db; background: #ffffff; border-radius: 7px; padding: 8px 14px; }
QPushButton:hover { background: #f3f4f6; }
QPushButton[primary="true"] { border: 1px solid #2563eb; background: #2563eb; color: white; font-weight: 600; }
QPushButton[primary="true"]:hover { background: #1d4ed8; }
QPushButton[danger="true"] { border: 1px solid #ef4444; color: #dc2626; }
QFrame[card="true"], QGroupBox { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px; }
QGroupBox { margin-top: 12px; padding: 14px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; }
QLineEdit, QComboBox, QDateEdit, QSpinBox, QTextEdit, QTextBrowser {
    background: #ffffff; border: 1px solid #d1d5db; border-radius: 7px; padding: 7px 9px;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QTextEdit:focus { border: 1px solid #3b82f6; }
QTableWidget {
    background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px; gridline-color: #eef2f7;
    selection-background-color: #eff6ff; selection-color: #111827;
}
QHeaderView::section {
    background: #f9fafb; border: none; border-bottom: 1px solid #e5e7eb;
    padding: 8px; font-weight: 600; color: #374151;
}
QTableWidget::item { padding: 8px; }
#PageTitle { font-size: 24px; font-weight: 800; color: #111827; }
#SectionTitle { font-size: 15px; font-weight: 700; color: #111827; }
#MutedText { color: #6b7280; }
#StatusGood { color: #16a34a; font-weight: 600; }
#StatusWarn { color: #d97706; font-weight: 600; }
#SensitiveText { color: #dc2626; font-weight: 600; }
"""
