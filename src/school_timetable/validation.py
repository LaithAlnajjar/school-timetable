"""Independent domain checks shared by generation, editing and final exports."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Project, slot_index, teaching_slots


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
