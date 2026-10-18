#!/bin/sh
# Rebuild all four Russian fonts into patched_raw/ (run from the project root)
cd "$(dirname "$0")/.." || exit 1
python3 -I scripts/make_ru_font.py extracted/data/Chapter/Pack/Common/font.nftr patched_raw/Chapter/Pack/Common/font.nftr
for n in Savefont_Chiaro_12px_log8 katharinefont profile_font; do
  python3 -I scripts/make_ru_font.py extracted/data/2D/$n.NFTR patched_raw/2D/$n.NFTR
done
