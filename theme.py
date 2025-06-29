"""
Light and dark Qt style sheets — import theme.DARK / theme.LIGHT.
"""

DARK = """
* { font-family: "Segoe UI", "Noto Sans", sans-serif; font-size: 10pt; }

QWidget      { background: #121417; color: #dadada; }
QGroupBox    { border: 1px solid #444; border-radius: 6px; margin-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left;
                   padding: 0 6px 0 6px; color: #8cb3ff; font-weight: 600; }

QLineEdit, QTextEdit, QComboBox, QSpinBox {
    background: #1e1f22; border: 1px solid #444; border-radius: 4px;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border-color: #3d89ff;
}

QPushButton { background: #2b2d31; border: 1px solid #444; border-radius: 6px; padding: 4px 10px; }
QPushButton:hover   { background: #34363c; }
QPushButton:pressed { background: #3d3f45; }
QPushButton:disabled{ background: #202124; color: #555; }

QProgressBar        { background: #1e1f22; border: 1px solid #444; border-radius: 5px; text-align: center; }
QProgressBar::chunk { background-color: #3d89ff; }

QTabWidget::pane { border: 1px solid #444; top: -1px; }
QTabBar::tab {
    background: #1e1f22; padding: 6px 12px; border: 1px solid #444;
    border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px;
}
QTabBar::tab:selected { background: #282a30; color: #8cb3ff; }

QToolBar { background: #1a1b1d; spacing: 4px; padding: 3px; border-bottom: 1px solid #303030; }

QScrollBar:vertical, QScrollBar:horizontal { background: transparent; width: 12px; height: 12px; }
QScrollBar::handle { background: #3d3f45; border-radius: 6px; }
QScrollBar::handle:hover { background: #4c4e54; }
"""

LIGHT = """
* { font-family: "Segoe UI", "Noto Sans", sans-serif; font-size: 10pt; }

QWidget   { background: #f5f6fa; color: #202124; }
QGroupBox { border: 1px solid #c6c9d4; border-radius: 6px; margin-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left;
                   padding: 0 6px 0 6px; color: #2257c7; font-weight: 600; }

QLineEdit, QTextEdit, QComboBox, QSpinBox {
    background: #ffffff; border: 1px solid #c6c9d4; border-radius: 4px;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border-color: #2257c7;
}

QPushButton { background: #e7e9f2; border: 1px solid #c6c9d4; border-radius: 6px; padding: 4px 10px; }
QPushButton:hover   { background: #dfe2ec; }
QPushButton:pressed { background: #d6d9e4; }
QPushButton:disabled{ background: #f1f2f7; color: #a7a9b3; }

QProgressBar        { background: #ffffff; border: 1px solid #c6c9d4; border-radius: 5px; text-align: center; }
QProgressBar::chunk { background-color: #2257c7; }

QTabWidget::pane { border: 1px solid #c6c9d4; top: -1px; }
QTabBar::tab {
    background: #e7e9f2; padding: 6px 12px; border: 1px solid #c6c9d4;
    border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px;
}
QTabBar::tab:selected { background: #ffffff; }

QToolBar { background: #eceef7; spacing: 4px; padding: 3px; border-bottom: 1px solid #c6c9d4; }
"""
