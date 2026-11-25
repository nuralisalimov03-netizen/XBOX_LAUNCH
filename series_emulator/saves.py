"""series_emulator.saves — сохранение рекорда и прогресса (ядро СОН)."""
from __future__ import annotations

import json
import os

DEFAULT_SAVE_PATH = os.path.join(os.path.expanduser("~"),
                                 ".series_emulator_save.json")


def load_save(path: str = DEFAULT_SAVE_PATH) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save(data: dict, path: str = DEFAULT_SAVE_PATH) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def submit_score(score: int, path: str = DEFAULT_SAVE_PATH) -> bool:
    """Пишет рекорд, только если новый score выше сохранённого.
    Остальные поля файла сохраняются."""
    data = load_save(path)
    best = int(data.get("best", 0))
    if score <= best:
        return False
    data["best"] = score
    return save(data, path)
