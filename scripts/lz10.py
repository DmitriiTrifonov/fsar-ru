"""Nintendo LZ10 (type 0x10) decompress / compress."""
import ctypes
import pathlib

_lib = None
_libpath = pathlib.Path(__file__).resolve().parent.parent / "tools" / "liblz10.dylib"
if _libpath.exists():
    _lib = ctypes.CDLL(str(_libpath))
    _lib.lz10_compress.restype = ctypes.c_long
    _lib.lz10_compress.argtypes = [ctypes.c_char_p, ctypes.c_long, ctypes.c_char_p]
    if hasattr(_lib, 'lz10_compress_opt'):
        _lib.lz10_compress_opt.restype = ctypes.c_long
        _lib.lz10_compress_opt.argtypes = [ctypes.c_char_p, ctypes.c_long, ctypes.c_char_p]


def decompress(data: bytes) -> bytes:
    if data[0] != 0x10:
        raise ValueError("not LZ10")
    size = int.from_bytes(data[1:4], "little")
    pos = 4
    out = bytearray()
    while len(out) < size:
        flags = data[pos]; pos += 1
        for bit in range(8):
            if len(out) >= size:
                break
            if flags & (0x80 >> bit):
                b1, b2 = data[pos], data[pos + 1]; pos += 2
                length = (b1 >> 4) + 3
                disp = ((b1 & 15) << 8 | b2) + 1
                for _ in range(length):
                    out.append(out[-disp])
            else:
                out.append(data[pos]); pos += 1
    return bytes(out[:size])


def compress_py(data: bytes) -> bytes:
    out = bytearray(b"\x10" + len(data).to_bytes(3, "little"))
    pos, n = 0, len(data)
    while pos < n:
        flag_pos = len(out); out.append(0); flags = 0
        for bit in range(8):
            if pos >= n:
                break
            best_len, best_disp = 0, 0
            for disp in range(1, min(pos, 4096) + 1):
                l = 0
                while l < 18 and pos + l < n and data[pos + l - disp] == data[pos + l]:
                    l += 1
                if l > best_len:
                    best_len, best_disp = l, disp
                    if l == 18:
                        break
            if best_len >= 3:
                flags |= 0x80 >> bit
                d = best_disp - 1
                out += bytes([(best_len - 3) << 4 | d >> 8, d & 255])
                pos += best_len
            else:
                out.append(data[pos]); pos += 1
        out[flag_pos] = flags
    return bytes(out)


def compress(data: bytes) -> bytes:
    """Native (C) compressor when tools/liblz10.dylib exists, otherwise pure Python."""
    if _lib is None:
        return compress_py(data)
    buf = ctypes.create_string_buffer(len(data) + len(data) // 8 + 16)
    n = _lib.lz10_compress(data, len(data), buf)
    if n < 0:
        raise ValueError("lz10_compress failed")
    return buf.raw[:n]


def compress_opt(data: bytes) -> bytes:
    """Optimal-parse LZ10 (native only), for files that must not grow past their ROM slot."""
    buf = ctypes.create_string_buffer(len(data) + len(data) // 8 + 16)
    n = _lib.lz10_compress_opt(data, len(data), buf)
    if n < 0:
        raise ValueError("lz10_compress_opt failed")
    return buf.raw[:n]
