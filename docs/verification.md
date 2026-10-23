# Verification record — 23 October 2026

Environment: Windows 11 Home x64, build 22631, CPython 3.12.14, Ryzen 7 5800H
(16 logical processors), approximately 15.4 GiB RAM. Exact dependency locks are in
requirements.txt and requirements-dev.txt. PySide6 6.10.2, OR-Tools 9.15.6755,
openpyxl 3.1.5, PyInstaller 6.18.0 with hooks 2026.9.

## Observed local results

- **42 pytest tests passed** (7.42 seconds on the final pre-commit run).
- Ruff lint and formatting checks passed; `pip check` reported no broken requirements.
- Tests cover exact period/resource assertions, teacher/class/room clashes, availability,
  enabled workload/daily subject caps, doubles, locks/regeneration, invalid and valid
  whole-block moves/swaps, undo/redo, strict storage/corruption/atomic replacement failure,
  backups/recovery, actual Qt responsiveness/cancellation, stale results, old-schedule
  preservation, synchronized views, literal/safe XLSX sheet names and PDF pagination.
- Real source entry-point smoke passed on the Windows Qt platform: generation,
  move/locks/undo/redo, locked regeneration, save/reopen, backup/recovery, help,
  class/teacher XLSX/PDF, invalid export rejection, impossible/cancelled search preservation.
- The complete Windows build script passed folder build and extracted-ZIP smoke.
  Both use the native `windows` Qt platform, bundled Python (`frozen: true`), and a
  PATH containing only Windows directories, with Python/Qt development variables removed.
  PE headers confirm Windows x64 and GUI subsystem (no console).
- Folder smoke: 1.985 seconds, 50 UI heartbeat events. Final ZIP after notice bundling:
  extracted smoke passed in 1.813 seconds, 46 UI heartbeat events. Outcomes were optimal,
  optimal with locks, impossible and cancelled. This tests the actual executable.
- Class and teacher PDFs from the frozen app were reopened, rendered and visually
  inspected. Separate normal/long-name PDF output was rendered using Poppler and
  inspected. Tests cover wide and tall grids with repeated headings and no lost periods.
- Larger example: 20 classes, 20 teachers, 100 requirements, 380 weekly periods;
  feasible in 15.351 seconds with no independent validation issues. A real 0.01-second
  search returned timeout in 0.227 seconds. See performance.md for constraints and limits.

ZIP: `dist/SchoolTimetable-1.0.0-windows-x64.zip`, 97,152,999 bytes.
SHA256: `dfe3e933e18a89f312c136b8ff347265cd9f1239ea8329c7c6771d37f2f48247`.
Build/test artifacts and smoke reports are in ignored `build/` and `dist/` folders.

## Remote review and remaining limits

Final integration branch: `codex/integration`. Review order: project-data PR #1,
scheduler PR #2, desktop PR #3, then integration/packaging PR. These branches are
stacked; the complete application is on the integration branch. CI status is pending
observation when this record is first committed; a follow-up records actual run results.

Windows 10 minimum support follows the pinned Qt platform requirement, but only
Windows 11 was exercised locally. No pristine Windows VM, signing certificate or
single-file EXE was used. No claim of unlimited school size or instant optimization.
Hard infeasibility explanations are suggestions when an exact conflict was not isolated.
Setup changes clear timetable edit history. The program uses one shared weekly grid.

The initial checkout was clean; no unrelated pre-existing changes were present.
Source changes are committed incrementally; generated bundles and real project data
are ignored. PR merging and GitHub Release publication remain with the owner.
