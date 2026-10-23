@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Python environment missing. Follow README.md to install dependencies.
    exit /b 1
)
".venv\Scripts\python.exe" -B -m backend.launch %*
exit /b %errorlevel%
