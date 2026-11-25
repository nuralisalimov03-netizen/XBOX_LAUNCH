import importlib.util
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(ROOT, name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


xbox_core = _load("xbox_core")


class GuessEmuTests(unittest.TestCase):
    def write_tmp(self, data, suffix):
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        self.addCleanup(os.unlink, path)
        return path

    def test_xex_is_xenia(self):
        self.assertEqual(xbox_core.guess_emu("game.xex"), "xenia")

    def test_xbe_is_xemu(self):
        self.assertEqual(xbox_core.guess_emu("game.xbe"), "xemu")

    def test_og_iso_is_xemu(self):
        path = self.write_tmp(b"\x00" * 4096 + b"MICROSOFT*XBOX*MEDIA", ".iso")
        self.assertEqual(xbox_core.guess_emu(path), "xemu")

    def test_plain_iso_is_xenia(self):
        path = self.write_tmp(b"\x00" * 65536 + b"XBOX_DVD_0", ".iso")
        self.assertEqual(xbox_core.guess_emu(path), "xenia")

    def test_unknown_ext_defaults_to_xenia(self):
        self.assertEqual(xbox_core.guess_emu("game.rar"), "xenia")


class ResolveEmuTests(unittest.TestCase):
    def test_override_wins(self):
        self.assertEqual(
            xbox_core.resolve_emu_path("xenia", {}, override="/opt/xenia"),
            "/opt/xenia",
        )

    def test_empty_when_nothing_found(self):
        self.assertEqual(xbox_core.resolve_emu_path("definitely-not-an-emu", {}), "")


class ParseStartAppsTests(unittest.TestCase):
    def test_filters_uwp_only(self):
        raw = "\n".join(
            [
                "Microsoft.MinecraftUWP_8wekyb3d8bbwe!App|Minecraft for Windows",
                '"Microsoft.SeaofThieves_8wekyb3d8bbwe!Game"|Sea of Thieves',
                "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\notepad.exe|Notepad",
                "Microsoft.Windows.ShellExperienceHost|Windows",
            ]
        )
        apps = xbox_core.parse_start_apps(raw)
        self.assertEqual(
            apps,
            [
                ("Minecraft for Windows", "Microsoft.MinecraftUWP_8wekyb3d8bbwe!App"),
                ("Sea of Thieves", "Microsoft.SeaofThieves_8wekyb3d8bbwe!Game"),
            ],
        )

    def test_empty_input(self):
        self.assertEqual(xbox_core.parse_start_apps(""), [])


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self._orig = xbox_core.CONFIG_PATH
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        xbox_core.CONFIG_PATH = path
        self.addCleanup(os.unlink, path)
        self.addCleanup(setattr, xbox_core, "CONFIG_PATH", self._orig)

    def test_save_and_load_roundtrip(self):
        err = xbox_core.save_config({"emu": "xenia", "last_game": "x.iso"})
        self.assertIsNone(err)
        cfg = xbox_core.load_config()
        self.assertEqual(cfg["emu"], "xenia")
        self.assertEqual(cfg["last_game"], "x.iso")

    def test_load_missing_is_empty(self):
        cfg = xbox_core.load_config()
        self.assertEqual(cfg, {})


if __name__ == "__main__":
    unittest.main()
