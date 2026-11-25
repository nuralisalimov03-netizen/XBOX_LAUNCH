@echo off
cd /d %~dp0
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m series_emulator --gui
    goto :eof
)
where python >nul 2>nul
if %errorlevel%==0 (
    python -m series_emulator --gui
    goto :eof
)
echo Python not found. Install it from https://www.python.org/downloads/
pause
