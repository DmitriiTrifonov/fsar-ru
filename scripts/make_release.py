"""make_release.py: build the patched ROM (build/fsar-ru.nds), make release/fsar-ru.xdelta against the original ROM and verify it by applying it.
Needs xdelta3 (brew install xdelta). Run only on the user's command: it rebuilds the ROM. The ROM itself is never put into git or release/."""
import hashlib, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(ROOT, "roms", "Flower, Sun and Rain - Murder and Mystery in Paradise (Europe) (En,Fr,De,Es,It).nds")
NEW = os.path.join(ROOT, "build", "fsar-ru.nds"); PATCH = os.path.join(ROOT, "release", "fsar-ru.xdelta"); CHECK = os.path.join(ROOT, "build", "fsar-ru-check.nds")

def sha1(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def run(*a): print("$", " ".join(a)); subprocess.run(a, check=True, cwd=ROOT)

if __name__ == "__main__":
    run(sys.executable, "scripts/build_rom.py", "--out=build/fsar-ru.nds")
    os.makedirs(os.path.dirname(PATCH), exist_ok=True)
    if os.path.exists(PATCH): os.remove(PATCH)
    run("xdelta3", "-e", "-9", "-s", ORIG, NEW, PATCH)
    if os.path.exists(CHECK): os.remove(CHECK)
    run("xdelta3", "-d", "-s", ORIG, PATCH, CHECK)
    ok = sha1(NEW) == sha1(CHECK); print("patch applies to the original and reproduces the ROM:", ok)
    info = f"original  SHA-1 {sha1(ORIG)}\npatched   SHA-1 {sha1(NEW)}\npatch     {os.path.getsize(PATCH)} bytes\n"
    open(os.path.join(ROOT, "release", "CHECKSUMS.txt"), "w").write(info); print(info)
    sys.exit(0 if ok else 1)
