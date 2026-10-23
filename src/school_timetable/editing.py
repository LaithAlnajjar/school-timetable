"""Atomic timetable edits with bounded undo/redo history."""

from copy import deepcopy

from .models import Lesson, Project, slot_index
from .validation import validate_schedule


class EditError(ValueError):
    pass


def destination_slots(project: Project, first_slot: str, length: int) -> list[str]:
    index = slot_index(project)
    if first_slot not in index:
        raise EditError("Choose an existing teaching period.")
    d, i, _ = index[first_slot]
    block = project.days[d].slots[i : i + length]
    if len(block) != length or not all(s.teaching for s in block):
        raise EditError(
            "This lesson block does not fit here without crossing a break or day boundary."
        )
    if length == 2 and block[0].end != block[1].start:
        raise EditError("A double lesson cannot cross a gap between lesson times.")
    return [s.id for s in block]


def move_or_swap(
    project: Project, lesson_id: str, first_slot: str, swap_id: str | None = None
) -> list[Lesson]:
    candidate = deepcopy(project.lessons)
    by_id = {lesson.id: lesson for lesson in candidate}
    lesson = by_id.get(lesson_id)
    other = by_id.get(swap_id) if swap_id else None
    if not lesson or (swap_id and not other):
        raise EditError("Select the lesson to move and, for a swap, the other lesson.")
    if lesson.locked or (other and other.locked):
        raise EditError("Unlock both lesson blocks before moving or swapping them.")
    if other and other.id == lesson.id:
        raise EditError("Choose a different lesson for the swap.")
    destination = other.slot_ids[0] if other else first_slot
    old_start = lesson.slot_ids[0]
    lesson.slot_ids = destination_slots(project, destination, len(lesson.slot_ids))
    if other:
        other.slot_ids = destination_slots(project, old_start, len(other.slot_ids))
    issues = validate_schedule(project, candidate)
    if issues:
        raise EditError("\n".join(dict.fromkeys(i.message for i in issues)))
    return candidate


class ScheduleHistory:
    def __init__(self):
        self.undo_stack: list[list[Lesson]] = []
        self.redo_stack: list[list[Lesson]] = []

    def apply(self, project: Project, candidate: list[Lesson]):
        self.undo_stack.append(deepcopy(project.lessons))
        del self.undo_stack[:-100]
        self.redo_stack.clear()
        project.lessons = deepcopy(candidate)

    def undo(self, project: Project):
        if self.undo_stack:
            self.redo_stack.append(deepcopy(project.lessons))
            project.lessons = self.undo_stack.pop()

    def redo(self, project: Project):
        if self.redo_stack:
            self.undo_stack.append(deepcopy(project.lessons))
            project.lessons = self.redo_stack.pop()
