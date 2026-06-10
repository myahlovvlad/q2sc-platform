$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$env:PYTHONPATH = "$Root\backend"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root'; backend\.venv\Scripts\uvicorn.exe app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\frontend'; `$env:VITE_API_BASE_URL='http://127.0.0.1:8000'; npm run electron:dev"
