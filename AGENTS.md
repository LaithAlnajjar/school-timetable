# Repository conventions

Read README.md, CONTRIBUTING.md and docs/implementation-plan.md before changing code.
Preserve existing history and unrelated staged/unstaged changes. Work in this checkout;
use `codex/` feature branches and focused stacked PRs when necessary. Never merge PRs,
publish releases, force push, invent Git identity, or commit generated distributions.

Keep scheduling, independent validation, project storage, exports and Qt UI separate.
Mandatory rules must never be silently relaxed. Validate every generated or edited
schedule and every export. Failed/cancelled searches preserve the previous schedule.
Use stable record IDs and portable versioned project files. Examples must be synthetic.

For each coherent change: run relevant checks, review unstaged and staged diffs, stage
only intended files, and commit with a specific Conventional Commit subject. Keep the
implementation plan current at milestone boundaries. All authored source must be committed.

Commands (Python 3.12, Windows PowerShell):

```powershell
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m pytest
.venv\Scripts\python -m school_timetable
powershell -ExecutionPolicy Bypass -File scripts/build-windows.ps1
```

Install exact dependencies as described in CONTRIBUTING.md. Use `QT_QPA_PLATFORM=offscreen`
for headless GUI tests. Test semantic constraints, not solver placement choices.
