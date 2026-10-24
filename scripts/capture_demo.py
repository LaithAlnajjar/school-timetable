"""Capture only the app's synthetic demo UI for review documentation."""

import tempfile
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from school_timetable.examples import example_school
from school_timetable.scheduler import Scheduler
from school_timetable.ui.window import MainWindow


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    app.setPalette(app.style().standardPalette())
    app.setFont(QFont("Segoe UI", 11))
    project = example_school()
    project.settings.time_limit = 2
    result = Scheduler().solve(project)
    if not result.usable:
        raise RuntimeError(result.message)
    project.lessons = result.lessons
    project.scheduled_fingerprint = project.fingerprint()
    output = Path("docs/images")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        window = MainWindow(Path(folder), check_recovery=False)
        window.replace_project(project)
        window.navigation.setCurrentRow(5)
        window.show()

        def capture():
            window.render_review()
            window.grab().save(str(output / "review.png"))
            window.navigation.setCurrentRow(3)
            app.processEvents()
            window.grab().save(str(output / "requirements.png"))
            window.close()
            app.quit()

        QTimer.singleShot(300, capture)
        app.exec()


if __name__ == "__main__":
    main()
