#!/bin/sh
# Builds tools/liblz10.dylib (used by scripts/lz10.py via ctypes; falls back to pure Python if missing)
cd "$(dirname "$0")/.." && clang -O2 -dynamiclib -o tools/liblz10.dylib scripts/lz10c.c
