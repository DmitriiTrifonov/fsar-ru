"""Rebuild ROM: copy extracted/data -> build/data, recompress all text .z (.s.z/.txt.z) from decoded/, pack with ndstool."""
import sys, pathlib, shutil, subprocess
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import lz10

FORCE = "--force" in sys.argv   # recompress every text file even if unchanged (tests the compressor)
ex, dec, out = pathlib.Path("extracted"), pathlib.Path("decoded"), pathlib.Path("build")
shutil.rmtree(out / "data", ignore_errors=True)
shutil.copytree(ex / "data", out / "data")
# raw files (fonts etc.) that replace extracted/data files as-is: patched_raw/<path under data>
for rf in pathlib.Path("patched_raw").rglob("*") if pathlib.Path("patched_raw").exists() else []:
    if rf.is_file():
        shutil.copyfile(rf, out / "data" / rf.relative_to("patched_raw"))
n = kept = 0
for f in (out / "data").rglob("*.z"):
    if f.name.endswith((".s.z", ".txt.z")):
        rel = f.relative_to(out / "data").with_suffix("")
        patched = pathlib.Path("patched") / rel
        raw = (patched if patched.exists() else dec / rel).read_bytes()
        if not FORCE and raw == lz10.decompress(f.read_bytes()):
            kept += 1          # unchanged: keep the original .z bytes
            continue
        f.write_bytes(lz10.compress(raw)); n += 1
print("recompressed", n, "kept original", kept)
lock = pathlib.Path("build/layout.json")      # layout lock: see scripts/layout_lock.py
if lock.exists():
    import json
    want = json.loads(lock.read_text()); padded = grew = 0
    for f in (out / "data").rglob("*"):
        if not f.is_file(): continue
        rel = f.relative_to(out / "data").as_posix(); sz = f.stat().st_size
        if rel in want and sz < want[rel]:
            f.write_bytes(f.read_bytes() + bytes(want[rel] - sz)); padded += 1
        elif rel in want and sz > want[rel]:
            print("WARNING: file grew past its slot (later files shift, old savestates break):", rel, sz, ">", want[rel]); grew += 1
    print("layout lock: padded", padded, "grew", grew)
outarg = [a for a in sys.argv[1:] if a.startswith("--out=")]
rom = pathlib.Path(outarg[0][6:]) if outarg else out / "fsar-test.nds"   # --out=build/other.nds keeps the ROM that is running in the emulator untouched
subprocess.run(["tools/ndstool/ndstool", "-c", str(rom), "-9", str(ex / "arm9.bin"), "-7", str(ex / "arm7.bin"),
                "-y9", str(ex / "y9.bin"), "-y7", str(ex / "y7.bin"), "-d", str(out / "data"),
                "-y", str(ex / "overlay"), "-t", str(ex / "banner.bin"), "-h", str(ex / "header.bin")], check=True)
print(rom, rom.stat().st_size)
