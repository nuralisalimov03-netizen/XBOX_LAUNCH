#!/usr/bin/env python3
"""Тесты каркаса эмулятора. Запуск из корня репозитория:
python -m unittest tests.test_series_emulator -v"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from series_emulator.memory import (Memory, MemoryError, REGION_GAME,
                                    REGION_GPU)
from series_emulator.gpu import GPU
from series_emulator.apu import APU
from series_emulator.input import InputManager
from series_emulator.kernel import Kernel
from series_emulator.cpu import StubCPU
from series_emulator.console import SeriesConsole, boot_demo_console


class MemoryTests(unittest.TestCase):
    def test_u64_roundtrip(self):
        mem = Memory(size_bytes=64 * 1024 * 1024)
        mem.write_u64(0x100, 0xDEADBEEFCAFEBABE)
        self.assertEqual(mem.read_u64(0x100), 0xDEADBEEFCAFEBABE)

    def test_write_across_page_boundary(self):
        mem = Memory(size_bytes=64 * 1024 * 1024)
        addr = 0x1000 * 2 - 2
        mem.write_u32(addr, 305419896)
        self.assertEqual(mem.read_u32(addr), 305419896)

    def test_out_of_range_raises(self):
        mem = Memory()
        with self.assertRaises(MemoryError):
            mem.read_u8(0x10_0000_0000)

    def test_region_alloc_and_bad_region(self):
        mem = Memory()
        a = mem.alloc(0x100)
        self.assertEqual(mem.region_of(a), "user")
        gpu1 = mem.alloc(0x2000, region=REGION_GPU)
        self.assertEqual(mem.region_of(gpu1), "gpu")
        with self.assertRaises(MemoryError):
            mem.alloc(1, region=0xDEAD)

    def test_alloc_regions(self):
        mem = Memory(size_bytes=64 * 1024 * 1024)
        a = mem.alloc(0x1000, region=REGION_GPU)
        b = mem.alloc(0x1000, region=REGION_GAME)
        self.assertEqual(mem.region_of(a), "gpu")
        self.assertEqual(mem.region_of(b), "game")


class GpuTests(unittest.TestCase):
    def setUp(self):
        self.gpu = GPU(Memory(size_bytes=64 * 1024 * 1024),
                       width=64, height=48)

    def test_clear_and_pixel(self):
        self.gpu.clear(10, 20, 30)
        self.assertEqual(self.gpu.get_pixel(0, 0), (10, 20, 30, 255))
        self.gpu.put_pixel(63, 47, 255, 0, 0)
        self.assertEqual(self.gpu.get_pixel(63, 47), (255, 0, 0, 255))

    def test_triangle_rasterization(self):
        self.gpu.clear(0, 0, 0)
        drawn = self.gpu.raster_triangle((2, 2), (40, 4), (20, 30),
                                         color=(0, 255, 0, 255))
        self.assertGreater(drawn, 50)
        self.assertEqual(self.gpu.get_pixel(20, 10), (0, 255, 0, 255))

    def test_degenerate_triangle_draws_nothing(self):
        self.assertEqual(self.gpu.raster_triangle((5, 5), (5, 5), (5, 5)), 0)

    def test_export_ppm_header(self):
        self.gpu.clear(1, 2, 3)
        head = self.gpu.export_ppm().decode("ascii").splitlines()[:3]
        self.assertEqual(head, ["P3", "64 48", "255"])


class KernelTests(unittest.TestCase):
    def test_object_lifecycle(self):
        kernel = Kernel(Memory(size_bytes=16 * 1024 * 1024))
        h = kernel.create_object("game", {"title": "Halo"})
        self.assertEqual(kernel.get_object(h)["payload"]["title"], "Halo")
        kernel.close_object(h)
        with self.assertRaises(Exception):
            kernel.get_object(h)

    def test_unknown_syscall(self):
        kernel = Kernel(Memory(size_bytes=16 * 1024 * 1024))
        with self.assertRaises(Exception):
            kernel.syscall("definitely_not_real")


class CpuTests(unittest.TestCase):
    def test_program_runs(self):
        cpu = StubCPU()
        cpu.load_program(["set", 10, "add", 5, "sub", 2, "hlt"])
        cpu.run()
        self.assertEqual(cpu.rax, 13)
        self.assertTrue(cpu.halted)


class ConsoleTests(unittest.TestCase):
    def test_boot_and_frame(self):
        console = boot_demo_console(width=64, height=32)
        self.assertEqual(console.frames, 1)
        self.assertGreater(console.status()["kernel_objects"], 0)
        report = console.boot()
        self.assertTrue(report["ok"])

    def test_run_frame_with_draw_callback(self):
        console = SeriesConsole(width=32, height=32)
        console.boot()

        def draw(gpu):
            gpu.raster_triangle((0, 0), (31, 0), (16, 24))

        console.run_frame(draw=draw)
        self.assertEqual(console.frames, 1)
        self.assertEqual(console.gpu.get_pixel(16, 5)[0], 255)


class InputTests(unittest.TestCase):
    def test_axes_clipped(self):
        mgr = InputManager()
        c = mgr.controller(0)
        c.set_axis("ls_x", 5.0)
        self.assertEqual(c.axes["ls_x"], 1.0)
        c.set_axis("rt", -0.5)
        self.assertEqual(c.axes["rt"], 0.0)


class ApuTests(unittest.TestCase):
    def test_mix_sums_chunks(self):
        apu = APU()
        self.assertEqual(apu.main.submit([0.5, -0.5]), 2)
        self.assertEqual(apu.main.mix(1), [0.5, -0.5])


if __name__ == "__main__":
    unittest.main(verbosity=2)
