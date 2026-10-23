"""Portable domain data. IDs, never display names, join records together."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from uuid import uuid4


def new_id() -> str:
    return uuid4().hex


@dataclass
class Slot:
    id: str = field(default_factory=new_id)
    name: str = "Lesson"
    start: str = "08:00"
    end: str = "08:45"
    teaching: bool = True


@dataclass
class Day:
    id: str = field(default_factory=new_id)
    name: str = "Monday"
    slots: list[Slot] = field(default_factory=list)


@dataclass
class Teacher:
    id: str = field(default_factory=new_id)
    name: str = ""
    unavailable: list[str] = field(default_factory=list)
    max_daily: int | None = None
    max_consecutive: int | None = None


@dataclass
class SchoolClass:
    id: str = field(default_factory=new_id)
    name: str = ""
    year: str = ""


@dataclass
class Subject:
    id: str = field(default_factory=new_id)
    name: str = ""


@dataclass
class Room:
    id: str = field(default_factory=new_id)
    name: str = ""
    unavailable: list[str] = field(default_factory=list)


@dataclass
class Requirement:
    id: str = field(default_factory=new_id)
    class_id: str = ""
    subject_id: str = ""
    teacher_id: str = ""
    periods: int = 1
    doubles: int = 0
    max_per_day: int | None = None
    room_ids: list[str] = field(default_factory=list)
    spread: bool = False


@dataclass
class Lesson:
    id: str
    requirement_id: str
    slot_ids: list[str]
    room_id: str | None = None
    locked: bool = False


@dataclass
class Settings:
    rooms_enabled: bool = False
    reduce_gaps: bool = False
    time_limit: float = 30.0


@dataclass
class Project:
    school_name: str = "My school"
    days: list[Day] = field(default_factory=list)
    teachers: list[Teacher] = field(default_factory=list)
    classes: list[SchoolClass] = field(default_factory=list)
    subjects: list[Subject] = field(default_factory=list)
    rooms: list[Room] = field(default_factory=list)
    requirements: list[Requirement] = field(default_factory=list)
    settings: Settings = field(default_factory=Settings)
    lessons: list[Lesson] = field(default_factory=list)
    scheduled_fingerprint: str = ""

    def fingerprint(self) -> str:
        data = asdict(self)
        for key in ("lessons", "scheduled_fingerprint"):
            data.pop(key)
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def lookup(self, collection: str, record_id: str):
        return next((r for r in getattr(self, collection) if r.id == record_id), None)


def slot_index(project: Project) -> dict[str, tuple[int, int, Slot]]:
    return {
        slot.id: (d, s, slot)
        for d, day in enumerate(project.days)
        for s, slot in enumerate(day.slots)
    }


def teaching_slots(project: Project) -> list[Slot]:
    return [s for day in project.days for s in day.slots if s.teaching]


def chains(day: Day) -> list[list[Slot]]:
    """Clock-adjacent teaching runs; breaks and unrepresented gaps split runs."""
    result: list[list[Slot]] = []
    for slot in day.slots:
        if not slot.teaching:
            continue
        if result and result[-1][-1].end == slot.start:
            result[-1].append(slot)
        else:
            result.append([slot])
    return result


def lesson_blocks(requirement: Requirement) -> list[tuple[str, int]]:
    return [(f"{requirement.id}:double:{i}", 2) for i in range(requirement.doubles)] + [
        (f"{requirement.id}:single:{i}", 1)
        for i in range(requirement.periods - 2 * requirement.doubles)
    ]


def references(project: Project, collection: str, record_id: str) -> list[Requirement]:
    field_name = {
        "teachers": "teacher_id",
        "classes": "class_id",
        "subjects": "subject_id",
        "rooms": "room_ids",
    }[collection]
    return [
        r
        for r in project.requirements
        if (
            record_id in r.room_ids
            if collection == "rooms"
            else getattr(r, field_name) == record_id
        )
    ]


def delete_record(project: Project, collection: str, record_id: str, *, cascade=False) -> None:
    affected = references(project, collection, record_id)
    if affected and not cascade:
        raise ValueError(f"This record is used by {len(affected)} lesson requirement(s).")
    if collection == "rooms":
        for requirement in affected:
            requirement.room_ids.remove(record_id)
    else:
        ids = {r.id for r in affected}
        project.requirements = [r for r in project.requirements if r.id not in ids]
        project.lessons = [lesson for lesson in project.lessons if lesson.requirement_id not in ids]
    setattr(project, collection, [r for r in getattr(project, collection) if r.id != record_id])
