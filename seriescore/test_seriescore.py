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


class HumanSizeTests(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(seriescore.human_size(0), "0 Б")
        self.assertEqual(seriescore.human_size(1023), "1023 Б")

    def test_units(self):
        self.assertEqual(seriescore.human_size(1024), "1.0 КБ")
        self.assertEqual(seriescore.human_size(5 * 1024 * 1024), "5.0 МБ")
        self.assertEqual(seriescore.human_size(3 * 1024 ** 3), "3.0 ГБ")


class HexdumpTests(unittest.TestCase):
    def test_format(self):
        dump = seriescore.hexdump(b"XVD" + b"\x00" * 13 + b"A")
        first = dump.splitlines()[0]
        self.assertTrue(first.startswith("00000000  58 56 44 00"))
        self.assertIn("|XVD", first)

    def test_limit(self):
        dump = seriescore.hexdump(bytes(range(256)), limit=16)
        self.assertEqual(len(dump.splitlines()), 1)

    def test_non_printable_shown_as_dot(self):
        dump = seriescore.hexdump(b"\x00\xff")
        self.assertIn("|..|", dump)


class ScanTests(unittest.TestCase):
    def write_tmp(self, data):
        fd, path = tempfile.mkstemp(suffix=".img")
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        self.addCleanup(os.unlink, path)
        return path

    def test_finds_signatures_at_offsets(self):
        path = self.write_tmp(
            b"\x00" * 10
            + b"CD001"
            + b"\x00" * 1000
            + b"MICROSOFT*XBOX*MEDIA"
        )
        hits, err = seriescore.scan_signatures(path)
        self.assertIsNone(err)
        self.assertEqual(len(hits), 2)
        self.assertIn((10, "ISO9660"), hits)
        self.assertIn((1015, "XDVDFS (файловая система Xbox)"), hits)

    def test_no_signatures(self):
        path = self.write_tmp(b"\x00" * 4096)
        hits, err = seriescore.scan_signatures(path)
        self.assertIsNone(err)
        self.assertEqual(hits, [])

    def test_missing_file(self):
        hits, err = seriescore.scan_signatures(os.path.join(HERE, "no_such.bin"))
        self.assertIsNone(hits)
        self.assertIn("No such file", err)

    def test_signature_across_chunk_boundary(self):
        sig = b"MICROSOFT*XBOX*MEDIA"
        data = b"A" * ((1 << 20) - 10) + sig
        path = self.write_tmp(data)
        hits, err = seriescore.scan_signatures(path, chunk_size=1 << 20)
        self.assertIsNone(err)
        self.assertIn(((1 << 20) - 10, "XDVDFS (файловая система Xbox)"), hits), hits


class CapabilitiesTests(unittest.TestCase):
    def test_matrix_structure(self):
        allowed_states = {
            "полная", "частичная", "официальная", "метаданные", "не поддерживается",
        }
        for topic, state, note in seriescore.SERIES_SUPPORT:
            self.assertTrue(topic)
            self.assertIn(state, allowed_states)
            self.assertTrue(note)

    def test_key_rows_present(self):
        topics = [topic for topic, _, _ in seriescore.SERIES_SUPPORT]
        self.assertIn("CPU (AMD Zen 2)", topics)
        self.assertIn("Игры Series X|S на ПК", topics)
        self.assertIn("Пиратский контент", topics)



class EntropyTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(seriescore.entropy(b""), 0.0)

    def test_uniform_zero(self):
        self.assertEqual(seriescore.entropy(b"\x00" * 4096), 0.0)

    def test_one_bit(self):
        self.assertAlmostEqual(seriescore.entropy(bytes([0, 255] * 512)), 1.0, places=6)

    def test_higher_than_threshold_for_random(self):
        import os as _os

        h = seriescore.entropy(_os.urandom(65536))
        self.assertGreater(h, 7.9)
        self.assertLessEqual(h, 8.0)


class EntropyBlocksTests(unittest.TestCase):
    def write_tmp(self, data):
        fd, path = tempfile.mkstemp(suffix=".img")
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        self.addCleanup(os.unlink, path)
        return path

    def test_zero_blocks_are_structural(self):
        path = self.write_tmp(b"\x00" * 4096)
        rows, err = seriescore.entropy_blocks(path, block_size=1024, max_blocks=4)
        self.assertIsNone(err)
        self.assertTrue(rows)
        for r in rows:
            self.assertEqual(r["entropy"], 0.0)
            self.assertFalse(r["high"])

    def test_perfect_entropy_block_flagged_high(self):
        path = self.write_tmp(bytes(range(256)) * 8)
        rows, err = seriescore.entropy_blocks(path, block_size=1024, max_blocks=2)
        self.assertIsNone(err)
        self.assertTrue(all(r["high"] for r in rows))
        self.assertTrue(all(r["entropy"] >= 7.99 for r in rows))

    def test_mixed_file_layout(self):
        path = self.write_tmp(b"\x00" * 1024 + bytes(range(256)) * 4)
        rows, err = seriescore.entropy_blocks(path, block_size=1024, max_blocks=2)
        self.assertIsNone(err)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["offset"], 0)
        self.assertEqual(rows[1]["offset"], 1024)
        self.assertFalse(rows[0]["high"])
        self.assertTrue(rows[1]["high"])

    def test_missing_file(self):
        rows, err = seriescore.entropy_blocks(os.path.join(HERE, "no_such.img"))
        self.assertIsNone(rows)
        self.assertIn("No such file", err)



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
