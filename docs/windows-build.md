# Windows delivery

Target: Windows x64, Windows 10 1809 or later; Windows 11 recommended. Development
and local packaging were exercised on Windows 11 build 22631. A Windows 10 machine
and a pristine Windows VM have not been tested. The primary deliverable is a folder
distribution in a ZIP; no single-file EXE or installer is needed.

## Reproduce

Install Python 3.12 x64 for development, then from the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pip install --no-deps --no-build-isolation -e .
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build-windows.ps1
```

If PowerShell is not on PATH, use
`& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File scripts/build-windows.ps1`.
From PowerShell 7, `./scripts/build-windows.ps1` also works. An alternative installed
Python can be selected with `-Python C:\path\to\python.exe` (3.12 x64 required).

The script runs pip consistency, Ruff lint/format and pytest checks, builds
`packaging/SchoolTimetable.spec`, copies the start guide/examples/licenses, launches
the folder EXE through the synthetic UI workflow, creates the ZIP, extracts it to a
new ignored folder and runs the same EXE workflow again. Both smoke launches remove
Python/Qt development variables and use a PATH containing only Windows directories.
The verifier also checks PE x64/GUI headers and reopens/renders the produced XLSX/PDFs.

Output: `dist/SchoolTimetable-1.0.0-windows-x64.zip`. It contains `SchoolTimetable/`
with the GUI EXE, `_internal/`, START_HERE.txt, USER_GUIDE.md, Examples and licenses.
Extract everything, then double-click SchoolTimetable.exe. Users need no Python,
Excel, account, internet connection or administrator rights. The build is unsigned.
No GitHub Release is published by these scripts.

## Native dependency handling

PyInstaller collects the OR-Tools native libraries and protocol modules, NumPy/pandas,
Python runtime and Qt widgets/GUI/platform plugins. The pinned Qt build uses Windows'
system ICU API. A developer's foreign ICU DLL (for example from Poppler) must not shadow
it; the spec filters those DLLs and the build script isolates PATH. This fixed a startup
failure observed during packaging; a console diagnostic build established the exact
missing symbols. The distribution keeps dynamically loaded libraries replaceable.

PyInstaller may report unused optional pandas/OR-Tools imports such as Jinja2, plotting
or Unix-only modules. They are not needed by this app; the actual frozen workflows
are the acceptance check. Do not bundle extra optional packages just to silence warnings.

## GitHub Actions

Checks run on PRs and pushes to main, on Windows and Ubuntu with Python 3.12. Official
actions are pinned to reviewed commit SHAs and workflows have `contents: read` only.
Local commands in CONTRIBUTING.md reproduce the checks.

Once the packaging workflow is available on the default branch, open Actions →
Package Windows → Run workflow, choose the integration/default branch, and download
the `SchoolTimetable-windows-x64` artifact. It contains the distributable ZIP; extract
the artifact wrapper first, then the application ZIP. The workflow also uploads smoke
reports. Creating a workflow is distinct from observing it succeed; actual run status
is recorded in verification.md. PRs and releases remain for the repository owner to merge/publish.
Source/build changes pushed to `codex/integration` also run packaging, allowing the
complete distributable to be verified in Windows CI before any PR is merged.
Documentation-only pushes do not rerun this packaging job.

The exact dependency locks are tracked; EXE/ZIP/build outputs, caches, logs and real
school projects are ignored. Source builds reproduce the process, not necessarily
byte-identical timestamps/signatures. Synthetic fixture files are intentionally tracked.
