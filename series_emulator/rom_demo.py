"""series_emulator.rom_demo — демо-«картридж» для каркаса консоли.

Заглушка настоящего загрузчика игр: мини-игра, которая использует только
открытые модули консоли (input + gpu). Управление: оси ls_x/ls_y.
"""
from __future__ import annotations

import random

PLAYER_COLOR = (255, 255, 255, 255)
TARGET_COLOR = (0, 200, 255, 255)
BG_COLOR = (16, 124, 16, 255)
HUD_COLOR = (10, 10, 10, 255)


class DemoROM:
    """Мини-игра «собери кубы»: управляемый квадрат ловит цели."""

    WIDTH = 240
    HEIGHT = 135
    PLAYER_SIZE = 8
    TARGET_SIZE = 5
    SPEED = 60.0

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)
        self.px = self.WIDTH / 2 - self.PLAYER_SIZE / 2
        self.py = self.HEIGHT / 2 - self.PLAYER_SIZE / 2
        self.score = 0
        self.tx, self.ty = self._spawn_target()
        self.collisions = 0

    def _spawn_target(self):
        margin = self.TARGET_SIZE + 2
        return (float(self.rng.randint(margin, self.WIDTH - margin - self.TARGET_SIZE)),
                float(self.rng.randint(margin + 10, self.HEIGHT - margin - self.TARGET_SIZE)))

    def update(self, dt: float, input_manager):
        pad = input_manager.controller(0)
        self.px += pad.axes["ls_x"] * self.SPEED * dt
        self.py += pad.axes["ls_y"] * self.SPEED * dt
        self.px = max(1.0, min(self.WIDTH - self.PLAYER_SIZE - 1, self.px))
        self.py = max(1.0, min(self.HEIGHT - self.PLAYER_SIZE - 1, self.py))

        if self._hits_target():
            self.score += 1
            self.collisions += 1
            self.tx, self.ty = self._spawn_target()

    def _hits_target(self) -> bool:
        pxc = self.px + self.PLAYER_SIZE / 2
        pyc = self.py + self.PLAYER_SIZE / 2
        txc = self.tx + self.TARGET_SIZE / 2
        tyc = self.ty + self.TARGET_SIZE / 2
        reach = (self.PLAYER_SIZE + self.TARGET_SIZE) / 2
        return abs(pxc - txc) < reach and abs(pyc - tyc) < reach

    def draw(self, gpu):
        gpu.clear(*BG_COLOR)
        gpu.draw_rect(int(self.px), int(self.py),
                      self.PLAYER_SIZE, self.PLAYER_SIZE, PLAYER_COLOR)
        gpu.draw_rect(int(self.tx), int(self.ty),
                      self.TARGET_SIZE, self.TARGET_SIZE, TARGET_COLOR)
        gpu.draw_text("SCORE", 4, 3, HUD_COLOR, scale=1)
        gpu.draw_text(str(self.score), 4 + 5 * 4, 3, HUD_COLOR, scale=1)
