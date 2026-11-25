import importlib.util
import os
import struct
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PE_PATH = os.path.join(HERE, "pe_parser.py")

spec = importlib.util.spec_from_file_location("pe_parser", PE_PATH)
pe_parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pe_parser)


class MinimalPETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = pe_parser.build_minimal_pe()

    def test_headers(self):
        info = pe_parser.parse_pe(self.data)
        self.assertEqual(info["machine"], 0x8664)
        self.assertEqual(info["machine_name"], "x86-64")
        self.assertTrue(info["pe32plus"])
        self.assertEqual(info["entry_point"], 0x1000)
        self.assertEqual(info["image_base"], 0x140000000)
        self.assertEqual(info["image_size"], 0x2000)

    def test_sections(self):
        info = pe_parser.parse_pe(self.data)
        self.assertEqual(len(info["sections"]), 1)
        sec = info["sections"][0]
        self.assertEqual(sec["name"], ".text")
        self.assertEqual(sec["virtual_address"], 0x1000)
        self.assertEqual(sec["raw_offset"], 0x400)
        self.assertEqual(sec["raw_size"], 0x200)
        self.assertIn("CODE", sec["flags"])
        self.assertIn("EXECUTE", sec["flags"])
        self.assertIn("READ", sec["flags"])


class PEP32Tests(unittest.TestCase):
    def test_pe32_image_base(self):
        data = bytearray(pe_parser.build_minimal_pe())
        pe_off = 0x80
        opt = pe_off + 4 + 20
        struct.pack_into("<H", data, opt, pe_parser.OPT_PE32)
        struct.pack_into("<I", data, opt + 28, 0x400000)
        struct.pack_into("<I", data, opt + 56, 0x2000)
        info = pe_parser.parse_pe(bytes(data))
        self.assertFalse(info["pe32plus"])
        self.assertEqual(info["image_base"], 0x400000)
        self.assertEqual(info["image_size"], 0x2000)
        self.assertEqual(info["entry_point"], 0x1000)


class PEErrorTests(unittest.TestCase):
    def test_not_mz(self):
        with self.assertRaises(pe_parser.PEError) as cm:
            pe_parser.parse_pe(b"ELF\x00\x00" + b"\x00" * 200)
        self.assertIn("MZ", str(cm.exception))

    def test_bad_pe_signature(self):
        data = bytearray(pe_parser.build_minimal_pe())
        data[0x80:0x84] = b"PEXX"
        with self.assertRaises(pe_parser.PEError) as cm:
            pe_parser.parse_pe(bytes(data))
        self.assertIn("PE", str(cm.exception))

    def test_truncated(self):
        with self.assertRaises(pe_parser.PEError) as cm:
            pe_parser.parse_pe(b"MZ\x00\x00")
        self.assertIn("обрезан", str(cm.exception))

    def test_unknown_optional_magic(self):
        data = bytearray(pe_parser.build_minimal_pe())
        opt = 0x80 + 4 + 20
        struct.pack_into("<H", data, opt, 0x1FF)
        with self.assertRaises(pe_parser.PEError) as cm:
            pe_parser.parse_pe(bytes(data))
        self.assertIn("optional header", str(cm.exception))

    def test_parse_pe_file_missing(self):
        info, err = pe_parser.parse_pe_file(os.path.join(HERE, "no_such.exe"))
        self.assertIsNone(info)
        self.assertIn("No such file", err)


class MinimalPEFileRoundtripTests(unittest.TestCase):
    def test_write_and_parse(self):
        import tempfile

        path = None
        try:
            fd, path = tempfile.mkstemp(suffix=".exe")
            with os.fdopen(fd, "wb") as f:
                f.write(pe_parser.build_minimal_pe())
            info, err = pe_parser.parse_pe_file(path)
            self.assertIsNone(err)
            self.assertEqual(info["machine_name"], "x86-64")
            self.assertEqual(len(info["sections"]), 1)
        finally:
            if path and os.path.exists(path):
                os.unlink(path)


if __name__ == "__main__":
    unittest.main()
