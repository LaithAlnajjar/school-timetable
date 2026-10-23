# Implementation milestones

1. **Complete — project data.** Models, week validation, stable references, atomic
   storage/recovery, examples, repository conventions and pinned environment.
2. **Next — scheduling.** CP-SAT constraints/preferences, preflight, independent
   schedule validation, locks, cancellation and representative benchmark.
3. **Pending — desktop workflow.** Guided Qt setup, responsive generation, shared
   views, atomic manual edits/undo, Excel/Qt PDF exports and user guide.
4. **Pending — Windows delivery.** PyInstaller folder build, reproducible scripts,
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
