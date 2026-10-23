"""Capture real Qt widgets with synthetic data; never reads a user's projects.

Run with QT_QPA_PLATFORM=windows for native Windows rendering. QT_SCALE_FACTOR
can exercise Qt scaling in a fresh process; it does not change monitor DPI.
"""

import argparse
import json
import tempfile
from copy import deepcopy
from pathlib import Path

# Match the production entry point's backend-before-Qt initialization.
import openpyxl  # noqa: F401
from ortools.sat.python import cp_model  # noqa: F401
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QMessageBox, QTabWidget, QToolTip

from school_timetable.examples import example_school
from school_timetable.models import Project, Teacher
from school_timetable.scheduler import Scheduler
from school_timetable.ui.dialogs import DayDialog, RecordDialog, RequirementDialog, SlotDialog
from school_timetable.ui.window import MainWindow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=860)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    app.setStyle("Fusion")
    app.setPalette(app.style().standardPalette())
    app.setFont(QFont("Segoe UI", 11))
    try:
        from school_timetable.ui.theme import apply_theme

        apply_theme(app)
    except ImportError:
        pass  # Also captures the unmodified baseline.
    report = {
        "platform": app.platformName(),
        "color_scheme": app.styleHints().colorScheme().name,
        "screen_dpr": app.primaryScreen().devicePixelRatio(),
        "screen_dpi": app.primaryScreen().logicalDotsPerInch(),
        "captures": [],
    }

    def capture(widget, name):
        widget.show()
        widget.activateWindow()
        QTest.qWait(90)
        path = args.output / f"{name}.png"
        assert widget.grab().save(str(path)), path
        report["captures"].append(name)

    def toggle_advanced(widget):
        for check in widget.findChildren(QCheckBox):
            if "Advanced" in check.text():
                check.setChecked(True)

    with tempfile.TemporaryDirectory() as folder:
        w = MainWindow(Path(folder), check_recovery=False)
        w.resize(args.width, args.height)
        for index, name in enumerate(
            ("week", "teachers", "classes", "requirements", "generate", "review", "export")
        ):
            w.navigation.setCurrentRow(index)
            capture(w, "empty-" + name)
        p = example_school()
        p.settings.time_limit = 1
        result = Scheduler().solve(p)
        assert result.usable
        p.lessons = result.lessons
        p.scheduled_fingerprint = p.fingerprint()
        w.replace_project(p)
        for index, name in enumerate(
            ("week", "teachers", "classes", "requirements", "generate", "review", "export")
        ):
            w.navigation.setCurrentRow(index)
            capture(w, name)
        w.navigation.setCurrentRow(2)
        w.pages.widget(2).findChild(QTabWidget).setCurrentIndex(1)
        capture(w, "subjects")
        w.navigation.setCurrentRow(4)
        toggle_advanced(w.pages.widget(4))
        capture(w, "generate-advanced")
        for name, dialog in (
            ("teacher", RecordDialog(p, "teachers", p.teachers[0], w)),
            ("class", RecordDialog(p, "classes", p.classes[0], w)),
            ("subject", RecordDialog(p, "subjects", p.subjects[0], w)),
            ("room", RecordDialog(p, "rooms", p.rooms[0], w)),
            ("day", DayDialog(p, p.days[0], w)),
            ("period", SlotDialog(p.days[0].slots[0], w)),
            ("requirement", RequirementDialog(p, p.requirements[0], w)),
        ):
            capture(dialog, "dialog-" + name)
            toggle_advanced(dialog)
            if name == "teacher":
                dialog.availability.expandAll()
                dialog.availability.topLevelItem(0).setCheckState(0, Qt.CheckState.Checked)
                dialog.availability.setFocus()
                capture(dialog, "availability")
            if name in ("requirement", "room"):
                capture(dialog, "dialog-" + name + "-advanced")
            dialog.reject()
        invalid = RecordDialog(p, "teachers", Teacher(), w)
        invalid.show()
        invalid.accept()
        capture(invalid, "invalid-name")
        invalid.reject()
        w.navigation.setCurrentRow(3)
        w.requirements_table.setCurrentCell(0, 0)
        w.requirements_table.setFocus()
        capture(w, "selection-focused")
        inactive = QMessageBox(QMessageBox.Icon.Information, "Information", "Example", parent=w)
        inactive.show()
        QTest.qWait(80)
        w.grab().save(str(args.output / "selection-inactive.png"))
        inactive.close()
        w.navigation.setCurrentRow(5)
        position = next(pos for pos, cell in w.cell_map.items() if cell.lesson_id)
        w.review_table.setCurrentCell(*position)
        w.cell_clicked(*position)
        capture(w, "review-selected")
        w.arm_move()
        capture(w, "review-moving")
        blocked = next(pos for pos, cell in w.cell_map.items() if not cell.teaching)
        w.cell_clicked(*blocked)
        capture(w, "review-rejected")
        w.cancel_move()
        w.toggle_lock()
        capture(w, "review-locked")
        w.view_kind.setCurrentIndex(1)
        capture(w, "review-teacher")
        w.view_kind.setCurrentIndex(2)
        capture(w, "review-school")
        long = deepcopy(p)
        long.teachers[0].name = "Mrs Alexandra Montgomery — Mathematics and Further Mathematics"
        long.subjects[0].name = "Mathematics: problem solving, reasoning and advanced applications"
        w.replace_project(long)
        w.navigation.setCurrentRow(5)
        capture(w, "review-long-names")
        QTimer.singleShot(120, lambda: capture(app.activeModalWidget(), "help"))
        QTimer.singleShot(260, lambda: app.activeModalWidget().accept())
        w.help()
        QTimer.singleShot(120, lambda: capture(app.activeModalWidget(), "message-warning"))
        QTimer.singleShot(260, lambda: app.activeModalWidget().accept())
        w.show_error("Cannot move this lesson", "The teacher is already teaching at this time.")
        QTimer.singleShot(120, lambda: capture(app.activeModalWidget(), "message-unsaved"))
        QTimer.singleShot(260, lambda: app.activeModalWidget().reject())
        w.session.dirty = True
        w.confirm_unsaved()
        w.session.dirty = False
        w.navigation.setCurrentRow(0)
        w.school_name.setFocus()
        capture(w, "field-focused")
        QToolTip.showText(
            w.school_name.mapToGlobal(w.school_name.rect().bottomLeft()),
            "School name appears on every exported timetable.",
            w.school_name,
        )
        QTest.qWait(80)
        for widget in app.topLevelWidgets():
            if widget.isVisible() and widget.windowType() == Qt.WindowType.ToolTip:
                widget.grab().save(str(args.output / "tooltip.png"))
                report["captures"].append("tooltip")
        QToolTip.hideText()
        w.replace_project(example_school(class_count=20))
        w.navigation.setCurrentRow(4)
        w.generate()
        capture(w, "generate-busy")
        w.cancel_generation()
        while w.thread is not None:
            QTest.qWait(20)
        capture(w, "generate-cancelled")
        w.replace_project(Project())
        w.navigation.setCurrentRow(4)
        w.generate()
        while w.thread is not None:
            QTest.qWait(20)
        capture(w, "generate-invalid")
        report["palette"] = {
            group.name: {
                role.name: app.palette().color(group, role).name()
                for role in (
                    QPalette.ColorRole.Window,
                    QPalette.ColorRole.WindowText,
                    QPalette.ColorRole.Base,
                    QPalette.ColorRole.Text,
                    QPalette.ColorRole.Highlight,
                    QPalette.ColorRole.HighlightedText,
                )
            }
            for group in (
                QPalette.ColorGroup.Active,
                QPalette.ColorGroup.Inactive,
                QPalette.ColorGroup.Disabled,
            )
        }
        w.session.dirty = False
        w.close()
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
