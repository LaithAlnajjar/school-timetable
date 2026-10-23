from collections import Counter
from copy import deepcopy
from threading import Thread
from time import sleep

import pytest
from ortools.sat.python import cp_model

from school_timetable.examples import example_school
from school_timetable.models import (
    Day,
    Project,
    Requirement,
    SchoolClass,
    Slot,
    Subject,
    Teacher,
    new_id,
)
from school_timetable.scheduler import Outcome, Scheduler, preflight
from school_timetable.validation import validate_schedule


def fast_example():
    p = example_school()
    p.settings.time_limit = 2.0
    for r in p.requirements:
        r.spread = False
    return p


def solved():
    p = fast_example()
    result = Scheduler().solve(p)
    assert result.usable, (result.message, result.issues)
    p.lessons = result.lessons
    p.scheduled_fingerprint = p.fingerprint()
    return p


def test_exact_counts_teacher_class_clashes_double_and_room_constraints():
    p = solved()
    totals = Counter()
    resources = set()
    double_counts = Counter()
    for lesson in p.lessons:
        r = p.lookup("requirements", lesson.requirement_id)
        totals[r.id] += len(lesson.slot_ids)
        if len(lesson.slot_ids) == 2:
            double_counts[r.id] += 1
            positions = [
                (d, i, s)
                for d, day in enumerate(p.days)
                for i, s in enumerate(day.slots)
                if s.id in lesson.slot_ids
            ]
            assert positions[0][0] == positions[1][0]
            assert positions[1][1] == positions[0][1] + 1
            assert positions[0][2].end == positions[1][2].start
        for sid in lesson.slot_ids:
            for resource in (("class", r.class_id, sid), ("teacher", r.teacher_id, sid)):
                assert resource not in resources
                resources.add(resource)
            if r.room_ids:
                assert lesson.room_id in r.room_ids
                resource = ("room", lesson.room_id, sid)
                assert resource not in resources
                resources.add(resource)
    assert totals == Counter({r.id: r.periods for r in p.requirements})
    assert double_counts == Counter({r.id: r.doubles for r in p.requirements if r.doubles})
    assert validate_schedule(p) == []


def test_teacher_availability_daily_consecutive_and_room_unavailability():
    p = fast_example()
    teacher = p.teachers[0]
    teacher.unavailable = [s.id for s in p.days[0].slots]
    teacher.max_daily = 4
    teacher.max_consecutive = 2
    p.rooms[0].unavailable = [s.id for s in p.days[1].slots]
    result = Scheduler().solve(p)
    assert result.usable
    p.lessons = result.lessons
    for lesson in p.lessons:
        r = p.lookup("requirements", lesson.requirement_id)
        if r.teacher_id == teacher.id:
            assert not set(lesson.slot_ids) & set(teacher.unavailable)
        if lesson.room_id:
            assert not set(lesson.slot_ids) & set(p.rooms[0].unavailable)
    assert validate_schedule(p) == []
    taught = {
        sid
        for lesson in p.lessons
        if p.lookup("requirements", lesson.requirement_id).teacher_id == teacher.id
        for sid in lesson.slot_ids
    }
    for day in p.days:
        assert sum(slot.id in taught for slot in day.slots) <= 4
        run, previous_end = 0, None
        for slot in day.slots:
            if not slot.teaching or previous_end != slot.start:
                run = 0
            run = run + 1 if slot.teaching and slot.id in taught else 0
            assert run <= 2
            previous_end = slot.end if slot.teaching else None


def test_whole_day_restrictions_cover_added_and_copied_periods():
    p = fast_example()
    p.teachers[0].unavailable = [p.days[0].id]
    p.rooms[0].unavailable = [p.days[1].id]
    p.days[0].slots.append(Slot("new-period", "New period", "13:30", "14:15"))
    # Replacing a daily pattern changes slot IDs, while its day identity remains stable.
    for slot in p.days[1].slots:
        slot.id = new_id()
    result = Scheduler().solve(p)
    assert result.usable
    unavailable_teacher = {slot.id for slot in p.days[0].slots}
    unavailable_room = {slot.id for slot in p.days[1].slots}
    for lesson in result.lessons:
        r = p.lookup("requirements", lesson.requirement_id)
        if r.teacher_id == p.teachers[0].id:
            assert not set(lesson.slot_ids) & unavailable_teacher
        if lesson.room_id == p.rooms[0].id:
            assert not set(lesson.slot_ids) & unavailable_room
    assert validate_schedule(p, result.lessons) == []


def test_day_restrictions_in_capacity_and_independent_validation():
    p = solved()
    lesson = p.lessons[0]
    r = p.lookup("requirements", lesson.requirement_id)
    teacher = p.lookup("teachers", r.teacher_id)
    day = next(day for day in p.days if any(s.id == lesson.slot_ids[0] for s in day.slots))
    teacher.unavailable = [day.id]
    assert any(
        teacher.name in i.message and "unavailable" in i.message for i in validate_schedule(p)
    )
    teacher.unavailable = [day.id for day in p.days]
    assert any(teacher.name in i.message and "only 0" in i.message for i in preflight(p))


def test_independent_validator_rejects_bad_counts_clashes_availability_and_breaks():
    p = solved()
    assert any("exactly" in i.message for i in validate_schedule(p, p.lessons[:-1]))
    bad = deepcopy(p.lessons)
    bad[1].slot_ids = list(bad[0].slot_ids)
    assert any("two lessons" in i.message for i in validate_schedule(p, bad))
    bad = deepcopy(p.lessons)
    bad[0].slot_ids = [p.days[0].slots[2].id]
    assert any("break" in i.message for i in validate_schedule(p, bad))
    r = p.lookup("requirements", p.lessons[0].requirement_id)
    p.lookup("teachers", r.teacher_id).unavailable = p.lessons[0].slot_ids[:]
    assert any("unavailable" in i.message for i in validate_schedule(p))


def test_locked_blocks_survive_regeneration_and_conflicts_explained():
    p = solved()
    double = next(lesson for lesson in p.lessons if len(lesson.slot_ids) == 2)
    double.locked = True
    result = Scheduler().solve(p)
    assert result.usable
    assert next(lesson for lesson in result.lessons if lesson.id == double.id) == double
    p.lookup("requirements", double.requirement_id).doubles = 0
    assert any("block" in i.message for i in preflight(p))


def test_capacity_names_and_counts_and_no_mutation():
    p = example_school(impossible=True)
    before = deepcopy(p)
    result = Scheduler().solve(p)
    assert result.outcome == Outcome.IMPOSSIBLE
    assert any("7A" in i.message and "49" in i.message and "30" in i.message for i in result.issues)
    assert p == before
    p = fast_example()
    p.teachers[0].unavailable = [s.id for d in p.days for s in d.slots]
    result = Scheduler().solve(p)
    assert any(
        "Mrs Smith" in i.message and "15" in i.message and "0" in i.message for i in result.issues
    )


def test_doubles_cannot_cross_break_gap_or_day():
    p = fast_example()
    for day in p.days:
        for slot in day.slots:
            if slot.teaching:
                # Keep 45-minute lessons separated by at least one minute.
                h, m = map(int, slot.end.split(":"))
                slot.end = f"{(h * 60 + m - 1) // 60:02}:{(h * 60 + m - 1) % 60:02}"
    result = Scheduler().solve(p)
    assert result.outcome == Outcome.IMPOSSIBLE
    assert any("no suitable consecutive" in i.message for i in result.issues)


def test_combined_impossibility_proven_without_false_exact_diagnosis():
    p = Project(
        days=[Day("d", "School day", [Slot("s1", "1"), Slot("s2", "2", "08:45", "09:30")])],
        teachers=[Teacher("t1", "Alice", ["s2"]), Teacher("t2", "Bob", ["s2"])],
        classes=[SchoolClass("c", "7A")],
        subjects=[Subject("a", "Art"), Subject("b", "Biology")],
        requirements=[Requirement("r1", "c", "a", "t1"), Requirement("r2", "c", "b", "t2")],
    )
    assert preflight(p) == []
    result = Scheduler().solve(p)
    assert result.outcome == Outcome.IMPOSSIBLE
    assert "not an exact conflict diagnosis" in result.issues[0].message


def test_time_limit_outcome_is_not_impossibility(monkeypatch):
    monkeypatch.setattr(cp_model.CpSolver, "solve", lambda *_: cp_model.UNKNOWN)
    result = Scheduler().solve(fast_example())
    assert result.outcome == Outcome.TIMEOUT
    assert "does not prove" in result.message


def test_feasible_unfinished_optimization_is_usable(monkeypatch):
    real_solve = cp_model.CpSolver.solve

    def unfinished(self, model):
        assert real_solve(self, model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        return cp_model.FEASIBLE

    monkeypatch.setattr(cp_model.CpSolver, "solve", unfinished)
    result = Scheduler().solve(fast_example())
    assert result.usable and result.outcome == Outcome.FEASIBLE
    assert "unfinished" in result.message
    assert validate_schedule(fast_example(), result.lessons) == []


def test_cancellation_before_and_during_generation_preserves_project():
    p = example_school(class_count=20)
    original = deepcopy(p)
    scheduler = Scheduler()
    scheduler.cancel()
    assert scheduler.solve(p).outcome == Outcome.CANCELLED
    scheduler = Scheduler()
    results = []
    worker = Thread(target=lambda: results.append(scheduler.solve(p)))
    worker.start()
    sleep(0.1)
    scheduler.cancel()
    worker.join(timeout=10)
    assert not worker.is_alive()
    assert results[0].outcome == Outcome.CANCELLED
    assert p == original


def test_invalid_and_internal_error_distinct(monkeypatch):
    p = fast_example()
    p.requirements[0].teacher_id = "missing"
    assert Scheduler().solve(p).outcome == Outcome.INVALID
    monkeypatch.setattr(
        cp_model.CpSolver, "solve", lambda *_: (_ for _ in ()).throw(RuntimeError("test"))
    )
    assert Scheduler().solve(fast_example()).outcome == Outcome.ERROR


@pytest.mark.parametrize("kind", ["daily", "consecutive", "subject", "room", "lock"])
def test_validator_checks_enabled_limits_and_locks(kind):
    p = solved()
    lesson = p.lessons[0]
    r = p.lookup("requirements", lesson.requirement_id)
    if kind == "daily":
        p.lookup("teachers", r.teacher_id).max_daily = 1
    elif kind == "consecutive":
        double = next(lesson for lesson in p.lessons if len(lesson.slot_ids) == 2)
        dr = p.lookup("requirements", double.requirement_id)
        p.lookup("teachers", dr.teacher_id).max_consecutive = 1
    elif kind == "subject":
        double = next(lesson for lesson in p.lessons if len(lesson.slot_ids) == 2)
        p.lookup("requirements", double.requirement_id).max_per_day = 1
    elif kind == "room":
        next(lesson for lesson in p.lessons if lesson.room_id).room_id = None
    else:
        lesson.locked = True
        changed = deepcopy(p.lessons)
        changed[0].locked = False
        assert any("locked lesson" in i.message for i in validate_schedule(p, changed))
        return
    assert validate_schedule(p)
