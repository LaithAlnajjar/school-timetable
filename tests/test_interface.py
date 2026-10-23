"""Regressions for observed unreadable surfaces and interaction states."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QDialogButtonBox,
    QLineEdit,
    QPushButton,
    QTableWidgetItem,
)

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


@pytest.fixture
def interface_window(qapp, tmp_path):
    from school_timetable.ui.window import MainWindow

    w = MainWindow(tmp_path, check_recovery=False)
    w.show()
    yield w
    w.session.dirty = False
    w.close()


@pytest.fixture(scope="module")
def solved_school():
    from school_timetable.examples import example_school
    from school_timetable.scheduler import Scheduler

    project = example_school()
    project.settings.time_limit = 1
    result = Scheduler().solve(project)
    assert result.usable
    project.lessons = result.lessons
    project.scheduled_fingerprint = project.fingerprint()
    return project


def test_keyboard_select_move_reject_cancel_and_undo(interface_window, solved_school):
    from copy import deepcopy

    w = interface_window
    w.replace_project(deepcopy(solved_school))
    w.navigation.setCurrentRow(5)
    table = w.review_table
    source = next(pos for pos, cell in w.cell_map.items() if cell.lesson_id)
    table.setCurrentCell(*source)
    table.setFocus()
    QTest.qWait(20)
    assert w.selected_lesson == w.cell_map[source].lesson_id
    assert w.move_button.isEnabled() and not w.cancel_move_button.isEnabled()
    QTest.keyClick(w, Qt.Key.Key_M, Qt.KeyboardModifier.AltModifier)
    QTest.qWait(130)  # QPushButton shortcuts use Qt's normal animated activation.
    assert w.pending_lesson == w.selected_lesson
    assert w.cancel_move_button.isEnabled() and not w.move_button.isEnabled()
    before = deepcopy(w.project.lessons)
    blocked = next(pos for pos, cell in w.cell_map.items() if not cell.teaching)
    table.setCurrentCell(*blocked)
    QTest.keyClick(table, Qt.Key.Key_Return)
    assert w.project.lessons == before
    assert w.pending_lesson and "rejected" in w.edit_help.text()
    assert w.edit_help.property("tone") == "error"
    QTest.keyClick(w, Qt.Key.Key_Escape)
    assert w.pending_lesson is None
    assert not w.cancel_move_button.isEnabled()
    table.setCurrentCell(*source)
    w.toggle_lock()
    assert w.lock_button.isEnabled() and w.lock_button.text() == "Unlock lesson"
    assert w.undo_button.isEnabled()
    QTest.keyClick(w, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert w.project.lessons == before
    assert w.redo_button.isEnabled()


def test_view_change_cancels_move_and_export_explains_unavailable(interface_window, solved_school):
    from copy import deepcopy

    w = interface_window
    assert not w.export_button.isEnabled()
    assert "Generate" in w.export_status.text()
    w.replace_project(deepcopy(solved_school))
    assert w.export_button.isEnabled()
    assert w.export_status.text() == ""
    source = next(pos for pos, cell in w.cell_map.items() if cell.lesson_id)
    w.cell_clicked(*source)
    w.arm_move()
    w.view_kind.setCurrentIndex(1)
    assert w.pending_lesson is None and w.selected_lesson is None
    assert not w.move_button.isEnabled() and not w.lock_button.isEnabled()
    w.project.requirements[0].periods = 999
    w.data_changed()
    assert not w.export_button.isEnabled()
    assert w.schedule_state.property("tone") == "error"
    assert "Review" in w.export_status.text()


def test_small_window_can_scroll_every_action_into_view(interface_window, solved_school):
    from copy import deepcopy

    w = interface_window
    w.replace_project(deepcopy(solved_school))
    w.resize(820, 480)
    QTest.qWait(30)
    assert w.size().width() == 820
    assert not w.checklist.isVisible()
    for index in range(7):
        w.navigation.setCurrentRow(index)
        area = w.pages.widget(index)
        for control in area.findChildren(QPushButton):
            if not control.isVisibleTo(area):
                continue
            area.ensureWidgetVisible(control)
            QTest.qWait(5)
            bounds = control.rect().translated(
                control.mapTo(area.viewport(), control.rect().topLeft())
            )
            assert area.viewport().rect().contains(bounds), (index, control.text(), bounds)


def test_long_lesson_rewraps_when_column_is_resized(interface_window, solved_school):
    from copy import deepcopy

    from PySide6.QtWidgets import QStyleOptionViewItem

    w = interface_window
    project = deepcopy(solved_school)
    project.subjects[0].name = "Mathematics " * 12
    project.teachers[0].name = "Alexandra Montgomery " * 7
    w.replace_project(project)
    w.navigation.setCurrentRow(5)
    pos = next(pos for pos, cell in w.cell_map.items() if "Mathematics" in cell.text)
    row, col = pos
    w.review_table.setColumnWidth(col, 360)
    tall = w.review_table.rowHeight(row)
    w.review_table.setColumnWidth(col, 190)
    assert w.review_table.rowHeight(row) >= tall
    option = QStyleOptionViewItem()
    hint = w.review_table.itemDelegate().sizeHint(option, w.review_table.model().index(row, col))
    assert w.review_table.rowHeight(row) >= hint.height()


def test_dialog_validation_labels_tab_order_and_hidden_advanced(qapp):
    from school_timetable.examples import example_school
    from school_timetable.ui.dialogs import RequirementDialog

    apply_theme(qapp)
    dialog = RecordDialog(example_school(), "teachers", Teacher())
    dialog.show()
    QTest.qWait(10)
    assert not dialog.advanced_body.isVisible()
    dialog.name.setFocus()
    assert dialog.name.accessibleName() == "Name"
    QTest.keyClick(dialog.name, Qt.Key.Key_Tab)
    assert QApplication.focusWidget() is dialog.advanced_toggle
    dialog.accept()
    assert dialog.error.isVisible() and dialog.name.property("invalid")
    assert QApplication.focusWidget() is dialog.name
    QTest.keyClicks(dialog.name, "Mrs Example")
    assert not dialog.error.isVisible() and not dialog.name.property("invalid")
    dialog.reject()
    form = RequirementDialog(example_school())
    form.show()
    form.periods.setValue(1)
    form.doubles.setValue(2)
    form.accept()
    assert form.advanced_toggle.isChecked()
    assert form.doubles.isVisible() and form.error.isVisible()
    for field in form.findChildren(QLineEdit):
        assert field.focusPolicy() != Qt.FocusPolicy.NoFocus
    form.reject()


def test_form_controls_expose_label_names_to_accessibility(qapp):
    from PySide6.QtGui import QAccessible

    from school_timetable.examples import example_school
    from school_timetable.ui.dialogs import RequirementDialog, SlotDialog

    project = example_school()
    for form in (RequirementDialog(project), SlotDialog(project.days[0].slots[0])):
        for row in range(form.form.rowCount()):
            field = form.form.itemAt(row, form.form.ItemRole.FieldRole)
            label_item = form.form.itemAt(row, form.form.ItemRole.LabelRole)
            if field and label_item and field.widget():
                interface = QAccessible.queryAccessibleInterface(field.widget())
                assert interface.text(QAccessible.Text.Name), label_item.widget().text()
        form.reject()
