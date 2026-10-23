# Implementation milestones

1. **Complete — project data.** Models, week validation, stable references, atomic
   storage/recovery, examples, repository conventions and pinned environment.
2. **Complete — scheduling.** CP-SAT constraints/preferences, preflight, independent
   schedule validation, locks, cancellation and representative benchmark.
3. **Complete — desktop workflow.** Guided Qt setup, responsive generation, shared
   views, atomic manual edits/undo, Excel/Qt PDF exports and user guide.
4. **Complete — Windows delivery.** PyInstaller folder build, reproducible scripts,
   Windows/Linux checks, manual packaging CI, smoke/visual QA and final audit.

The checkout began clean at `7048b84` on `main`; origin's default is `main`.
No pre-existing AGENTS.md or CONTRIBUTING.md. Preserve the initial README/history.
Each milestone will be committed and proposed as a stacked PR; later work does not
wait for a merge. Source is tracked; synthetic examples are allowlisted; builds and
real projects are ignored. Minor decisions and actual validation appear below.

Decisions: Python 3.12 x64; teaching periods are explicitly timed slots; consecutive
means adjoining in clock time, so breaks and gaps reset a sequence. A required room
is represented as a suitable-room list of one. Default advanced mandatory limits
are unset. Manual edits preserve complete lesson blocks and use shared validation.

Project-data validation: 10 pytest cases passed on Windows 11 / CPython 3.12.14;
Ruff lint/format and `pip check` passed. Exact runtime/transitive pins are recorded
in requirements.txt; development/build/inspection pins are in requirements-dev.txt.
Recovery integration belongs to the desktop milestone; atomic storage is ready.

Scheduler validation: 26 tests passed, including independent count/resource assertions,
availability/limits, real doubles and room constraints, locks, impossible combinations,
cancel-before/during search and controlled solver-status regression tests. No input
project is mutated by generation. CP-SAT uses four workers and seed 42; valid feasible
results remain usable before preference optimality is proved. Hard infeasibility gets
honest suggestions rather than an unproved exact diagnosis. See performance.md.

Desktop foundation: atomic moves/swaps, bounded undo/redo, shared class/teacher
projections, validated XLSX/Qt PDF exports. 32 tests passed. Representative normal
and long-name PDFs rendered and visually inspected; repeated headers, readable
fixed font and paginated day columns. Windows offscreen tests explicitly load system
fonts; text extraction normalizes PDF whitespace. Names are limited to 180 characters
(period names 60) for readable output.

Desktop integration: guided setup/forms/checklist, class/teacher loads, advanced
availability/limits/rooms, actual QThread generation/cancellation and revision guards,
shared school/class/teacher review with atomic block editing/locks/undo, current-state
exports, safe Save/Open/Save As, unsaved prompts, debounced/30-second recovery, per-window
recovery locks, rotating logs and built-in plain-English help. Backup files open as copies.
41 tests passed including the Qt workflow, responsive event loop, stale results,
failure preservation, autosave, current edited exports and both PDF pagination axes.
Synthetic screenshots in docs/images were visually inspected; row heights account for
wrapped room/double/lock labels.

Windows delivery: pinned PyInstaller spec and fail-fast Windows build script, isolated
DLL discovery, x64/no-console verification, official dependency notices, ZIP extraction
and native GUI smoke with development paths removed. A real frozen-startup failure
was traced to Poppler's foreign ICU DLL; the spec/PATH isolation now prevents it.
Final ZIP extracted smoke passed, with actual Qt Windows platform and bundled Python.
42 local tests, Ruff lint/format, pip consistency, source smoke and folder/ZIP smoke
passed. PDF pages from the packaged app were rendered and visually inspected.
Final self-review fixes: the desktop preserves fractional search limits, and whole-day
teacher/room absences follow stable day IDs when periods are added or copied. Individual
slot restrictions remain supported without a file-schema migration. 46 tests now pass;
the corrected folder and extracted ZIP were rebuilt and passed native smoke again.
CI workflows are configured for PR/main Windows/Linux checks and manual Windows
artifact packaging. Actual remote CI status and remaining review are recorded in
verification.md after the final integration PR is opened. No merges/releases performed.
Integration source/build pushes additionally trigger the same Windows packaging job;
this permits pre-merge CI verification while manual dispatch awaits default-branch registration.

Final remote verification: Windows and Ubuntu checks passed in Actions run 39978302172;
Windows packaging run 39978295834 passed the full build, folder/extracted native smoke
and artifact uploads. The distributable and smoke reports are available as CI artifacts.
All app source is committed on codex/integration. See verification.md and review-order.md.

Startup follow-up (24 October): parse command-line arguments before loading desktop
dependencies, and load openpyxl/OR-Tools before Qt installs its feature-import hook.
This removes hundreds of redundant source inspections along the reported interrupted
startup path. Two fresh-interpreter regressions verify lightweight help, initialized
backends before Qt, and a visible main window. All 48 tests, Ruff and dependency checks
pass. The source workflow, rebuilt folder EXE and extracted replacement ZIP pass native
Windows smoke. See verification.md for measurements and the replacement ZIP checksum.

Interface repair (24 October), first checkpoint: native Windows captures of every
workflow, dialogs, availability, errors, help, selections and generation states
confirmed dark Windows palette leakage into light-styled forms and unreadable
selected lessons. A centralized light palette now defines active, inactive and
disabled roles, readable selections/placeholders, boundaries, focus, tooltips and
control symbols. Five focused contrast/rendering regressions and the existing
desktop/startup tests pass (16 tests); Ruff and pip consistency pass. Layout,
keyboard editing, full visual/scaling verification and replacement delivery follow
on codex/interface-repair, stacked above codex/integration. Baseline captures are
in build/ui-before; representative evidence is retained in docs/images.
