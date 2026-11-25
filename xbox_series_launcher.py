#!/usr/bin/env python3
"""Xbox Series Launcher — дашборд-лаунчер в стиле Xbox Series X/S.

Тёмный экран-плитки, запуск игр через Xenia (Xbox 360) и xemu (оригинальный Xbox).
Вся логика вынесена в launcher_core.py.
   python3 xbox_series_launcher.py            # GUI
   python3 xbox_series_launcher.py --selftest # проверка ядра без GUI
   python3 xbox_series_launcher.py --gamesdir "D:/Games/Xbox"
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time

import launcher_core as core

try:
    from launcher_core import DEFAULT_CONFIG_PATH
except ImportError:  # pragma: no cover
    DEFAULT_CONFIG_PATH = "~/.xbox_series_launcher.json"

BG_COLOR = "#0e0e0e"
PANEL_COLOR = "#1a1a1a"
TILE_COLOR = "#11897a"
TILE_HOVER = "#16b3a0"
ACCENT_COLOR = "#107c10"
TEXT_COLOR = "#f2f2f2"
MUTED_COLOR = "#9a9a9a"

TILE_W = 240
TILE_H = 130
LIBRARY_REFRESH_MS = 100


def _try_import_tk():
    try:
        import tkinter as tk
        from tkinter import filedialog, font, messagebox, ttk
        return tk, filedialog, font, messagebox, ttk
    except ImportError:
        return None


def create_app(config_path: str = DEFAULT_CONFIG_PATH):
    """Создаёт окно приложения. Отдельная функция — удобно для тестов."""
    tk_modules = _try_import_tk()
    if tk_modules is None:
        raise RuntimeError(
            "Tkinter недоступен (модуль tkinter не установлен вместе с Python)")
    tk, filedialog, font, messagebox, ttk = tk_modules

    cfg = core.load_config(config_path)

    class SeriesLauncher(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("Xbox Series Launcher")
            self.geometry("1280x740")
            self.minsize(900, 560)
            self.configure(bg=BG_COLOR)
            self.config_path = config_path
            self.cfg = cfg
            self.process = None
            self.games = []
            self.selected_index = 0
            self.tile_buttons = []
            self.status_var = tk.StringVar(value="Библиотека: не просканирована")
            self._build_header()
            self._build_toolbar()
            self._build_library()
            self._build_statusbar()
            self.bind("<Configure>", lambda e: self._regrid())
            self.protocol("WM_DELETE_WINDOW", self._on_close)
            self.after(LIBRARY_REFRESH_MS, self.refresh_library)

        def _build_header(self):
            header = tk.Frame(self, bg=PANEL_COLOR, height=90)
            header.pack(fill="x")
            title_font = font.Font(family="Segoe UI", size=26, weight="bold")
            tk.Label(header, text="XBOX SERIES", font=title_font,
                     bg=PANEL_COLOR, fg=TEXT_COLOR).pack(side="left", padx=24, pady=14)
            tk.Label(header, text="Библиотека игр  •  Xenia + xemu",
                     bg=PANEL_COLOR, fg=MUTED_COLOR).pack(side="left", padx=(0, 12))
            self.clock = tk.Label(header, text="", bg=PANEL_COLOR, fg=MUTED_COLOR,
                                  font=("Segoe UI", 11))
            self.clock.pack(side="right", padx=24)
            self._tick_clock()

        def _tick_clock(self):
            self.clock.configure(text=time.strftime("%H:%M:%S"))
            self.after(1000, self._tick_clock)

        def _build_toolbar(self):
            bar = tk.Frame(self, bg=BG_COLOR)
            bar.pack(fill="x", padx=20, pady=(12, 4))
            tk.Button(bar, text="⟳ Обновить", command=self.refresh_library,
                      bg=PANEL_COLOR, fg=TEXT_COLOR, bd=0, padx=14, pady=8,
                      activebackground=TILE_HOVER, activeforeground=TEXT_COLOR,
                      cursor="hand2").pack(side="left", padx=(0, 8))
            tk.Button(bar, text="Настройки", command=self._open_settings,
                      bg=PANEL_COLOR, fg=TEXT_COLOR, bd=0, padx=14, pady=8,
                      activebackground=TILE_HOVER, activeforeground=TEXT_COLOR,
                      cursor="hand2").pack(side="left", padx=(0, 8))
            tk.Button(bar, text="Открыть папку игр", command=self._open_games_dir,
                      bg=PANEL_COLOR, fg=TEXT_COLOR, bd=0, padx=14, pady=8,
                      activebackground=TILE_HOVER, activeforeground=TEXT_COLOR,
                      cursor="hand2").pack(side="left")
            self.stop_btn = tk.Button(bar, text="■ Стоп", command=self._stop,
                                      bg="#5a1a1a", fg=TEXT_COLOR, bd=0, padx=14,
                                      pady=8, state="disabled",
                                      activebackground="#7a2323",
                                      activeforeground=TEXT_COLOR)
            self.stop_btn.pack(side="right")
            self.launch_btn = tk.Button(bar, text="▶ Запустить", command=self._launch_selected,
                                        bg=ACCENT_COLOR, fg=TEXT_COLOR, bd=0, padx=18,
                                        pady=8, activebackground="#1aa51a",
                                        activeforeground=TEXT_COLOR, cursor="hand2")
            self.launch_btn.pack(side="right", padx=(0, 8))

        def _build_library(self):
            wrapper = tk.Frame(self, bg=BG_COLOR)
            wrapper.pack(fill="both", expand=True, padx=20, pady=10)
            self.canvas = tk.Canvas(wrapper, bg=BG_COLOR, bd=0, highlightthickness=0)
            scroll = ttk.Scrollbar(wrapper, orient="vertical", command=self.canvas.yview)
            self.canvas.configure(yscrollcommand=scroll.set)
            scroll.pack(side="right", fill="y")
            self.canvas.pack(side="left", fill="both", expand=True)
            self.tiles_frame = tk.Frame(self.canvas, bg=BG_COLOR)
            self.canvas.create_window((0, 0), window=self.tiles_frame, anchor="nw",
                                      tags="tiles_win")
            self.tiles_frame.bind(
                "<Configure>",
                lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
            self.canvas.bind_all("<MouseWheel>", self._on_wheel)
            self.bind("<Up>", lambda e: self._move_selection(-1, 0))
            self.bind("<Down>", lambda e: self._move_selection(1, 0))
            self.bind("<Left>", lambda e: self._move_selection(-1, 0))
            self.bind("<Right>", lambda e: self._move_selection(1, 0))
            self.bind("<Return>", lambda e: self._launch_selected())

        def _build_statusbar(self):
            bar = tk.Frame(self, bg=PANEL_COLOR, height=30)
            bar.pack(fill="x", side="bottom")
            tk.Label(bar, textvariable=self.status_var, bg=PANEL_COLOR,
                     fg=MUTED_COLOR, anchor="w", font=("Segoe UI", 10)
                     ).pack(fill="x", padx=16, pady=5)

        def _on_wheel(self, event):
            if self.canvas.winfo_exists():
                self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

        def games_dir(self):
            return self.cfg.get("games_dir", "")

        def refresh_library(self):
            gdir = self.games_dir()
            if not gdir:
                self.status_var.set(
                    "Укажите папку с играми: Настройки → Папка с играми (поддержка .iso .cci .xex .xbe .gdi .chd)")
                self.games = []
                self._render_tiles()
                return
            if not os.path.isdir(gdir):
                self.status_var.set("Папка не найдена: %s" % gdir)
                self.games = []
                self._render_tiles()
                return
            self.status_var.set("Сканирую библиотеку…")
            threading.Thread(target=self._scan_worker,
                             args=(gdir,), daemon=True).start()

        def _scan_worker(self, gdir):
            found = core.scan_library(gdir)
            self.after(0, lambda: self._apply_scan(gdir, found))

        def _apply_scan(self, gdir, found):
            self.games = found
            self.selected_index = 0
            recents = self.cfg.get("recent_games", [])
            found.sort(key=lambda g: (
                recents.index(g["path"]) if g["path"] in recents else len(recents),
                g["title"].lower()))
            self._render_tiles()
            self.status_var.set(
                "Библиотека: %d игр из %s" % (len(found), gdir))
            missing = []
            for emu in ("xenia", "xemu"):
                if not core.resolve_emu_path(self.cfg, emu):
                    missing.append(core.EMU_LABELS[emu])
            if missing:
                self.status_var.set(
                    "Библиотека: %d игр. Не найден эмулятор: %s — укажите путь в Настройках"
                    % (len(found), ", ".join(missing)))

        def _render_tiles(self):
            for w in self.tiles_frame.winfo_children():
                w.destroy()
            self.tile_buttons = []
            if not self.games:
                tk.Label(self.tiles_frame,
                         text="Игры не найдены.\nНажмите «Настройки» и укажите папку с .iso/.xex/.xbe файлами.",
                         bg=BG_COLOR, fg=MUTED_COLOR, font=("Segoe UI", 12),
                         justify="left").grid(row=0, column=0, padx=8, pady=24,
                                              sticky="nw")
                return
            for i, game in enumerate(self.games):
                tile = tk.Button(
                    self.tiles_frame,
                    text="%s\n%s" % (game["title"],
                                     game["emu"].upper()),
                    width=TILE_W // 8, height=TILE_H // 18,
                    bg=TILE_COLOR, fg=TEXT_COLOR, bd=0,
                    activebackground=TILE_HOVER, activeforeground=TEXT_COLOR,
                    font=("Segoe UI", 10, "bold"),
                    justify="left", anchor="w", cursor="hand2",
                    command=lambda idx=i: self._select(idx) or self._launch_selected())
                tile.grid(row=0, column=i, padx=6, pady=6)
                tile.bind("<Enter>", lambda e, idx=i: self._hover(idx))
                tile.bind("<Leave>", lambda e, idx=i: self._unhover(idx))
                self.tile_buttons.append(tile)
            self._highlight_selection()
            self.after(10, self._regrid)

        def _regrid(self):
            if not hasattr(self, "tiles_frame"):
                return
            width = max(self.winfo_width(), 400) - 60
            per_row = max(1, width // (TILE_W + 12))
            for tile in self.tile_buttons:
                tile.grid_forget()
            for i, tile in enumerate(self.tile_buttons):
                tile.grid(row=i // per_row, column=i % per_row, padx=6, pady=6)

        def _hover(self, idx):
            self.tile_buttons[idx].configure(bg=TILE_HOVER)

        def _unhover(self, idx):
            if idx != self.selected_index:
                self.tile_buttons[idx].configure(bg=TILE_COLOR)

        def _move_selection(self, delta, _unused):
            if not self.games:
                return
            self.selected_index = (self.selected_index + delta) % len(self.games)
            self._highlight_selection()

        def _select(self, idx):
            self.selected_index = idx
            self._highlight_selection()
            return None

        def _highlight_selection(self):
            for i, tile in enumerate(self.tile_buttons):
                tile.configure(bg=TILE_HOVER if i == self.selected_index else TILE_COLOR)

        def _launch_selected(self):
            if self.process is not None and self.process.poll() is None:
                self.status_var.set("Эмулятор уже запущен")
                return
            if not self.games:
                self.status_var.set("Нет игр для запуска")
                return
            idx = self.selected_index
            game = self.games[idx]

            emu = game["emu"]
            emu_path = core.resolve_emu_path(self.cfg, emu)
            if not emu_path or not os.path.isfile(emu_path):
                self.status_var.set(
                    "%s не найден. Скачайте: %s и укажите путь в Настройках"
                    % (core.EMU_LABELS[emu], core.EMU_HINTS[emu]))
                messagebox.showerror(
                    "Эмулятор не найден",
                    "Не найден %s.\n\nСкачайте здесь: %s\nи укажите путь в Настройках."
                    % (core.EMU_LABELS[emu], core.EMU_HINTS[emu]))
                return

            cmd = core.build_launch_command(emu, emu_path, game["path"])
            self.cfg["emu"] = emu
            self.cfg.setdefault("emu_paths", {})[emu] = emu_path
            core.record_recent(self.cfg, game["path"])
            core.save_config(self.cfg, self.config_path)

            self.status_var.set("Запуск: %s (%s)" % (game["title"], core.EMU_LABELS[emu]))
            try:
                self.process = subprocess.Popen(
                    cmd,
                    cwd=os.path.dirname(emu_path) or None,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except OSError as e:
                self.status_var.set("Не удалось запустить эмулятор: %s" % e)
                messagebox.showerror("Ошибка запуска", str(e))
                return
            self.launch_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.after(500, self._poll)

        def _poll(self):
            if self.process is None:
                return
            code = self.process.poll()
            if code is None:
                self.after(500, self._poll)
                return
            self.process = None
            self.launch_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            if code == 0:
                self.status_var.set("Готово")
            else:
                self.status_var.set("Эмулятор завершился с кодом %s" % code)

        def _stop(self):
            if self.process and self.process.poll() is None:
                self.process.terminate()
                self.status_var.set("Останавливаю эмулятор…")

        def _open_games_dir(self):
            gdir = self.games_dir()
            if gdir and os.path.isdir(gdir):
                try:
                    if sys.platform.startswith("win"):
                        os.startfile(gdir)  # noqa
                    elif sys.platform == "darwin":
                        subprocess.Popen(["open", gdir])
                    else:
                        subprocess.Popen(["xdg-open", gdir])
                    return
                except OSError:
                    pass
            self._open_settings()

        def _open_settings(self):
            win = tk.Toplevel(self)
            win.title("Настройки Xbox Series Launcher")
            win.configure(bg=BG_COLOR, padx=16, pady=16)
            win.transient(self)
            win.grab_set()

            rows = []
            gdir_var = tk.StringVar(value=self.cfg.get("games_dir", ""))
            xenia_var = tk.StringVar(
                value=(self.cfg.get("emu_paths") or {}).get("xenia", ""))
            xemu_var = tk.StringVar(
                value=(self.cfg.get("emu_paths") or {}).get("xemu", ""))

            def add_row(label, var, pick_mode, picker_args=None):
                tk.Label(win, text=label, bg=BG_COLOR, fg=TEXT_COLOR).grid(
                    row=len(rows), column=0, sticky="w", pady=3)
                tk.Entry(win, textvariable=var, width=48, bg=PANEL_COLOR,
                         fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=0).grid(
                    row=len(rows), column=1, pady=3)

                def browse():
                    if pick_mode == "dir":
                        p = filedialog.askdirectory(title=label)
                    else:
                        p = filedialog.askopenfilename(title=label,
                                                       filetypes=picker_args or ())
                    if p:
                        var.set(p)

                tk.Button(win, text="Обзор…", command=browse, bg=PANEL_COLOR,
                          fg=TEXT_COLOR, bd=0, padx=10, cursor="hand2").grid(
                    row=len(rows), column=2, padx=(8, 0))
                rows.append(var)

            add_row("Папка с играми:", gdir_var, "dir")
            add_row("Xenia (Xbox 360):", xenia_var, "file",
                    [("", "*.exe"), ("", "*")])
            add_row("xemu (оригинальный Xbox):", xemu_var, "file",
                    [("", "*.exe"), ("", "*")])

            hint = tk.Label(
                win,
                text="Если путь оставить пустым, лаунчер будет искать эмулятор в PATH.\n"
                     "Xenia: %s\nxemu: %s" % (
                         core.EMU_HINTS["xenia"], core.EMU_HINTS["xemu"]),
                bg=BG_COLOR, fg=MUTED_COLOR, justify="left")
            hint.grid(row=len(rows), column=0, columnspan=3, sticky="w", pady=(10, 4))

            def on_save():
                self.cfg["games_dir"] = gdir_var.get().strip()
                paths = self.cfg.setdefault("emu_paths", {})
                if xenia_var.get().strip():
                    paths["xenia"] = xenia_var.get().strip()
                else:
                    paths.pop("xenia", None)
                if xemu_var.get().strip():
                    paths["xemu"] = xemu_var.get().strip()
                else:
                    paths.pop("xemu", None)
                core.save_config(self.cfg, self.config_path)
                win.destroy()
                self.refresh_library()

            tk.Button(win, text="Сохранить и просканировать", command=on_save,
                      bg=ACCENT_COLOR, fg=TEXT_COLOR, bd=0, padx=16, pady=6,
                      cursor="hand2").grid(row=len(rows) + 1, column=0,
                                           columnspan=3, sticky="w", pady=(10, 0))

        def _on_close(self):
            self._stop()
            self.destroy()

    return SeriesLauncher()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="xbox-series-launcher")
    parser.add_argument("--gamesdir", help="Папка с играми (.iso/.xex/.xbe)")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH,
                        help="Путь к конфиг-файлу")
    parser.add_argument("--selftest", action="store_true",
                        help="Проверить ядро без запуска GUI")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args(argv)

    if args.version:
        print("xbox-series-launcher 1.0.0")
        return 0
    if args.selftest:
        return core.selftest()

    cfg = core.load_config(args.config)
    if args.gamesdir:
        cfg["games_dir"] = os.path.abspath(args.gamesdir)
        save_ok = core.save_config(cfg, args.config)
        if not save_ok:
            print("Не удалось сохранить конфиг", file=sys.stderr)

    try:
        app = create_app(args.config)
    except RuntimeError as e:
        print("Не удалось открыть окно: %s" % e, file=sys.stderr)
        print("На Windows/Linux установите Tkinter: python -m tkinter "
              "(в Debian/Ubuntu: apt install python3-tk).", file=sys.stderr)
        return 1

    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
