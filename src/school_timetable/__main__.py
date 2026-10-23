"""Application entry point; all writable state belongs in local application data."""

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from .storage import ProjectFileError, load_project
from .ui.window import MainWindow


def main():
    parser = argparse.ArgumentParser(description="School Timetable — offline weekly planner")
    parser.add_argument("project", nargs="?", help="Optional .schooltimetable file to open")
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setOrganizationName("SchoolTimetable")
    app.setApplicationName("School Timetable")
    app.setStyle("Fusion")
    app.setPalette(app.style().standardPalette())
    app.setFont(QFont("Segoe UI", 11))
    app_data = Path(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    )
    app_data.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        app_data / "application.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    logging.basicConfig(
        handlers=[handler], level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    def report_error(exc_type, exc, tb):
        logging.error("Unhandled application error", exc_info=(exc_type, exc, tb))
        QMessageBox.warning(
            None,
            "School Timetable",
            (
                "An unexpected error occurred. Your last saved project is safe. "
                "Please save a copy if you can. Details are in the application "
                "log."
            ),
        )

    sys.excepthook = report_error
    window = MainWindow(app_data, check_recovery=not bool(args.project))
    if args.project:
        try:
            window.replace_project(load_project(args.project), args.project)
        except ProjectFileError as exc:
            window.show_error("Cannot open project", str(exc))
    geometry = app.primaryScreen().availableGeometry()
    window.resize(min(1280, geometry.width() - 30), min(860, geometry.height() - 40))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
