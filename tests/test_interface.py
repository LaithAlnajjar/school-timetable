"""Regressions for observed unreadable surfaces and interaction states."""

import pytest
from PySide6.QtGui import QColor, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialogButtonBox, QTableWidgetItem

from school_timetable.models import Teacher
from school_timetable.ui.dialogs import RecordDialog, readonly_table
from school_timetable.ui.theme import BORDER, DISABLED, DISABLED_TEXT, FOCUS, TEXT, apply_theme
from school_timetable.views import PALETTE


def contrast(a, b):
    def luminance(value):
        color = QColor(value)
        channels = [color.redF(), color.greenF(), color.blueF()]
        channels = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return sum(c * weight for c, weight in zip(channels, (0.2126, 0.7152, 0.0722), strict=True))

    low, high = sorted((luminance(a), luminance(b)))
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize("group", [QPalette.Active, QPalette.Inactive, QPalette.Disabled])
def test_native_palette_contrast_in_every_activation_group(qapp, group):
    # Reproduce Windows dark appearance leaking through the former mixed theme.
    dark = QPalette()
    dark.setColor(QPalette.Window, QColor("#323232"))
    qapp.setPalette(dark)
    qapp.setProperty("schoolThemeApplied", False)
    apply_theme(qapp)
    palette = qapp.palette()
    for foreground, background in (
        (QPalette.WindowText, QPalette.Window),
        (QPalette.Text, QPalette.Base),
        (QPalette.ButtonText, QPalette.Button),
        (QPalette.HighlightedText, QPalette.Highlight),
        (QPalette.PlaceholderText, QPalette.Base),
        (QPalette.ToolTipText, QPalette.ToolTipBase),
    ):
        assert contrast(palette.color(group, foreground), palette.color(group, background)) >= 4.5
    assert contrast(BORDER, palette.color(group, QPalette.Base)) >= 3
    assert contrast(FOCUS, palette.color(group, QPalette.Window)) >= 3
    assert contrast(DISABLED_TEXT, DISABLED) >= 4.5


def test_rendered_dialog_scroll_surface_and_selected_table(qapp, tmp_path):
    from school_timetable.examples import example_school
    from school_timetable.ui.window import MainWindow

    w = MainWindow(tmp_path, check_recovery=False)
    dialog = RecordDialog(example_school(), "teachers", Teacher(), w)
    dialog.show()
    QTest.qWait(20)
    surface = dialog.form.parentWidget()
    # A real rendered pixel in the form body was #323232 with dark text before.
    assert contrast(TEXT, surface.grab().toImage().pixelColor(surface.width() - 5, 100)) >= 4.5
    dialog.buttons.button(QDialogButtonBox.Ok).setEnabled(False)
    disabled = dialog.buttons.button(QDialogButtonBox.Ok).palette()
    assert (
        contrast(
            disabled.color(QPalette.Disabled, QPalette.ButtonText),
            disabled.color(QPalette.Disabled, QPalette.Button),
        )
        >= 4.5
    )
    table = readonly_table(["Name"])
    table.setRowCount(1)
    table.setItem(0, 0, QTableWidgetItem("Mrs Smith"))
    table.show()
    table.setCurrentCell(0, 0)
    table.setFocus()
    QTest.qWait(20)
    rect = table.visualItemRect(table.item(0, 0))
    image = table.viewport().grab().toImage()
    background = image.pixelColor(rect.right() - 10, rect.center().y())
    assert contrast("white", background) >= 4.5
    assert table.fontMetrics().height() >= 16
    table.close()
    dialog.reject()
    w.close()


def test_every_subject_and_break_background_has_readable_text():
    for background in (*PALETTE, "#FFFFFF", "#EBEEF2"):
        assert contrast(TEXT, background) >= 4.5
