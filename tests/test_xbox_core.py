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


class ScanLibraryTests(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp()

    def make(self, rel, content=b"X"):
        path = os.path.join(self.base, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)
        return path

    def test_finds_games_recursively(self):
        iso = self.make("racing/racing.iso")
        xex = self.make("shooters/x.xex")
        xbe = self.make("classic/default.xbe")
        self.make("docs/readme.txt")
        games = xbox_core.scan_library([self.base])
        names = [os.path.basename(p) for p in games]
        self.assertIn("racing.iso", names)
        self.assertIn("x.xex", names)
        self.assertIn("default.xbe", names)
        self.assertNotIn("readme.txt", names)
        self.assertIn(iso, games)
        self.assertEqual(len(games), 3)

    def test_accepts_single_file_root(self):
        path = self.make("one.cci")
        self.assertEqual(xbox_core.scan_library([path]), [path])

    def test_missing_root_ignored(self):
        result = xbox_core.scan_library([os.path.join(self.base, "nope")])
        self.assertEqual(result, [])

    def test_deduplicates(self):
        path = self.make("dup.iso")
        games = xbox_core.scan_library([self.base, self.base])
        self.assertEqual(games, [path])


class ResolveGameTests(unittest.TestCase):
    def test_direct_file_path(self):
        fd, path = tempfile.mkstemp(suffix=".iso")
        os.close(fd)
        self.addCleanup(os.unlink, path)
        matches, err = xbox_core.resolve_game(path, {})
        self.assertIsNone(err)
        self.assertEqual(matches, [os.path.abspath(path)])

    def test_library_name_match(self):
        cfg = {"library": ["/games/Halo/halo.iso", "/games/Forza/forza.iso"]}
        matches, err = xbox_core.resolve_game("halo", cfg)
        self.assertIsNone(err)
        self.assertEqual(matches, ["/games/Halo/halo.iso"])

    def test_library_multiple_matches(self):
        cfg = {"library": ["/a/halo1.iso", "/b/halo2.iso"]}
        matches, err = xbox_core.resolve_game("halo", cfg)
        self.assertIsNone(err)
        self.assertEqual(len(matches), 2)

    def test_not_found(self):
        matches, err = xbox_core.resolve_game("unknown-game", {"library": []})
        self.assertEqual(matches, [])
        self.assertIn("Не найдено", err)

    def test_empty_query(self):
        matches, err = xbox_core.resolve_game("", {})
        self.assertEqual(matches, [])
        self.assertTrue(err)


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
