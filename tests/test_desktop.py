import time
from copy import deepcopy

import pytest
from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from school_timetable.editing import EditError, move_or_swap
from school_timetable.examples import example_school
from school_timetable.models import Teacher
from school_timetable.recovery import RecoveryStore
from school_timetable.scheduler import Outcome, Scheduler, SolveResult
from school_timetable.session import ProjectSession
from school_timetable.storage import load_project
from school_timetable.ui.dialogs import AvailabilityTree, DayDialog, RecordDialog, RequirementDialog
from school_timetable.ui.window import MainWindow
from school_timetable.validation import validate_schedule


def wait_for(qapp, predicate, seconds=10):
    deadline = time.monotonic() + seconds
    while not predicate() and time.monotonic() < deadline:
        qapp.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 30)
        time.sleep(0.005)
    assert predicate(), "Qt operation did not finish in time"


@pytest.fixture
def window(qapp, tmp_path):
    w = MainWindow(tmp_path, check_recovery=False)
    yield w
    if w.thread:
        w.cancel_generation()
        wait_for(qapp, lambda: w.thread is None)
    w.session.dirty = False
    w.close()
    qapp.processEvents()


def test_gui_generate_edit_lock_save_and_reopen(window, qapp, tmp_path):
    w = window
    p = example_school()
    p.settings.time_limit = 1
    w.replace_project(p)
    w.show()
    pulses = []
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: pulses.append(1))
    timer.start()
    w.generate()
    wait_for(qapp, lambda: w.thread is None)
    timer.stop()
    assert pulses  # UI event loop continued to process while the scheduler worked.
    assert validate_schedule(w.project) == []
    assert w.navigation.currentRow() == 5
    assert w.generate_button.isEnabled() and not w.cancel_button.isEnabled()
    chosen = next(lesson for lesson in p.lessons if len(lesson.slot_ids) == 1)
    requirement = p.lookup("requirements", chosen.requirement_id)
    w.view_record.setCurrentIndex(w.view_record.findData(requirement.class_id))
    source = next(position for position, cell in w.cell_map.items() if cell.lesson_id == chosen.id)
    destination = None
    for position, cell in w.cell_map.items():
        if cell.teaching and cell.lesson_id is None:
            try:
                move_or_swap(p, chosen.id, cell.slot_id)
                destination = position
                break
            except EditError:
                pass
    assert destination is not None
    w.cell_clicked(*source)
    w.arm_move()
    destination_id = w.cell_map[destination].slot_id
    w.cell_clicked(*destination)
    assert chosen.id in {lesson.id for lesson in p.lessons if lesson.slot_ids == [destination_id]}
    position = next(
        position for position, cell in w.cell_map.items() if cell.lesson_id == chosen.id
    )
    w.cell_clicked(*position)
    w.toggle_lock()
    assert next(lesson for lesson in p.lessons if lesson.id == chosen.id).locked
    w.undo()
    assert not next(lesson for lesson in p.lessons if lesson.id == chosen.id).locked
    w.redo()
    assert next(lesson for lesson in p.lessons if lesson.id == chosen.id).locked
    w.view_kind.setCurrentIndex(1)
    assert w.view_record.count() == len(p.teachers)
    w.view_kind.setCurrentIndex(2)
    assert w.review_table.columnCount() == len(p.classes)
    target = tmp_path / "term.schooltimetable"
    assert w.save_to(target)
    assert load_project(target) == p
    assert not w.session.dirty
    w.replace_project(load_project(target), target)
    assert validate_schedule(w.project) == []


def test_generation_failure_preserves_previous_schedule(window, qapp):
    p = example_school()
    p.settings.time_limit = 1
    result = Scheduler().solve(p)
    assert result.usable
    p.lessons = result.lessons
    window.replace_project(p)
    old = deepcopy(p.lessons)
    p.requirements[0].periods = 35
    window.data_changed()
    window.generate()
    wait_for(qapp, lambda: window.thread is None)
    assert p.lessons == old
    assert "cannot" in window.generation_status.text()
    assert "needs attention" in window.schedule_state.text()


def test_cancel_live_worker_and_reject_stale_results(window, qapp):
    p = example_school(class_count=20)
    p.settings.time_limit = 10
    window.replace_project(p)
    before = deepcopy(p.lessons)
    window.generate()
    QTimer.singleShot(50, window.cancel_generation)
    wait_for(qapp, lambda: window.thread is None)
    assert "cancelled" in window.generation_status.text().lower()
    assert p.lessons == before
    session = ProjectSession(example_school())
    session.project.settings.time_limit = 1
    revision = session.revision
    result = Scheduler().solve(session.project)
    assert result.usable
    session.project.teachers[0].name = "New name"
    session.changed(setup=True)
    assert not session.accept_result(result, revision)
    assert session.project.lessons == []
    old = deepcopy(session.project)
    failure = SolveResult(Outcome.CANCELLED, "Cancelled")
    assert not session.accept_result(failure, session.revision)
    assert session.project == old


def test_corrupt_open_preserves_current_project(window, monkeypatch, tmp_path):
    p = example_school()
    window.replace_project(p)
    bad = tmp_path / "damaged.schooltimetable"
    bad.write_text("damaged", encoding="utf-8")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: (str(bad), ""))
    errors = []
    monkeypatch.setattr(window, "show_error", lambda title, message: errors.append(message))
    window.open_project()
    assert window.project == p
    assert errors and "unchanged" in errors[0]


def test_forms_inline_validation_and_day_availability(qapp):
    p = example_school()
    dialog = RecordDialog(p, "teachers", Teacher())
    dialog.accept()
    assert dialog.result() != QDialog.DialogCode.Accepted
    assert "name" in dialog.error.text()
    dialog.name.setText(p.teachers[0].name)
    dialog.accept()
    assert "already" in dialog.error.text()
    tree = AvailabilityTree(p, [])
    tree.topLevelItem(0).setCheckState(0, Qt.CheckState.Checked)
    assert set(tree.selected()) == {s.id for s in p.days[0].slots if s.teaching}
    requirement = RequirementDialog(p, p.requirements[0])
    requirement.doubles.setValue(3)
    requirement.accept()
    assert "two periods" in requirement.error.text()
    day = deepcopy(p.days[0])
    day.slots[1].start = "08:30"
    form = DayDialog(p, day)
    form.accept()
    assert "overlap" in form.error.text()


def test_autosave_and_multiple_instance_recovery_safety(qapp, tmp_path):
    p = example_school()
    first, second = RecoveryStore(tmp_path), RecoveryStore(tmp_path)
    first.write(p)
    assert load_project(first.path) == p
    assert first.path not in second.candidates()
    first.lock.unlock()  # simulates a terminated previous session
    assert first.path in second.candidates()
    first.close()
    second.close()


def test_unsaved_prompt_cancel_and_window_autosave(window, monkeypatch, tmp_path):
    p = example_school()
    window.replace_project(p, dirty=True)
    window.autosave()
    assert load_project(window.recovery.path) == p
    monkeypatch.setattr(QMessageBox, "exec", lambda *_: QMessageBox.StandardButton.Cancel)
    window.new_project()
    assert window.project == p and window.session.dirty
    assert window.save_to(tmp_path / "kept.schooltimetable")
    assert not window.recovery.path.exists()


def test_ui_exports_selected_teacher_pdf_and_all_classes_excel(window, qapp, monkeypatch, tmp_path):
    from openpyxl import load_workbook
    from pypdf import PdfReader

    p = example_school()
    p.settings.time_limit = 1
    result = Scheduler().solve(p)
    assert result.usable
    p.lessons = result.lessons
    window.replace_project(p, dirty=True)
    xlsx = tmp_path / "all.xlsx"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_: (str(xlsx), ""))
    window.export_current()
    assert len(load_workbook(xlsx).worksheets) == 1 + len(p.classes)
    window.export_kind.setCurrentIndex(1)
    window.export_scope.setCurrentIndex(1)
    window.export_format.setCurrentIndex(1)
    pdf = tmp_path / "teacher.pdf"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_: (str(pdf), ""))
    window.export_current()
    assert len(PdfReader(pdf).pages) == 2
    assert window.session.dirty  # Export includes unsaved edits but is not a project save.
