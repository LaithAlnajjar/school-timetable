"""Application entry point; all writable state belongs in local application data."""

import argparse
import logging
import sys
from importlib import import_module
from logging.handlers import RotatingFileHandler
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="School Timetable — offline weekly planner")
    parser.add_argument("project", nargs="?", help="Optional .schooltimetable file to open")
    parser.add_argument(
        "--smoke-test",
        type=Path,
        metavar="OUTPUT_FOLDER",
        help="Run the synthetic packaged workflow and write a JSON report",
    )
    args = parser.parse_args()

    # Qt's feature-import hook inspects newly imported modules' source files.
    # Load the spreadsheet/solver dependency trees first to avoid hundreds of
    # unnecessary file reads before the window appears, especially on Windows.
    for backend in ("openpyxl", "ortools.sat.python.cp_model"):
        import_module(backend)

    from PySide6.QtCore import QStandardPaths
    from PySide6.QtWidgets import QApplication, QMessageBox

    from .storage import ProjectFileError, load_project
    from .ui.theme import apply_theme
    from .ui.window import MainWindow

    app = QApplication(sys.argv[:1])
    app.setOrganizationName("SchoolTimetable")
    app.setApplicationName("School Timetable")
    apply_theme(app)
    app_data = (
        args.smoke_test / "app-data"
        if args.smoke_test
        else Path(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
        )
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
    window = MainWindow(app_data, check_recovery=not bool(args.project or args.smoke_test))
    if args.project:
        try:
            window.replace_project(load_project(args.project), args.project)
        except ProjectFileError as exc:
            window.show_error("Cannot open project", str(exc))
    geometry = app.primaryScreen().availableGeometry()
    window.resize(min(1280, geometry.width() - 30), min(860, geometry.height() - 40))
    window.show()
    if args.smoke_test:
        from .smoke import run_smoke

        run_smoke(app, window, args.smoke_test)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
