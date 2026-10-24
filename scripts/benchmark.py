"""Reproducible larger-school benchmark; records actual elapsed time and environment."""

import argparse
import json
import platform
import time
from importlib.metadata import version
from pathlib import Path

from school_timetable.examples import example_school
from school_timetable.scheduler import Scheduler
from school_timetable.validation import validate_schedule


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--classes", type=int, default=20)
    parser.add_argument("--seconds", type=float, default=15)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    p = example_school(class_count=args.classes)
    p.settings.time_limit = args.seconds
    start = time.perf_counter()
    result = Scheduler().solve(p)
    errors = validate_schedule(p, result.lessons) if result.usable else result.issues
    report = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "processor": platform.processor(),
        "ortools": version("ortools"),
        "classes": len(p.classes),
        "teachers": len(p.teachers),
        "requirements": len(p.requirements),
        "periods": sum(r.periods for r in p.requirements),
        "teaching_slots": sum(s.teaching for d in p.days for s in d.slots),
        "search_limit_seconds": args.seconds,
        "outcome": result.outcome,
        "elapsed_seconds": round(time.perf_counter() - start, 3),
        "validation_issues": [i.message for i in errors],
        "preferences": "spread each subject; gaps disabled",
        "rooms": p.settings.rooms_enabled,
    }
    text = json.dumps(report, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    return 0 if result.usable and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
