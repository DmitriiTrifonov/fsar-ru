"""layout_lock.py --make <reference.nds>: write build/layout.json (file path -> size in the ROM the savestates were taken on).
build_rom.py pads smaller files with zeros up to these sizes (LZ10 ignores trailing bytes) so every later file keeps its offset;
savestates keep the file table of the ROM they were taken on and hang if any start offset moves."""
import sys, json, ndspy.rom

def sizes(path):
    r = ndspy.rom.NintendoDSRom.fromFile(path)
    def walk(folder, prefix=""):
        out = {}
        for i, name in enumerate(folder.files): out[prefix + name] = len(r.files[folder.firstID + i])
        for n, sub in folder.folders: out.update(walk(sub, prefix + n + "/"))
        return out
    return walk(r.filenames)

if __name__ == "__main__" and sys.argv[1] == "--make":
    m = sizes(sys.argv[2]); json.dump(m, open("build/layout.json", "w")); print(len(m), "files ->", "build/layout.json")
