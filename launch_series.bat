@echo off
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0xbox_series_launcher.py" %*
    goto :eof
)
where python >nul 2>nul
if %errorlevel%==0 (
    python "%~dp0xbox_series_launcher.py" %*
    goto :eof
)
echo Python not found. Install it from https://www.python.org/downloads/
pause
