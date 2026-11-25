import json
import os
import shutil
import subprocess

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".xbox_launcher.json")

EMU_LABELS = {
    "xenia": "Xenia (Xbox 360)",
    "xemu": "xemu (оригинальный Xbox)",
}

EMU_HINTS = {
    "xenia": "https://xenia.jp/download/",
    "xemu": "https://xemu.app/",
}

EMU_ARGS = {
    "xenia": [],
    "xemu": ["-dvd_path"],
}

GAME_EXTENSIONS = (".iso", ".cci", ".xex", ".xbe")
MAX_LIBRARY = 5000


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except OSError as e:
        return str(e)
    return None


def find_emu_in_path(name):
    for candidate in (name, name + ".exe"):
        p = shutil.which(candidate)
        if p:
            return p
    return ""


def resolve_emu_path(emu, config, override=""):
    if override:
        return override
    configured = config.get("emu_paths", {}).get(emu, "")
    if configured and os.path.isfile(configured):
        return configured
    return find_emu_in_path(emu)


def guess_emu(game_path):
    ext = os.path.splitext(game_path)[1].lower()
    if ext in (".xex",):
        return "xenia"
    if ext in (".xbe",):
        return "xemu"
    if ext in (".iso", ".cci"):
        try:
            with open(game_path, "rb") as f:
                header = f.read(0x20000)
        except OSError:
            return "xenia"
        if b"MICROSOFT*XBOX*MEDIA" in header or b"MICROSOFT\\XBOX\\MEDIA" in header:
            return "xemu"
        return "xenia"
    return "xenia"


def scan_library(roots):
    entries = []
    for root in roots:
        if os.path.isfile(root):
            entries.append(os.path.abspath(root))
            continue
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            for fn in filenames:
                if (
                    fn.lower() == "default.xbe"
                    or os.path.splitext(fn)[1].lower() in GAME_EXTENSIONS
                ):
                    entries.append(os.path.join(dirpath, fn))
            if len(entries) >= MAX_LIBRARY:
                break
        if len(entries) >= MAX_LIBRARY:
            break
    return sorted(set(entries))[:MAX_LIBRARY]


def resolve_game(query, config):
    if not query:
        return [], "Указан пустой путь"
    if os.path.isfile(query):
        return [os.path.abspath(query)], None
    if os.path.isdir(query):
        return scan_library([query]), None
    needle = query.lower()
    matches = [
        p
        for p in config.get("library", [])
        if needle in os.path.basename(p).lower()
    ]
    if not matches:
        return [], "Не найдено в библиотеке: %s" % query
    return matches, None


def parse_start_apps(raw):
    apps = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        app_id, _, name = line.partition("|")
        app_id = app_id.strip().strip('"')
        name = name.strip()
        if "!" in app_id:
            apps.append((name, app_id))
    return apps


def list_store_apps():
    try:
        out = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-WindowStyle",
                "Hidden",
                "-Command",
                "Get-StartApps | ForEach-Object { $_.AppID + '|' + $_.Name }",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return parse_start_apps(out)
