"""A deliberate light desktop theme, independent of Windows' app appearance.

Palette roles cover native Qt controls and all three activation groups. The
stylesheet supplies geometry and a small set of semantic surfaces on top of it.
Keep timetable/export subject colors in views.py, outside this UI theme.
"""

from importlib.resources import files

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

TEXT = "#20344D"
MUTED = "#4B5E71"
SURFACE = "#FFFFFF"
WINDOW = "#F4F6F9"
BORDER = "#718096"
PRIMARY = "#205C86"
FOCUS = "#1458A8"
SELECTION = "#205C86"
DISABLED_TEXT = "#536273"
DISABLED = "#E9EDF2"

STYLE = """
QWidget { color: palette(window-text); font-family: 'Segoe UI'; font-size: 11pt; }
QMainWindow, QDialog { background: palette(window); }
QPushButton, QToolButton {
    color: palette(button-text); background: palette(button);
    border: 2px solid #718096; border-radius: 5px;
    padding: 6px 12px; min-height: 22px;
}
QPushButton:hover, QToolButton:hover { background: #E6EEF6; border-color: #205C86; }
QPushButton:pressed, QToolButton:pressed { background: #D7E5F2; }
QPushButton:focus, QToolButton:focus { border: 2px solid #1458A8; background: #E6EEF6; }
QPushButton#primary { background: #205C86; color: white; font-weight: 600; }
QPushButton#primary:hover { background: #16476A; }
QPushButton#primary:focus { border: 2px solid #102E47; background: #16476A; }
QPushButton:disabled, QPushButton#primary:disabled, QToolButton:disabled {
    color: #536273; background: #E9EDF2; border-color: #718096;
}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTimeEdit {
    background: palette(base); color: palette(text); border: 2px solid #718096;
    border-radius: 4px; padding: 5px 7px; min-height: 22px;
    selection-background-color: #205C86; selection-color: white;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTimeEdit:focus {
    border: 2px solid #1458A8;
}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled,
QDoubleSpinBox:disabled, QTimeEdit:disabled { background: #E9EDF2; color: #536273; }
QLineEdit[invalid="true"], QSpinBox[invalid="true"], QComboBox[invalid="true"],
QTimeEdit[invalid="true"] { border-color: #A12B24; background: #FFF1EF; }
QComboBox QAbstractItemView {
    background: white; color: #20344D; border: 2px solid #718096;
    selection-background-color: #205C86; selection-color: white; outline: 0;
}
QTableWidget, QTreeWidget, QListWidget, QTextBrowser {
    background: palette(base); color: palette(text); border: 1px solid #718096;
    gridline-color: #C3CDD8; selection-background-color: #205C86; selection-color: white;
}
QTableWidget::item { padding: 7px; }
QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {
    background: #205C86; color: white;
}
QTableWidget:focus, QTreeWidget:focus, QListWidget:focus, QTextBrowser:focus {
    border: 2px solid #1458A8;
}
QTreeWidget::item, QListWidget::item { min-height: 28px; padding: 3px; }
QHeaderView::section {
    background: #E6ECF3; color: #20344D; border: 0;
    border-right: 1px solid #C3CDD8; border-bottom: 1px solid #718096;
    padding: 9px; font-weight: 600;
}
QTableCornerButton::section { background: #E6ECF3; border: 1px solid #718096; }
QListWidget#navigation { background: #19374F; color: white; border: 2px solid #19374F; }
QListWidget#navigation::item {
    padding: 13px 10px; color: white; border-left: 4px solid transparent;
}
QListWidget#navigation::item:selected { background: #305A7A; border-left: 4px solid white; }
QListWidget#navigation::item:hover { background: #305A7A; }
QListWidget#navigation:focus { border: 2px solid #1458A8; }
QLabel#pageTitle { font-size: 21pt; font-weight: 600; color: #19374F; }
QLabel#hint { color: #4B5E71; }
QLabel#fieldError { color: #A12B24; padding: 6px; }
QLabel[notice="true"] {
    background: #E6EEF6; color: #20344D; border: 1px solid #718096;
    border-radius: 4px; padding: 9px;
}
QLabel[tone="success"] { background: #EDF7F0; color: #215B37; border: 1px solid #377C55; }
QLabel[tone="error"] { background: #FFF1EF; color: #A12B24; border: 1px solid #A12B24; }
QLabel[tone="moving"] { background: #FFF4D6; color: #654700; border: 2px solid #826000; }
QToolBar { background: white; border-bottom: 1px solid #718096; padding: 5px; spacing: 5px; }
QToolBar QToolButton { border-color: transparent; padding: 5px 9px; }
QToolBar QToolButton:focus { border-color: #1458A8; }
QGroupBox {
    background: white; font-weight: 600; border: 1px solid #718096;
    border-radius: 5px; margin-top: 14px; padding: 18px 12px 12px;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; }
QTabWidget::pane { border: 1px solid #718096; background: #F4F6F9; }
QTabBar::tab {
    background: #E6ECF3; color: #20344D; border: 1px solid #718096;
    padding: 9px 22px; min-height: 20px;
}
QTabBar::tab:selected { background: white; border-bottom: 3px solid #205C86; font-weight: 600; }
QTabBar::tab:focus { border: 2px solid #1458A8; }
QCheckBox { spacing: 8px; padding: 4px 2px; }
QCheckBox:disabled { color: #536273; }
QCheckBox::indicator { width: 20px; height: 20px; }
QCheckBox:focus { outline: 2px solid #1458A8; }
QToolTip { background: #20344D; color: white; border: 1px solid #20344D; padding: 7px; }
QScrollArea { border: 0; background: #F4F6F9; }
QScrollBar:vertical { background: #EDF1F5; width: 16px; margin: 0; }
QScrollBar:horizontal { background: #EDF1F5; height: 16px; margin: 0; }
QScrollBar::handle { background: #697D90; border: 3px solid #EDF1F5; border-radius: 7px; }
QScrollBar::handle:vertical { min-height: 30px; }
QScrollBar::handle:horizontal { min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: #EDF1F5; }
QProgressBar { border: 1px solid #718096; border-radius: 3px; background: white; min-height: 10px; }
QProgressBar::chunk { background: #205C86; }
"""

CONTROL_STYLE = """
QComboBox { padding-right: 30px; }
QComboBox::drop-down { width: 28px; border-left: 1px solid #718096; }
QComboBox::down-arrow { image: url("DOWN"); width: 12px; height: 12px; }
QSpinBox, QDoubleSpinBox, QTimeEdit { padding-right: 28px; }
QSpinBox::up-button, QDoubleSpinBox::up-button, QTimeEdit::up-button {
    subcontrol-origin: border; subcontrol-position: top right;
    width: 26px; height: 18px; border-left: 1px solid #718096;
}
QSpinBox::down-button, QDoubleSpinBox::down-button, QTimeEdit::down-button {
    subcontrol-origin: border; subcontrol-position: bottom right;
    width: 26px; height: 18px; border-left: 1px solid #718096;
}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow, QTimeEdit::up-arrow {
    image: url("UP"); width: 12px; height: 12px;
}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QTimeEdit::down-arrow {
    image: url("DOWN"); width: 12px; height: 12px;
}
QCheckBox::indicator, QTreeView::indicator, QListView::indicator {
    width: 20px; height: 20px;
    background: white; border: 1px solid #718096; border-radius: 3px;
}
QCheckBox::indicator:checked, QTreeView::indicator:checked, QListView::indicator:checked {
    background: #205C86; image: url("CHECK");
}
QCheckBox::indicator:indeterminate, QTreeView::indicator:indeterminate,
QListView::indicator:indeterminate { background: #205C86; image: url("PARTIAL"); }
QCheckBox::indicator:disabled, QTreeView::indicator:disabled,
QListView::indicator:disabled { background: #E9EDF2; }
"""


def apply_theme(app: QApplication):
    """Set every native role explicitly, including unfocused/disabled controls."""
    if app.property("schoolThemeApplied"):
        return
    app.setStyle("Fusion")
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    palette = QPalette()
    roles = {
        "Window": WINDOW,
        "WindowText": TEXT,
        "Base": SURFACE,
        "AlternateBase": "#F0F4F8",
        "Text": TEXT,
        "Button": SURFACE,
        "ButtonText": TEXT,
        "BrightText": SURFACE,
        "Light": SURFACE,
        "Midlight": "#E6ECF3",
        "Mid": BORDER,
        "Dark": "#536273",
        "Shadow": TEXT,
        "Highlight": SELECTION,
        "HighlightedText": SURFACE,
        "ToolTipBase": TEXT,
        "ToolTipText": SURFACE,
        "PlaceholderText": MUTED,
        "Link": "#1458A8",
        "LinkVisited": "#654497",
        "Accent": PRIMARY,
    }
    for group in (
        QPalette.ColorGroup.Active,
        QPalette.ColorGroup.Inactive,
        QPalette.ColorGroup.Disabled,
    ):
        for name, color in roles.items():
            palette.setColor(group, getattr(QPalette.ColorRole, name), QColor(color))
    for name in ("WindowText", "Text", "ButtonText", "PlaceholderText"):
        palette.setColor(
            QPalette.ColorGroup.Disabled, getattr(QPalette.ColorRole, name), QColor(DISABLED_TEXT)
        )
    for name in ("Base", "Button"):
        palette.setColor(
            QPalette.ColorGroup.Disabled, getattr(QPalette.ColorRole, name), QColor(DISABLED)
        )
    app.setPalette(palette)
    app.setFont(QFont("Segoe UI", 11))
    controls = CONTROL_STYLE
    for token, name in (("UP", "up"), ("DOWN", "down"), ("CHECK", "check"), ("PARTIAL", "partial")):
        controls = controls.replace(
            token, files("school_timetable").joinpath(f"resources/{name}.svg").as_posix()
        )
    app.setStyleSheet(STYLE + controls)
    app.setProperty("schoolThemeApplied", True)


def status(widget, text, tone="info"):
    """A visible message always explains the state in words as well as color."""
    widget.setText(text)
    widget.setVisible(bool(text))
    widget.setAccessibleDescription(text)
    widget.setProperty("notice", True)
    widget.setProperty("tone", tone)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
