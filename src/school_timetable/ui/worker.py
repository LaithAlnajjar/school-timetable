"""Qt signal bridge. The domain scheduler owns its thread-safe cancellation flag."""

from copy import deepcopy

from PySide6.QtCore import QThread, Signal

from ..scheduler import Scheduler


class GenerationThread(QThread):
    status = Signal(str)
    completed = Signal(object)

    def __init__(self, project, revision, parent=None):
        super().__init__(parent)
        self.snapshot = deepcopy(project)
        self.revision = revision
        self.scheduler = Scheduler()

    def run(self):
        self.completed.emit(self.scheduler.solve(self.snapshot, self.status.emit))

    def cancel(self):
        self.scheduler.cancel()
