"""Parser for the game's .s dialogue files: '[[ID' header line, then text lines (<R> = line break)."""
import re

LANGS = ["ue", "fr", "de", "es", "it"]


def read_s(path):
    return open(path, "rb").read().decode("utf-16")


def parse(text):
    """-> list of (id, body) preserving everything needed to rebuild."""
    parts = re.split(r"^\[\[(\S*)[ \t]*\r?\n", text, flags=re.M)
    head, rest = parts[0], parts[1:]
    return head, [(rest[i], rest[i + 1]) for i in range(0, len(rest), 2)]


def build(head, entries):
    return head + "".join(f"[[{i}\r\n{b}" for i, b in entries)
