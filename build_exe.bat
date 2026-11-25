@echo off
rem Сборка обоих exe. Требуется Python 3.8+ на Windows.
cd /d %~dp0
where py >nul 2>nul && (set PY=py -3) || (set PY=python)

if not exist dist md dist
%PY% -m pip install --upgrade pyinstaller 2>nul

echo === [1/2] SeriesDemo.exe (эмулятор-демо, окно с игрой) ===
%PY% -m PyInstaller --onefile --noconfirm --name SeriesDemo ^
     --collect-submodules series_emulator entry_demo.py
if errorlevel 1 goto :fail

echo === [2/2] XboxSeriesLauncher.exe (дашборд-лаунчер Xenia/xemu) ===
%PY% -m PyInstaller --onefile --noconfirm --name XboxSeriesLauncher ^
     entry_launcher.py
if errorlevel 1 goto :fail

move /y dist\SeriesDemo.exe . >nul
move /y dist\XboxSeriesLauncher.exe . >nul
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del SeriesDemo.spec XboxSeriesLauncher.spec 2>nul
echo.
echo Готово. В папке репозитория появились:
echo   SeriesDemo.exe            — окно с демо-игрой эмулятора
echo   XboxSeriesLauncher.exe    — дашборд-лаунчер (нужны Xenia/xemu)
pause
exit /b 0

:fail
echo Сборка не удалась — прокрутите вывод выше для деталей.
pause
exit /b 1
