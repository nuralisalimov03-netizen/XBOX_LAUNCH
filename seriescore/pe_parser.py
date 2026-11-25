import struct

MACHINE_NAMES = {
    0x14C: "x86",
    0x8664: "x86-64",
    0xAA64: "ARM64",
    0x1C0: "ARM",
}

SUBSYSTEM_NAMES = {
    2: "Windows GUI",
    3: "Windows console",
    14: "Xbox",
}

OPT_PE32PLUS = 0x20B
OPT_PE32 = 0x10B

SECTION_CHARS = [
    (0x00000020, "CODE"),
    (0x00000040, "INITIALIZED_DATA"),
    (0x00000080, "UNINITIALIZED_DATA"),
    (0x02000000, "DISCARDABLE"),
    (0x04000000, "NOT_CACHED"),
    (0x10000000, "SHARED"),
    (0x20000000, "EXECUTE"),
    (0x40000000, "READ"),
    (0x80000000, "WRITE"),
]

DOS_HEADER_SIZE = 0x40
COFF_SIZE = 20
SECTION_ENTRY_SIZE = 40


class PEError(ValueError):
    pass


def _need(data, size, what):
    if len(data) < size:
        raise PEError("Файл обрезан: не хватает %s" % what)


def _parse_section_flags(value):
    flags = [name for mask, name in SECTION_CHARS if value & mask]
    return "+".join(flags) if flags else "-"


def parse_pe(data):
    _need(data, DOS_HEADER_SIZE, "заголовка DOS")
    if data[:2] != b"MZ":
        raise PEError("Не PE-файл: нет сигнатуры MZ")
    (pe_off,) = struct.unpack_from("<I", data, 0x3C)
    _need(data, pe_off + 4 + COFF_SIZE, "заголовка PE")
    if data[pe_off : pe_off + 4] != b"PE\x00\x00":
        raise PEError("Не PE-файл: нет сигнатуры PE у смещения 0x%X" % pe_off)

    coff = pe_off + 4
    machine, n_sections, _ts, _ptr, _nsym, opt_size, chars = struct.unpack_from(
        "<HHIIIHH", data, coff
    )
    opt = coff + COFF_SIZE
    _need(data, opt + 2, "optional header")
    (opt_magic,) = struct.unpack_from("<H", data, opt)
    if opt_magic == OPT_PE32PLUS:
        pe32plus = True
        _need(data, opt + 32, "optional header PE32+")
        entry, base_code = struct.unpack_from("<II", data, opt + 16)
        (image_base,) = struct.unpack_from("<Q", data, opt + 24)
        (image_size,) = struct.unpack_from("<I", data, opt + 56)
    elif opt_magic == OPT_PE32:
        pe32plus = False
        _need(data, opt + 32, "optional header PE32")
        entry, base_code, _base_data = struct.unpack_from("<III", data, opt + 16)
        (image_base,) = struct.unpack_from("<I", data, opt + 28)
        (image_size,) = struct.unpack_from("<I", data, opt + 56)
    else:
        raise PEError("Неизвестная сигнатура optional header: 0x%X" % opt_magic)

    section_off = opt + opt_size
    _need(data, section_off + n_sections * SECTION_ENTRY_SIZE, "таблицы секций")
    sections = []
    for i in range(n_sections):
        base = section_off + i * SECTION_ENTRY_SIZE
        raw_name = data[base : base + 8].rstrip(b"\x00")
        name = raw_name.decode("ascii", errors="replace")
        v_size, v_addr, raw_size, raw_off = struct.unpack_from("<IIII", data, base + 8)
        (s_chars,) = struct.unpack_from("<I", data, base + 36)
        sections.append(
            {
                "name": name,
                "virtual_size": v_size,
                "virtual_address": v_addr,
                "raw_size": raw_size,
                "raw_offset": raw_off,
                "characteristics": s_chars,
                "flags": _parse_section_flags(s_chars),
            }
        )

    return {
        "pe_offset": pe_off,
        "machine": machine,
        "machine_name": MACHINE_NAMES.get(machine, "0x%04X" % machine),
        "subsystem": None,
        "subsystem_name": None,
        "pe32plus": pe32plus,
        "entry_point": entry,
        "base_of_code": base_code,
        "image_base": image_base,
        "image_size": image_size,
        "sections": sections,
        "coff_characteristics": chars,
    }


def read_subsystem(data, info):
    opt = info["pe_offset"] + 4 + COFF_SIZE
    _need(data, opt + 72, "subsystem")
    (subsystem,) = struct.unpack_from("<H", data, opt + 68)
    return subsystem


def parse_pe_file(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        return None, str(e)
    try:
        info = parse_pe(data)
    except PEError as e:
        return None, str(e)
    try:
        subsystem = read_subsystem(data, info)
        info["subsystem"] = subsystem
        info["subsystem_name"] = SUBSYSTEM_NAMES.get(subsystem, "0x%X" % subsystem)
    except PEError:
        pass
    return info, None


def build_minimal_pe():
    opt_size = 240
    pe_off = 0x80
    buf = bytearray(0x600)
    buf[0:2] = b"MZ"
    struct.pack_into("<I", buf, 0x3C, pe_off)
    buf[pe_off : pe_off + 4] = b"PE\x00\x00"
    struct.pack_into(
        "<HHIIIHH",
        buf,
        pe_off + 4,
        0x8664,
        1,
        0,
        0,
        0,
        opt_size,
        0x0022,
    )
    opt = pe_off + 4 + COFF_SIZE
    struct.pack_into("<H", buf, opt, OPT_PE32PLUS)
    struct.pack_into("<I", buf, opt + 16, 0x1000)
    struct.pack_into("<I", buf, opt + 20, 0x1000)
    struct.pack_into("<Q", buf, opt + 24, 0x140000000)
    struct.pack_into("<I", buf, opt + 56, 0x2000)
    sec = opt + opt_size
    buf[sec : sec + 8] = b".text".ljust(8, b"\x00")
    struct.pack_into("<IIII", buf, sec + 8, 0x100, 0x1000, 0x200, 0x400)
    struct.pack_into("<I", buf, sec + 36, 0x60000020)
    buf[0x400:0x404] = b"SCX1"
    return bytes(buf)
