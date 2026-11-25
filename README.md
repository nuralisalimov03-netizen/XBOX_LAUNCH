# Xbox Launch

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
   - Windows: двойной клик по `launch.bat` или `python xbox_launcher.py`
   - Linux/macOS: `python3 xbox_launcher.py`

Внешние зависимости не нужны — используется стандартная библиотека Python (Tkinter).

## Использование

1. Выберите эмулятор (Xenia или xemu).
2. Укажите путь к `xenia.exe` / `xemu.exe` (если эмулятор не найден в PATH — нажмите «Обзор…»).
3. Нажмите «Обзор…» у поля «Файл игры» и выберите ISO/XEX/XBE.
4. Нажмите «Запустить игру». Кнопка «Остановить» закрывает эмулятор.

Настройки сохраняются автоматически в `~/.xbox_launcher.json`.

Скачанный Xenia требует Visual C++ Redistributable: https://aka.ms/vs/17/release/vc_redist.x64.exe

# SeriesCore — эксперимент с Xbox Series X|S

В каталоге [`seriescore/`](seriescore/README.md) находится пре-альфа каркас
открытого проекта по эмуляции Xbox Series X|S: честная архитектурная
документация, дорожная карта и CLI (`seriescore.py`). Эмулятора Series X|S
не существует ни в одном открытом проекте — здесь только фундамент, игры не запускаются.

Легальный путь играть в игры Series X|S на ПК — Microsoft Store / приложение
Xbox (Xbox Play Anywhere, Game Pass): это «официальная технология Series X|S
on PC».
