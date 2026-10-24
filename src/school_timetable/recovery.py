"""Per-session autosave files in application data, separate from user project files."""

from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QLockFile

from .storage import save_project


class RecoveryStore:
    def __init__(self, app_data: Path):
        self.folder = app_data / "recovery"
        self.folder.mkdir(parents=True, exist_ok=True)
        self.path = self.folder / f"recovery-{uuid4().hex}.schooltimetable"
        self.lock = QLockFile(str(self.path.with_suffix(".lock")))
        if not self.lock.tryLock(0):
            raise OSError("Cannot create the recovery session lock.")

    def write(self, project):
        save_project(project, self.path, backup=False)

    def candidates(self):
        candidates = []
        for path in self.folder.glob("recovery-*.schooltimetable"):
            if path == self.path:
                continue
            lock = QLockFile(str(path.with_suffix(".lock")))
            if lock.tryLock(0):
                candidates.append(path)
                lock.unlock()
        return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)

    def clear(self):
        self.path.unlink(missing_ok=True)

    def close(self):
        self.clear()
        self.lock.unlock()
