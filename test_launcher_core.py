#!/usr/bin/env python3
"""Тесты ядра лаунчера (без GUI). Запуск: python3 -m unittest test_launcher_core -v"""
import os
import tempfile
import unittest

import launcher_core as core


class PrettyTitleTests(unittest.TestCase):
    def test_strips_extension_and_underscores(self):
        self.assertEqual(core.pretty_title("Halo_2.iso"), "Halo 2")

    def test_keeps_multi_dot_names_readable(self):
        self.assertEqual(core.pretty_title("GTA.San.Andreas.iso"), "GTA San Andreas")


class GuessEmuTests(unittest.TestCase):
    def test_xex_goes_to_xenia(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "game.xex")
            open(path, "wb").close()
            self.assertEqual(core.guess_emu(path), "xenia")

    def test_xbe_goes_to_xemu(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "game.xbe")
            open(path, "wb").close()
            self.assertEqual(core.guess_emu(path), "xemu")

    def test_og_xbox_iso_detected_by_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "og.iso")
            with open(path, "wb") as f:
                f.write(b"\x00" * 0x100)
                f.write(core.XBOX_MEDIA_MAGIC + b"\x00" * 16)
            self.assertEqual(core.guess_emu(path), "xemu")

    def test_iso_without_header_defaults_to_xenia(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "x360.iso")
            with open(path, "wb") as f:
                f.write(b"\x00" * 0x800)
            self.assertEqual(core.guess_emu(path), "xenia")

    def test_unreadable_file_defaults_to_xenia(self):
        self.assertEqual(core.guess_emu(os.path.join("Z:", "none.iso")), "xenia")


class ScanLibraryTests(unittest.TestCase):
    def test_scans_recursively_and_skips_other_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib = os.path.join(tmp, "Games")
            sub = os.path.join(lib, "sub")
            os.makedirs(sub)
            for name in ("b.iso", "a.xex", "readme.txt"):
                open(os.path.join(lib, name), "wb").close()
            open(os.path.join(sub, "deep.cci"), "wb").close()
            games = core.scan_library(lib)
            titles = [g["title"] for g in games]
            self.assertEqual(titles, sorted(titles, key=str.lower))
            self.assertEqual(len(games), 3)
            self.assertIn("deep", titles)

    def test_missing_dir_returns_empty(self):
        self.assertEqual(core.scan_library(os.path.join(tempfile.gettempdir(), "no_such")),
                         [])


class LaunchCommandTests(unittest.TestCase):
    def test_xemu_uses_dvd_path(self):
        cmd = core.build_launch_command("xemu", "xemu.exe", "game.iso")
        self.assertEqual(cmd, ["xemu.exe", "-dvd_path", "game.iso"])

    def test_xenia_passes_game_directly(self):
        cmd = core.build_launch_command("xenia", "xenia.exe", "game.xex")
        self.assertEqual(cmd, ["xenia.exe", "game.xex"])

    def test_unknown_emu_raises(self):
        with self.assertRaises(ValueError):
            core.build_launch_command("rpcs3", "rpcs3", "game.iso")


class ConfigTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cfg.json")
            cfg = {"games_dir": "X:/Games", "emu_paths": {"xenia": "x.exe"}}
            self.assertTrue(core.save_config(cfg, path))
            self.assertEqual(core.load_config(path), cfg)

    def test_load_missing_returns_empty_dict(self):
        self.assertEqual(core.load_config(os.path.join(tempfile.gettempdir(), "no.json")), {})

    def test_record_recent_dedupes_and_limits(self):
        cfg = {"recent_games": ["a.iso", "b.iso"]}
        core.record_recent(cfg, "a.iso", size=2)
        self.assertEqual(cfg["recent_games"], ["a.iso", "b.iso"])
        core.record_recent(cfg, "c.iso", size=2)
        self.assertEqual(cfg["recent_games"], ["c.iso", "a.iso"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
