@echo off
if "%~1"=="" (
    echo Перетащите файл игры (ISO, XEX, XBE) или папку на этот файл,
    echo и игра запустится через подходящий эмулятор.
    pause
    exit /b
)
where python >nul 2>nul
if not %errorlevel%==0 (
    echo Python not found. Install it from https://www.python.org/downloads/
    pause
    exit /b
)
python "%~dp0xbox_launch.py" --launch "%~1" --save
pause
