"""series_emulator.console — сборка «консоли» из модулей."""
from __future__ import annotations

import time

from .memory import Memory
from .gpu import GPU
from .apu import APU
from .input import InputManager
from .kernel import Kernel
from .cpu import StubCPU


class SeriesConsole:
    """Виртуальная консоль: память + GPU + APU + ввод + ядро + CPU."""

    CONSOLE_MODEL = "Series X (skeleton)"

    def __init__(self, width: int = 640, height: int = 360):
        self.mem = Memory()
        self.gpu = GPU(self.mem, width=width, height=height)
        self.apu = APU()
        self.input = InputManager()
        self.kernel = Kernel(self.mem)
        self.cpu = StubCPU()
        self.frames = 0
        self.booted_at = None

    def boot(self, splash_color=(16, 124, 16)):
        self.kernel.log("boot %s" % self.CONSOLE_MODEL)
        self.gpu.clear(*splash_color)
        self.frames = 0
        self.booted_at = time.time()
        self.kernel.log("framebuffer 0x%X (%dx%d RGBA)"
                        % (self.gpu.framebuffer, self.gpu.width, self.gpu.height))
        self.kernel.create_object("framebuffer", {
            "base": self.gpu.framebuffer,
            "width": self.gpu.width,
            "height": self.gpu.height,
        })
        return {
            "model": self.CONSOLE_MODEL,
            "framebuffer": self.gpu.framebuffer,
            "objects": len(self.kernel.objects),
            "ok": True,
        }

    def run_frame(self, draw=None):
        """Один кадр: вызов draw-колбэка (если задан) и шаг заглушки CPU."""
        self.frames += 1
        if draw:
            draw(self.gpu)
        self.cpu.step()
        return self.frames

    def status(self) -> dict:
        return {
            "model": self.CONSOLE_MODEL,
            "frames": self.frames,
            "memory_regions_used": len(self.mem._pages),
            "kernel_objects": len(self.kernel.objects),
            "apu": self.apu.status(),
            "boot_log": self.kernel.boot_log,
        }

    def shutdown(self):
        self.kernel.log("shutdown")


def boot_demo_console(width=320, height=180):
    """Готовая консоль с демо-кадром: зелёная заливка + треугольник."""
    console = SeriesConsole(width=width, height=height)
    console.boot()
    console.run_frame(draw=lambda gpu: gpu.raster_triangle(
        (10, 10), (100, 150), (200, 30), color=(255, 255, 255, 255)))
    return console
