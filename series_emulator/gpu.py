"""series_emulator.gpu — софтверный растеризатор в окне RDNA-памяти.

Заглушка полноценного RDNA 2: сейчас это framebuffer RGBA + утилиты
clear/triangle, пригодные для тестов и отладки пайплайна.
"""
from __future__ import annotations

import struct

from .memory import Memory, REGION_GPU


class GPU:
    def __init__(self, mem: Memory, width: int = 640, height: int = 360):
        self.mem = mem
        self.width = width
        self.height = height
        self.stride = width * 4
        self.fb_size = self.stride * height
        self.framebuffer = mem.alloc(self.fb_size, region=REGION_GPU)

    def clear(self, r: int, g: int, b: int, a: int = 255):
        pixel = struct.pack("<BBBB", r, g, b, a)
        row = pixel * self.width
        for y in range(self.height):
            self.mem.write_bytes(self.framebuffer + y * self.stride, row)

    def put_pixel(self, x: int, y: int, r: int, g: int, b: int, a: int = 255):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        addr = self.framebuffer + (y * self.stride) + x * 4
        self.mem.write_bytes(addr, struct.pack("<BBBB", r, g, b, a))

    def get_pixel(self, x: int, y: int):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return (0, 0, 0, 0)
        addr = self.framebuffer + (y * self.stride) + x * 4
        return struct.unpack("<BBBB", self.mem.read_bytes(addr, 4))

    def raster_triangle(self, v0, v1, v2, color=(255, 0, 0, 255)):
        """Растеризация одного треугольника по barycentric-тесту."""
        xs = (v0[0], v1[0], v2[0])
        ys = (v0[1], v1[1], v2[1])
        eps = 1e-9
        area = (xs[1] - xs[0]) * (ys[2] - ys[0]) - (xs[2] - xs[0]) * (ys[1] - ys[0])
        if abs(area) < eps:
            return 0
        x_min = max(int(min(xs)), 0)
        x_max = min(int(max(xs)) + 1, self.width)
        y_min = max(int(min(ys)), 0)
        y_max = min(int(max(ys)) + 1, self.height)
        drawn = 0
        for y in range(y_min, y_max):
            for x in range(x_min, x_max):
                px = x + 0.5
                py = y + 0.5
                w0 = ((xs[1] - px) * (ys[2] - py) - (xs[2] - px) * (ys[1] - py)) / area
                w1 = ((xs[2] - px) * (ys[0] - py) - (xs[0] - px) * (ys[2] - py)) / area
                w2 = 1.0 - w0 - w1
                if w0 >= -eps and w1 >= -eps and w2 >= -eps:
                    self.put_pixel(x, y, *color)
                    drawn += 1
        return drawn

    def export_ppm(self) -> bytes:
        """Материал для сборки P3 PPM (для отладки без GUI)."""
        rows = ["P3", "%d %d" % (self.width, self.height), "255"]
        for y in range(self.height):
            row = self.mem.read_bytes(self.framebuffer + y * self.stride,
                                      self.stride)
            values = []
            for x in range(self.width):
                r, g, b, _a = struct.unpack_from("<BBBB", row, x * 4)
                values.extend((str(r), str(g), str(b)))
            rows.append(" ".join(values))
        return ("\n".join(rows) + "\n").encode("ascii")
