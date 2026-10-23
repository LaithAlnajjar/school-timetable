# Contributing

Use 64-bit Python 3.12. Create a virtual environment and install pinned dependencies:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pip install --no-deps --no-build-isolation -e .
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
$env:QT_QPA_PLATFORM = 'offscreen'
.venv\Scripts\python -m pytest
```

Run the UI with `.venv\Scripts\python -m school_timetable`. For packaging, run
`powershell -ExecutionPolicy Bypass -File scripts/build-windows.ps1`. Build output
belongs in ignored `build/` and `dist/`; never commit EXE, ZIP or real school data.

Use `codex/` branches from the actual default branch (`main`), one logical change
per Conventional Commit, and focused PRs. If work depends on an unmerged PR, branch
from it and target that branch; document review order. Review both working and staged
diffs before committing. Preserve unrelated changes and configured Git identity.
Run applicable checks before each commit and the full suite before requesting review.
Never bypass hooks, force push, merge PRs or publish releases without authorization.

Tests exercise scheduling, independent validation, editing, storage and exports.
Keep Qt out of domain modules. Add a regression test for behavior changes. Update
docs/implementation-plan.md at milestone boundaries. Record genuine environment
limitations instead of claiming unobserved results.
