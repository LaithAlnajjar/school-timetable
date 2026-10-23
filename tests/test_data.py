import json
from copy import deepcopy

import pytest

from school_timetable.examples import example_school
from school_timetable.models import delete_record, references
from school_timetable.storage import ProjectFileError, dumps, load_project, loads, save_project
from school_timetable.validation import validate_setup


def test_example_valid_and_rename_preserves_relationships():
    p = example_school()
    assert validate_setup(p) == []
    teacher_id = p.requirements[0].teacher_id
    p.teachers[0].name = "A new name"
    assert p.lookup("teachers", teacher_id).name == "A new name"
    assert references(p, "teachers", teacher_id)
    with pytest.raises(ValueError, match="used by"):
        delete_record(p, "teachers", teacher_id)
    delete_record(p, "teachers", teacher_id, cascade=True)
    assert not any(r.teacher_id == teacher_id for r in p.requirements)


def test_atomic_roundtrip_backup_and_failed_serialization(tmp_path):
    p = example_school()
    target = tmp_path / "term.schooltimetable"
    save_project(p, target)
    assert load_project(target) == p
    p.school_name = "New term"
    save_project(p, target)
    assert load_project(target).school_name == "New term"
    assert load_project(str(target) + ".bak").school_name.startswith("Willow")
    p.settings.time_limit = float("nan")
    with pytest.raises(ValueError):
        save_project(p, target)
    assert load_project(target).school_name == "New term"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(version=99),
        lambda d: d["project"]["teachers"][0].update(name=12),
        lambda d: d["project"]["requirements"][0].update(periods=True),
        lambda d: d["project"].pop("days"),
        lambda d: d["project"].update(unknown="field"),
    ],
)
def test_corrupt_unsupported_and_wrong_types_rejected(mutation):
    data = json.loads(dumps(example_school()))
    mutation(data)
    with pytest.raises(ProjectFileError):
        loads(json.dumps(data))


def test_missing_and_non_json(tmp_path):
    with pytest.raises(ProjectFileError, match="Cannot open"):
        load_project(tmp_path / "missing")
    with pytest.raises(ProjectFileError):
        loads("not json")


def test_week_times_and_missing_references():
    p = example_school()
    p.days[0].slots[1].start = "08:30"
    assert any("overlap" in i.message for i in validate_setup(p))
    p = example_school()
    p.requirements[0].teacher_id = "deleted"
    assert any("missing teacher" in i.message for i in validate_setup(p))
    p = example_school()
    p.requirements[0].doubles = 3
    assert any("two periods" in i.message for i in validate_setup(p))


def test_fingerprint_tracks_setup_but_not_schedule():
    p = example_school()
    q = deepcopy(p)
    q.scheduled_fingerprint = "previous"
    assert p.fingerprint() == q.fingerprint()
    q.classes[0].name = "Renamed"
    assert p.fingerprint() != q.fingerprint()
