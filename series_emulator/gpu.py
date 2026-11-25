"""series_emulator.gpu — софтверный растеризатор в окне RDNA-памяти.

Заглушка полноценного RDNA 2: framebuffer RGBA, треугольники/квады,
HUD-текст через font3x5, экспорт PPM.
"""
from __future__ import annotations

import struct

from .font3x5 import FONT
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

    def raster_quad(self, x0, y0, x1, y1, color=(255, 255, 255, 255)):
        """Прямоугольник (x0,y0)-(x1,y1) включительно из двух треугольников."""
        a = self.raster_triangle((x0, y0), (x1, y0), (x1, y1), color=color)
        b = self.raster_triangle((x0, y0), (x1, y1), (x0, y1), color=color)
        return a + b

    def draw_rect(self, x, y, w, h, color=(255, 255, 255, 255)):
        """Прямоугольник шириной w и высотой h, пиксели (x..x+w-1, y..y+h-1)."""
        drawn = 0
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.put_pixel(xx, yy, *color)
                drawn += 1
        return drawn

    def draw_gradient(self, top=(20, 20, 20), bottom=(5, 5, 5)):
        """Вертикальный градиент фона (r,g,b) от верха к низу."""
        height = max(self.height - 1, 1)
        for y in range(self.height):
            t = y / height
            r = int(top[0] + (bottom[0] - top[0]) * t)
            g = int(top[1] + (bottom[1] - top[1]) * t)
            b = int(top[2] + (bottom[2] - top[2]) * t)
            row = struct.pack("<BBBB", r, g, b, 255) * self.width
            self.mem.write_bytes(self.framebuffer + y * self.stride, row)

    def draw_frame_rect(self, x, y, w, h, color=(255, 255, 255, 255), thickness=1):
        """Полый прямоугольник (рамка) толщиной thickness."""
        drawn = 0
        for t in range(thickness):
            drawn += self.draw_rect(x + t, y + t, w - 2 * t, 1, color)
            drawn += self.draw_rect(x + t, y + h - 1 - t, w - 2 * t, 1, color)
            if w - 2 * t > 0 and h - 2 * t > 0:
                drawn += self.draw_rect(x + t, y + 1 + t, 1, h - 2 - 2 * t, color)
                drawn += self.draw_rect(x + w - 1 - t, y + 1 + t, 1, h - 2 - 2 * t, color)
        return drawn

    def draw_circle(self, cx, cy, radius, color=(255, 255, 255, 255),
                    fill=True, thickness=1):
        """Окружность/диск (по расстоянию до центра)."""
        drawn = 0
        r = max(1, int(radius))
        for y in range(max(0, cy - r), min(self.height, cy + r + 1)):
            for x in range(max(0, cx - r), min(self.width, cx + r + 1)):
                d2 = (x - cx) * (x - cx) + (y - cy) * (y - cy)
                if fill:
                    hit = d2 <= r * r
                else:
                    band = thickness - 1
                    hit = (r - 1 - band) * (r - 1 - band) <= d2 <= r * r                         if r - 1 - band >= 0 else d2 <= r * r
                if hit:
                    self.put_pixel(x, y, *color)
                    drawn += 1
        return drawn

    def draw_text(self, text, x, y, color=(255, 255, 255, 255), scale=1):
        """Рисует строку шрифтом font3x5. char advance = 4*scale."""
        drawn = 0
        cx = x
        for ch in text:
            glyph = FONT.get(ch.upper(), FONT[" "])
            for ry, row in enumerate(glyph):
                for rx, bit in enumerate(row):
                    if bit == "1":
                        for sy in range(scale):
                            for sx in range(scale):
                                self.put_pixel(cx + rx * scale + sx,
                                               y + ry * scale + sy, *color)
                                drawn += 1
            cx += 4 * scale
        return drawn
