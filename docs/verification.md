# Verification record — 24 October 2026

Environment: Windows 11 Home x64, build 22631, CPython 3.12.14, Ryzen 7 5800H
(16 logical processors), approximately 15.4 GiB RAM. Exact dependency locks are in
requirements.txt and requirements-dev.txt. PySide6 6.10.2, OR-Tools 9.15.6755,
openpyxl 3.1.5, PyInstaller 6.18.0 with hooks 2026.9.

## Latest interface repair and replacement ZIP

Branch: **codex/interface-repair**, based on integration startup fix `d1f62a7`.
Built application source: `74349f4`. [PR #5](https://github.com/LaithAlnajjar/school-timetable/pull/5)
depends on #4; see [review order](review-order.md). Full before/after evidence,
design decisions, measured colors and limits are in [UI verification](ui-verification.md).

- **61 tests passed** in the Windows build (15.33 seconds), including 13 interface
  regressions. Ruff lint, formatting and `pip check` passed. All 31 installed locked
  dependencies also match their exact repository pins.
- Native Windows source entry-point smoke passed: 1.844 seconds, 45 UI heartbeats.
  Folder EXE smoke passed: 2.062 seconds, 50 heartbeats. Freshly extracted ZIP EXE
  smoke passed: 1.906 seconds, 46 heartbeats. Frozen runs report bundled Python and
  the native `windows` Qt platform with development paths removed. All exercise
  generation, move/lock/undo/redo, locked regeneration, saving/reopening, recovery,
  backup, XLSX/PDF, invalid export rejection and old-schedule preservation after
  impossible/cancelled generation. PE x64/GUI headers and bundled symbol files pass.
- Every workflow and important interaction state was captured and visually examined.
  Five final native runs produced 249 captures: actual Windows light/dark app
  appearance at 100%, plus Qt scale factors 125/150/200%. Final frame checks report
  zero off-screen windows. The Windows app appearance setting was restored.
  Higher scales used fresh-process `QT_SCALE_FACTOR`, not changes to the monitor's
  Windows Display setting; per-monitor DPI transitions remain unverified.
- Representative body contrast is 12.65:1, active/inactive selection 7.15:1,
  disabled labels 5.31:1, subject text 9.93–10.66:1, boundaries 4.02:1 and focus
  6.48:1. Original dark forms and selections measured 1.01:1 and 1.20:1.
- The folder and extracted EXEs produced readable class/teacher exports. All 16
  extracted-app PDF pages (6 class, 10 teacher) were reopened, rendered with Poppler
  and visually inspected; representative frozen-app pages were also rendered by
  PyMuPDF. Shared export presentation code is unchanged.
- [Windows and Ubuntu CI checks](https://github.com/LaithAlnajjar/school-timetable/actions/runs/40028886828)
  passed for application source `74349f4`, including pinned installation, dependency
  consistency, Ruff, formatting and all 61 tests.

Replacement ZIP: `dist/SchoolTimetable-1.0.0-windows-x64.zip`, **94,635,296 bytes**.
SHA256: `613ad0d84f733f8812a71f5b04f851e056d1e2a55acc12f5a5882427fa74ff7d`.
Folder: `dist/SchoolTimetable/SchoolTimetable.exe`.
Build log: `build/interface-build.log`; current native reports are under
`build/source-interface-final`, `build/packaged-smoke` and `build/extracted-smoke`.
The extracted checkout is `build/extracted-db9145c249a04b978375d58f15e0eaf5/SchoolTimetable`.
Full PDF visual evidence is in `build/pdf-visual-final`.

Remaining limits: Windows 10, a pristine machine without developer tools,
per-monitor DPI changes and Narrator were not exercised; the package remains
unsigned. The computer-use helper failed during sandbox setup, so visual inspection
used real native Qt widget captures and separate window-frame geometry checks.
All authored source and representative documentation images are committed. Generated
distributions and full test/capture output are ignored. No merges/releases performed.

The sections below retain the earlier integration/startup verification history;
their previous ZIP sizes and checksums describe superseded builds.

## Earlier integration results

- **48 pytest tests passed** (9.95 seconds in the latest Windows build).
- Ruff lint and formatting checks passed; `pip check` reported no broken requirements.
- Tests cover exact period/resource assertions, teacher/class/room clashes, availability,
  enabled workload/daily subject caps, doubles, locks/regeneration, invalid and valid
  whole-block moves/swaps, undo/redo, strict storage/corruption/atomic replacement failure,
  backups/recovery, actual Qt responsiveness/cancellation, stale results, old-schedule
  preservation, synchronized views, literal/safe XLSX sheet names and PDF pagination.
  Final regressions also cover fractional search-limit persistence and whole-day
  teacher/room restrictions after adding/copying periods, with independent workload assertions.
  Fresh-interpreter startup tests verify that help imports no GUI/backend libraries,
  the backends finish loading before Qt, and the real entry point shows its window.
- Real source entry-point smoke passed on the Windows Qt platform: generation,
  move/locks/undo/redo, locked regeneration, save/reopen, backup/recovery, help,
  class/teacher XLSX/PDF, invalid export rejection, impossible/cancelled search preservation.
- The complete Windows build script passed folder build and extracted-ZIP smoke.
  Both use the native `windows` Qt platform, bundled Python (`frozen: true`), and a
  PATH containing only Windows directories, with Python/Qt development variables removed.
  PE headers confirm Windows x64 and GUI subsystem (no console).
- Folder smoke: 2.047 seconds, 51 UI heartbeat events. Latest corrected ZIP:
  extracted smoke passed in 1.812 seconds, 46 UI heartbeat events. Outcomes were optimal,
  optimal with locks, impossible and cancelled. This tests the actual executable.
- Class and teacher PDFs from the frozen app were reopened, rendered and visually
  inspected. Separate normal/long-name PDF output was rendered using Poppler and
  inspected. Tests cover wide and tall grids with repeated headings and no lost periods.
- Larger example: 20 classes, 20 teachers, 100 requirements, 380 weekly periods;
  feasible in 15.351 seconds with no independent validation issues. A real 0.01-second
  search returned timeout in 0.227 seconds. See performance.md for constraints and limits.

ZIP: `dist/SchoolTimetable-1.0.0-windows-x64.zip`, 94,616,276 bytes.
SHA256: `a0efb04bf5a17c9367e972a1ba086ecacb6837614132438ad3ee1c2992d9dcb0`.
Build/test artifacts and smoke reports are in ignored `build/` and `dist/` folders.

## Startup follow-up

The reported `KeyboardInterrupt` occurred while Qt's feature-import hook inspected
openpyxl source during startup. Loading the spreadsheet and solver dependency trees
before Qt reduces observed source-inspection calls from 659 to 49 (dependency calls:
502 to 4). No Qt hooks or installed dependencies are patched. Argument parsing now
runs first, so `--help` needs no Qt, spreadsheet or solver imports.

Paired native Windows launches with a warm file cache opened the window in
2.27–2.70 seconds before and 2.29–2.48 seconds after the change. These overlapping
times do not establish a warm-cache speedup; the fix removes redundant source I/O
that can delay startup on cold or slow storage. The source workflow smoke passed
again (2.235 seconds after startup, 52 heartbeat events), as did the rebuilt folder
and extracted ZIP. The original entry point fails the new backend-order assertion.

## Remote review and remaining limits

Final integration branch: `codex/integration`. Review/merge order is documented in
[review-order.md](review-order.md); all four PRs are open and stacked.

**Earlier observed GitHub Actions results on application source at `d1560d3`
(before the startup follow-up):**

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
