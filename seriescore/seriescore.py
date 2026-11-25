#!/usr/bin/env python3
import argparse
import hashlib
import os
import sys

PROJECT = "SeriesCore"
VERSION = "0.0.1"

MODULES = [
    ("containers", "Чтение образов XVD", "заготовка"),
    ("kernel", "Шимы системных вызовов консоли", "не начат"),
    ("video", "Перехват и перенос команд D3D12 Ultimate", "не начат"),
    ("audio", "Вывод звука", "не начат"),
    ("input", "Геймпад и HID", "не начат"),
    ("net", "Эмуляция XNet", "не начат"),
    ("ui", "Оболочка", "не начат"),
]

XVD_MAGIC = b"XVD"


def xvd_info(path):
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            head = f.read(4096)
    except OSError as e:
        return None, str(e)
    report = {
        "path": path,
        "size_bytes": size,
        "sha256_head": hashlib.sha256(head).hexdigest(),
        "has_xvd_magic": head.startswith(XVD_MAGIC),
    }
    if head:
        report["head_hex"] = head[:32].hex(" ")
    return report, None


def cmd_status(_):
    print("%s %s — пре-альфа, игры не запускаются" % (PROJECT, VERSION))
    print()
    for name, desc, state in MODULES:
        print("  %-11s %-46s %s" % (name, desc, state))
    return 0


def cmd_xvd_info(args):
    report, err = xvd_info(args.file)
    if err:
        print("Ошибка: %s" % err)
        return 1
    for key in ("path", "size_bytes", "sha256_head", "head_hex", "has_xvd_magic"):
        if key in report:
            print("%s: %s" % (key, report[key]))
    if not report["has_xvd_magic"]:
        print("Сигнатура XVD не найдена: файл не является образом консоли,"
              " либо формат заголовка требует уточнения исследованиями")
    return 0


def cmd_selftest(_):
    import tempfile

    fd, tmp = tempfile.mkstemp(suffix=".xvd")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(XVD_MAGIC + b"\x00" * 509)
        report, err = xvd_info(tmp)
        assert err is None, err
        assert report["has_xvd_magic"] is True
        assert report["size_bytes"] == 512
        assert report["head_hex"].startswith("58 56 44 00")

        fd, tmp2 = tempfile.mkstemp(suffix=".bin")
        with os.fdopen(fd, "wb") as f:
            f.write(b"NOTXVD" + b"\x00" * 10)
        report2, err2 = xvd_info(tmp2)
        os.unlink(tmp2)
        assert err2 is None, err2
        assert report2["has_xvd_magic"] is False
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    print("selftest: OK")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="seriescore",
        description="Каркас эмулятора Xbox Series X|S (пре-альфа): "
        "документация и инструменты контейнеров, без DRM и расшифрования",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Состояние проекта и модулей")
    p_info = sub.add_parser("xvd-info", help="Краткая информация об образе XVD")
    p_info.add_argument("file")
    sub.add_parser("selftest", help="Внутренняя проверка")
    args = parser.parse_args()

    if args.command == "status":
        return cmd_status(args)
    if args.command == "xvd-info":
        return cmd_xvd_info(args)
    if args.command == "selftest":
        return cmd_selftest(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
