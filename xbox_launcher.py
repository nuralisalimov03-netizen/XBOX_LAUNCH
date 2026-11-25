#!/usr/bin/env python3
import os
import subprocess
import sys
import threading

from xbox_core import (
    EMU_ARGS,
    EMU_HINTS,
    EMU_LABELS,
    find_emu_in_path,
    guess_emu,
    list_store_apps,
    load_config,
    parse_start_apps,
    save_config as _save_config,
)

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError as e:
    print("GUI-режим недоступен: не найден Tkinter. Установите python3-tk.")
    print("Работает консольный режим: python xbox_launch.py --launch game.iso")
    print("Подробности: %s" % e)
    sys.exit(1)

FILE_TYPES = [
    ("Образы и исполняемые файлы Xbox", "*.iso *.cci *.xex *.xbe"),
    ("Все файлы", "*.*"),
]


def save_config(cfg):
    err = _save_config(cfg)
    if err:
        messagebox.showwarning("Настройки", "Не удалось сохранить настройки:\n%s" % err)


class StoreAppDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Игры Microsoft Store / Xbox app (Series X|S on PC)")
        self.geometry("560x440")
        self.apps_list = []
        self.visible = []
        ttk.Label(self, text="Поиск:").pack(anchor="w", padx=8, pady=(8, 0))
        self.search_var = tk.StringVar()
        search = ttk.Entry(self, textvariable=self.search_var)
        search.pack(fill="x", padx=8, pady=(0, 6))
        search.bind("<KeyRelease>", lambda e: self._refresh())
        self.listbox = tk.Listbox(self, font=("Consolas", 9))
        self.listbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.listbox.bind("<Double-Button-1>", lambda e: self._launch_selected())
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="Запустить выбранную", command=self._launch_selected).pack(
            side="left"
        )
        ttk.Button(bar, text="Обновить список", command=self._load).pack(
            side="left", padx=6
        )
        self.status_var = tk.StringVar(value="Загрузка списка установленных игр…")
        ttk.Label(self, textvariable=self.status_var, foreground="gray").pack(
            anchor="w", padx=8, pady=(0, 8)
        )
        self._load()

    def _load(self):
        self.status_var.set("Загрузка списка установленных игр…")
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        apps = list_store_apps()
        self.after(0, lambda: self._apply(apps))

    def _apply(self, apps):
        if apps is None:
            self.status_var.set(
                "Недоступно: нужен Windows с PowerShell. "
                "Series X|S-игры устанавливаются через приложение Xbox / Store"
            )
            self.apps_list = []
        elif not apps:
            self.status_var.set("Store-игры не найдены — установите их через приложение Xbox")
            self.apps_list = []
        else:
            self.status_var.set("Найдено приложений: %d. Двойной клик — запуск" % len(apps))
            self.apps_list = apps
        self._refresh()

    def _refresh(self):
        query = self.search_var.get().lower()
        self.listbox.delete(0, "end")
        self.visible = [(name, aid) for name, aid in self.apps_list if query in name.lower()]
        for name, _ in self.visible:
            self.listbox.insert("end", name)

    def _launch_selected(self):
        selection = self.listbox.curselection()
        if not selection:
            return
        name, app_id = self.visible[selection[0]]
        try:
            subprocess.Popen(["explorer.exe", "shell:appsFolder\\" + app_id])
            self.status_var.set("Запуск: %s" % name)
        except OSError as e:
            messagebox.showerror("Ошибка", "Не удалось запустить:\n%s" % e, parent=self)


class XboxLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Xbox Launch — запуск игр Xbox на ПК")
        self.geometry("720x420")
        self.minsize(640, 380)
        self.config_data = load_config()
        self.process = None
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 8, "pady": 6}
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, **pad)

        ttk.Label(frame, text="Эмулятор:").grid(row=0, column=0, sticky="w")
        self.emu_var = tk.StringVar(value=self.config_data.get("emu", "xenia"))
        emu_box = ttk.Combobox(
            frame,
            textvariable=self.emu_var,
            values=list(EMU_LABELS.keys()),
            state="readonly",
            width=12,
        )
        emu_box.grid(row=0, column=1, sticky="w")
        emu_box.bind("<<ComboboxSelected>>", lambda e: self._refresh_emu_path())
        ttk.Label(frame, textvariable=self._emu_label_var(), foreground="gray").grid(
            row=0, column=2, sticky="w"
        )

        ttk.Label(frame, text="Путь к эмулятору:").grid(row=1, column=0, sticky="w")
        self.emu_path_var = tk.StringVar(
            value=self.config_data.get("emu_paths", {}).get(self.emu_var.get(), "")
        )
        ttk.Entry(frame, textvariable=self.emu_path_var).grid(
            row=1, column=1, columnspan=2, sticky="we"
        )
        ttk.Button(frame, text="Обзор…", command=self._pick_emu).grid(
            row=1, column=3, padx=(4, 0)
        )

        ttk.Label(frame, text="Файл игры:").grid(row=2, column=0, sticky="w")
        self.game_var = tk.StringVar(value=self.config_data.get("last_game", ""))
        ttk.Entry(frame, textvariable=self.game_var).grid(
            row=2, column=1, columnspan=2, sticky="we"
        )
        ttk.Button(frame, text="Обзор…", command=self._pick_game).grid(
            row=2, column=3, padx=(4, 0)
        )

        self.recent = self.config_data.get("recent_games", [])
        ttk.Label(frame, text="Недавние:").grid(row=3, column=0, sticky="w")
        self.recent_box = ttk.Combobox(
            frame, values=self.recent, state="readonly", width=40
        )
        self.recent_box.grid(row=3, column=1, columnspan=2, sticky="we")
        self.recent_box.bind(
            "<<ComboboxSelected>>",
            lambda e: self.game_var.set(self.recent_box.get()),
        )

        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)

        self.launch_btn = ttk.Button(
            frame, text="Запустить игру", command=self.launch
        )
        self.launch_btn.grid(row=4, column=1, sticky="we", pady=(10, 4))
        self.stop_btn = ttk.Button(
            frame, text="Остановить", command=self.stop, state="disabled"
        )
        self.stop_btn.grid(row=4, column=2, sticky="we", pady=(10, 4))
        ttk.Button(frame, text="Store / Xbox app…", command=self._open_store).grid(
            row=4, column=3, sticky="we", pady=(10, 4)
        )

        self.status_var = tk.StringVar(value="Готов к запуску")
        ttk.Label(frame, textvariable=self.status_var, foreground="gray").grid(
            row=5, column=0, columnspan=4, sticky="w"
        )

        self.log = tk.Text(self, height=10, state="disabled", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        menubar = tk.Menu(self)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(
            label="Поддержка Xbox Series X|S", command=self._show_series_help
        )
        menubar.add_cascade(label="Справка", menu=help_menu)
        self.configure(menu=menubar)
        self._refresh_emu_path()
        self._auto_detect_emu_path()

    def _show_series_help(self):
        messagebox.showinfo(
            "Xbox Series X|S",
            "Полного эмулятора Xbox Series X|S не существует — ни в этом проекте, "
            "ни в мире (архитектура закрыта, образы шифруются).\n\n"
            "Игры этого поколения на ПК работают официально:\n"
            "Microsoft Store или приложение Xbox (Xbox Play Anywhere, Game Pass).\n\n"
            "Нажмите «Store / Xbox app…», чтобы увидеть установленные игры "
            "Series X|S и запустить их в один клик.",
            parent=self,
        )

    def _emu_label_var(self):
        if not hasattr(self, "_emu_text"):
            self._emu_text = tk.StringVar()
        emu = self.emu_var.get()
        self._emu_text.set(EMU_LABELS.get(emu, emu))
        return self._emu_text

    def _refresh_emu_path(self):
        paths = self.config_data.setdefault("emu_paths", {})
        self.emu_path_var.set(paths.get(self.emu_var.get(), ""))
        self._emu_label_var()
        self._auto_detect_emu_path()

    def _auto_detect_emu_path(self):
        if not self.emu_path_var.get():
            found = find_emu_in_path(self.emu_var.get())
            if found:
                self.emu_path_var.set(found)

    def _pick_emu(self):
        path = filedialog.askopenfilename(
            title="Выберите исполняемый файл эмулятора",
            filetypes=[("Исполняемые файлы", "*.exe"), ("Все файлы", "*.*")],
        )
        if path:
            self.emu_path_var.set(path)
            self.config_data.setdefault("emu_paths", {})[self.emu_var.get()] = path
            save_config(self.config_data)

    def _pick_game(self):
        path = filedialog.askopenfilename(
            title="Выберите файл игры (ISO, XEX, XBE)",
            filetypes=FILE_TYPES,
        )
        if path:
            self.game_var.set(path)
            self.config_data["last_game"] = path
            detected = guess_emu(path)
            if detected != self.emu_var.get():
                self.emu_var.set(detected)
                self._refresh_emu_path()
                self.status_var.set(
                    "Определён тип файла — выбран эмулятор: %s" % EMU_LABELS[detected]
                )

    def _open_store(self):
        StoreAppDialog(self)

    def log_write(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _remember_recent(self, game_path):
        if game_path in self.recent:
            self.recent.remove(game_path)
        self.recent.insert(0, game_path)
        self.recent = self.recent[:8]
        self.config_data["recent_games"] = list(self.recent)
        self.recent_box.configure(values=self.recent)

    def launch(self):
        emu_path = self.emu_path_var.get().strip()
        game_path = self.game_var.get().strip()
        if not emu_path or not os.path.isfile(emu_path):
            messagebox.showerror(
                "Ошибка",
                "Эмулятор не найден: %s\nСкачайте его здесь: %s"
                % (emu_path or "(не указан)", EMU_HINTS[self.emu_var.get()]),
            )
            return
        if not game_path or not os.path.exists(game_path):
            messagebox.showerror("Ошибка", "Файл игры не найден: %s" % (game_path or "(не указан)"))
            return

        emu = self.emu_var.get()
        args = [emu_path] + EMU_ARGS[emu]
        if emu == "xemu":
            args.append(game_path)
        else:
            args.append(game_path)

        self.config_data["last_game"] = game_path
        self._remember_recent(game_path)
        self.config_data["emu"] = emu
        self.config_data.setdefault("emu_paths", {})[emu] = emu_path
        save_config(self.config_data)

        self.status_var.set("Запуск: %s" % os.path.basename(game_path))
        self.log_write("> %s\n" % " ".join(args))
        try:
            self.process = subprocess.Popen(
                args, cwd=os.path.dirname(emu_path) or None,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except OSError as e:
            messagebox.showerror("Ошибка", "Не удалось запустить эмулятор:\n%s" % e)
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
            self.status_var.set("Эмулятор завершил работу")
        else:
            self.status_var.set("Эмулятор завершился с кодом %s" % code)

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()

    def _on_close(self):
        self.stop()
        self.destroy()


def main():
    app = XboxLauncher()
    app.mainloop()


if __name__ == "__main__":
    sys.exit(main())
