"""series_emulator.frontend — оконный фронтенд каркаса на Tkinter.

Показывает framebuffer консоли в окне ПК и мапит клавиатуру на геймпад:
стрелки/WASD — стик, Z — A, X — B. Полноценная эмуляция Series X — см. ROADMAP.
"""
from __future__ import annotations

import base64
import time

from .console import SeriesConsole
from .rom_demo import DemoROM

FPS = 30
SCALE = 2


def _rgb_bytes(gpu) -> bytes:
    """RGBA framebuffer -> P6 PPM bytes (для tk.PhotoImage format='ppm')."""
    rgb = bytearray(gpu.width * gpu.height * 3)
    pos = 0
    for y in range(gpu.height):
        row = gpu.mem.read_bytes(gpu.framebuffer + y * gpu.stride, gpu.stride)
        for x in range(gpu.width):
            src = x * 4
            rgb[pos] = row[src]
            rgb[pos + 1] = row[src + 1]
            rgb[pos + 2] = row[src + 2]
            pos += 3
    return b"P6\n%d %d\n255\n" % (gpu.width, gpu.height) + bytes(rgb)


def run_gui(rom=None, width=DemoROM.WIDTH, height=DemoROM.HEIGHT,
            scale=SCALE, fps=FPS):
    try:
        import tkinter as tk
    except ImportError:
        print("Tkinter недоступен. Установите python3-tk и повторите.")
        return 1

    console = SeriesConsole(width=width, height=height)
    console.boot()
    rom = rom or DemoROM()

    root = tk.Tk()
    root.title("Series Emulator (work in progress) — DEMO cart")
    root.configure(bg="#0e0e0e")
    canvas = tk.Canvas(root, width=width * scale, height=height * scale,
                       bg="#0e0e0e", highlightthickness=0)
    canvas.pack(padx=8, pady=8)
    hud = tk.Label(root, text="", bg="#0e0e0e", fg="#9a9a9a",
                   font=("Segoe UI", 9))
    hud.pack(fill="x")

    key_axis = {"Left": "left", "Right": "right", "Up": "up", "Down": "down",
                "a": "left", "d": "right", "w": "up", "s": "down"}
    pressed = set()
    buttons = {"z": "A", "x": "B"}

    def _on_press(e):
        pressed.add(e.keysym)

    def _on_release(e):
        pressed.discard(e.keysym)

    for k in key_axis:
        root.bind("<KeyPress-%s>" % k, _on_press)
        root.bind("<KeyRelease-%s>" % k, _on_release)
    for k in buttons:
        root.bind("<KeyPress-%s>" % k, _on_press)
        root.bind("<KeyRelease-%s>" % k, _on_release)
    root.bind("<Escape>", lambda e: root.destroy())

    pad = console.input.controller(0)

    def apply_input():
        pad.set_axis("ls_x",
                     (1 if "Right" in pressed or "d" in pressed else 0)
                     - (1 if "Left" in pressed or "a" in pressed else 0))
        pad.set_axis("ls_y",
                     (1 if "Down" in pressed or "s" in pressed else 0)
                     - (1 if "Up" in pressed or "w" in pressed else 0))
        for k, btn in buttons.items():
            (pad.press(btn) if k in pressed else pad.release(btn))

    img_holder = {"img": None}

    def blit():
        data = base64.b64encode(_rgb_bytes(console.gpu))
        img = tk.PhotoImage(data=data, format="ppm",
                            width=width, height=height)
        if scale > 1:
            img = img.zoom(scale)
        img_holder["img"] = img
        canvas.delete("all")
        canvas.create_image(0, 0, image=img, anchor="nw")

    interval = int(1000 / fps)
    last = time.time()

    def tick():
        nonlocal last
        now = time.time()
        dt = min(0.1, now - last)
        last = now
        apply_input()
        rom.update(dt, console.input)
        console.frames += 1
        rom.draw(console.gpu)
        blit()
        hud.configure(text="score %d   frames %d   GPU: soft raster %dx%d   "
                           "(Series X emulation — фаза 0 из ROADMAP.md)"
                           % (rom.score, console.frames, width, height))
        root.after(interval, tick)

    root.after(interval, tick)
    root.mainloop()
    console.shutdown()
    return 0
