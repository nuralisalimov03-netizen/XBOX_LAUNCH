#!/usr/bin/env python3
import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys

PROJECT = "SeriesCore"
VERSION = "0.4.0"

_here = os.path.dirname(os.path.abspath(__file__))
_pe_spec = importlib.util.spec_from_file_location(
    "pe_parser", os.path.join(_here, "pe_parser.py")
)
pe_parser = importlib.util.module_from_spec(_pe_spec)
_pe_spec.loader.exec_module(pe_parser)

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
SERIES_SUPPORT = [
    ("CPU (AMD Zen 2)", "полная",
     "архитектура x86-64 совпадает с ПК — трансляция инструкций не требуется"),
    ("GPU (AMD RDNA 2)", "частичная",
     "современные GPU AMD близки по ISA; нужен перенос команд D3D12 Ultimate"),
    ("Игры Series X|S на ПК", "официальная",
     "Microsoft Store / приложение Xbox (Xbox Play Anywhere, Game Pass); "
     "кнопка «Store / Xbox app…» в лаунчере"),
    ("Образы XVD", "метаданные",
     "чтение заголовка и поиск подписей; шифрование XTS-AES не обходится"),
    ("Пиратский контент", "не поддерживается",
     "обход DRM не входит в проект; только легальный контент"),
]
KNOWN_SIGNATURES = [
    (b"XVD", "XVD-контейнер Xbox"),
    (b"MICROSOFT*XBOX*MEDIA", "XDVDFS (файловая система Xbox)"),
    (b"CD001", "ISO9660"),
]
DUMP_WIDTH = 16
DEFAULT_BLOCK = 1 << 20
MAX_BLOCKS = 64


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


def entropy(data):
    if not data:
        return 0.0
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    total = len(data)
    h = 0.0
    for c in counts:
        if c:
            p = c / total
            h -= p * math.log2(p)
    return h


def is_high_entropy(h, n, margin=0.05):
    if n <= 0:
        return False
    ceiling = math.log2(256 if n >= 256 else n)
    ceiling -= 255 / (2 * math.log(2) * n)
    return h >= ceiling - margin


def entropy_blocks(path, block_size=DEFAULT_BLOCK, max_blocks=MAX_BLOCKS):
    try:
        size = os.path.getsize(path)
    except OSError as e:
        return None, str(e)
    total_blocks = max(1, (size + block_size - 1) // block_size)
    step = max(1, total_blocks // max_blocks)
    rows = []
    try:
        with open(path, "rb") as f:
            for bi in range(0, total_blocks, step):
                f.seek(bi * block_size)
                data = f.read(block_size)
                if not data:
                    break
                h = entropy(data)
                rows.append(
                    {
                        "offset": bi * block_size,
                        "entropy": round(h, 3),
                        "high": is_high_entropy(h, len(data)),
                    }
                )
    except OSError as e:
        return None, str(e)
    return rows, None


def cmd_capabilities(_):
    print("Поддержка Xbox Series X|S в %s %s" % (PROJECT, VERSION))
    print()
    for topic, state, note in SERIES_SUPPORT:
        print("  %-26s %s" % (topic, state))
        print("  %s- %s" % (" " * 26, note))
        print()
    return 0


def cmd_entropy(args):
    rows, err = entropy_blocks(args.file, block_size=max(1, args.block))
    if err:
        print("Ошибка: %s" % err)
        return 1
    if not rows:
        print("Пустой файл")
        return 0
    high = sum(1 for r in rows if r["high"])
    print("Блоков: %d (по %s) | высокая энтропия: %d" % (len(rows), human_size(args.block), high))
    print()
    for r in rows:
        mark = "возможно шифрование/сжатие" if r["high"] else "структурные данные"
        print("0x%012x  H=%.3f  %s" % (r["offset"], r["entropy"], mark))
    return 0


def cmd_pe_info(args):
    info, err = pe_parser.parse_pe_file(args.file)
    if err:
        print("Ошибка: %s" % err)
        return 1
    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return 0
    print("Файл: %s" % args.file)
    print("PE-заголовок: смещение 0x%X, %s" % (info["pe_offset"], "PE32+" if info["pe32plus"] else "PE32"))
    print("Машина: %s" % info["machine_name"])
    print("Подсистема: %s" % info["subsystem_name"])
    print("Точка входа: RVA 0x%X (VA 0x%X)" % (info["entry_point"], info["image_base"] + info["entry_point"]))
    print("Образ: 0x%X..0x%X" % (info["image_base"], info["image_base"] + info["image_size"]))
    print("Секций: %d" % len(info["sections"]))
    for s in info["sections"]:
        print(
            "  %-8s VA 0x%-8X raw 0x%-8X size %-8d %s"
            % (s["name"], s["virtual_address"], s["raw_offset"], s["raw_size"], s["flags"])
        )
    return 0


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

        assert entropy(b"") == 0.0
        assert entropy(b"\x00" * 1000) == 0.0
        assert entropy_blocks(tmp, block_size=512, max_blocks=1)[0][0]["high"] is False
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
    sub.add_parser("capabilities", help="Матрица поддержки Xbox Series X|S")
    p_ent = sub.add_parser(
        "entropy", help="Энтропия по блокам образа: где данные зашифрованы"
    )
    p_ent.add_argument("file")
    p_ent.add_argument(
        "--block",
        type=int,
        default=DEFAULT_BLOCK,
        help="размер блока в байтах (по умолчанию 1 МБ)",
    )
    p_pe = sub.add_parser("pe-info", help="Разбор PE-образа (секции, точка входа)")
    p_pe.add_argument("file")
    p_pe.add_argument("--json", action="store_true", help="Вывод в формате JSON")
    args = parser.parse_args()

    if args.command == "status":
        return cmd_status(args)
    if args.command == "xvd-info":
        return cmd_xvd_info(args)
    if args.command == "scan":
        return cmd_scan(args)
    if args.command == "selftest":
        return cmd_selftest(args)
    if args.command == "capabilities":
        return cmd_capabilities(args)
    if args.command == "entropy":
        return cmd_entropy(args)
    if args.command == "pe-info":
        return cmd_pe_info(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
