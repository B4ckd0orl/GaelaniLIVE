#!/usr/bin/env python3
"""Extract human-readable English phrase runs (UI copy) from the HTML pages."""
import re
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "analysis")

phrase = re.compile(r"\b[A-Z][A-Za-z0-9'’]*(?:[ \-][A-Za-z0-9'’()%/.,!?+&]+){1,10}")
single = re.compile(r"\b[a-z][a-z]+(?:[ \-][a-z'’()%/.,!?+]{2,}){2,12}\b")  # lowercase sentences

for fn in ("gaelanilive_page.html", "gaelanilive_remote.html"):
    s = open(os.path.join(ROOT, "src", fn), encoding="utf-8").read()
    found = set()
    for m in phrase.finditer(s):
        t = m.group(0).strip(" .,:;!?")
        if len(t.split()) >= 2:
            found.add(t)
    for m in single.finditer(s):
        t = m.group(0).strip(" .,:;!?")
        if len(t.split()) >= 3:
            found.add(t)
    path = os.path.join(OUT, fn + ".phrases.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(found)))
    print(fn, len(found), "->", path)
