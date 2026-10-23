"""Exercise startup in new interpreters, without pytest's already-imported Qt."""

import os
import subprocess
import sys
import textwrap
from pathlib import Path


def run_fresh_python(script, output):
    env = dict(os.environ)
    source = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = os.pathsep.join(filter(None, (source, env.get("PYTHONPATH"))))
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script), str(output)],
        cwd=output,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_help_does_not_load_gui_or_backend_libraries(tmp_path):
    result = run_fresh_python(
        """
        import runpy
        import sys

        def reject_heavy_imports(event, args):
            if event == "import" and args[0].split(".")[0] in {
                "PySide6", "shiboken6", "openpyxl", "ortools", "pandas", "numpy"
            }:
                raise AssertionError("Help imported " + args[0])

        sys.addaudithook(reject_heavy_imports)
        sys.argv = ["school_timetable", "--help"]
        runpy.run_module("school_timetable", run_name="__main__")
        """,
        tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "offline weekly planner" in result.stdout
    assert "--smoke-test" in result.stdout


def test_real_entry_point_loads_backends_before_qt_and_shows_window(tmp_path):
    result = run_fresh_python(
        """
        import runpy
        import sys
        import types

        qt_imports = []

        def check_import_order(event, args):
            if event == "import" and args[0] == "PySide6":
                # Check usable public classes, rather than a timing threshold or
                # modules merely present while their imports are still running.
                assert hasattr(sys.modules.get("openpyxl"), "Workbook")
                assert hasattr(sys.modules.get("ortools.sat.python.cp_model"), "CpSolver")
                qt_imports.append(args[0])

        def check_window(app, window, output):
            from PySide6.QtCore import QTimer

            assert qt_imports, "Qt import was not observed"
            assert window.isVisible(), "Entry point did not show the main window"
            assert window.windowTitle().startswith("School Timetable")
            print("WINDOW_READY", flush=True)
            QTimer.singleShot(0, window.close)

        sys.addaudithook(check_import_order)
        # Use the entry point's isolated app-data option, replacing only the
        # full scheduling/export smoke callback with a startup visibility check.
        smoke = types.ModuleType("school_timetable.smoke")
        smoke.run_smoke = check_window
        sys.modules[smoke.__name__] = smoke
        sys.argv = ["school_timetable", "--smoke-test", sys.argv[1]]
        runpy.run_module("school_timetable", run_name="__main__")
        """,
        tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "WINDOW_READY" in result.stdout
