$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (!(Test-Path ".env")) { Copy-Item ".env.example" ".env" }

$PythonLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($PythonLauncher) {
    & py -3.13 -c "import sys; assert sys.version_info[:2] == (3, 13)" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Python 3.13 is required. Install it or create backend\.venv with Python 3.10-3.13."
    }
    $CreateVenv = { & py -3.13 -m venv backend\.venv }
} else {
    $Version = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    if ([version]$Version -lt [version]"3.10" -or [version]$Version -ge [version]"3.14") {
        throw "Python 3.10-3.13 is required; found Python $Version."
    }
    $CreateVenv = { & python -m venv backend\.venv }
}

if (!(Test-Path "backend\.venv\Scripts\python.exe")) {
    & $CreateVenv
}

$VenvVersion = & backend\.venv\Scripts\python.exe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ([version]$VenvVersion -lt [version]"3.10" -or [version]$VenvVersion -ge [version]"3.14") {
    throw "backend\.venv uses unsupported Python $VenvVersion. Recreate it with Python 3.13."
}

& backend\.venv\Scripts\python.exe -m pip install --upgrade pip
& backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
& backend\.venv\Scripts\python.exe -m pip install -r scripts\requirements-docs.txt

Set-Location frontend
npm ci
Set-Location $Root

Write-Host "Environment is ready. Run: powershell -ExecutionPolicy Bypass -File scripts/dev.ps1"
