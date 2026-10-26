"""publish_export.py <dest-dir>: writes the PUBLIC copy of the tracked files into <dest-dir> (existing files there are overwritten, .git is kept).
What differs from the local repo (original game text must not be published):
  - text/gfx/**/*.tsv: the English column (original page text) is masked (letters -> a/A, keeping case, digits, punctuation and length class), RU column stays
  - .mcp.json, release/ (the patch goes to GitHub Releases, not to the tree) are left out
  - absolute home paths in docs are replaced by ~
Then: cd <dest-dir>; git add -A; git commit; git push."""
import os, re, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = (".mcp.json", "release/")
def mask(t):
    return "".join(("A" if c.isupper() else "a") if c.isalpha() else c for c in t)
def main(dest):
    files = subprocess.run(["git", "-c", "core.quotepath=false", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split("\n")
    n = 0
    for f in filter(None, files):
        if f.startswith(SKIP) or f == ".mcp.json": continue
        src, dst = os.path.join(ROOT, f), os.path.join(dest, f); os.makedirs(os.path.dirname(dst), exist_ok=True)
        if f.startswith("text/gfx/") and f.endswith(".tsv"):
            out = []
            for ln in open(src, encoding="utf-8").read().split("\n"):
                c = ln.split("\t")
                if len(c) >= 3 and c[0].isdigit() and not c[1].startswith("SKIP"): c[1] = mask(c[1])
                out.append("\t".join(c))
            open(dst, "w", encoding="utf-8").write("\n".join(out))
        elif f.endswith((".md", ".txt", ".py", ".sh")):
            t = open(src, encoding="utf-8").read(); t = re.sub(r"/Users/[A-Za-z0-9_]+/", "~/", t); open(dst, "w", encoding="utf-8").write(t)
        else: shutil.copyfile(src, dst)
        n += 1
    print("exported", n, "files to", dest)
if __name__ == "__main__": main(sys.argv[1])
