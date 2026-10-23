# PyInstaller folder distribution. Build on Windows x64 with the locked environment.
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files

root = Path(SPECPATH).parent
ortools_data, ortools_binaries, ortools_hidden = collect_all("ortools")
data = collect_data_files("school_timetable", includes=["resources/*.md"])

a = Analysis(
    [str(root / "scripts" / "launch.py")],
    pathex=[str(root / "src")],
    binaries=ortools_binaries,
    datas=data + ortools_data,
    hiddenimports=ortools_hidden,
    hookspath=[],
    excludes=["pytest", "ruff", "fitz", "pymupdf", "pypdf", "tkinter"],
    noarchive=False,
)
# This pinned Qt build imports Windows' unversioned ICU API (Windows 10 1809+).
# Foreign ICU DLLs on a developer PATH (for example Poppler) use different symbols.
# Never shadow the operating-system ICU with one gathered from a build tool.
a.binaries = [entry for entry in a.binaries
              if Path(entry[0]).name.lower() not in {"icuuc.dll", "icuin.dll", "icudt.dll"}]
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="SchoolTimetable",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    version=str(root / "packaging" / "version_info.txt"),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="SchoolTimetable")
