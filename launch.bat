@echo off
where python >nul 2>nul
if %errorlevel%==0 (
    python "%~dp0xbox_launcher.py"
) else (
    echo Python not found. Install it from https://www.python.org/downloads/
    pause
)
