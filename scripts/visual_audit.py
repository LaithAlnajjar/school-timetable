"""Capture real Qt widgets with synthetic data; never reads a user's projects.

Run with QT_QPA_PLATFORM=windows for native Windows rendering. QT_SCALE_FACTOR
can exercise Qt scaling in a fresh process; it does not change monitor DPI.
"""

import argparse
import json
import os
import tempfile
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

# Match the production entry point's backend-before-Qt initialization.
import openpyxl  # noqa: F401
from ortools.sat.python import cp_model  # noqa: F401
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QMessageBox, QTabWidget, QToolTip

from school_timetable.examples import example_school
from school_timetable.models import Project, Teacher
from school_timetable.scheduler import Scheduler
from school_timetable.ui.dialogs import DayDialog, RecordDialog, RequirementDialog, SlotDialog
from school_timetable.ui.window import MainWindow


@contextmanager
def windows_appearance(value):
    """Temporarily exercise the actual Windows app setting, restoring it on exit."""
    if value is None:
        yield
        return
    if os.name != "nt":
        raise RuntimeError("Windows appearance checks require Windows.")
    import ctypes
    import winreg

    key_name = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, key_name, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE
    ) as key:
        previous, kind = winreg.QueryValueEx(key, "AppsUseLightTheme")

        def broadcast():
            message = ctypes.c_wchar_p("ImmersiveColorSet")
            result = ctypes.c_size_t()
            send = ctypes.windll.user32.SendMessageTimeoutW
            send.argtypes = [
                ctypes.c_void_p,
                ctypes.c_uint,
                ctypes.c_size_t,
                ctypes.c_void_p,
                ctypes.c_uint,
                ctypes.c_uint,
                ctypes.POINTER(ctypes.c_size_t),
            ]
            send(
                0xFFFF,
                0x1A,
                0,
                ctypes.cast(message, ctypes.c_void_p),
                2,
                2000,
                ctypes.byref(result),
            )

        try:
            winreg.SetValueEx(
                key, "AppsUseLightTheme", 0, winreg.REG_DWORD, 1 if value == "light" else 0
            )
            broadcast()
            yield
        finally:
            winreg.SetValueEx(key, "AppsUseLightTheme", 0, kind, previous)
            broadcast()


def contrast(a, b):
    def luminance(value):
        c = QColor(value)
        rgb = [c.redF(), c.greenF(), c.blueF()]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
        return sum(v * w for v, w in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))

    low, high = sorted((luminance(a), luminance(b)))
    return round((high + 0.05) / (low + 0.05), 2)


def contact_sheets(output):
    images = sorted(p for p in output.glob("*.png") if not p.name.startswith("contact-"))
    for batch in range((len(images) + 7) // 8):
        canvas = QImage(1280, 1840, QImage.Format.Format_RGB32)
        canvas.fill(QColor("#D6DDE5"))
        painter = QPainter(canvas)
        painter.setFont(QFont("Segoe UI", 11))
        painter.setPen(QColor("black"))
        for i, path in enumerate(images[batch * 8 : batch * 8 + 8]):
            picture = QImage(str(path)).scaled(
                632,
                428,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x, y = i % 2 * 640, i // 2 * 460
            painter.drawText(x + 8, y + 20, path.stem)
            painter.drawImage(x + 4, y + 26, picture)
        painter.end()
        canvas.save(str(output / f"contact-{batch}.png"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=860)
    parser.add_argument("--windows-appearance", choices=("light", "dark"))
    args = parser.parse_args()
    with windows_appearance(args.windows_appearance):
        run(args)


def run(args):
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    native_color_scheme = app.styleHints().colorScheme().name
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
        "windows_app_appearance": args.windows_appearance,
        "native_color_scheme_before_theme": native_color_scheme,
        "color_scheme": app.styleHints().colorScheme().name,
        "qt_scale_factor": os.environ.get("QT_SCALE_FACTOR", "1"),
        "screen_dpr": app.primaryScreen().devicePixelRatio(),
        "screen_dpi": app.primaryScreen().logicalDotsPerInch(),
        "captures": [],
        "window_bounds_issues": [],
    }

    def capture(widget, name):
        widget.show()
        widget.activateWindow()
        QTest.qWait(90)
        path = args.output / f"{name}.png"
        assert widget.grab().save(str(path)), path
        report["captures"].append(name)
        if not widget.screen().availableGeometry().contains(widget.frameGeometry()):
            report["window_bounds_issues"].append(name)

    def toggle_advanced(widget):
        for check in widget.findChildren(QCheckBox):
            if "Advanced" in check.text():
                check.setChecked(True)

    with tempfile.TemporaryDirectory() as folder:
        w = MainWindow(Path(folder), check_recovery=False)
        geometry = app.primaryScreen().availableGeometry()
        report["available_screen_logical_size"] = [geometry.width(), geometry.height()]
        w.resize(min(args.width, geometry.width() - 30), min(args.height, geometry.height() - 40))
        report["window_logical_size"] = [w.width(), w.height()]
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
            area = w.pages.widget(index)
            if area.verticalScrollBar().maximum():
                area.verticalScrollBar().setValue(area.verticalScrollBar().maximum())
                capture(w, name + "-bottom")
                area.verticalScrollBar().setValue(0)
        w.navigation.setCurrentRow(2)
        w.pages.widget(2).findChild(QTabWidget).setCurrentIndex(1)
        capture(w, "subjects")
        w.navigation.setCurrentRow(4)
        toggle_advanced(w.pages.widget(4))
        capture(w, "generate-advanced")
        area = w.pages.widget(4)
        area.verticalScrollBar().setValue(area.verticalScrollBar().maximum())
        capture(w, "generate-advanced-bottom")
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
        requirement = RequirementDialog(p, p.requirements[0], w)
        requirement.show()
        requirement.doubles.setValue(99)
        requirement.accept()
        capture(requirement, "invalid-doubles")
        requirement.reject()
        w.navigation.setCurrentRow(6)
        w.export_format.showPopup()
        QTest.qWait(50)
        capture(w.export_format.view().window(), "combo-popup")
        w.export_format.hidePopup()
        w.navigation.setCurrentRow(3)
        w.requirements_table.setCurrentCell(0, 0)
        w.requirements_table.setFocus()
        capture(w, "selection-focused")
        inactive = QMessageBox(QMessageBox.Icon.Information, "Information", "Example", parent=w)
        inactive.show()
        QTest.qWait(80)
        w.grab().save(str(args.output / "selection-inactive.png"))
        report["captures"].append("selection-inactive")
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
        position = next(
            pos for pos, cell in w.cell_map.items() if cell.lesson_id == w.selected_lesson
        )
        w.review_table.scrollToItem(w.review_table.item(*position))
        capture(w, "review-locked")
        w.view_kind.setCurrentIndex(1)
        capture(w, "review-teacher")
        w.view_kind.setCurrentIndex(2)
        capture(w, "review-school")
        long = deepcopy(p)
        long.teachers[0].name = "Mrs Alexandra Montgomery — Mathematics and Further Mathematics"
        long.subjects[0].name = "Mathematics: problem solving, reasoning and advanced applications"
        long.classes[0].name = "Year Seven — extended mathematics and language teaching group"
        w.replace_project(long)
        w.navigation.setCurrentRow(5)
        capture(w, "review-long-names")
        area = w.pages.widget(5)
        area.ensureWidgetVisible(w.cancel_move_button)
        capture(w, "review-actions-bottom")
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
        pairs = {
            "body": ("#20344D", "#FFFFFF"),
            "hint": ("#4B5E71", "#F4F6F9"),
            "selection_active_and_inactive": ("#FFFFFF", "#205C86"),
            "disabled": ("#536273", "#E9EDF2"),
            "boundary": ("#718096", "#FFFFFF"),
            "focus": ("#1458A8", "#F4F6F9"),
            "error": ("#A12B24", "#FFF1EF"),
            "valid": ("#215B37", "#EDF7F0"),
            "moving": ("#654700", "#FFF4D6"),
            "moving_boundary": ("#826000", "#FFF4D6"),
            "scrollbar": ("#697D90", "#EDF1F5"),
            "before_dark_form": ("#20344D", "#323232"),
            "before_selected_lesson": ("#F0F0F0", "#CBDFF3"),
        }
        from school_timetable.views import PALETTE

        pairs.update({f"subject_{i + 1}": ("#20344D", bg) for i, bg in enumerate(PALETTE)})
        report["contrast"] = {
            name: {"foreground": fg, "background": bg, "ratio": contrast(fg, bg)}
            for name, (fg, bg) in pairs.items()
        }
        w.session.dirty = False
        w.close()
        contact_sheets(args.output)
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
