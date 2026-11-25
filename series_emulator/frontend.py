"""series_emulator.frontend — оконный фронтенд каркаса на Tkinter.

Тёмное «Xbox»-окно: шапка с названием, игровое изображение с рамкой,
строка статуса со счётом/FPS. Клавиатура → геймпад (стрелки/WASD, Z=A, X=B).
"""
from __future__ import annotations

import base64
import time

from .console import SeriesConsole
from .rom_demo import DemoROM

FPS = 30
SCALE = 3

BG = "#0b0c0e"
PANEL = "#15171a"
HEADER_TEXT = "#e6e8eb"
MUTED = "#8a8f96"
EDGE = "#107c10"


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
    root.title("Xbox Series — Demo")
    root.configure(bg=BG)
    root.resizable(False, False)

    header = tk.Frame(root, bg=PANEL)
    header.pack(fill="x", padx=10, pady=(10, 0))
    import tkinter.font as tkfont
    head_font = tkfont.Font(family="Segoe UI", size=13, weight="bold")
    sub_font = tkfont.Font(family="Segoe UI", size=8)
    tk.Label(header, text="XBOX SERIES", bg=PANEL, fg=HEADER_TEXT,
             font=head_font).pack(side="left", padx=(12, 8), pady=8)
    tk.Label(header, text="DEMO CART", bg=PANEL, fg=MUTED,
             font=sub_font).pack(side="left")

    edge = tk.Frame(root, bg=EDGE)
    edge.pack(fill="x", padx=10, pady=(8, 0))
    screen_w, screen_h = width * scale, height * scale
    canvas = tk.Canvas(edge, width=screen_w, height=screen_h,
                       bg="#000000", highlightthickness=0)
    canvas.pack(padx=1, pady=1)

    status_bar = tk.Frame(root, bg=PANEL)
    status_bar.pack(fill="x", padx=10, pady=(2, 10))
    status_var = tk.StringVar(value="")
    tk.Label(status_bar, textvariable=status_var, bg=PANEL, fg=MUTED,
             font=sub_font, anchor="w").pack(fill="x", padx=10, pady=6)
    help_font = tkfont.Font(family="Segoe UI", size=8)
    tk.Label(root, text="стрелки/WASD — стик  •  Z — A  •  X — B  •  Esc — выход",
             bg=BG, fg=MUTED, font=help_font).pack(pady=(0, 8))

    key_axis = {"Left": None, "Right": None, "Up": None, "Down": None,
                "a": None, "d": None, "w": None, "s": None}
    pressed = set()
    buttons = {"z": "A", "x": "B"}

    def _on_press(e):
        pressed.add(e.keysym)

    def _on_release(e):
        pressed.discard(e.keysym)

    for k in list(key_axis) + list(buttons):
        root.bind("<KeyPress-%s>" % k, _on_press)
        root.bind("<KeyRelease-%s>" % k, _on_release)
    root.bind("<Escape>", lambda e: root.destroy())

    pad = console.input.controller(0)

    def apply_input():
        right = ("Right" in pressed) or ("d" in pressed)
        left = ("Left" in pressed) or ("a" in pressed)
        down = ("Down" in pressed) or ("s" in pressed)
        up = ("Up" in pressed) or ("w" in pressed)
        pad.set_axis("ls_x", (1 if right else 0) - (1 if left else 0))
        pad.set_axis("ls_y", (1 if down else 0) - (1 if up else 0))
        for k, btn in buttons.items():
            (pad.press(btn) if k in pressed else pad.release(btn))

    img_holder = {"img": None}

    def _photo_rowput():
        img = tk.PhotoImage(width=width, height=height)
        stride = console.gpu.stride
        for y in range(height):
            row = console.gpu.mem.read_bytes(
                console.gpu.framebuffer + y * stride, stride)
            cells = " ".join(
                "#%02x%02x%02x" % (row[x * 4], row[x * 4 + 1], row[x * 4 + 2])
                for x in range(width))
            img.put("{%s}" % cells, to=(0, y))
        return img

    def _make_photo():
        ppm = _rgb_bytes(console.gpu)
        for data in (ppm,
                     base64.b64encode(ppm).decode("ascii"),
                     None):
            try:
                if data is None:
                    return _photo_rowput()
                img = tk.PhotoImage(data=data, format="ppm",
                                    width=width, height=height)
                if img.width() != width or img.height() != height:
                    raise tk.TclError("PPM не декодировался")
                return img
            except tk.TclError:
                continue
        raise tk.TclError("Ни один способ blit не сработал")

    def blit():
        img = _make_photo()
        if scale > 1:
            try:
                img = img.zoom(scale)
            except tk.TclError:
                img_holder["img"] = img
                canvas.delete("all")
                canvas.create_image(0, 0, image=img, anchor="nw")
                return
        img_holder["img"] = img
        canvas.delete("all")
        canvas.create_image(0, 0, image=img, anchor="nw")

    interval = int(1000 / fps)
    last = time.time()
    fps_smooth = float(fps)

    def tick():
        nonlocal last, fps_smooth
        now = time.time()
        dt = min(0.1, now - last)
        if dt > 0:
            fps_smooth += ((1.0 / dt) - fps_smooth) * 0.1
        last = now
        apply_input()
        rom.update(dt, console.input)
        console.frames += 1
        rom.draw(console.gpu)
        blit()
        cpu = console.cpu.regs["rax"] if hasattr(console.cpu, "regs") else console.cpu.rax
        status_var.set("score: %d    кадр: %d    FPS: %.0f    CPU rax: %d    "
                       "фаза: 1 (MiniX64) — см. ROADMAP.md"
                       % (rom.score, console.frames, fps_smooth, cpu))
        root.after(interval, tick)

    root.after(interval, tick)
    root.mainloop()
    console.shutdown()
    return 0
