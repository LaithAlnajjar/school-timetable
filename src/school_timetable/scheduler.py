"""Explicit finite-placement CP-SAT model; no Qt or persistence dependencies."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum

from ortools.sat.python import cp_model

from .models import Lesson, Project, chains, lesson_blocks, teaching_slots, unavailable_slots
from .validation import Issue, requirement_name, validate_schedule, validate_setup


class Outcome(StrEnum):
    OPTIMAL = "optimal"
    FEASIBLE = "feasible"
    IMPOSSIBLE = "impossible"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    INVALID = "invalid"
    ERROR = "error"


@dataclass
class SolveResult:
    outcome: Outcome
    message: str
    lessons: list[Lesson] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    elapsed: float = 0.0
    fingerprint: str = ""

    @property
    def usable(self):
        return self.outcome in (Outcome.OPTIMAL, Outcome.FEASIBLE)


def placements(project: Project, requirement, length):
    teacher = project.lookup("teachers", requirement.teacher_id)
    blocked = unavailable_slots(project, teacher)
    room_ids = (
        requirement.room_ids if project.settings.rooms_enabled and requirement.room_ids else [None]
    )
    room_blocked = {
        room_id: unavailable_slots(project, project.lookup("rooms", room_id))
        for room_id in room_ids
        if room_id is not None
    }
    for d, day in enumerate(project.days):
        for i, slot in enumerate(day.slots):
            block = day.slots[i : i + length]
            if len(block) != length or not all(s.teaching for s in block):
                continue
            if length == 2 and slot.end != block[1].start:
                continue
            ids = [s.id for s in block]
            if any(sid in blocked for sid in ids):
                continue
            for room_id in room_ids:
                if room_id and any(sid in room_blocked[room_id] for sid in ids):
                    continue
                yield d, ids, room_id


def preflight(project: Project) -> list[Issue]:
    issues = validate_setup(project)
    if issues:
        return issues

    def error(text):
        issues.append(Issue("requirements", text))

    slots = teaching_slots(project)
    for group in project.classes:
        required = sum(r.periods for r in project.requirements if r.class_id == group.id)
        if required > len(slots):
            error(
                f"{group.name} needs {required} periods but has only {len(slots)} teaching slots."
            )
    for teacher in project.teachers:
        blocked = unavailable_slots(project, teacher)
        required = sum(r.periods for r in project.requirements if r.teacher_id == teacher.id)
        available = sum(s.id not in blocked for s in slots)
        capacity = 0
        for day in project.days:
            daily = sum(s.teaching and s.id not in blocked for s in day.slots)
            if teacher.max_consecutive is not None:
                # Availability splits teaching runs too. This is an upper bound on capacity.
                daily = 0
                for chain in chains(day):
                    run = 0
                    for slot in chain + [None]:
                        if slot and slot.id not in blocked:
                            run += 1
                        else:
                            daily += run - run // (teacher.max_consecutive + 1)
                            run = 0
            capacity += min(daily, teacher.max_daily) if teacher.max_daily is not None else daily
        if required > available:
            error(
                f"{teacher.name} has {required} assigned periods but only {available} "
                "available teaching slots."
            )
        elif required > capacity:
            error(
                f"{teacher.name} has {required} assigned periods but their daily/consecutive "
                f"limits allow at most {capacity}."
            )
    for r in project.requirements:
        label = requirement_name(project, r)
        if r.max_per_day is not None and r.periods > r.max_per_day * len(project.days):
            error(
                f"{label} needs {r.periods} periods but its daily subject limit allows only "
                f"{r.max_per_day * len(project.days)} in the week."
            )
        if r.doubles and not any(placements(project, r, 2)):
            error(
                f"{label} needs double lessons but has no suitable consecutive available slots "
                "without a break or time gap (including teacher and room availability)."
            )
    locked = [lesson for lesson in project.lessons if lesson.locked]
    if locked:
        issues.extend(validate_schedule(project, locked, complete=False))
    return issues


class Scheduler:
    def __init__(self):
        self.cancelled = threading.Event()
        self.solver: cp_model.CpSolver | None = None

    def cancel(self):
        self.cancelled.set()
        if self.solver is not None:
            self.solver.stop_search()

    def solve(self, project: Project, status=lambda text: None) -> SolveResult:
        snapshot = deepcopy(project)
        start = time.monotonic()
        fingerprint = snapshot.fingerprint()

        def result(outcome, message, lessons=None, issues=None):
            return SolveResult(
                outcome, message, lessons or [], issues or [], time.monotonic() - start, fingerprint
            )

        try:
            if self.cancelled.is_set():
                return result(
                    Outcome.CANCELLED, "Generation cancelled. The previous timetable is unchanged."
                )
            status("Checking lesson requirements and locked lessons…")
            invalid = validate_setup(snapshot)
            if invalid:
                return result(
                    Outcome.INVALID,
                    "Please correct the school setup before generating.",
                    issues=invalid,
                )
            problems = preflight(snapshot)
            if problems:
                return result(
                    Outcome.IMPOSSIBLE, "These requirements cannot all be met.", issues=problems
                )
            model = cp_model.CpModel()
            buckets = defaultdict(list)
            options = {}
            locks = {lesson.id: lesson for lesson in snapshot.lessons if lesson.locked}
            terms = []
            status("Building the timetable rules…")
            for r in snapshot.requirements:
                for block_id, length in lesson_blocks(r):
                    if self.cancelled.is_set():
                        return result(
                            Outcome.CANCELLED,
                            "Generation cancelled. The previous timetable is unchanged.",
                        )
                    candidates = []
                    lock = locks.get(block_id)
                    for d, ids, room_id in placements(snapshot, r, length):
                        if lock and (lock.slot_ids != ids or lock.room_id != room_id):
                            continue
                        var = model.new_bool_var(f"{block_id}:{ids[0]}:{room_id}")
                        candidates.append((var, ids, room_id))
                        for sid in ids:
                            buckets["class", r.class_id, sid].append(var)
                            buckets["teacher", r.teacher_id, sid].append(var)
                            buckets["teacher_day", r.teacher_id, d].append(var)
                            buckets["subject_day", r.id, d].append(var)
                            if room_id:
                                buckets["room", room_id, sid].append(var)
                    if not candidates:
                        text = (
                            f"{requirement_name(snapshot, r)}: no position satisfies "
                            "this lesson's rules"
                        )
                        return result(Outcome.IMPOSSIBLE, text + (" and lock." if lock else "."))
                    model.add_exactly_one(var for var, _, _ in candidates)
                    options[block_id] = (r, candidates)
            for (kind, _, _), variables in list(buckets.items()):
                if kind in ("class", "teacher", "room"):
                    model.add_at_most_one(variables)
            occupancy = {}
            for teacher in snapshot.teachers:
                for d, day in enumerate(snapshot.days):
                    if teacher.max_daily is not None:
                        model.add(sum(buckets["teacher_day", teacher.id, d]) <= teacher.max_daily)
                    for chain in chains(day):
                        for i in range(len(chain)):
                            slot = chain[i]
                            busy = model.new_bool_var(f"busy:{teacher.id}:{slot.id}")
                            model.add(busy == sum(buckets["teacher", teacher.id, slot.id]))
                            occupancy[teacher.id, slot.id] = busy
                        if teacher.max_consecutive is not None:
                            n = teacher.max_consecutive + 1
                            for i in range(len(chain) - n + 1):
                                model.add(
                                    sum(occupancy[teacher.id, s.id] for s in chain[i : i + n]) < n
                                )
                    if snapshot.settings.reduce_gaps:
                        # Count free teaching slots between this day's first/last lesson.
                        day_slots = [s for s in day.slots if s.teaching]
                        for i in range(1, len(day_slots) - 1):
                            before = model.new_bool_var(f"before:{teacher.id}:{d}:{i}")
                            after = model.new_bool_var(f"after:{teacher.id}:{d}:{i}")
                            model.add_max_equality(
                                before, [occupancy[teacher.id, s.id] for s in day_slots[:i]]
                            )
                            model.add_max_equality(
                                after, [occupancy[teacher.id, s.id] for s in day_slots[i + 1 :]]
                            )
                            gap = model.new_bool_var(f"gap:{teacher.id}:{d}:{i}")
                            model.add(
                                gap >= before + after - occupancy[teacher.id, day_slots[i].id] - 1
                            )
                            terms.append(gap)
            for r in snapshot.requirements:
                for d in range(len(snapshot.days)):
                    daily = sum(buckets["subject_day", r.id, d])
                    if r.max_per_day is not None:
                        model.add(daily <= r.max_per_day)
                    if r.spread:
                        excess = model.new_int_var(0, r.periods * r.periods, f"spread:{r.id}:{d}")
                        # Convex penalty: balanced daily totals beat concentrated ones.
                        count = model.new_int_var(0, r.periods, f"count:{r.id}:{d}")
                        model.add(count == daily)
                        model.add_multiplication_equality(excess, [count, count])
                        terms.append(excess * 2)
            if terms:
                model.minimize(sum(terms))
            if self.cancelled.is_set():
                return result(
                    Outcome.CANCELLED, "Generation cancelled. The previous timetable is unchanged."
                )
            self.solver = cp_model.CpSolver()
            self.solver.parameters.max_time_in_seconds = snapshot.settings.time_limit
            self.solver.parameters.num_search_workers = 4
            self.solver.parameters.random_seed = 42
            status("Searching for a valid timetable; then improving enabled preferences…")
            # Close the stop-before-solve race; also cancel searches without solutions.
            done = threading.Event()

            def watch_cancel():
                while not done.wait(0.05):
                    if self.cancelled.is_set():
                        self.solver.stop_search()

            watcher = threading.Thread(target=watch_cancel, daemon=True)
            watcher.start()
            try:
                code = self.solver.solve(model)
            finally:
                done.set()
                watcher.join()
            if self.cancelled.is_set():
                return result(
                    Outcome.CANCELLED, "Generation cancelled. The previous timetable is unchanged."
                )
            if code == cp_model.INFEASIBLE:
                suggestion = Issue(
                    "schedule",
                    "The solver proved the combined mandatory rules impossible. "
                    "Possible causes to review: competing teacher/room availability, "
                    "daily limits and locks. These suggestions are not an exact "
                    "conflict diagnosis.",
                )
                return result(
                    Outcome.IMPOSSIBLE,
                    "The mandatory rules cannot all be satisfied.",
                    issues=[suggestion],
                )
            if code == cp_model.UNKNOWN:
                return result(
                    Outcome.TIMEOUT,
                    "Search time expired without finding a timetable. "
                    "This does not prove the rules are impossible. Try a longer search.",
                )
            if code not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                return result(
                    Outcome.ERROR, "The scheduling model could not be solved. Please check the log."
                )
            lessons = []
            for block_id, (r, candidates) in options.items():
                for var, ids, room_id in candidates:
                    if self.solver.boolean_value(var):
                        lessons.append(Lesson(block_id, r.id, ids, room_id, block_id in locks))
            status("Independently checking every lesson and mandatory rule…")
            failures = validate_schedule(snapshot, lessons)
            if failures:
                logging.error("Solver output failed validation: %s", failures)
                return result(
                    Outcome.ERROR,
                    "The generated timetable failed verification; "
                    "the previous timetable is unchanged.",
                    issues=failures,
                )
            optimal = code == cp_model.OPTIMAL
            return result(
                Outcome.OPTIMAL if optimal else Outcome.FEASIBLE,
                "Valid timetable found."
                if optimal
                else "Valid timetable found. Preference optimization is unfinished; "
                "all mandatory rules are satisfied.",
                lessons,
            )
        except Exception:
            logging.exception("Timetable generation failed")
            return result(
                Outcome.ERROR,
                "An internal error stopped generation. The previous timetable "
                "is unchanged. See the application log for details.",
            )
