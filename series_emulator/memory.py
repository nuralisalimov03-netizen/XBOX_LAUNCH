"""series_emulator.memory — единое адресное пространство консоли."""
from __future__ import annotations

import struct

PAGE_SIZE = 0x1000
REGION_SPAN = 0x4000000  # 64 МБ на регион в каркасе

REGION_KERNEL = 0x0000_0000_0000_0000
REGION_USER = 0x0000_0001_0000_0000
REGION_GPU = 0x0000_0002_0000_0000
REGION_GAME = 0x0000_0003_0000_0000

REGION_NAMES = {
    REGION_KERNEL: "kernel",
    REGION_USER: "user",
    REGION_GPU: "gpu",
    REGION_GAME: "game",
}

_REGION_BASES = sorted(REGION_NAMES)


class MemoryError(Exception):
    pass


class Memory:
    """Линейное little-endian адресное пространство с разбиением на регионы.

    У каждого региона свой курсор аллокации: alloc(size, region) резервирует
    память в границах конкретного региона, а не всего пространства.
    """

    def __init__(self, size_bytes: int = None):
        self._pages = {}
        self._fp = {base: base for base in REGION_NAMES}

    def _region_end(self, base: int) -> int:
        idx = _REGION_BASES.index(base)
        if idx + 1 < len(_REGION_BASES):
            return _REGION_BASES[idx + 1]
        return base + REGION_SPAN

    def _validate(self, addr: int):
        for base in _REGION_BASES:
            if base <= addr < self._region_end(base):
                return
        raise MemoryError("Адрес вне известных регионов: 0x%X" % addr)

    def _page(self, addr: int):
        idx = addr // PAGE_SIZE
        page = self._pages.get(idx)
        if page is None:
            page = bytearray(PAGE_SIZE)
            self._pages[idx] = page
        return page

    def _write(self, addr: int, data: bytes):
        offset = 0
        while offset < len(data):
            page = self._page(addr + offset)
            start = (addr + offset) % PAGE_SIZE
            chunk = min(PAGE_SIZE - start, len(data) - offset)
            page[start:start + chunk] = data[offset:offset + chunk]
            offset += chunk

    def _read(self, addr: int, length: int) -> bytes:
        out = bytearray(length)
        offset = 0
        while offset < length:
            page = self._page(addr + offset)
            start = (addr + offset) % PAGE_SIZE
            chunk = min(PAGE_SIZE - start, length - offset)
            out[offset:offset + chunk] = page[start:start + chunk]
            offset += chunk
        return bytes(out)

    def write_u8(self, addr: int, value: int):
        self._validate(addr)
        self._write(addr, struct.pack("<B", value & 0xFF))

    def write_u16(self, addr: int, value: int):
        self._validate(addr)
        self._write(addr, struct.pack("<H", value & 0xFFFF))

    def write_u32(self, addr: int, value: int):
        self._validate(addr)
        self._write(addr, struct.pack("<I", value & 0xFFFFFFFF))

    def write_u64(self, addr: int, value: int):
        self._validate(addr)
        self._write(addr, struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF))

    def write_bytes(self, addr: int, data: bytes):
        self._validate(addr)
        self._write(addr, bytes(data))

    def read_u8(self, addr: int) -> int:
        self._validate(addr)
        return self._read(addr, 1)[0]

    def read_u16(self, addr: int) -> int:
        self._validate(addr)
        return struct.unpack("<H", self._read(addr, 2))[0]

    def read_u32(self, addr: int) -> int:
        self._validate(addr)
        return struct.unpack("<I", self._read(addr, 4))[0]

    def read_u64(self, addr: int) -> int:
        self._validate(addr)
        return struct.unpack("<Q", self._read(addr, 8))[0]

    def read_bytes(self, addr: int, length: int) -> bytes:
        self._validate(addr)
        return self._read(addr, length)

    def alloc(self, size: int, region: int = REGION_USER) -> int:
        """Резервирует size байт в указанном регионе, возвращает базовый адрес."""
        if size <= 0:
            raise MemoryError("Размер должен быть > 0")
        if region not in REGION_NAMES:
            raise MemoryError("Неизвестный регион: 0x%X" % region)
        base = (self._fp[region] + PAGE_SIZE - 1) & ~(PAGE_SIZE - 1)
        top = base + size
        if top > self._region_end(region):
            raise MemoryError("Регион %s переполнен" % REGION_NAMES[region])
        self._fp[region] = top
        self._page(top - 1)
        return base

    def region_of(self, addr: int) -> str:
        for base in _REGION_BASES:
            if base <= addr < self._region_end(base):
                return REGION_NAMES[base]
        raise MemoryError("Адрес вне известных регионов: 0x%X" % addr)
