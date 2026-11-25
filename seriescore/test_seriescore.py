import importlib.util
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SERIESCORE_PATH = os.path.join(HERE, "seriescore.py")

spec = importlib.util.spec_from_file_location("seriescore", SERIESCORE_PATH)
seriescore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seriescore)


class XvdInfoTests(unittest.TestCase):
    def write_tmp(self, data):
        fd, path = tempfile.mkstemp(suffix=".tmp")
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        self.addCleanup(os.unlink, path)
        return path

    def test_xvd_magic_detected(self):
        path = self.write_tmp(b"XVD" + b"\x00" * 509)
        report, err = seriescore.xvd_info(path)
        self.assertIsNone(err)
        self.assertTrue(report["has_xvd_magic"])
        self.assertEqual(report["size_bytes"], 512)
        self.assertTrue(report["head_hex"].startswith("58 56 44"))

    def test_non_xvd_file(self):
        path = self.write_tmp(b"MZ\x00\x00" + b"\x00" * 20)
        report, err = seriescore.xvd_info(path)
        self.assertIsNone(err)
        self.assertFalse(report["has_xvd_magic"])

    def test_empty_file(self):
        path = self.write_tmp(b"")
        report, err = seriescore.xvd_info(path)
        self.assertIsNone(err)
        self.assertEqual(report["size_bytes"], 0)
        self.assertFalse(report["has_xvd_magic"])
        self.assertNotIn("head_hex", report)

    def test_missing_file(self):
        report, err = seriescore.xvd_info(os.path.join(HERE, "no_such_image.xvd"))
        self.assertIsNone(report)
        self.assertIn("No such file", err)

    def test_sha256_head_is_stable(self):
        path = self.write_tmp(b"XVD-fixture" + b"\x00" * 100)
        report, _ = seriescore.xvd_info(path)
        self.assertEqual(len(report["sha256_head"]), 64)


class ModuleTableTests(unittest.TestCase):
    def test_all_modules_listed(self):
        names = [name for name, _, _ in seriescore.MODULES]
        for expected in ("containers", "kernel", "video", "audio", "input", "net", "ui"):
            self.assertIn(expected, names)

    def test_constants(self):
        self.assertEqual(seriescore.XVD_MAGIC, b"XVD")
        self.assertTrue(seriescore.VERSION)


if __name__ == "__main__":
    unittest.main()
