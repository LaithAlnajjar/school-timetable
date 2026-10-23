"""Guided offline desktop workflow. Domain state lives in ProjectSession."""

from __future__ import annotations

import logging
import time
from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QColor, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..editing import EditError, move_or_swap
from ..examples import example_school
from ..exports import ExportError, export_excel, export_pdf
from ..models import Day, Project, new_id, teaching_slots
from ..recovery import RecoveryStore
from ..scheduler import preflight
from ..session import ProjectSession
from ..storage import ProjectFileError, load_project, save_project
from ..validation import validate_schedule, validate_setup
from ..views import timetable
from .dialogs import DayDialog, FormDialog, RequirementDialog, button, label, readonly_table
from .records import RecordsPanel
from .theme import apply_theme, status
from .widgets import CELL_ROLE, ActionFlow, LessonDelegate, WrappedHeader, fit_setup_table
from .worker import GenerationThread


class MainWindow(QMainWindow):
    def __init__(self, app_data: Path, *, check_recovery=True):
        super().__init__()
        apply_theme(QApplication.instance())
        self.resize(1280, 860)
        self.setMinimumSize(760, 440)
        self.session = ProjectSession()
        self.recovery = RecoveryStore(app_data)
        self.thread: GenerationThread | None = None
        self.rendering = False
        self.close_when_finished = False
        self.pending_lesson: str | None = None
        self.selected_lesson: str | None = None
        self.cell_map = {}
        self.record_panels = []
        self._make_toolbar()
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(16, 16, 16, 16)
        side = QVBoxLayout()
        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")
        self.navigation.setFixedWidth(215)
        self.navigation.setAccessibleName("Workflow steps")
        self.navigation.addItems(
            [
                "1  School week",
                "2  Teachers",
                "3  Classes and subjects",
                "4  Lesson requirements",
                "5  Generate",
                "6  Review and edit",
                "7  Export",
            ]
        )
        side.addWidget(self.navigation)
        self.checklist = label("")
        self.checklist.setFixedWidth(215)
        self.checklist.setObjectName("hint")
        side.addWidget(self.checklist)
        outer.addLayout(side)
        self.pages = QStackedWidget()
        outer.addWidget(self.pages, 1)
        self.navigation.currentRowChanged.connect(self.pages.setCurrentIndex)
        self._make_week()
        self._make_records()
        self._make_requirements()
        self._make_generation()
        self._make_review()
        self._make_export()
        self.navigation.setCurrentRow(0)
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(2000)
        self.debounce.timeout.connect(self.autosave)
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(30000)
        self.autosave_timer.timeout.connect(self.autosave)
        self.autosave_timer.start()
        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.setInterval(500)
        self.elapsed_timer.timeout.connect(self.update_elapsed)
        self.refresh()
        if check_recovery:
            QTimer.singleShot(0, self.offer_recovery)

    @property
    def project(self):
        return self.session.project

    def _make_toolbar(self):
        toolbar = QToolBar("Project")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        for text, callback, shortcut in (
            ("New", self.new_project, QKeySequence.StandardKey.New),
            ("Open…", self.open_project, QKeySequence.StandardKey.Open),
            ("Save", self.save, QKeySequence.StandardKey.Save),
            ("Save As…", self.save_as, QKeySequence.StandardKey.SaveAs),
            ("Load example school", self.load_example, None),
            ("Help", self.help, QKeySequence.StandardKey.HelpContents),
        ):
            action = QAction(text, self)
            action.setToolTip(
                text + (f" ({QKeySequence(shortcut).toString()})" if shortcut else "")
            )
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
            elif text == "Load example school":
                action.setShortcut(QKeySequence("Ctrl+Shift+L"))
            action.triggered.connect(callback)
            toolbar.addAction(action)
            toolbar.widgetForAction(action).setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        for text, keys, callback in (
            ("Undo timetable edit", QKeySequence.StandardKey.Undo, self.undo),
            ("Redo timetable edit", QKeySequence.StandardKey.Redo, self.redo),
            ("Cancel lesson move", "Escape", self.cancel_move),
        ):
            action = QAction(text, self)
            action.setShortcuts(
                QKeySequence.keyBindings(keys)
                if not isinstance(keys, str)
                else [QKeySequence(keys)]
            )
            action.triggered.connect(callback)
            self.addAction(action)
        for index in range(7):
            action = QAction(self)
            action.setShortcut(QKeySequence(f"Alt+{index + 1}"))
            action.triggered.connect(lambda _=False, row=index: self.navigation.setCurrentRow(row))
            self.addAction(action)

    def page(self, title, explanation):
        # Every page can scroll at high scaling or on a smaller display. Tables
        # retain their own two-axis scrolling for larger schools.
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QScrollArea.Shape.NoFrame)
        area.setAccessibleName(title)
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 4, 6, 4)
        layout.setSpacing(12)
        heading = label(title)
        heading.setObjectName("pageTitle")
        layout.addWidget(heading)
        subtitle = label(explanation)
        subtitle.setObjectName("hint")
        layout.addWidget(subtitle)
        area.setWidget(page)
        self.pages.addWidget(area)
        return layout

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "checklist"):
            self.checklist.setVisible(self.height() >= 700)

    def _make_week(self):
        layout = self.page(
            "Your school week",
            "Start here. Choose your operating days, teaching periods and breaks.",
        )
        row = QHBoxLayout()
        name_label = label("School name")
        row.addWidget(name_label)
        self.school_name = QLineEdit()
        self.school_name.setMaxLength(180)
        self.school_name.setPlaceholderText("For example, Willow Secondary")
        self.school_name.setAccessibleName("School name")
        name_label.setBuddy(self.school_name)
        self.school_name.textEdited.connect(self.school_name_changed)
        row.addWidget(self.school_name, 1)
        layout.addLayout(row)
        self.day_table = readonly_table(["Day", "Teaching periods", "All periods / breaks"])
        self.day_table.setAccessibleName("School days and periods")
        self.day_table.set_empty(
            "Your week starts here.\nChoose Add day, or Load example school above."
        )
        self.day_table.cellActivated.connect(lambda *_: self.edit_day())
        layout.addWidget(self.day_table)
        controls = ActionFlow()
        for text, callback in (
            ("Add day", self.add_day),
            ("Edit day", self.edit_day),
            ("Delete day", self.delete_day),
            ("Copy pattern…", self.copy_day),
        ):
            button(text, callback, controls)
        layout.addLayout(controls)
        self.week_error = label(
            "Tip: add a day, then use the starter pattern or enter your own "
            "periods. You can begin with Load example school above."
        )
        self.week_error.setObjectName("hint")
        layout.addWidget(self.week_error)
        self.next_button(layout, 1)

    def _make_records(self):
        layout = self.page(
            "Teachers",
            (
                "Enter the teachers who will deliver your lessons. The generator "
                "uses the teachers you assign."
            ),
        )
        panel = RecordsPanel(self, "teachers")
        self.record_panels.append(panel)
        layout.addWidget(panel)
        self.next_button(layout, 2)
        layout = self.page(
            "Classes and subjects",
            "A class is a teaching group, such as 7A or Grade 10B. Add subjects in the second tab.",
        )
        tabs = QTabWidget()
        for collection, title in (("classes", "Classes"), ("subjects", "Subjects")):
            panel = RecordsPanel(self, collection)
            self.record_panels.append(panel)
            tabs.addTab(panel, title)
        layout.addWidget(tabs)
        self.next_button(layout, 3)

    def _make_requirements(self):
        layout = self.page(
            "What needs to be taught?",
            (
                "One row for each class and subject. Assign its teacher and total "
                "teaching periods per week."
            ),
        )
        self.requirements_table = readonly_table(
            ["Class", "Subject", "Assigned teacher", "Periods / week", "Doubles"]
        )
        self.requirements_table.setAccessibleName("Weekly lesson requirements")
        self.requirements_table.set_empty(
            "No lesson requirements yet.\nAdd your classes, subjects and teachers, "
            "then choose Add lesson requirement."
        )
        self.requirements_table.cellActivated.connect(lambda *_: self.edit_requirement())
        layout.addWidget(self.requirements_table)
        controls = ActionFlow()
        button("Add lesson requirement", self.add_requirement, controls)
        button("Edit selected", self.edit_requirement, controls)
        button("Delete selected", self.delete_requirement, controls)
        layout.addLayout(controls)
        self.loads = QTextBrowser()
        self.loads.setAccessibleName("Class and teacher teaching loads")
        self.loads.setMaximumHeight(155)
        layout.addWidget(self.loads)
        self.next_button(layout, 4)

    def _make_generation(self):
        layout = self.page(
            "Make a weekly timetable",
            (
                "All required lessons must fit. Free periods are allowed. Existing"
                " locked lessons stay in place."
            ),
        )
        controls = QHBoxLayout()
        self.generate_button = button("Generate timetable", self.generate, controls)
        self.generate_button.setObjectName("primary")
        self.cancel_button = button("Cancel generation", self.cancel_generation, controls)
        self.cancel_button.setEnabled(False)
        controls.addStretch()
        self.elapsed = label("")
        controls.addWidget(self.elapsed)
        layout.addLayout(controls)
        self.generation_status = label("Ready when your setup checklist is complete.")
        self.generation_status.setObjectName("generationStatus")
        status(self.generation_status, self.generation_status.text())
        layout.addWidget(self.generation_status)
        self.generation_progress = QProgressBar()
        self.generation_progress.setRange(0, 0)
        self.generation_progress.setTextVisible(False)
        self.generation_progress.setAccessibleName("Generating timetable")
        self.generation_progress.hide()
        layout.addWidget(self.generation_progress)
        self.generation_details = QTextBrowser()
        self.generation_details.setMinimumHeight(160)
        self.generation_details.setMaximumHeight(240)
        self.generation_details.setAccessibleName("Setup checks and generation results")
        layout.addWidget(self.generation_details)
        toggle = QCheckBox("Advanced planning settings (optional)")
        layout.addWidget(toggle)
        advanced = QWidget()
        advanced.setVisible(False)
        toggle.toggled.connect(advanced.setVisible)
        box = QVBoxLayout(advanced)
        box.addWidget(
            label(
                "Mandatory rules are configured under each teacher or lesson "
                "requirement. Preferences help when possible."
            )
        )
        row = QFormLayout()
        self.search_limit = QDoubleSpinBox()
        self.search_limit.setRange(0.01, 3600)
        self.search_limit.setDecimals(2)
        self.search_limit.setSingleStep(5)
        self.search_limit.valueChanged.connect(self.settings_changed)
        row.addRow("Search limit (seconds)", self.search_limit)
        box.addLayout(row)
        box.addWidget(
            label(
                "The search limit applies to solving. Preparing and checking the "
                "timetable may take extra time. A time limit is not proof of "
                "impossibility."
            )
        )
        self.reduce_gaps = QCheckBox("Prefer reducing teachers' free periods between lessons")
        self.rooms_enabled = QCheckBox("Enable specialist room planning")
        for widget in (self.reduce_gaps, self.rooms_enabled):
            widget.toggled.connect(self.settings_changed)
            box.addWidget(widget)
        panel = RecordsPanel(self, "rooms")
        self.record_panels.append(panel)
        box.addWidget(panel)
        box.addWidget(
            label(
                "After adding rooms, edit a lesson requirement's advanced options "
                "to select suitable rooms."
            )
        )
        layout.addWidget(advanced)
        layout.addStretch()

    def _make_review(self):
        layout = self.page(
            "Review and adjust",
            (
                "Select a lesson, choose Move / swap, then click a destination "
                "period. Every edit is checked before it is applied."
            ),
        )
        self.schedule_state = label("")
        self.schedule_state.setObjectName("scheduleState")
        layout.addWidget(self.schedule_state)
        row = QHBoxLayout()
        self.view_kind = QComboBox()
        self.view_kind.setAccessibleName("Timetable view")
        self.view_kind.addItems(["Class timetable", "Teacher timetable", "School overview"])
        self.view_kind.currentIndexChanged.connect(self.view_changed)
        self.view_record = QComboBox()
        self.view_record.setAccessibleName("Class or teacher to review")
        self.view_record.currentIndexChanged.connect(self.review_record_changed)
        row.addWidget(self.view_kind)
        row.addWidget(self.view_record, 1)
        layout.addLayout(row)
        self.review_table = readonly_table([])
        self.review_table.setAccessibleName("Editable timetable")
        self.review_table.setAccessibleDescription(
            "Use arrow keys to select a lesson, Alt+M to move, Enter to choose a destination, "
            "Escape to cancel."
        )
        self.review_table.set_empty(
            "No timetable yet.\nComplete your setup, then choose Generate (step 5)."
        )
        self.review_table.setMinimumHeight(240)
        self.review_table.setHorizontalHeader(WrappedHeader(self.review_table))
        self.review_table.setItemDelegate(LessonDelegate(self))
        self.review_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.review_table.setSelectionBehavior(self.review_table.SelectionBehavior.SelectItems)
        self.review_table.cellClicked.connect(self.cell_clicked)
        self.review_table.cellActivated.connect(self.cell_clicked)
        self.review_table.currentCellChanged.connect(self.review_selection_changed)
        self.review_table.horizontalHeader().sectionResized.connect(self.resize_review_rows)
        layout.addWidget(self.review_table, 1)
        self.edit_help = label("Select a lesson to move it or change its lock.")
        self.edit_help.setObjectName("editHelp")
        layout.addWidget(self.edit_help)
        row = QHBoxLayout()
        self.move_button = button("Move / swap lesson", self.arm_move, row)
        self.move_button.setObjectName("primary")
        self.move_button.setShortcut(QKeySequence("Alt+M"))
        self.move_button.setToolTip("Move or swap the selected lesson block (Alt+M)")
        self.cancel_move_button = button("Cancel move (Esc)", self.cancel_move, row)
        self.lock_button = button("Lock lesson", self.toggle_lock, row)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.undo_button = button("Undo", self.undo, row)
        self.redo_button = button("Redo", self.redo, row)
        self.unlock_all_button = button("Unlock all lessons", self.unlock_all, row)
        layout.addLayout(row)
        self.schedule_problems = QTextBrowser()
        self.schedule_problems.setMaximumHeight(100)
        layout.addWidget(self.schedule_problems)

    def _make_export(self):
        layout = self.page(
            "Share your timetables",
            (
                "Export the current edited timetable. All mandatory rules must "
                "pass before a final export can be created."
            ),
        )
        group = QGroupBox("Choose your export")
        form = QFormLayout(group)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setVerticalSpacing(14)
        self.export_kind = QComboBox()
        self.export_kind.addItems(["Class timetables", "Teacher timetables"])
        self.export_kind.currentIndexChanged.connect(self.refresh_export_records)
        self.export_scope = QComboBox()
        self.export_scope.addItems(["All timetables", "One selected timetable"])
        self.export_scope.currentIndexChanged.connect(self.refresh_export_records)
        self.export_record = QComboBox()
        self.export_format = QComboBox()
        self.export_format.addItems(["Excel workbook (.xlsx)", "Printable PDF (.pdf)"])
        for text, widget in (
            ("Timetables for", self.export_kind),
            ("Include", self.export_scope),
            ("Selected class or teacher", self.export_record),
            ("File type", self.export_format),
        ):
            form.addRow(text, widget)
            widget.setAccessibleName(text)
        self.export_button = QPushButton("Export timetable…")
        self.export_button.setObjectName("primary")
        self.export_button.clicked.connect(self.export_current)
        form.addRow(self.export_button)
        layout.addWidget(group)
        layout.addWidget(
            label(
                "Excel is not needed to create a workbook. PDFs can contain "
                "several timetables and split wide weeks across pages.\n\nUnsaved "
                "edits are included in the export. Use Save as well to keep the "
                "editable school project."
            )
        )
        self.export_status = label("")
        layout.addWidget(self.export_status)
        layout.addStretch()

    def next_button(self, layout, index):
        row = QHBoxLayout()
        row.addStretch()
        names = (
            "School week",
            "Teachers",
            "Classes and subjects",
            "Lesson requirements",
            "Generate",
        )
        widget = button(
            f"Next: {names[index]} →", lambda: self.navigation.setCurrentRow(index), row
        )
        widget.setObjectName("primary")
        layout.addLayout(row)

    def data_changed(self):
        self.session.changed(setup=True)
        self.pending_lesson = self.selected_lesson = None
        self.debounce.start()
        self.refresh()

    def school_name_changed(self, text):
        self.project.school_name = text
        self.session.changed(setup=True)
        self.debounce.start()
        self.refresh_status()

    def settings_changed(self, *_):
        if self.rendering:
            return
        self.project.settings.time_limit = float(self.search_limit.value())
        self.project.settings.rooms_enabled = self.rooms_enabled.isChecked()
        self.project.settings.reduce_gaps = self.reduce_gaps.isChecked()
        self.data_changed()

    def refresh(self):
        self.rendering = True
        self.school_name.setText(self.project.school_name)
        self.day_table.setRowCount(len(self.project.days))
        for row, day in enumerate(self.project.days):
            for col, text in enumerate(
                (day.name, str(sum(s.teaching for s in day.slots)), str(len(day.slots)))
            ):
                self.day_table.setItem(row, col, QTableWidgetItem(text))
        fit_setup_table(self.day_table)
        for panel in self.record_panels:
            panel.refresh()
        self.requirements_table.setRowCount(len(self.project.requirements))
        for row, r in enumerate(self.project.requirements):
            names = []
            for collection, record_id in (
                ("classes", r.class_id),
                ("subjects", r.subject_id),
                ("teachers", r.teacher_id),
            ):
                record = self.project.lookup(collection, record_id)
                names.append(record.name if record else "Missing - edit this row")
            for col, text in enumerate([*names, str(r.periods), str(r.doubles)]):
                self.requirements_table.setItem(row, col, QTableWidgetItem(text))
        fit_setup_table(self.requirements_table)
        loads = ["Class totals (unused periods remain free):"]
        capacity = len(teaching_slots(self.project))
        for group in self.project.classes:
            required = sum(r.periods for r in self.project.requirements if r.class_id == group.id)
            loads.append(f"{group.name}: {required} required / {capacity} available periods")
        loads.append("\nTeacher assigned teaching load:")
        for teacher in self.project.teachers:
            required = sum(
                r.periods for r in self.project.requirements if r.teacher_id == teacher.id
            )
            loads.append(f"{teacher.name}: {required} periods per week")
        if not self.project.requirements:
            loads.append("\nNo lesson requirements yet. Use Add lesson requirement to begin.")
        self.loads.setPlainText("\n".join(loads))
        self.search_limit.setValue(self.project.settings.time_limit)
        self.rooms_enabled.setChecked(self.project.settings.rooms_enabled)
        self.reduce_gaps.setChecked(self.project.settings.reduce_gaps)
        self.rendering = False
        self.view_changed()
        self.refresh_export_records()
        self.refresh_status()

    def refresh_status(self):
        setup = validate_setup(self.project)
        groups = [
            ("School week", ("days", "school_name")),
            ("Teachers", ("teachers",)),
            ("Classes & subjects", ("classes", "subjects")),
            ("Lesson requirements", ("requirements",)),
        ]
        checklist = ["SETUP PROGRESS"]
        for name, paths in groups:
            bad = any(
                any(i.path == path or i.path.startswith(path + ".") for path in paths)
                for i in setup
            )
            checklist.append(("To do: " if bad else "Done: ") + name)
        self.checklist.setText("\n".join(checklist))
        path = self.session.path.name if self.session.path else "New project"
        self.setWindowTitle(f"{'* ' if self.session.dirty else ''}School Timetable — {path}")
        self.statusBar().showMessage(
            (
                "Unsaved changes"
                if self.session.dirty
                else "Saved"
                if self.session.path
                else "New project"
            )
            + (
                f"  |  {self.session.path}"
                if self.session.path
                else "  |  Choose Save to keep your work"
            )
        )
        if not self.thread:
            problems = preflight(self.project)
            self.generation_details.setPlainText(
                "\n".join(dict.fromkeys(i.message for i in problems))
                or "Your setup is ready. Generate to place the requested lessons."
            )
        schedule_issues = validate_schedule(self.project)
        if not self.project.lessons:
            state = "No timetable yet. Complete setup, then choose Generate."
        elif schedule_issues:
            state = (
                "This timetable needs attention. Correct the problems below or "
                "regenerate; final exports are blocked."
            )
        elif self.project.scheduled_fingerprint != self.project.fingerprint():
            state = (
                "School data changed. The current timetable was rechecked and "
                "still satisfies all mandatory rules."
            )
        else:
            state = "Valid timetable • All mandatory rules checked • Ready to export"
        status(
            self.schedule_state,
            state,
            "error"
            if self.project.lessons and schedule_issues
            else "success"
            if self.project.lessons
            else "info",
        )
        self.export_button.setEnabled(bool(self.project.lessons) and not schedule_issues)
        if not self.project.lessons:
            status(self.export_status, "Generate a timetable in step 5 before exporting.")
        elif schedule_issues:
            status(
                self.export_status,
                "Export is unavailable. Review the timetable problems in step 6.",
                "error",
            )
        elif self.export_status.text().startswith(
            ("Generate a timetable", "Export is unavailable.")
        ):
            status(self.export_status, "")
        self.schedule_problems.setVisible(bool(schedule_issues and self.project.lessons))
        self.schedule_problems.setPlainText(
            "\n".join(dict.fromkeys(i.message for i in schedule_issues))
        )
        self.undo_button.setEnabled(bool(self.session.history.undo_stack))
        self.redo_button.setEnabled(bool(self.session.history.redo_stack))
        self.update_edit_controls()

    def add_day(self):
        self.day_dialog(Day(name=f"Day {len(self.project.days) + 1}"))

    def edit_day(self):
        row = self.day_table.currentRow()
        if row >= 0:
            self.day_dialog(self.project.days[row])
        else:
            self.week_error.setText("Select a day to edit.")

    def day_dialog(self, day):
        dialog = DayDialog(self.project, day, self)
        if dialog.exec():
            index = next((i for i, d in enumerate(self.project.days) if d.id == day.id), None)
            if index is None:
                self.project.days.append(dialog.day)
            else:
                self.project.days[index] = dialog.day
            self.data_changed()

    def delete_day(self):
        row = self.day_table.currentRow()
        if row < 0:
            self.week_error.setText("Select a day to delete.")
            return
        if (
            QMessageBox.question(
                self,
                "Delete day",
                (
                    "Delete this day and all its periods? Existing lessons, locks and "
                    "unavailable-period rules will be rechecked and may need "
                    "correction."
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.project.days.pop(row)
            self.data_changed()

    def copy_day(self):
        row = self.day_table.currentRow()
        if row < 0:
            self.week_error.setText("Select the day whose pattern you want to copy.")
            return
        source = self.project.days[row]
        dialog = FormDialog("Copy daily pattern", self)
        dialog.buttons.button(dialog.buttons.StandardButton.Ok).setText("Copy pattern")
        dialog.form.addRow(
            label(
                "Select the days to replace. Existing locks and unavailable-period"
                " rules for replaced periods may need correction."
            )
        )
        targets = QListWidget()
        for day in self.project.days:
            if day.id != source.id:
                item = QListWidgetItem(day.name, targets)
                item.setData(Qt.ItemDataRole.UserRole, day.id)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
        dialog.form.addRow(targets)
        if dialog.exec():
            ids = {
                targets.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(targets.count())
                if targets.item(i).checkState() == Qt.CheckState.Checked
            }
            if not ids:
                return
            for day in self.project.days:
                if day.id in ids:
                    day.slots = deepcopy(source.slots)
                    for slot in day.slots:
                        slot.id = new_id()
            self.data_changed()

    def add_requirement(self):
        self.requirement_dialog()

    def edit_requirement(self):
        row = self.requirements_table.currentRow()
        if row >= 0:
            self.requirement_dialog(self.project.requirements[row])

    def requirement_dialog(self, requirement=None):
        dialog = RequirementDialog(self.project, requirement, self)
        if dialog.exec():
            r = dialog.requirement
            index = next(
                (i for i, old in enumerate(self.project.requirements) if old.id == r.id), None
            )
            if index is None:
                self.project.requirements.append(r)
            else:
                self.project.requirements[index] = r
            self.data_changed()

    def delete_requirement(self):
        row = self.requirements_table.currentRow()
        if row < 0:
            return
        if (
            QMessageBox.question(
                self,
                "Delete lesson requirement",
                "Delete this requirement and its scheduled lessons and locks?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            r = self.project.requirements.pop(row)
            self.project.lessons = [
                lesson for lesson in self.project.lessons if lesson.requirement_id != r.id
            ]
            self.data_changed()

    def generate(self):
        if self.thread is not None:
            return
        self.thread = GenerationThread(self.project, self.session.revision, self)
        self.thread.status.connect(lambda text: status(self.generation_status, text))
        self.thread.completed.connect(self.generation_finished)
        self.thread.finished.connect(self.worker_finished)
        self.generate_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.generation_progress.show()
        status(self.generation_status, "Generating timetable… Your previous timetable is safe.")
        self.generation_details.clear()
        self.pages.widget(4).verticalScrollBar().setValue(0)
        self.started_at = time.monotonic()
        self.elapsed_timer.start()
        self.thread.start()

    def cancel_generation(self):
        if self.thread:
            self.thread.cancel()
            self.cancel_button.setEnabled(False)
            status(
                self.generation_status,
                "Cancelling generation… Your previous timetable will be kept.",
            )

    def update_elapsed(self):
        self.elapsed.setText(f"Elapsed: {time.monotonic() - self.started_at:.1f} seconds")

    def generation_finished(self, result):
        self.last_result = result
        accepted = self.session.accept_result(result, self.thread.revision)
        if result.usable and not accepted:
            message = (
                "School data or timetable edits changed during generation. This "
                "result was discarded. Generate again to use the latest changes."
            )
        else:
            message = result.message
        if accepted:
            self.pending_lesson = self.selected_lesson = None
            self.debounce.start()
            self.refresh()
            self.navigation.setCurrentRow(5)
        status(
            self.generation_status,
            message,
            "success" if accepted else "info" if "cancelled" in message.lower() else "error",
        )
        self.generation_details.setPlainText(
            message + "\n\n" + "\n".join(dict.fromkeys(i.message for i in result.issues))
        )
        self.elapsed.setText(f"Finished in {result.elapsed:.2f} seconds")
        self.pages.widget(4).verticalScrollBar().setValue(0)

    def worker_finished(self):
        self.elapsed_timer.stop()
        worker = self.thread
        self.thread = None
        self.generate_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.generation_progress.hide()
        worker.deleteLater()
        if self.close_when_finished:
            QTimer.singleShot(0, self.close)

    def view_changed(self, *_):
        if self.rendering:
            return
        old = self.view_record.currentData()
        self.view_record.blockSignals(True)
        self.view_record.clear()
        kind = "teachers" if self.view_kind.currentIndex() == 1 else "classes"
        for record in getattr(self.project, kind):
            self.view_record.addItem(record.name, record.id)
        index = self.view_record.findData(old)
        if index >= 0:
            self.view_record.setCurrentIndex(index)
        self.view_record.setVisible(self.view_kind.currentIndex() != 2)
        self.view_record.blockSignals(False)
        self.pending_lesson = self.selected_lesson = None
        status(self.edit_help, "Select a lesson to move it or change its lock.")
        self.render_review()

    def review_record_changed(self, *_):
        self.pending_lesson = self.selected_lesson = None
        status(self.edit_help, "Select a lesson to move it or change its lock.")
        self.render_review()

    def review_selection_changed(self, row, col, *_):
        if not self.pending_lesson and not getattr(self, "rendering_review", False):
            self.cell_clicked(row, col)

    def render_review(self, *_):
        if self.rendering:
            return
        self.rendering_review = True
        self.cell_map.clear()
        self.review_table.clear()
        overview = self.view_kind.currentIndex() == 2
        if overview:
            tables = [
                timetable(self.project, "classes", group.id) for group in self.project.classes
            ]
            headers = [group.name for group in self.project.classes]
            rows = [
                (d, s) for d, day in enumerate(self.project.days) for s in range(len(day.slots))
            ]
            self.review_table.setRowCount(len(rows))
            self.review_table.setColumnCount(len(headers))
            self.review_table.setHorizontalHeaderLabels(headers)
            labels = []
            for row, (d, s) in enumerate(rows):
                day, slot = self.project.days[d], self.project.days[d].slots[s]
                labels.append(f"{day.name}\n{slot.name} | {slot.start}-{slot.end}")
                for col, table in enumerate(tables):
                    self.set_cell(row, col, table.columns[d][s], heading=False)
            self.review_table.setVerticalHeaderLabels(labels)
            self.review_table.verticalHeader().show()
        else:
            kind = "teachers" if self.view_kind.currentIndex() == 1 else "classes"
            record_id = self.view_record.currentData()
            if record_id is None:
                self.review_table.setRowCount(0)
                self.review_table.setColumnCount(0)
                self.rendering_review = False
                self.update_edit_controls()
                return
            table = timetable(self.project, kind, record_id)
            self.review_table.setColumnCount(len(table.days))
            self.review_table.setHorizontalHeaderLabels(table.days)
            self.review_table.setRowCount(max((len(col) for col in table.columns), default=0))
            self.review_table.verticalHeader().hide()
            for col, cells in enumerate(table.columns):
                for row, cell in enumerate(cells):
                    self.set_cell(row, col, cell)
        header = self.review_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        columns = self.review_table.columnCount()
        for col in range(columns):
            self.review_table.setColumnWidth(
                col, max(190, (self.review_table.viewport().width() - 20) // max(1, columns))
            )
            item = self.review_table.horizontalHeaderItem(col)
            if item:
                item.setToolTip(item.text())
        self.rendering_review = False
        self.resize_review_rows()
        self.update_edit_controls()

    def resize_review_rows(self, *_):
        if getattr(self, "rendering_review", False):
            return
        self.review_table.resizeRowsToContents()

    def set_cell(self, row, col, cell, *, heading=True):
        text = (cell.heading + "\n" if heading else "") + cell.text
        item = QTableWidgetItem(text)
        item.setData(CELL_ROLE, cell)
        item.setToolTip(text)
        item.setData(Qt.ItemDataRole.AccessibleTextRole, text)
        item.setBackground(QColor(cell.color))
        item.setForeground(QColor("#173650"))
        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.review_table.setItem(row, col, item)
        self.cell_map[row, col] = cell

    def cell_clicked(self, row, col):
        cell = self.cell_map.get((row, col))
        if not cell:
            return
        if self.pending_lesson:
            if not cell.teaching:
                status(
                    self.edit_help,
                    "Move rejected. Breaks and blocked periods cannot hold lessons. "
                    "Choose another teaching period, or press Esc to cancel.",
                    "error",
                )
                return
            try:
                candidate = move_or_swap(
                    self.project, self.pending_lesson, cell.slot_id, cell.lesson_id
                )
            except EditError as exc:
                status(
                    self.edit_help,
                    "Move rejected. "
                    + str(exc)
                    + " Choose another period, or press Esc to cancel.",
                    "error",
                )
                return
            self.session.history.apply(self.project, candidate)
            self.pending_lesson = None
            self.schedule_changed("Lesson block moved. All mandatory rules checked.")
        else:
            self.selected_lesson = cell.lesson_id
            status(
                self.edit_help,
                "Selected lesson: " + cell.text.replace("\n", " • ")
                if cell.lesson_id
                else "This is a free period or break. Select a lesson first.",
            )
            self.update_edit_controls()

    def update_edit_controls(self):
        lesson = next(
            (lesson for lesson in self.project.lessons if lesson.id == self.selected_lesson), None
        )
        moving = bool(self.pending_lesson)
        self.move_button.setEnabled(bool(lesson and not lesson.locked and not moving))
        self.cancel_move_button.setEnabled(moving)
        self.lock_button.setEnabled(bool(lesson) and not moving)
        self.lock_button.setText("Unlock lesson" if lesson and lesson.locked else "Lock lesson")
        self.unlock_all_button.setEnabled(any(lesson.locked for lesson in self.project.lessons))
        self.review_table.viewport().setCursor(
            Qt.CursorShape.CrossCursor if moving else Qt.CursorShape.ArrowCursor
        )
        self.review_table.viewport().update()

    def arm_move(self):
        lesson = next(
            (lesson for lesson in self.project.lessons if lesson.id == self.selected_lesson), None
        )
        if not lesson:
            status(self.edit_help, "Select a lesson in the timetable first.")
        elif lesson.locked:
            status(self.edit_help, "Unlock this lesson block before moving it.")
        else:
            self.pending_lesson = lesson.id
            status(
                self.edit_help,
                "Moving selected lesson — choose a destination. Click a teaching period, "
                "or use arrow keys and Enter. An occupied period attempts a swap. "
                "Every move is checked. Press Esc to cancel.",
                "moving",
            )
            self.review_table.setFocus()
            self.update_edit_controls()

    def cancel_move(self):
        self.pending_lesson = None
        status(
            self.edit_help,
            "Move cancelled. Your timetable is unchanged. Select a lesson to continue.",
        )
        self.update_edit_controls()

    def toggle_lock(self):
        candidate = deepcopy(self.project.lessons)
        lesson = next((lesson for lesson in candidate if lesson.id == self.selected_lesson), None)
        if not lesson:
            self.edit_help.setText("Select a lesson in the timetable first.")
            return
        lesson.locked = not lesson.locked
        self.session.history.apply(self.project, candidate)
        self.pending_lesson = None
        self.schedule_changed(
            "Lesson block locked in place." if lesson.locked else "Lesson block unlocked."
        )
        self.selected_lesson = lesson.id
        self.update_edit_controls()

    def unlock_all(self):
        if not any(lesson.locked for lesson in self.project.lessons):
            self.edit_help.setText("There are no locked lessons.")
            return
        candidate = deepcopy(self.project.lessons)
        for lesson in candidate:
            lesson.locked = False
        self.session.history.apply(self.project, candidate)
        self.pending_lesson = None
        self.schedule_changed(
            "All lesson blocks unlocked. You can regenerate to correct incompatible positions."
        )

    def undo(self):
        if self.session.history.undo_stack:
            self.session.history.undo(self.project)
            self.schedule_changed("Timetable edit undone.")

    def redo(self):
        if self.session.history.redo_stack:
            self.session.history.redo(self.project)
            self.schedule_changed("Timetable edit redone.")

    def schedule_changed(self, message):
        self.session.changed()
        self.pending_lesson = self.selected_lesson = None
        self.debounce.start()
        self.render_review()
        self.refresh_status()
        status(self.edit_help, message, "success")

    def refresh_export_records(self, *_):
        if self.rendering:
            return
        old = self.export_record.currentData()
        self.export_record.clear()
        kind = "classes" if self.export_kind.currentIndex() == 0 else "teachers"
        for record in getattr(self.project, kind):
            self.export_record.addItem(record.name, record.id)
        index = self.export_record.findData(old)
        if index >= 0:
            self.export_record.setCurrentIndex(index)
        self.export_record.setEnabled(self.export_scope.currentIndex() == 1)

    def export_current(self):
        issues = validate_schedule(self.project)
        if issues:
            status(
                self.export_status,
                "Correct these timetable problems first:\n"
                + "\n".join(dict.fromkeys(i.message for i in issues)),
                "error",
            )
            return
        kind = "classes" if self.export_kind.currentIndex() == 0 else "teachers"
        ids = None if self.export_scope.currentIndex() == 0 else [self.export_record.currentData()]
        pdf = self.export_format.currentIndex() == 1
        suffix = ".pdf" if pdf else ".xlsx"
        name, _ = QFileDialog.getSaveFileName(
            self,
            "Export timetable",
            f"{kind}-timetables{suffix}",
            "PDF (*.pdf)" if pdf else "Excel workbook (*.xlsx)",
        )
        if not name:
            return
        target = Path(name)
        if target.suffix.lower() != suffix:
            target = Path(str(target) + suffix)
        try:
            (export_pdf if pdf else export_excel)(self.project, target, kind, ids)
            status(
                self.export_status,
                f"Export complete: {target}\nYour current edits are included. "
                "Save the project too if you want to edit it later.",
                "success",
            )
        except (OSError, ValueError, ExportError) as exc:
            self.show_error("Cannot export timetable", str(exc))

    def show_error(self, title, message):
        box = QMessageBox(QMessageBox.Icon.Warning, title, "", parent=self)
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText(message)
        box.exec()

    def confirm_unsaved(self):
        if not self.session.dirty:
            return True
        box = QMessageBox(
            QMessageBox.Icon.Question,
            "Keep your changes?",
            "Save your changes before continuing?",
            parent=self,
        )
        box.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(QMessageBox.StandardButton.Save)
        choice = box.exec()
        if choice == QMessageBox.StandardButton.Cancel:
            return False
        return self.save() if choice == QMessageBox.StandardButton.Save else True

    def replace_project(self, project, path=None, *, dirty=False):
        if self.thread:
            self.cancel_generation()
        self.session.replace(project, path, dirty=dirty)
        self.recovery.clear()
        self.pending_lesson = self.selected_lesson = None
        status(self.generation_status, "Ready to generate when your setup is complete.")
        status(self.export_status, "")
        self.refresh()
        self.navigation.setCurrentRow(0)
        if dirty:
            self.debounce.start()

    def new_project(self):
        if self.confirm_unsaved():
            self.replace_project(Project())

    def open_project(self):
        if not self.confirm_unsaved():
            return
        name, _ = QFileDialog.getOpenFileName(
            self,
            "Open school project",
            "",
            "School Timetable (*.schooltimetable);;Backup (*.bak);;All files (*)",
        )
        if not name:
            return
        try:
            project = load_project(name)
        except ProjectFileError as exc:
            self.show_error(
                "Cannot open project",
                str(exc)
                + "\nYour current project is unchanged. You can also try its .bak backup file.",
            )
            return
        if Path(name).suffix.lower() == ".bak":
            self.replace_project(project, dirty=True)
            self.statusBar().showMessage(
                "Backup opened as a copy. Use Save As to keep the recovered project."
            )
        else:
            self.replace_project(project, name)

    def load_example(self):
        if self.confirm_unsaved():
            self.replace_project(example_school(), dirty=True)

    def save(self):
        return self.save_to(self.session.path) if self.session.path else self.save_as()

    def save_as(self):
        name, _ = QFileDialog.getSaveFileName(
            self,
            "Save school project",
            str(self.session.path or "My school.schooltimetable"),
            "School Timetable (*.schooltimetable)",
        )
        if not name:
            return False
        if not name.lower().endswith(".schooltimetable"):
            name += ".schooltimetable"
        return self.save_to(Path(name))

    def save_to(self, path):
        try:
            save_project(self.project, path)
        except (OSError, ValueError) as exc:
            self.show_error("Cannot save project", f"Choose another writable folder.\n{exc}")
            return False
        self.session.path = Path(path)
        self.session.dirty = False
        self.recovery.clear()
        self.refresh_status()
        return True

    def autosave(self):
        if self.session.dirty:
            try:
                self.recovery.write(self.project)
            except (OSError, ValueError):
                logging.exception("Recovery save failed")
                self.statusBar().showMessage(
                    "Automatic recovery save failed. Please use Save and choose a writable folder."
                )

    def offer_recovery(self):
        candidates = self.recovery.candidates()
        if not candidates:
            return
        dialog = FormDialog("Recover unsaved work", self)
        dialog.form.addRow(
            label(
                "Unsaved work from a previous session was found. Choose Recover to"
                " open a copy, then use Save As. Cancel leaves recovery files for "
                "later."
            )
        )
        choices = QComboBox()
        for candidate in candidates:
            try:
                name = load_project(candidate).school_name
            except ProjectFileError:
                name = "Unreadable recovery file"
            choices.addItem(
                f"{name} — "
                f"{time.strftime('%d %b %H:%M', time.localtime(candidate.stat().st_mtime))}",
                str(candidate),
            )
        dialog.form.addRow("Unsaved project", choices)
        dialog.buttons.button(dialog.buttons.StandardButton.Ok).setText("Recover")
        discard = QPushButton("Discard selected recovery")
        dialog.form.addRow(discard)

        def discard_selected():
            Path(choices.currentData()).unlink(missing_ok=True)
            dialog.reject()

        discard.clicked.connect(discard_selected)
        if dialog.exec():
            path = Path(choices.currentData())
            try:
                project = load_project(path)
                self.replace_project(project, dirty=True)
                self.recovery.write(project)
                path.unlink(missing_ok=True)
            except (OSError, ProjectFileError) as exc:
                self.show_error("Cannot recover project", str(exc))

    def help(self):
        from importlib.resources import files

        dialog = QDialog(self)
        dialog.setWindowTitle("School Timetable — Help")
        available = self.screen().availableGeometry()
        dialog.resize(min(760, available.width() - 40), min(650, available.height() - 60))
        layout = QVBoxLayout(dialog)
        text = QTextBrowser()
        text.setMarkdown(
            files("school_timetable").joinpath("resources/guide.md").read_text(encoding="utf-8")
        )
        layout.addWidget(text)
        button("Close", dialog.accept, layout)
        dialog.exec()

    def closeEvent(self, event):
        if self.thread is not None:
            self.close_when_finished = True
            self.cancel_generation()
            event.ignore()
            return
        if not self.confirm_unsaved():
            self.close_when_finished = False
            event.ignore()
            return
        self.debounce.stop()
        self.autosave_timer.stop()
        try:
            self.recovery.close()
        except OSError:
            logging.exception("Could not clean up recovery data")
        event.accept()
