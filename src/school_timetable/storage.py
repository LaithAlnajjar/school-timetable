"""Strict versioned JSON and atomic saves. No executable content in project files."""

from __future__ import annotations

import json
import os
import tempfile
import types
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from typing import get_args, get_origin, get_type_hints

from .models import Project

FORMAT = "school-timetable"
VERSION = 1
MAX_FILE_BYTES = 50 * 1024 * 1024


class ProjectFileError(ValueError):
    pass


def _decode(cls, value, where="project"):
    origin, args = get_origin(cls), get_args(cls)
    if origin is types.UnionType:
        for member in args:
            try:
                return _decode(member, value, where)
            except ProjectFileError:
                continue
        raise ProjectFileError(f"{where} has the wrong kind of value.")
    if cls is type(None) and value is None:
        return None
    if origin is list:
        if not isinstance(value, list):
            raise ProjectFileError(f"{where} must be a list.")
        return [_decode(args[0], item, f"{where}[{i}]") for i, item in enumerate(value)]
    if is_dataclass(cls):
        if not isinstance(value, dict):
            raise ProjectFileError(f"{where} must be a record.")
        hints = get_type_hints(cls)
        unknown = value.keys() - hints.keys()
        if unknown:
            raise ProjectFileError(f"{where} contains unsupported fields: {', '.join(unknown)}.")
        # All fields are stored by this version, so truncated files cannot silently default.
        missing = {f.name for f in fields(cls)} - value.keys()
        if missing:
            raise ProjectFileError(f"{where} is missing: {', '.join(sorted(missing))}.")
        return cls(
            **{key: _decode(hints[key], val, f"{where}.{key}") for key, val in value.items()}
        )
    if cls is float and type(value) in (int, float):
        if not float("-inf") < value < float("inf"):
            raise ProjectFileError(f"{where} must be a finite number.")
        return float(value)
    if type(value) is not cls:
        raise ProjectFileError(f"{where} has the wrong kind of value.")
    return value


def dumps(project: Project) -> str:
    return (
        json.dumps(
            {"format": FORMAT, "version": VERSION, "project": asdict(project)},
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )


def loads(text: str) -> Project:
    try:
        data = json.loads(text)
        if not isinstance(data, dict) or data.get("format") != FORMAT:
            raise ProjectFileError("This is not a School Timetable project.")
        if type(data.get("version")) is not int or data["version"] != VERSION:
            raise ProjectFileError("This project version is not supported. Open it in a newer app.")
        if set(data) != {"format", "version", "project"}:
            raise ProjectFileError("The project envelope contains missing or unsupported fields.")
        return _decode(Project, data["project"])
    except (json.JSONDecodeError, RecursionError, TypeError, KeyError) as exc:
        raise ProjectFileError("This project is damaged or is not a valid project file.") from exc


def load_project(path: str | Path) -> Project:
    try:
        source = Path(path)
        if source.stat().st_size > MAX_FILE_BYTES:
            raise ProjectFileError("This file is too large to open (maximum 50 MB).")
        return loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        raise ProjectFileError(f"Cannot open this project: {exc}") from exc


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as f:
            temp_path = Path(f.name)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def save_project(project: Project, path: str | Path, *, backup=True) -> None:
    target = Path(path)
    content = dumps(project).encode("utf-8")
    # Serialize before touching either file. A failed replacement leaves the old project intact.
    if backup and target.exists():
        atomic_write(target.with_suffix(target.suffix + ".bak"), target.read_bytes())
    atomic_write(target, content)
