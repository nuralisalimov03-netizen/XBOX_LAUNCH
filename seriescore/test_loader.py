import importlib.util
import os
import struct
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pe_parser = _load("pe_parser")
loader = _load("loader")


class LoadImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = pe_parser.build_minimal_pe()
        cls.image = loader.load_image(cls.data)

    def test_layout(self):
        self.assertEqual(self.image["base"], 0x140000000)
        self.assertEqual(self.image["size"], 0x2000)
        self.assertEqual(self.image["entry_va"], 0x140001000)

    def test_section_data_mapped_at_va(self):
        self.assertEqual(loader.read_mem(self.image, 0x140001000, 4), b"SCX1")

    def test_section_at(self):
        sec = loader.section_at(self.image, 0x140001000)
        self.assertIsNotNone(sec)
        self.assertEqual(sec["name"], ".text")
        self.assertIsNone(loader.section_at(self.image, 0x140000100))

    def test_read_out_of_bounds(self):
        with self.assertRaises(loader.MemoryAccessError):
            loader.read_mem(self.image, 0x140003000, 4)
        with self.assertRaises(loader.MemoryAccessError):
            loader.read_mem(self.image, 0x0, 4)

    def test_read_entry_span(self):
        payload = loader.read_mem(self.image, 0x140001000, 8)
        self.assertTrue(payload.startswith(b"SCX1"))
        self.assertEqual(len(payload), 8)

    def test_section_overflow_rejected(self):
        data = bytearray(pe_parser.build_minimal_pe())
        opt = 0x80 + 4 + 20
        struct.pack_into("<I", data, opt + 56, 0x10)
        with self.assertRaises(loader.LoadError) as cm:
            loader.load_image(bytes(data))
        self.assertIn("границу образа", str(cm.exception))

    def test_invalid_pe_rejected(self):
        with self.assertRaises(loader.LoadError):
            loader.load_image(b"GARBAGE" + b"\x00" * 300)

    def test_load_image_file_missing(self):
        image, err = loader.load_image_file(os.path.join(HERE, "no_such.exe"))
        self.assertIsNone(image)
        self.assertIn("No such file", err)

    def test_load_image_file_roundtrip(self):
        import tempfile

        path = None
        try:
            fd, path = tempfile.mkstemp(suffix=".exe")
            with os.fdopen(fd, "wb") as f:
                f.write(self.data)
            image, err = loader.load_image_file(path)
            self.assertIsNone(err)
            self.assertEqual(loader.read_mem(image, image["entry_va"], 4), b"SCX1")
        finally:
            if path and os.path.exists(path):
                os.unlink(path)


if __name__ == "__main__":
    unittest.main()
