"""series_emulator.input — состояние геймпада (Series-схема Xbox)."""
from __future__ import annotations

AXIS_RANGE = (-32768, 32767)


class Controller:
    def __init__(self, index: int = 0):
        self.index = index
        self.buttons = {name: False for name in (
            "A", "B", "X", "Y", "LB", "RB", "LT", "RT",
            "view", "menu", "ls_click", "rs_click", "dpad_up",
            "dpad_down", "dpad_left", "dpad_right", "nexus")}
        self.axes = {name: 0.0 for name in (
            "ls_x", "ls_y", "rs_x", "rs_y", "lt", "rt")}

    def press(self, name: str):
        if name not in self.buttons:
            raise KeyError("Нет такой кнопки: %s" % name)
        self.buttons[name] = True

    def release(self, name: str):
        if name not in self.buttons:
            raise KeyError("Нет такой кнопки: %s" % name)
        self.buttons[name] = False

    def set_axis(self, name: str, value: float):
        if name not in self.axes:
            raise KeyError("Нет такой оси: %s" % name)
        value = max(-1.0, min(1.0, float(value)))
        if name in ("lt", "rt") and value < 0.0:
            value = 0.0
        self.axes[name] = value

    def to_dict(self) -> dict:
        return {"index": self.index,
                "buttons": dict(self.buttons),
                "axes": dict(self.axes)}


class InputManager:
    def __init__(self, controllers: int = 2):
        self.controllers = [Controller(i) for i in range(controllers)]

    def controller(self, index: int = 0) -> Controller:
        return self.controllers[index]

    def status(self) -> dict:
        return {"controllers": [c.to_dict() for c in self.controllers]}
