#!/usr/bin/env python3
"""launcher_core.py — ядро лаунчера без GUI.

Здесь только логика: конфиг, скан библиотеки, определение эмулятора,
сборка команды запуска. Никаких импортов Tkinter, чтобы этот модуль
гарантированно работал на любой машине и в автотестах.

Другие модули лаунчера (xbox_series_launcher.py) должны использовать
именно этот модуль — так GUI можно менять, не трогая логику.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

DEFAULT_CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".xbox_series_launcher.json")

GAME_EXTENSIONS = (".iso", ".cci", ".xex", ".xbe", ".gdi", ".chd")

EMU_LABELS = {
    "xenia": "Xenia (Xbox 360)",
    "xemu": "xemu (оригинальный Xbox)",
}

EMU_HINTS = {
    "xenia": "https://xenia.jp/download/",
    "xemu": "https://xemu.app/",
}

XBOX_MEDIA_MAGIC = b"MICROSOFT*XBOX*MEDIA"
HEADER_SNIFF_BYTES = 0x20000


def load_config(path: str = DEFAULT_CONFIG_PATH) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(cfg: dict, path: str = DEFAULT_CONFIG_PATH) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def pretty_title(filename: str) -> str:
    """'Sonic_Adventure_disc1.iso' -> 'Sonic Adventure disc1'."""
    base = os.path.basename(filename)
    stem, _ = os.path.splitext(base)
    return stem.replace("_", " ").replace(".", " ").strip()


def _sniff_xbox_media(path: str) -> bool:
    """Эвристика: ищем magic-строку XDVDFS в начале образа."""
    try:
        with open(path, "rb") as f:
            header = f.read(HEADER_SNIFF_BYTES)
    except OSError:
        return False
    escaped = header.replace(b"\\", b"*")
    return XBOX_MEDIA_MAGIC in escaped or XBOX_MEDIA_MAGIC in header


def guess_emu(game_path: str) -> str:
    """Возвращает 'xenia' или 'xemu' по расширению и заголовку файла."""
    ext = os.path.splitext(game_path)[1].lower()
    if ext == ".xex":
        return "xenia"
    if ext in (".xbe", ".gdi"):
        return "xemu"
    if ext in (".iso", ".cci", ".chd"):
        if _sniff_xbox_media(game_path):
            return "xemu"
        return "xenia"
    return "xenia"


def scan_library(games_dir: str, max_depth: int = 3) -> list:
    """Сканирует папку с играми и возвращает список записей библиотеки.

    Каждая запись: {'title', 'path', 'emu'}. Папка сканируется рекурсивно
    на глубину max_depth; файлы с расширениями из GAME_EXTENSIONS игнорируются.
    """
    games_dir = os.path.abspath(games_dir)
    results = []
    if not os.path.isdir(games_dir):
        return results
    games_dir = games_dir.rstrip(os.sep) + os.sep
    for root, _dirs, files in os.walk(games_dir):
        depth = root[len(games_dir):].count(os.sep)
        if depth > max_depth:
            _dirs[:] = []
            continue
        for name in files:
            if os.path.splitext(name)[1].lower() not in GAME_EXTENSIONS:
                continue
            path = os.path.join(root, name)
            results.append({
                "title": pretty_title(name),
                "path": path,
                "emu": guess_emu(path),
            })
    results.sort(key=lambda g: g["title"].lower())
    return results


def find_emu_in_path(name: str) -> str:
    """Ищет эмулятор в PATH ('xenia', 'xemu'). Возвращает путь или ''. """
    for candidate in (name, name + ".exe"):
        found = shutil.which(candidate)
        if found:
            return found
    return ""


def resolve_emu_path(cfg: dict, emu: str) -> str:
    """Путь к бинарнику эмулятора: из конфига, иначе поиск в PATH."""
    configured = (cfg.get("emu_paths") or {}).get(emu, "")
    if configured and os.path.isfile(configured):
        return configured
    return find_emu_in_path(emu)


def build_launch_command(emu: str, emu_path: str, game_path: str) -> list:
    """Готовая команда запуска игры выбранным эмулятором."""
    if emu not in EMU_LABELS:
        raise ValueError("Неизвестный эмулятор: %r" % emu)
    if emu == "xemu":
        return [emu_path, "-dvd_path", game_path]
    return [emu_path, game_path]


def record_recent(cfg: dict, game_path: str, size: int = 8) -> dict:
    """Добавляет игру в начало списка недавних (без дубликатов)."""
    recent = [p for p in cfg.get("recent_games", []) if p != game_path]
    recent.insert(0, game_path)
    cfg["recent_games"] = recent[:size]
    return cfg


def selftest() -> int:
    """Быстрая проверка ядра на временных файлах. Needed без GUI."""
    checks = []

    checks.append(("pretty_title", pretty_title("Halo_2.v2.iso") == "Halo 2 v2"))

    with tempfile.TemporaryDirectory() as tmp:
        xex = os.path.join(tmp, "game.xex")
        xbe = os.path.join(tmp, "game.xbe")
        open(xex, "wb").close()
        open(xbe, "wb").close()
        og_iso = os.path.join(tmp, "og.iso")
        with open(og_iso, "wb") as f:
            f.write(b"\x00" * 0x100)
            f.write(XBOX_MEDIA_MAGIC + b"\x00" * 0x10)
        plain_iso = os.path.join(tmp, "360.iso")
        with open(plain_iso, "wb") as f:
            f.write(b"\x00" * 0x800)
        checks.append(("guess xex->xenia", guess_emu(xex) == "xenia"))
        checks.append(("guess xbe->xemu", guess_emu(xbe) == "xemu"))
        checks.append(("guess og-iso->xemu", guess_emu(og_iso) == "xemu"))
        checks.append(("guess 360-iso->xenia", guess_emu(plain_iso) == "xenia"))

        lib = os.path.join(tmp, "Games")
        sub = os.path.join(lib, "sub")
        os.makedirs(sub)
        for name in ("b.iso", "a.xex", "note.txt", "z.cci"):
            open(os.path.join(lib, name), "wb").close()
        open(os.path.join(sub, "deep.xbe"), "wb").close()
        titles = [g["title"] for g in scan_library(lib)]
        checks.append(("scan finds, skips txt",
                       len(titles) == 4 and titles[0].lower().startswith("a")))

    cmd = build_launch_command("xemu", "xemu.exe", "/x/game.iso")
    checks.append(("xemu args", cmd == ["xemu.exe", "-dvd_path", "/x/game.iso"]))
    cmd = build_launch_command("xenia", "xenia.exe", "/x/game.iso")
    checks.append(("xenia args", cmd == ["xenia.exe", "/x/game.iso"]))

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "cfg.json")
        cfg = {"games_dir": "/x", "emu_paths": {"xenia": "x.exe"}}
        ok_save = save_config(cfg, path)
        cfg2 = load_config(path)
        checks.append(("config roundtrip", ok_save and cfg2 == cfg))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print("  [%s] %s" % ("OK" if ok else "FAIL", name))
    if failed:
        print("SELFTEST FAILED: %s" % ", ".join(failed))
        return 1
    print("CORE SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(selftest())
