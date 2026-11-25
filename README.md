# Xbox Launch

Лаунчеры и каркас эмулятора Xbox для ПК.

## Как запускать (быстро)

| Что | Как |
|---|---|
| Демо эмулятора (окно с игрой) | `run_demo.bat` или `python -m series_emulator --gui` |
| Дашборд-лаунчер (Xenia/xemu) | `launch_series.bat` или `python xbox_series_launcher.py` |
| Простой лаунчер | `launch.bat` или `python xbox_launcher.py` |
| Сборка всех .exe | `build_exe.bat` (нужен Python 3.8+, pyinstaller поставится сам) |

После `build_exe.bat` в папке появятся **SeriesDemo.exe** (демо) и
**XboxSeriesLauncher.exe** (лаунчер) — их можно запускать двойным кликом без Python.

Управление в демо: стрелки/WASD — стик, Z — «A», X — «B», Esc — выход.

## Series Emulator (каркас эмулятора)

Каркас эмулятора `series_emulator/` с работающими памятью, софт-растеризатором,
ядром и оконным демо на ПК: `run_demo.bat` или `python -m series_emulator --gui`.
Архитектура и фазы развития — в `series_emulator/ROADMAP.md`.

## Xbox Series Launcher (новый дашборд)

Полноэкранный тёмный дашборд в стиле Xbox Series X/S: плитки всех игр из папки,
недавние сверху, автозапуск нужного эмулятора, часы, статус-бар.

```bat
cd /d C:\path\to\XBOX_LAUNCH
launch_series.bat
```

либо `python xbox_series_launcher.py [--gamesdir "D:/Games/Xbox"] [--selftest]`

- **Настройки → Папка с играми**: укажите папку с `.iso .cci .xex .xbe .gdi .chd` — библиотека найдётся автоматически (включая вложенные папки).
- **Управление**: клик по плитке запускает игру; стрелки + Enter работают с клавиатуры.
- Недавние игры поднимаются наверх; путь к эмуляторам можно оставить пустым — лаунчер найдёт `xenia`/`xemu` в PATH.
- Проверка ядра без GUI: `python xbox_series_launcher.py --selftest`
- Тесты ядра: `python -m unittest test_launcher_core -v`

## Простой лаунчер (xbox_launcher.py)

Простой лаунчер для запуска файлов игр Xbox на компьютере через существующие эмуляторы.

## Как это работает

Утилита сама подбирает эмулятор под тип файла:

| Файл | Эмулятор | Консоль |
|------|----------|---------|
| `.xex` | Xenia | Xbox 360 |
| `.iso` (образ Xbox 360) | Xenia | Xbox 360 |
| `.iso` (образ оригинального Xbox) | xemu | Xbox (2001) |
| `.xbe` | xemu | Xbox (2001) |

Вы можете выбрать эмулятор вручную в выпадающем списке.

> **Важно:** эмулятора Xbox Series S/X не существует. Лаунчер запускает игры
> оригинального Xbox и Xbox 360. Используйте только образы тех игр, которыми
> вы владеете на законных основаниях.

## Установка

1. Установите [Python 3.8+](https://www.python.org/downloads/) (на Windows отметьте «Add Python to PATH»).
2. Скачайте эмуляторы:
   - [Xenia](https://xenia.jp/download/) — Xbox 360 (только 64-битная Windows)
   - [xemu](https://xemu.app/) — оригинальный Xbox (Windows / macOS / Linux)
3. Запустите лаунчер:
   - Windows: двойной клик по `launch_series.bat` (дашборд) или `launch.bat` (простой)
   - Linux/macOS: `python3 xbox_series_launcher.py` или `python3 xbox_launcher.py`

Внешние зависимости не нужны — используется стандартная библиотека Python (Tkinter).

## Использование

1. Выберите эмулятор (Xenia или xemu).
2. Укажите путь к `xenia.exe` / `xemu.exe` (если эмулятор не найден в PATH — нажмите «Обзор…»).
3. Нажмите «Обзор…» у поля «Файл игры» и выберите ISO/XEX/XBE.
4. Нажмите «Запустить игру». Кнопка «Остановить» закрывает эмулятор.

Настройки сохраняются автоматически в `~/.xbox_launcher.json`.

Скачанный Xenia требует Visual C++ Redistributable: https://aka.ms/vs/17/release/vc_redist.x64.exe
