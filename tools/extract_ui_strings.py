#!/usr/bin/env python3
"""Extract likely-UI string literals from the app HTML pages (for translation)."""
import re
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "analysis")

pat = re.compile(r"'([^'\\\n]{4,200})'|\"([^\"\\\n]{4,200})\"|`([^`\\\n]{4,300})`")
skip = re.compile(r"^[\w\-./:% #@(),+*&\[\]{}=;|<>!?$'\"\\]*$")

for fn in ("gaelanilive_page.html", "gaelanilive_remote.html"):
    s = open(os.path.join(ROOT, "src", fn), encoding="utf-8").read()
    cands = []
    for m in pat.finditer(s):
        x = next((g for g in m.groups() if g), "")
        if " " not in x:
            continue
        if not re.search(r"[A-Za-z]{3}", x):
            continue
        # drop pure code / css / urls / selectors
        if skip.match(x):
            continue
        if re.search(r"[{};=<>]|function\(|return |var |const |class=|px;|rgba|#\w{3,}", x):
            continue
        cands.append(x)
    uniq = sorted(set(cands))
    with open(os.path.join(OUT, os.path.basename(fn) + ".strings.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(uniq))
    print(fn, "->", len(uniq), "candidates")
