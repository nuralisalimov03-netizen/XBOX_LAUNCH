"""Входная точка: python -m series_emulator [options]"""
from __future__ import annotations

import argparse
import sys

from .console import boot_demo_console


def selftest() -> int:
    checks = []

    from .memory import Memory
    from .gpu import GPU
    from .kernel import Kernel
    from .cpu import StubCPU

    mem = Memory(size_bytes=16 * 1024 * 1024)
    mem.write_u64(0x1000, 0xDEADBEEFCAFEBABE)
    checks.append(("memory u64 roundtrip",
                   mem.read_u64(0x1000) == 0xDEADBEEFCAFEBABE))
    mem.write_u32(0x1FFFF, 12345)
    checks.append(("memory page crossing", mem.read_u32(0x1FFFF) == 12345))

    gpu = GPU(Memory(size_bytes=16 * 1024 * 1024), width=32, height=18)
    gpu.clear(0, 0, 0)
    gpu.put_pixel(5, 5, 255, 0, 0)
    checks.append(("gpu pixel", gpu.get_pixel(5, 5) == (255, 0, 0, 255)))
    drawn = gpu.raster_triangle((1, 1), (30, 1), (15, 15),
                                color=(0, 255, 0, 255))
    checks.append(("gpu triangle raster", drawn > 10))
    ppm = gpu.export_ppm().decode("ascii").splitlines()
    checks.append(("gpu ppm header", ppm[0] == "P3" and ppm[1] == "32 18"))

    kernel = Kernel(Memory(size_bytes=16 * 1024 * 1024))
    h = kernel.syscall("create", "game", {"title": "demo"})
    checks.append(("kernel create/get",
                   kernel.syscall("get", h)["type"] == "game"))
    kernel.syscall("close", h)
    try:
        kernel.syscall("get", h)
        checks.append(("kernel close", False))
    except Exception:
        checks.append(("kernel close", True))

    cpu = StubCPU()
    cpu.load_program(["set", 5, "add", 3, "sub", 1, "hlt"])
    steps = cpu.run()
    checks.append(("cpu stub program", cpu.rax == 7 and cpu.halted and steps == 4))

    console = boot_demo_console()
    checks.append(("console boot", console.frames == 1 and
                   console.status()["kernel_objects"] >= 1))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print("  [%s] %s" % ("OK" if ok else "FAIL", name))
    if failed:
        print("SERIES EMULATOR SELFTEST FAILED: %s" % ", ".join(failed))
        return 1
    print("SERIES EMULATOR SELFTEST OK")
    return 0


def dump_boot_ppm(out_path: str) -> int:
    console = boot_demo_console()
    data = console.gpu.export_ppm()
    with open(out_path, "wb") as f:
        f.write(data)
    print("Загрузочный PPM записан: %s (%dx%d)"
          % (out_path, console.gpu.width, console.gpu.height))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="series-emulator")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--boot-ppm", metavar="PATH",
                        help="сохранить загрузочный кадр в PPM")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.boot_ppm:
        return dump_boot_ppm(args.boot_ppm)
    if args.status:
        st = boot_demo_console().status()
        for key, value in st.items():
            print("%s: %s" % (key, value))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
