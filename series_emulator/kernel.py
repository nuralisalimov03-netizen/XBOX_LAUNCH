"""series_emulator.kernel — таблица объектов и системные вызовы ядра."""
from __future__ import annotations

import time
from collections import OrderedDict

from .memory import Memory, REGION_KERNEL


class KernelError(Exception):
    pass


class Kernel:
    """HLE-ядро: объекты, лимитированный набор сисколов, boot-лог."""

    MAX_OBJECTS = 4096

    def __init__(self, mem: Memory):
        self.mem = mem
        self.objects = OrderedDict()
        self._next_handle = 0x1000
        self.boot_log = []

    def log(self, message: str):
        self.boot_log.append("[%s] %s" % (time.strftime("%H:%M:%S"), message))

    def allocate(self, size: int, region: int = REGION_KERNEL) -> int:
        addr = self.mem.alloc(size, region=region)
        self.log("alloc %d bytes @ 0x%X" % (size, addr))
        return addr

    def create_object(self, obj_type: str, payload=None) -> int:
        if len(self.objects) >= self.MAX_OBJECTS:
            raise KernelError("Таблица объектов переполнена")
        handle = self._next_handle
        self._next_handle += 4
        self.objects[handle] = {"type": obj_type, "payload": payload,
                                "created_at": time.time()}
        self.log("obj 0x%X type=%s" % (handle, obj_type))
        return handle

    def get_object(self, handle: int) -> dict:
        if handle not in self.objects:
            raise KernelError("Нет объекта с handle 0x%X" % handle)
        return self.objects[handle]

    def close_object(self, handle: int):
        if handle not in self.objects:
            raise KernelError("Нет объекта с handle 0x%X" % handle)
        del self.objects[handle]
        self.log("close 0x%X" % handle)

    def syscall(self, name: str, *args):
        """Мини-набор сисколов: alloc, create, get, close, log."""
        table = {
            "alloc": self.allocate,
            "create": self.create_object,
            "get": self.get_object,
            "close": self.close_object,
            "log": self.log,
        }
        if name not in table:
            raise KernelError("Неизвестный сискол: %s" % name)
        return table[name](*args)
