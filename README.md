# school-timetable

School Timetable is an offline Windows desktop planner for a secondary-school headteacher.
Configure the week and teaching requirements, generate a clash-free timetable, adjust
and lock lessons, save a portable project and export class/teacher timetables.

Requires Windows 10 version 1809 or later, x64 (Windows 11 recommended). Packaged users
need no Python, account, Excel, administrator rights or network connection.

Development uses Python 3.12 x64. See [CONTRIBUTING.md](CONTRIBUTING.md) for the pinned
environment and check commands, [the specification](docs/specification.md) for scope,
and [the implementation plan](docs/implementation-plan.md) for milestone status.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pip install --no-deps --no-build-isolation -e .
.venv\Scripts\python -m pytest
```

Synthetic example project files are in `examples/`. Real school files, exports,
logs and distribution bundles are ignored by Git.
