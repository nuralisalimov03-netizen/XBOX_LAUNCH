"""series_emulator.rom_demo — демо-«картридж» каркаса консоли.

Полный игровой цикл: boot-анимация (логотип-сфера с расходящимся кольцом),
игра «собери кубы» с HUD (SCORE/BEST), пауза, рестарт, рекорд через saves.py.
"""
from __future__ import annotations

import random

from . import saves

PLAYER_COLOR = (255, 255, 255, 255)
PLAYER_GLOW = (107, 203, 255, 255)
TARGET_COLOR = (0, 200, 255, 255)
BG_TOP = (24, 26, 30, 255)
BG_BOTTOM = (8, 9, 11, 255)
SCENE_FRAME = (64, 70, 78, 255)
HUD_BACK = (12, 13, 15, 255)
HUD_TEXT = (230, 232, 235, 255)
LOGO_GREEN = (16, 124, 16, 255)
PAUSE_DIM = (0, 0, 0, 170)

BOOT_FRAMES = 60
LOGO_COLOR_1 = (16, 124, 16, 255)
LOGO_COLOR_2 = (230, 232, 235, 255)


class DemoROM:
    """Мини-игра: управляемый куб ловит цели. Содержит boot-заставку."""

    WIDTH = 240
    HEIGHT = 135
    PLAYER_SIZE = 8
    TARGET_SIZE = 5
    SPEED = 60.0
    HUD_H = 14

    def __init__(self, seed: int = 0, save_path: str = None):
        self.rng = random.Random(seed)
        self.save_path = save_path
        self.on_target_caught = None
        self.reset(new_game=True, save_path=save_path, seed=seed)
        loaded = saves.load_save(save_path) if save_path else {}
        self.best = int(loaded.get("best", 0))

    def reset(self, new_game=False, save_path=None, seed=None):
        if seed is not None:
            self.rng = random.Random(seed)
        if save_path is not None:
            self.save_path = save_path
        self.px = self.WIDTH / 2 - self.PLAYER_SIZE / 2
        self.py = self.HUD_H + (self.HEIGHT - self.HUD_H) / 2 - self.PLAYER_SIZE / 2
        self.score = 0
        self.collisions = 0
        self.paused = False
        self.frame = 0
        self.mode = "boot" if new_game else "play"
        self.tx, self.ty = self._spawn_target()

    def _spawn_target(self):
        margin = self.TARGET_SIZE + 4
        return (float(self.rng.randint(margin, self.WIDTH - margin - self.TARGET_SIZE)),
                float(self.rng.randint(self.HUD_H + margin,
                                       self.HEIGHT - margin - self.TARGET_SIZE)))

    def toggle_pause(self):
        if self.mode == "play":
            self.paused = not self.paused

    def update(self, dt: float, input_manager):
        self.frame += 1
        if self.mode == "boot":
            if self.frame >= BOOT_FRAMES:
                self.mode = "play"
                self.frame = 0
            return
        if self.paused:
            return
        pad = input_manager.controller(0)
        self.px += pad.axes["ls_x"] * self.SPEED * dt
        self.py += pad.axes["ls_y"] * self.SPEED * dt
        self.px = max(2.0, min(self.WIDTH - self.PLAYER_SIZE - 2, self.px))
        self.py = max(self.HUD_H + 2.0,
                      min(self.HEIGHT - self.PLAYER_SIZE - 2, self.py))

        if self._hits_target():
            self.score += 1
            self.collisions += 1
            if self.score > self.best:
                self.best = self.score
                if self.save_path and saves.submit_score(self.score, self.save_path):
                    self.saved_new_record = True
            self.tx, self.ty = self._spawn_target()
            if self.on_target_caught:
                try:
                    self.on_target_caught()
                except Exception:
                    pass

    def _hits_target(self) -> bool:
        pxc = self.px + self.PLAYER_SIZE / 2
        pyc = self.py + self.PLAYER_SIZE / 2
        txc = self.tx + self.TARGET_SIZE / 2
        tyc = self.ty + self.TARGET_SIZE / 2
        reach = (self.PLAYER_SIZE + self.TARGET_SIZE) / 2
        return abs(pxc - txc) < reach and abs(pyc - tyc) < reach

    def draw(self, gpu):
        gpu.draw_gradient(BG_TOP, BG_BOTTOM)
        if self.mode == "boot":
            self._draw_boot(gpu)
            return
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
        gpu.draw_text("BEST", self.WIDTH - 4 - 11 * 4, 4, HUD_TEXT, scale=1)
        gpu.draw_text(str(self.best), self.WIDTH - 4 - 2 * 4, 4, LOGO_GREEN, scale=1)
        if self.paused:
            gpu.draw_rect(self.WIDTH // 2 - 22, self.HEIGHT // 2 - 6,
                          44, 13, HUD_BACK)
            gpu.draw_frame_rect(self.WIDTH // 2 - 22, self.HEIGHT // 2 - 6,
                                44, 13, HUD_TEXT, 1)
            gpu.draw_text("PAUSE", self.WIDTH // 2 - 10, self.HEIGHT // 2 - 3,
                          HUD_TEXT, scale=1)

    def _draw_boot(self, gpu):
        t = self.frame
        cx, cy = self.WIDTH // 2, self.HEIGHT // 2
        if t < 20:
            r = t
            gpu.draw_circle(cx, cy, r, LOGO_COLOR_1, fill=True)
        elif t < 40:
            wave = int((t - 20) * 1.5)
            gpu.draw_circle(cx, cy, min(18 + wave, cy), (40, 160, 70, 60),
                            fill=False, thickness=2)
            gpu.draw_circle(cx, cy, 20, LOGO_COLOR_1, fill=True)
        else:
            gpu.draw_circle(cx, cy, 20, LOGO_COLOR_1, fill=True)
            alpha_y = min(cy - 26 + (t - 40), cy + 10)
            gpu.draw_text("XBOX", cx - 10, alpha_y, LOGO_COLOR_2, scale=1)
