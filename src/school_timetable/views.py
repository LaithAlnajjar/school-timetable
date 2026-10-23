"""One projection of the current schedule for UI, Excel and PDF."""

from dataclasses import dataclass

from .models import Project

PALETTE = ("#DCEAF8", "#E3EFDF", "#F9EACF", "#ECE2F4", "#F4DFE1", "#D9EDEC")


@dataclass(frozen=True)
class Cell:
    slot_id: str
    heading: str
    text: str
    lesson_id: str | None
    color: str
    teaching: bool


@dataclass(frozen=True)
class Timetable:
    name: str
    kind: str
    days: list[str]
    columns: list[list[Cell]]


def timetable(project: Project, kind: str, record_id: str) -> Timetable:
    if kind not in ("classes", "teachers"):
        raise ValueError("Choose classes or teachers.")
    record = project.lookup(kind, record_id)
    if record is None:
        raise ValueError("The selected class or teacher no longer exists.")
    subject_colors = {s.id: PALETTE[i % len(PALETTE)] for i, s in enumerate(project.subjects)}
    by_slot = {}
    for lesson in project.lessons:
        r = project.lookup("requirements", lesson.requirement_id)
        if not r or (r.class_id if kind == "classes" else r.teacher_id) != record_id:
            continue
        for sid in lesson.slot_ids:
            by_slot[sid] = (lesson, r)
    columns = []
    for day in project.days:
        cells = []
        for slot in day.slots:
            lesson_id = None
            text, color = (
                ("Free period", "#FFFFFF") if slot.teaching else ("Break / blocked", "#EBEEF2")
            )
            if slot.id in by_slot:
                lesson, r = by_slot[slot.id]
                subject = project.lookup("subjects", r.subject_id)
                other = (
                    project.lookup("teachers", r.teacher_id)
                    if kind == "classes"
                    else project.lookup("classes", r.class_id)
                )
                text = (
                    f"{subject.name if subject else 'Missing subject'}\n"
                    f"{other.name if other else 'Missing assignment'}"
                )
                if project.settings.rooms_enabled and lesson.room_id:
                    room = project.lookup("rooms", lesson.room_id)
                    text += f"\nRoom: {room.name if room else 'Missing room'}"
                if len(lesson.slot_ids) == 2:
                    text += "\nDouble lesson"
                if lesson.locked:
                    text += "\nLocked"
                color = subject_colors.get(r.subject_id, "#FFFFFF")
                lesson_id = lesson.id
            cells.append(
                Cell(
                    slot.id,
                    f"{slot.name} | {slot.start}-{slot.end}",
                    text,
                    lesson_id,
                    color,
                    slot.teaching,
                )
            )
        columns.append(cells)
    return Timetable(
        record.name,
        "Class" if kind == "classes" else "Teacher",
        [day.name for day in project.days],
        columns,
    )
