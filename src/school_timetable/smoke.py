"""Deterministic synthetic workflow for source and frozen-application verification."""

from __future__ import annotations

import json
import platform
import sys
import time
from copy import deepcopy
from importlib.resources import files
from pathlib import Path

import openpyxl
import ortools
import PySide6
from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication

from .editing import EditError, move_or_swap
from .examples import example_school
from .exports import ExportError, export_excel, export_pdf
from .scheduler import Outcome
from .storage import atomic_write, load_project
from .validation import validate_schedule
from .views import timetable


def run_smoke(app, window, output: Path):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    state = {"phase": "start", "pulses": 0, "error": None, "checks": [], "outcomes": []}
    started = time.monotonic()
    timer = QTimer(window)
    timer.setInterval(30)

    def finish():
        timer.stop()
        window.navigation.setCurrentRow(5)
        window.render_review()
        window.grab().save(str(output / "desktop.png"))
        report = {
            "passed": state["error"] is None,
            "error": state["error"],
            "checks": state["checks"],
            "outcomes": state["outcomes"],
            "ui_heartbeat_events": state["pulses"],
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "qt_platform": QGuiApplication.platformName(),
            "frozen": bool(getattr(sys, "frozen", False)),
            "PySide6": PySide6.__version__,
            "ortools": ortools.__version__,
            "openpyxl": openpyxl.__version__,
        }
        atomic_write(output / "smoke-report.json", (json.dumps(report, indent=2) + "\n").encode())
        window.session.dirty = False
        window.close()
        app.exit(0 if report["passed"] else 1)

    def record_outcome():
        state["outcomes"].append(window.last_result.outcome)

    def verify(condition, message):
        if not condition:
            raise AssertionError(message)

    def tick():
        state["pulses"] += 1
        if window.thread is not None:
            return
        if state["error"]:
            finish()
            return
        try:
            phase = state["phase"]
            if phase == "start":
                p = example_school()
                p.settings.time_limit = 3
                p.teachers[0].max_daily = 4
                p.teachers[0].max_consecutive = 2
                p.teachers[0].unavailable = [p.days[0].id]
                p.rooms[0].unavailable = [p.days[1].id]
                window.replace_project(p, dirty=True)
                window.generate()
                state["phase"] = "first"
            elif phase == "first":
                record_outcome()
                p = window.project
                verify(window.last_result.usable, "First generation did not find a timetable")
                verify(not validate_schedule(p), "Independent schedule validation failed")
                state["checks"].append(
                    "background generation, exact counts, clashes, availability, limits, "
                    "doubles, rooms"
                )
                chosen = next(lesson for lesson in p.lessons if len(lesson.slot_ids) == 1)
                r = p.lookup("requirements", chosen.requirement_id)
                window.view_kind.setCurrentIndex(0)
                window.view_record.setCurrentIndex(window.view_record.findData(r.class_id))
                source = next(
                    pos for pos, cell in window.cell_map.items() if cell.lesson_id == chosen.id
                )
                destination = None
                for pos, cell in window.cell_map.items():
                    if not cell.teaching or cell.lesson_id:
                        continue
                    try:
                        move_or_swap(p, chosen.id, cell.slot_id)
                        destination = pos
                        break
                    except EditError:
                        continue
                verify(destination is not None, "No valid demo edit was found")
                window.cell_clicked(*source)
                window.arm_move()
                dest_id = window.cell_map[destination].slot_id
                window.cell_clicked(*destination)
                chosen = next(lesson for lesson in p.lessons if lesson.id == chosen.id)
                verify(
                    chosen.slot_ids == [dest_id], "UI move did not update the underlying schedule"
                )
                source = next(
                    pos for pos, cell in window.cell_map.items() if cell.lesson_id == chosen.id
                )
                window.cell_clicked(*source)
                window.toggle_lock()
                window.undo()
                verify(
                    not next(lesson for lesson in p.lessons if lesson.id == chosen.id).locked,
                    "Undo failed",
                )
                window.redo()
                verify(
                    next(lesson for lesson in p.lessons if lesson.id == chosen.id).locked,
                    "Redo failed",
                )
                double = next(lesson for lesson in p.lessons if len(lesson.slot_ids) == 2)
                r = p.lookup("requirements", double.requirement_id)
                window.view_record.setCurrentIndex(window.view_record.findData(r.class_id))
                source = next(
                    pos for pos, cell in window.cell_map.items() if cell.lesson_id == double.id
                )
                window.cell_clicked(*source)
                window.toggle_lock()
                state["locks"] = {
                    lesson.id: deepcopy(lesson) for lesson in p.lessons if lesson.locked
                }
                verify(window.save_to(output / "example.schooltimetable"), "Project save failed")
                verify(
                    load_project(output / "example.schooltimetable") == p,
                    "Project round trip changed data",
                )
                state["checks"].append(
                    "UI manual move, whole-block locks, undo/redo, save/open round trip"
                )
                window.generate()
                state["phase"] = "regenerated"
            elif phase == "regenerated":
                record_outcome()
                p = window.project
                verify(window.last_result.usable, "Regeneration failed")
                by_id = {lesson.id: lesson for lesson in p.lessons}
                verify(
                    all(by_id[key] == lock for key, lock in state["locks"].items()),
                    "Regeneration changed locks",
                )
                verify(not validate_schedule(p), "Regenerated timetable failed validation")
                for lesson in p.lessons:
                    r = p.lookup("requirements", lesson.requirement_id)
                    for kind, record_id in (("classes", r.class_id), ("teachers", r.teacher_id)):
                        cells = [
                            cell for col in timetable(p, kind, record_id).columns for cell in col
                        ]
                        verify(
                            {cell.slot_id for cell in cells if cell.lesson_id == lesson.id}
                            == set(lesson.slot_ids),
                            "Class and teacher view mismatch",
                        )
                for kind in ("classes", "teachers"):
                    export_excel(p, output / f"{kind}.xlsx", kind)
                    export_pdf(p, output / f"{kind}.pdf", kind)
                bad = deepcopy(p)
                bad.lessons.pop()
                try:
                    export_pdf(bad, output / "invalid.pdf")
                except ExportError:
                    pass
                else:
                    raise AssertionError("An incomplete schedule was exported")
                verify(not (output / "invalid.pdf").exists(), "Invalid PDF was created")
                verify(
                    "School Timetable"
                    in files("school_timetable")
                    .joinpath("resources/guide.md")
                    .read_text(encoding="utf-8"),
                    "Bundled help is missing",
                )
                window.session.changed()
                window.autosave()
                verify(
                    load_project(window.recovery.path) == p, "Recovery file differs from project"
                )
                verify(window.save_to(output / "example.schooltimetable"), "Second save failed")
                verify((output / "example.schooltimetable.bak").exists(), "Recent backup missing")
                state["checks"].append(
                    "locked regeneration, consistent class/teacher views, XLSX/PDF, "
                    "invalid export blocked, help, recovery, backup"
                )
                state["old_lessons"] = deepcopy(p.lessons)
                p.requirements[0].periods = 35
                window.data_changed()
                window.generate()
                state["phase"] = "impossible"
            elif phase == "impossible":
                record_outcome()
                verify(
                    window.last_result.outcome == Outcome.IMPOSSIBLE,
                    "Impossible setup was not identified",
                )
                verify(
                    window.project.lessons == state["old_lessons"],
                    "Failed search overwrote the old timetable",
                )
                window.project.requirements[0].periods = 5
                window.data_changed()
                window.generate()
                window.cancel_generation()
                state["phase"] = "cancelled"
            elif phase == "cancelled":
                record_outcome()
                verify(
                    window.last_result.outcome == Outcome.CANCELLED, "Cancellation was not reported"
                )
                verify(
                    window.project.lessons == state["old_lessons"],
                    "Cancellation overwrote the timetable",
                )
                state["checks"].append("impossible/cancelled generation preserves old timetable")
                verify(state["pulses"] > 1, "UI heartbeat did not run")
                finish()
        except Exception as exc:
            state["error"] = f"{type(exc).__name__}: {exc}"
            if window.thread:
                window.cancel_generation()
            else:
                finish()

    def timeout():
        state["error"] = "Smoke test exceeded 75 seconds"
        if window.thread:
            window.cancel_generation()
        else:
            finish()

    timer.timeout.connect(tick)
    QTimer.singleShot(75000, timeout)
    timer.start()
