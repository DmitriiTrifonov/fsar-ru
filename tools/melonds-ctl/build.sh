#!/bin/sh
# builds tools/melonds-ctl/melonds-ctl against ~/Developer/tools/melonDS (libcore.a must exist: see docs/emu-mcp-status.md)
set -e
M="$HOME/Developer/tools/melonDS"
cd "$(dirname "$0")"
c++ -std=c++17 -O2 -fwrapv -Wno-invalid-offsetof main.cpp -I"$M/src" -I"$M/build/src" "$M/build/src/libcore.a" "$M/build/src/teakra/src/libteakra.a" -o melonds-ctl
echo built melonds-ctl
