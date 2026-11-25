#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys

PROJECT = "SeriesCore"
VERSION = "0.1.0"

MODULES = [
    ("containers", "Чтение образов XVD", "в разработке"),
    ("kernel", "Шимы системных вызовов консоли", "не начат"),
    ("video", "Перехват и перенос команд D3D12 Ultimate", "не начат"),
    ("audio", "Вывод звука", "не начат"),
    ("input", "Геймпад и HID", "не начат"),
    ("net", "Эмуляция XNet", "не начат"),
    ("ui", "Оболочка", "не начат"),
]

XVD_MAGIC = b"XVD"
KNOWN_SIGNATURES = [
    (b"XVD", "XVD-контейнер Xbox"),
    (b"MICROSOFT*XBOX*MEDIA", "XDVDFS (файловая система Xbox)"),
    (b"CD001", "ISO9660"),
]
DUMP_WIDTH = 16


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


def human_size(num):
    if num < 1024:
        return "%d Б" % num
    for unit in ("КБ", "МБ", "ГБ", "ТБ"):
        num /= 1024.0
        if num < 1024:
            return "%.1f %s" % (num, unit)
    return "%.1f ПБ" % num


def hexdump(data, limit=64):
    lines = []
    selected = data[:limit]
    for i in range(0, len(selected), DUMP_WIDTH):
        row = selected[i : i + DUMP_WIDTH]
        hex_part = " ".join("%02x" % b for b in row).ljust(DUMP_WIDTH * 3 - 1)
        text_part = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        lines.append("%08x  %s  |%s|" % (i, hex_part, text_part))
    return "\n".join(lines)


def scan_signatures(path, chunk_size=1 << 20):
    max_len = max(len(sig) for sig, _ in KNOWN_SIGNATURES)
    results = []
    file_off = 0
    carry = b""
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                buf = carry + chunk
                for sig, name in KNOWN_SIGNATURES:
                    start = 0
                    while True:
                        idx = buf.find(sig, start)
                        if idx < 0:
                            break
                        results.append((file_off - len(carry) + idx, name))
                        start = idx + 1
                file_off += len(chunk)
                carry = buf[-(max_len - 1) :]
    except OSError as e:
        return None, str(e)
    return sorted(set(results)), None


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
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    for key in ("path", "size_bytes", "sha256_head", "head_hex", "has_xvd_magic"):
        if key in report:
            print("%s: %s" % (key, report[key]))
    print("размер: %s" % human_size(report["size_bytes"]))
    print()
    try:
        with open(args.file, "rb") as f:
            head = f.read(64)
        print("Начало файла (первые 64 байта):")
        print(hexdump(head))
    except OSError as e:
        print("Не удалось прочитать начало файла: %s" % e)
        return 1
    if not report["has_xvd_magic"]:
        print()
        print("Сигнатура XVD не найдена: файл не является образом консоли,"
              " либо формат заголовка требует уточнения исследованиями")
    return 0


def cmd_scan(args):
    hits, err = scan_signatures(args.file)
    if err:
        print("Ошибка: %s" % err)
        return 1
    if not hits:
        print("Известных подписей не найдено")
        return 0
    for offset, name in hits:
        print("0x%012x  %s" % (offset, name))
    print()
    print("Всего совпадений: %d" % len(hits))
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

        assert human_size(0) == "0 Б"
        assert human_size(1023) == "1023 Б"
        assert human_size(1024) == "1.0 КБ"
        assert human_size(5 * 1024 * 1024) == "5.0 МБ"

        dump = hexdump(XVD_MAGIC + b"\x00ABC")
        assert dump.splitlines()[0].startswith("00000000  58 56 44")
        assert "|XVD.ABC|" in dump

        fd, tmp3 = tempfile.mkstemp(suffix=".img")
        with os.fdopen(fd, "wb") as f:
            f.write(b"\x00" * 10)
            f.write(b"CD001")
            f.write(b"\x00" * 1000)
            f.write(b"MICROSOFT*XBOX*MEDIA")
        hits, err3 = scan_signatures(tmp3)
        os.unlink(tmp3)
        assert err3 is None, err3
        assert (10, "ISO9660") in hits, hits
        assert (1015, "XDVDFS (файловая система Xbox)") in hits, hits
        assert len(hits) == 2, hits
    finally:
        for p in (locals().get("tmp"),):
            if p and os.path.exists(p):
                os.unlink(p)
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
    p_info.add_argument("--json", action="store_true", help="Вывод в формате JSON")
    p_scan = sub.add_parser("scan", help="Поиск известных подписей во всём образе")
    p_scan.add_argument("file")
    sub.add_parser("selftest", help="Внутренняя проверка")
    args = parser.parse_args()

    if args.command == "status":
        return cmd_status(args)
    if args.command == "xvd-info":
        return cmd_xvd_info(args)
    if args.command == "scan":
        return cmd_scan(args)
    if args.command == "selftest":
        return cmd_selftest(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
