"""Independent domain checks shared by generation, editing and final exports."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from .models import Lesson, Project, chains, lesson_blocks, slot_index, teaching_slots


@dataclass(frozen=True)
class Issue:
    path: str
    message: str


def minutes(time: str) -> int:
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", time):
        raise ValueError("Use a time such as 08:30 (24-hour clock).")
    hour, minute = map(int, time.split(":"))
    return hour * 60 + minute


def validate_setup(project: Project) -> list[Issue]:
    issues: list[Issue] = []

    def error(path, text):
        issues.append(Issue(path, text))

    seen = set()
    collections = ("days", "teachers", "classes", "subjects", "rooms", "requirements")
    for collection in collections:
        records = getattr(project, collection)
        names = set()
        for record in records:
            if not record.id or record.id in seen:
                error(collection, "Each record needs a unique internal ID.")
            seen.add(record.id)
            if hasattr(record, "name"):
                name = record.name.strip().casefold()
                if not name:
                    error(collection, "Please enter a name.")
                if name in names:
                    error(collection, f"The name '{record.name}' is already used here.")
                names.add(name)
    if not project.school_name.strip():
        error("school_name", "Enter the school name.")
    if not project.days:
        error("days", "Add at least one school day and its teaching slots.")
    for d, day in enumerate(project.days):
        previous_end = -1
        for s, slot in enumerate(day.slots):
            where = f"days.{d}.slots.{s}"
            if not slot.id or slot.id in seen:
                error(where, "Each time slot needs a unique internal ID.")
            seen.add(slot.id)
            if not slot.name.strip():
                error(where, f"{day.name}: enter a period name.")
            try:
                start, end = minutes(slot.start), minutes(slot.end)
            except ValueError as exc:
                error(where, f"{day.name}, {slot.name}: {exc}")
                continue
            if end <= start:
                error(where, f"{day.name}, {slot.name}: end time must be after start time.")
            if start < previous_end:
                error(where, f"{day.name}, {slot.name}: periods overlap or are out of time order.")
            previous_end = end
    slots = slot_index(project)
    available = teaching_slots(project)
    if not available:
        error("days", "Add at least one teaching slot. Breaks cannot hold lessons.")
    for collection in ("teachers", "rooms"):
        for record in getattr(project, collection):
            unknown = set(record.unavailable) - slots.keys()
            if unknown:
                error(collection, f"{record.name}: unavailable periods refer to removed slots.")
            if len(record.unavailable) != len(set(record.unavailable)):
                error(collection, f"{record.name}: unavailable periods contain duplicates.")
    for teacher in project.teachers:
        for key in ("max_daily", "max_consecutive"):
            value = getattr(teacher, key)
            if value is not None and value < 1:
                error("teachers", f"{teacher.name}: an enabled teaching limit must be at least 1.")
    if not 0.01 <= project.settings.time_limit <= 3600:
        error("settings", "Choose a search time between 0.01 seconds and 60 minutes.")
    for collection, name in (
        ("teachers", "teacher"),
        ("classes", "class"),
        ("subjects", "subject"),
    ):
        if not getattr(project, collection):
            error(collection, f"Add at least one {name}.")
    if not project.requirements:
        error(
            "requirements", "Add lesson requirements, for example 7A | Mathematics | Mrs Smith | 5."
        )
    pairs = set()
    for r in project.requirements:
        label = (
            f"Requirement {project.lookup('classes', r.class_id).name}"
            if project.lookup("classes", r.class_id)
            else "A lesson requirement"
        )
        for collection, key, name in (
            ("classes", "class_id", "class"),
            ("subjects", "subject_id", "subject"),
            ("teachers", "teacher_id", "teacher"),
        ):
            if not project.lookup(collection, getattr(r, key)):
                error("requirements", f"{label} has a missing {name}. Select an existing {name}.")
        pair = (r.class_id, r.subject_id)
        if pair in pairs:
            error("requirements", f"{label}: use one row per class and subject.")
        pairs.add(pair)
        if r.periods < 1:
            error("requirements", f"{label}: weekly periods must be at least 1.")
        if r.doubles < 0 or r.doubles * 2 > r.periods:
            error("requirements", f"{label}: double lessons use two periods each; reduce doubles.")
        if r.max_per_day is not None and r.max_per_day < 1:
            error("requirements", f"{label}: an enabled daily subject limit must be at least 1.")
        if len(set(r.room_ids)) != len(r.room_ids):
            error("requirements", f"{label}: suitable rooms contain duplicates.")
        if project.settings.rooms_enabled:
            for room_id in r.room_ids:
                if not project.lookup("rooms", room_id):
                    error("requirements", f"{label}: a suitable room is missing.")
    return issues


def requirement_name(project: Project, requirement) -> str:
    group = project.lookup("classes", requirement.class_id)
    subject = project.lookup("subjects", requirement.subject_id)
    return (
        f"{group.name if group else 'Missing class'} / "
        f"{subject.name if subject else 'Missing subject'}"
    )


def validate_schedule(
    project: Project, lessons: list[Lesson] | None = None, *, complete=True, preserve_locks=True
) -> list[Issue]:
    """Check actual placements/counts independently of CP-SAT variables or constraints."""
    issues = validate_setup(project)
    if issues:
        return issues
    proposed = project.lessons if lessons is None else lessons
    slots = slot_index(project)
    reqs = {r.id: r for r in project.requirements}
    expected = {key: (r.id, length) for r in reqs.values() for key, length in lesson_blocks(r)}
    seen: set[str] = set()
    counts: Counter = Counter()
    doubles: Counter = Counter()
    occupied: dict[tuple[str, str, str], str] = {}
    teacher_days: Counter = Counter()
    subject_days: Counter = Counter()
    teacher_slots: dict[str, set[str]] = defaultdict(set)

    def error(text):
        issues.append(Issue("schedule", text))

    for lesson in proposed:
        r = reqs.get(lesson.requirement_id)
        if not r:
            error("A lesson refers to a removed requirement. Regenerate or remove its lock.")
            continue
        label = requirement_name(project, r)
        if lesson.id in seen:
            error(f"{label}: a lesson block appears more than once.")
        seen.add(lesson.id)
        if expected.get(lesson.id) != (r.id, len(lesson.slot_ids)):
            error(f"{label}: this lesson block no longer matches its weekly requirements.")
        length = len(lesson.slot_ids)
        if length not in (1, 2) or len(set(lesson.slot_ids)) != length:
            error(f"{label}: a lesson must occupy one period or a two-period double.")
            continue
        if any(sid not in slots for sid in lesson.slot_ids):
            error(f"{label}: a lesson or lock refers to a removed time slot.")
            continue
        located = [slots[sid] for sid in lesson.slot_ids]
        if length == 2:
            a, b = located
            if a[0] != b[0] or b[1] != a[1] + 1 or a[2].end != b[2].start:
                error(f"{label}: a double must be adjacent on one day without a break or time gap.")
            doubles[r.id] += 1
        counts[r.id] += length
        teacher = project.lookup("teachers", r.teacher_id)
        room = project.lookup("rooms", lesson.room_id) if lesson.room_id else None
        if project.settings.rooms_enabled:
            if r.room_ids and lesson.room_id not in r.room_ids:
                error(f"{label}: choose one of its suitable rooms.")
            if lesson.room_id and not room:
                error(f"{label}: the assigned room no longer exists.")
            if not r.room_ids and lesson.room_id:
                error(f"{label}: remove the room or configure it in suitable rooms.")
        elif lesson.room_id is not None:
            error(f"{label}: room scheduling is disabled; regenerate without room assignments.")
        for sid, (d, _, slot) in zip(lesson.slot_ids, located, strict=True):
            day = project.days[d]
            where = f"{day.name}, {slot.name} ({slot.start})"
            if not slot.teaching:
                error(f"{label}: {where} is a break or blocked period.")
            if sid in teacher.unavailable:
                error(f"{teacher.name} is unavailable at {where}.")
            if project.settings.rooms_enabled and room and sid in room.unavailable:
                error(f"{room.name} is unavailable at {where}.")
            resources = [
                ("class", r.class_id, project.lookup("classes", r.class_id).name),
                ("teacher", teacher.id, teacher.name),
            ]
            if project.settings.rooms_enabled and room:
                resources.append(("room", room.id, room.name))
            for kind, record_id, name in resources:
                key = (kind, record_id, sid)
                if key in occupied:
                    error(f"{name} has two lessons at {where} ({occupied[key]} and {label}).")
                occupied[key] = label
            teacher_days[teacher.id, d] += 1
            subject_days[r.id, d] += 1
            teacher_slots[teacher.id].add(sid)
    for teacher in project.teachers:
        for d, day in enumerate(project.days):
            count = teacher_days[teacher.id, d]
            if teacher.max_daily is not None and count > teacher.max_daily:
                error(
                    f"{teacher.name} has {count} periods on {day.name}; "
                    f"daily limit is {teacher.max_daily}."
                )
            if teacher.max_consecutive is not None:
                longest = 0
                for chain in chains(day):
                    run = 0
                    for slot in chain:
                        run = run + 1 if slot.id in teacher_slots[teacher.id] else 0
                        longest = max(longest, run)
                if longest > teacher.max_consecutive:
                    error(
                        f"{teacher.name} has {longest} consecutive periods on {day.name}; "
                        f"limit is {teacher.max_consecutive}."
                    )
    for r in project.requirements:
        label = requirement_name(project, r)
        if complete and counts[r.id] != r.periods:
            error(f"{label} needs exactly {r.periods} periods; this timetable has {counts[r.id]}.")
        if complete and doubles[r.id] != r.doubles:
            error(f"{label} needs {r.doubles} double lessons; this timetable has {doubles[r.id]}.")
        if r.max_per_day is not None:
            for d, day in enumerate(project.days):
                if subject_days[r.id, d] > r.max_per_day:
                    error(f"{label} exceeds its limit of {r.max_per_day} periods on {day.name}.")
    if preserve_locks and lessons is not None:
        by_id = {lesson.id: lesson for lesson in proposed}
        for old in project.lessons:
            if old.locked:
                new = by_id.get(old.id)
                if (
                    not new
                    or not new.locked
                    or (new.slot_ids, new.room_id) != (old.slot_ids, old.room_id)
                ):
                    error("A locked lesson was moved, unlocked or removed. Unlock it first.")
    return issues
