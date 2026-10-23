param([string]$Python = "")

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$taskRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if (-not $Python) { $Python = Join-Path $taskRoot ".venv\Scripts\python.exe" }
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw "Build on Windows x64." }
$taskOldQtPlatform = $env:QT_QPA_PLATFORM
$taskOldPath = $env:PATH
Push-Location $taskRoot
try {
    & $Python -c "import struct,sys; assert sys.version_info[:2]==(3,12) and struct.calcsize('P')==8, 'Use Python 3.12 x64'"
    if ($LASTEXITCODE) { throw "Wrong Python runtime." }
    & $Python -m pip check
    if ($LASTEXITCODE) { throw "Dependency consistency check failed." }
    & $Python -m ruff check .
    if ($LASTEXITCODE) { throw "Lint failed." }
    & $Python -m ruff format --check .
    if ($LASTEXITCODE) { throw "Formatting failed." }
    $env:QT_QPA_PLATFORM = "offscreen"
    & $Python -m pytest
    if ($LASTEXITCODE) { throw "Tests failed." }
    $env:QT_QPA_PLATFORM = $taskOldQtPlatform
    $taskBasePython = & $Python -c "import sys; print(sys.base_prefix)"
    if ($LASTEXITCODE) { throw "Cannot locate the Python runtime." }
    $env:PATH = (Split-Path -Parent $Python) + ";" + $taskBasePython + ";" + $env:SystemRoot + "\System32;" + $env:SystemRoot
    & $Python -m PyInstaller --noconfirm --clean packaging/SchoolTimetable.spec
    if ($LASTEXITCODE) { throw "PyInstaller failed." }
    $taskFolder = Join-Path $taskRoot "dist\SchoolTimetable"
    Copy-Item -LiteralPath "packaging\START_HERE.txt" -Destination $taskFolder
    Copy-Item -LiteralPath "packaging\THIRD_PARTY_NOTICES.txt" -Destination $taskFolder
    Copy-Item -LiteralPath "src\school_timetable\resources\guide.md" -Destination (Join-Path $taskFolder "USER_GUIDE.md")
    $taskExamples = Join-Path $taskFolder "Examples"
    New-Item -ItemType Directory -Force -Path $taskExamples | Out-Null
    Copy-Item -LiteralPath "examples\willow.schooltimetable", "examples\impossible.schooltimetable" -Destination $taskExamples
    & $Python scripts/bundle_licenses.py (Join-Path $taskFolder "LICENSES")
    if ($LASTEXITCODE) { throw "License bundling failed." }
    & $Python scripts/check_packaged.py (Join-Path $taskFolder "SchoolTimetable.exe") "build\packaged-smoke"
    if ($LASTEXITCODE) { throw "Folder-distribution smoke test failed." }
    $taskZip = Join-Path $taskRoot "dist\SchoolTimetable-1.0.0-windows-x64.zip"
    Compress-Archive -LiteralPath $taskFolder -DestinationPath $taskZip -Force
    $taskExtracted = Join-Path $taskRoot ("build\extracted-" + [Guid]::NewGuid().ToString("N"))
    Expand-Archive -LiteralPath $taskZip -DestinationPath $taskExtracted
    & $Python scripts/check_packaged.py (Join-Path $taskExtracted "SchoolTimetable\SchoolTimetable.exe") "build\extracted-smoke"
    if ($LASTEXITCODE) { throw "Extracted-ZIP smoke test failed." }
    Get-FileHash -LiteralPath $taskZip -Algorithm SHA256
    Write-Output "Ready: $taskZip"
}
finally {
    $env:QT_QPA_PLATFORM = $taskOldQtPlatform
    $env:PATH = $taskOldPath
    Pop-Location
}
