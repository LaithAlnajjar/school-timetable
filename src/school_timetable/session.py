"""Document state and generation-result ownership, independent of Qt widgets."""

from pathlib import Path

from .editing import ScheduleHistory
from .models import Project
from .scheduler import SolveResult
from .validation import validate_schedule


class ProjectSession:
    def __init__(self, project: Project | None = None):
        self.project = project or Project()
        self.path: Path | None = None
        self.dirty = False
        self.revision = 0
        self.history = ScheduleHistory()

    def replace(self, project, path=None, *, dirty=False):
        self.project, self.path, self.dirty = project, Path(path) if path else None, dirty
        self.revision += 1
        self.history = ScheduleHistory()

    def changed(self, *, setup=False):
        self.dirty = True
        self.revision += 1
        if setup:
            self.history = ScheduleHistory()

    def accept_result(self, result: SolveResult, started_revision: int) -> bool:
        if not result.usable or started_revision != self.revision:
            return False
        if result.fingerprint != self.project.fingerprint():
            return False
        if validate_schedule(self.project, result.lessons):
            return False
        self.history.apply(self.project, result.lessons)
        self.project.scheduled_fingerprint = result.fingerprint
        self.changed()
        return True
