$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path $projectPython)) {
    throw 'The Python environment is missing. Follow README.md to install dependencies.'
}
& $projectPython -B -m backend.launch
if ($LASTEXITCODE -ne 0) { throw 'Project startup failed. See the message above.' }
