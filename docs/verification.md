# Verification record — 23 October 2026

Environment: Windows 11 Home x64, build 22631, CPython 3.12.14, Ryzen 7 5800H
(16 logical processors), approximately 15.4 GiB RAM. Exact dependency locks are in
requirements.txt and requirements-dev.txt. PySide6 6.10.2, OR-Tools 9.15.6755,
openpyxl 3.1.5, PyInstaller 6.18.0 with hooks 2026.9.

## Observed local results

- **46 pytest tests passed** (7.00 seconds in the final Windows build).
- Ruff lint and formatting checks passed; `pip check` reported no broken requirements.
- Tests cover exact period/resource assertions, teacher/class/room clashes, availability,
  enabled workload/daily subject caps, doubles, locks/regeneration, invalid and valid
  whole-block moves/swaps, undo/redo, strict storage/corruption/atomic replacement failure,
  backups/recovery, actual Qt responsiveness/cancellation, stale results, old-schedule
  preservation, synchronized views, literal/safe XLSX sheet names and PDF pagination.
  Final regressions also cover fractional search-limit persistence and whole-day
  teacher/room restrictions after adding/copying periods, with independent workload assertions.
- Real source entry-point smoke passed on the Windows Qt platform: generation,
  move/locks/undo/redo, locked regeneration, save/reopen, backup/recovery, help,
  class/teacher XLSX/PDF, invalid export rejection, impossible/cancelled search preservation.
- The complete Windows build script passed folder build and extracted-ZIP smoke.
  Both use the native `windows` Qt platform, bundled Python (`frozen: true`), and a
  PATH containing only Windows directories, with Python/Qt development variables removed.
  PE headers confirm Windows x64 and GUI subsystem (no console).
- Folder smoke: 1.875 seconds, 48 UI heartbeat events. Final corrected ZIP:
  extracted smoke passed in 1.860 seconds, 46 UI heartbeat events. Outcomes were optimal,
  optimal with locks, impossible and cancelled. This tests the actual executable.
- Class and teacher PDFs from the frozen app were reopened, rendered and visually
  inspected. Separate normal/long-name PDF output was rendered using Poppler and
  inspected. Tests cover wide and tall grids with repeated headings and no lost periods.
- Larger example: 20 classes, 20 teachers, 100 requirements, 380 weekly periods;
  feasible in 15.351 seconds with no independent validation issues. A real 0.01-second
  search returned timeout in 0.227 seconds. See performance.md for constraints and limits.

ZIP: `dist/SchoolTimetable-1.0.0-windows-x64.zip`, 94,616,520 bytes.
SHA256: `faffed2b0c12ea76c742c80139efbf2bdec447966f7e17d4bd7a72cd6c82401a`.
Build/test artifacts and smoke reports are in ignored `build/` and `dist/` folders.

## Remote review and remaining limits

Final integration branch: `codex/integration`. Review/merge order is documented in
[review-order.md](review-order.md); all four PRs are open and stacked.

**Observed GitHub Actions results on application source at `d1560d3`:**

- [Windows and Ubuntu checks](https://github.com/LaithAlnajjar/school-timetable/actions/runs/39978302172)
  both succeeded, including installation, dependency consistency, Ruff and all 46 tests.
- [Windows packaging](https://github.com/LaithAlnajjar/school-timetable/actions/runs/39978295834)
  succeeded, including 46 tests, PyInstaller build, native GUI folder smoke, ZIP creation,
  extraction, native GUI smoke again, and uploads of the distributable and smoke reports.
  This hosted build used Python 3.12.10. Folder smoke took 1.578 seconds (42 heartbeats),
  extracted smoke 1.547 seconds (43 heartbeats), both on the native Windows Qt platform.
- [CI distributable artifact](https://github.com/LaithAlnajjar/school-timetable/actions/runs/39978295834/artifacts/12512875530)
  and [smoke reports](https://github.com/LaithAlnajjar/school-timetable/actions/runs/39978295834/artifacts/12511464540)
  were uploaded successfully. The artifact wrapper contains the application ZIP.
  The CI application ZIP's SHA256 is `70fca5bcf2c5d7ab263762df81b16d58a65de2647f62ba300c8a0eea0c934b72`;
  its bytes differ from the local Python 3.12.14 build and timestamps.

The initial manual dispatch attempt returned HTTP 404 because the workflow is not yet
on main. The successful packaging run above used the integration push trigger. Manual
dispatch becomes available after merging the workflow into main; no merge was performed.

Windows 10 minimum support follows the pinned Qt platform requirement, but Windows 10
was not exercised. Local Windows 11 and hosted Windows CI were tested. No pristine
Windows desktop without developer tools, signing certificate or
single-file EXE was used. No claim of unlimited school size or instant optimization.
Hard infeasibility explanations are suggestions when an exact conflict was not isolated.
Setup changes clear timetable edit history. The program uses one shared weekly grid.

The initial checkout was clean; no unrelated pre-existing changes were present.
Source changes are committed incrementally; generated bundles and real project data
are ignored. PR merging and GitHub Release publication remain with the owner.
