import importlib.util
import os

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "pe_parser", os.path.join(_here, "pe_parser.py")
)
pe_parser = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pe_parser)


class MemoryAccessError(ValueError):
    pass


class LoadError(ValueError):
    pass


def load_image(data):
    try:
        info = pe_parser.parse_pe(data)
    except pe_parser.PEError as e:
        raise LoadError(str(e))
    base = info["image_base"]
    size = info["image_size"]
    if size <= 0:
        raise LoadError("Нулевой размер образа")
    mem = bytearray(size)
    for sec in info["sections"]:
        if sec["raw_size"] == 0:
            continue
        off = sec["virtual_address"]
        if off + sec["raw_size"] > size:
            raise LoadError(
                "Секция %s выходит за границу образа (VA 0x%X)"
                % (sec["name"], base + off)
            )
        end = sec["raw_offset"] + sec["raw_size"]
        if end > len(data):
            raise LoadError(
                "Секция %s выходит за границу файла" % sec["name"]
            )
        mem[off : off + sec["raw_size"]] = data[
            sec["raw_offset"] : sec["raw_offset"] + sec["raw_size"]
        ]
    return {
        "info": info,
        "base": base,
        "size": size,
        "entry_va": base + info["entry_point"],
        "mem": mem,
    }


def read_mem(image, va, count):
    off = va - image["base"]
    if off < 0 or off + count > image["size"]:
        raise MemoryAccessError("Чтение вне образа: VA 0x%X" % va)
    return bytes(image["mem"][off : off + count])


def section_at(image, va):
    rva = va - image["base"]
    for sec in image["info"]["sections"]:
        if sec["virtual_address"] <= rva < sec["virtual_address"] + max(
            sec["virtual_size"], sec["raw_size"]
        ):
            return sec
    return None


def load_image_file(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        return None, str(e)
    try:
        return load_image(data), None
    except (pe_parser.PEError, LoadError) as e:
        return None, str(e)
