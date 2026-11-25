#!/usr/bin/env python3
import argparse
import os
import platform
import subprocess
import sys

from xbox_core import (
    CONFIG_PATH,
    EMU_ARGS,
    EMU_HINTS,
    EMU_LABELS,
    find_emu_in_path,
    guess_emu,
    load_config,
    resolve_emu_path,
    save_config,
)


def cmd_check(_):
    print("Xbox Launch — диагностика")
    print()
    print("Python: %s" % platform.python_version())
    print("ОС: %s" % platform.platform())
    try:
        import tkinter

        print("Tkinter (GUI): есть")
    except ImportError:
        print("Tkinter (GUI): НЕТ — GUI-режим недоступен, консольный работает")

    for emu in EMU_LABELS:
        found = find_emu_in_path(emu)
        if found:
            state = "найден: %s" % found
        else:
            state = "НЕ найден в PATH — скачайте: %s" % EMU_HINTS[emu]
        print("%s: %s" % (EMU_LABELS[emu], state))

    print("Конфиг: %s" % (CONFIG_PATH if os.path.exists(CONFIG_PATH) else "нет"))
    return 0


def do_launch(args):
    game = args.launch
    if not os.path.isfile(game):
        print("Ошибка: файл игры не найден: %s" % game)
        return 1
    emu = args.emu
    if emu == "auto":
        emu = guess_emu(game)
    if emu not in EMU_ARGS:
        print("Ошибка: неизвестный эмулятор: %s (доступны: %s)"
              % (emu, ", ".join(list(EMU_ARGS) + ["auto"])))
        return 2
    config = load_config()
    emu_path = resolve_emu_path(emu, config, args.emupath)
    if not emu_path or not os.path.isfile(emu_path):
        print("Ошибка: эмулятор %s не найден. Скачайте: %s"
              % (EMU_LABELS[emu], EMU_HINTS[emu]))
        return 3
    if args.save:
        config["last_game"] = os.path.abspath(game)
        config["emu"] = emu
        config.setdefault("emu_paths", {})[emu] = os.path.abspath(emu_path)
        err = save_config(config)
        if err:
            print("Предупреждение: не удалось сохранить настройки: %s" % err)

    cmd = [emu_path] + EMU_ARGS[emu] + [game]
    if args.emu == "auto":
        print("Тип файла определён автоматически → %s" % EMU_LABELS[emu])
    else:
        print("Эмулятор: %s" % EMU_LABELS[emu])
    print("Запуск: %s" % " ".join(cmd))
    code = subprocess.call(cmd, cwd=os.path.dirname(emu_path) or None)
    print("Эмулятор завершился с кодом %s" % code)
    return code if 0 <= code < 256 else 1


def main():
    parser = argparse.ArgumentParser(
        prog="xbox_launch",
        description="Консольный запуск игр Xbox через эмуляторы Xenia/xemu "
        "(без GUI). Пример: python xbox_launch.py --launch game.iso",
    )
    parser.add_argument("--check", action="store_true",
                        help="показать диагностику окружения")
    parser.add_argument("--launch", metavar="FILE",
                        help="файл игры (ISO, XEX, XBE) для запуска")
    parser.add_argument("--emu", default="auto",
                        help="xenia, xemu или auto (по умолчанию auto)")
    parser.add_argument("--emupath", default="",
                        help="путь к исполняемому файлу эмулятора")
    parser.add_argument("--save", action="store_true",
                        help="запомнить игру и эмулятор в конфиге")
    args = parser.parse_args()

    if args.check:
        return cmd_check(args)
    if args.launch:
        return do_launch(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
