"""series_emulator.rom_demo — демо-«картридж» для каркаса консоли.

Мини-игра «собери кубы» в визуальном стиле тёмного дашборда: градиентный фон,
рамка сцены, HUD-панель со счётом. Управление: оси ls_x/ls_y геймпада.
"""
from __future__ import annotations

import random

PLAYER_COLOR = (255, 255, 255, 255)
PLAYER_GLOW = (107, 203, 255, 255)
TARGET_COLOR = (0, 200, 255, 255)
BG_TOP = (24, 26, 30, 255)
BG_BOTTOM = (8, 9, 11, 255)
SCENE_FRAME = (64, 70, 78, 255)
HUD_BACK = (12, 13, 15, 255)
HUD_TEXT = (230, 232, 235, 255)


class DemoROM:
    """Мини-игра «собери кубы»: управляемый квадрат ловит цели."""

    WIDTH = 240
    HEIGHT = 135
    PLAYER_SIZE = 8
    TARGET_SIZE = 5
    SPEED = 60.0
    HUD_H = 14

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)
        self.px = self.WIDTH / 2 - self.PLAYER_SIZE / 2
        self.py = self.HUD_H + (self.HEIGHT - self.HUD_H) / 2 - self.PLAYER_SIZE / 2
        self.score = 0
        self.tx, self.ty = self._spawn_target()
        self.collisions = 0

    def _spawn_target(self):
        margin = self.TARGET_SIZE + 4
        return (float(self.rng.randint(margin, self.WIDTH - margin - self.TARGET_SIZE)),
                float(self.rng.randint(self.HUD_H + margin,
                                       self.HEIGHT - margin - self.TARGET_SIZE)))

    def update(self, dt: float, input_manager):
        pad = input_manager.controller(0)
        self.px += pad.axes["ls_x"] * self.SPEED * dt
        self.py += pad.axes["ls_y"] * self.SPEED * dt
        self.px = max(2.0, min(self.WIDTH - self.PLAYER_SIZE - 2, self.px))
        self.py = max(self.HUD_H + 2.0,
                      min(self.HEIGHT - self.PLAYER_SIZE - 2, self.py))

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
        gpu.draw_gradient(BG_TOP, BG_BOTTOM)
        gpu.draw_frame_rect(0, self.HUD_H, self.WIDTH,
                            self.HEIGHT - self.HUD_H, SCENE_FRAME, 1)
        gpu.draw_rect(0, 0, self.WIDTH, self.HUD_H - 1, HUD_BACK)
        gpu.draw_frame_rect(0, 0, self.WIDTH, self.HUD_H, SCENE_FRAME, 1)
        gpu.draw_rect(int(self.px) - 1, int(self.py) - 1,
                      self.PLAYER_SIZE + 2, self.PLAYER_SIZE + 2, PLAYER_GLOW)
        gpu.draw_rect(int(self.px), int(self.py),
                      self.PLAYER_SIZE, self.PLAYER_SIZE, PLAYER_COLOR)
        gpu.draw_rect(int(self.tx) - 1, int(self.ty) - 1,
                      self.TARGET_SIZE + 2, self.TARGET_SIZE + 2, HUD_BACK)
        gpu.draw_rect(int(self.tx), int(self.ty),
                      self.TARGET_SIZE, self.TARGET_SIZE, TARGET_COLOR)
        gpu.draw_text("SCORE", 4, 4, HUD_TEXT, scale=1)
        gpu.draw_text(str(self.score), 4 + 6 * 5, 4, HUD_TEXT, scale=1)
