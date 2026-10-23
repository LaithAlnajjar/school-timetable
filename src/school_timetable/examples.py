"""Synthetic fixtures shared by the first-run example and verification."""

from .models import Day, Project, Requirement, Room, SchoolClass, Slot, Subject, Teacher


def example_school(*, impossible=False, class_count=3) -> Project:
    project = Project(school_name="Willow Secondary — Example")
    for d, name in enumerate(("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday")):
        slots = []
        for i, (start, end) in enumerate(
            (
                ("08:00", "08:45"),
                ("08:45", "09:30"),
                ("09:30", "09:50"),
                ("09:50", "10:35"),
                ("10:35", "11:20"),
                ("11:20", "12:05"),
                ("12:05", "12:45"),
                ("12:45", "13:30"),
            )
        ):
            blocked = i in (2, 6)
            slots.append(
                Slot(
                    f"d{d}s{i}",
                    "Break"
                    if i == 2
                    else "Lunch"
                    if i == 6
                    else f"Period {sum(s.teaching for s in slots) + 1}",
                    start,
                    end,
                    not blocked,
                )
            )
        project.days.append(Day(f"day{d}", name, slots))
    subject_names = ("Mathematics", "English", "Science", "History", "Physical education")
    project.subjects = [Subject(f"sub{i}", name) for i, name in enumerate(subject_names)]
    # Extra subject specialists for larger benchmark schools keep teacher loads feasible.
    teams = max(1, (class_count + 4) // 5)
    for team in range(teams):
        for i, name in enumerate(("Mrs Smith", "Mr Jones", "Ms Khan", "Mr Green", "Ms Brown")):
            project.teachers.append(Teacher(f"t{team}_{i}", f"{name} {team + 1}"))
    project.rooms = [Room("lab", "Science laboratory")]
    project.settings.rooms_enabled = class_count <= 5
    for c in range(class_count):
        project.classes.append(
            SchoolClass(f"c{c}", f"{7 + c // 3}{chr(65 + c % 3)}", str(7 + c // 3))
        )
        for i, periods in enumerate((5, 5, 4, 3, 2)):
            project.requirements.append(
                Requirement(
                    f"r{c}_{i}",
                    f"c{c}",
                    f"sub{i}",
                    f"t{c // 5}_{i}",
                    periods,
                    doubles=1 if i == 2 else 0,
                    max_per_day=2,
                    room_ids=["lab"] if i == 2 else [],
                    spread=True,
                )
            )
    if impossible:
        project.requirements[0].periods = 35
    return project
