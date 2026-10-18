"""make_list_state.py <rom-tag> <slot:number> ...: copies slot 5 of build/<rom-tag>.ml5 into the given slots with the LostList number (ARM9 0x02078638) replaced.
e.g. make_list_state.py fsar-gfx15 6:3 7:4 8:6"""
import struct, sys
tag = sys.argv[1]; base = 0x01FFFFDC; src = open(f"build/{tag}.ml5", "rb").read()
for a in sys.argv[2:]:
    slot, n = map(int, a.split(":")); s = bytearray(src); struct.pack_into("<I", s, 0x2078638 - base, n)
    open(f"build/{tag}.ml{slot}", "wb").write(s); print(f"slot {slot} = list {n}")
