#!/usr/bin/env python3
"""Mechanical rebrand LiveShell -> GaelaniLIVE (paths, targets, names, versions).

Keeps ports 9050/9049. Does NOT translate UI text (handled separately).
"""
import os
import re
import shutil

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "src")

# ---- 1. rename src files ----
renames = {
    "liveshell.hpp": "gaelanilive.hpp",
    "liveshell_daemon.cpp": "gaelanilive_daemon.cpp",
    "liveshell_web.cpp": "gaelanilive_web.cpp",
    "liveshell_tile.cpp": "gaelanilive_tile.cpp",
    "liveshell_shellui.cpp": "gaelanilive_shellui.cpp",
    "liveshell_page.html": "gaelanilive_page.html",
    "liveshell_remote.html": "gaelanilive_remote.html",
}
for a, b in renames.items():
    pa, pb = os.path.join(SRC, a), os.path.join(SRC, b)
    if os.path.exists(pa):
        shutil.move(pa, pb)
        print("renamed", a, "->", b)

# tools renames
t = os.path.join(ROOT, "tools")
sa, sb = os.path.join(t, "shutdown_liveshell.bat"), os.path.join(t, "shutdown_gaelanilive.bat")
if os.path.exists(sa):
    shutil.move(sa, sb)
    print("renamed shutdown bat")

# ---- 2. ordered replacements (longest/most specific first) ----
REPL = [
    # cmake macros and filenames
    ("LIVESHELL_SHELLUI_ELF", "GAELANILIVE_SHELLUI_ELF"),
    ("LIVESHELL_PAGE_HTML", "GAELANILIVE_PAGE_HTML"),
    ("LIVESHELL_REMOTE_HTML", "GAELANILIVE_REMOTE_HTML"),
    ("LIVESHELL_ICON_PNG", "GAELANILIVE_ICON_PNG"),
    ("liveshell_shellui.elf", "gaelanilive_shellui.elf"),
    ("liveshell_page.html", "gaelanilive_page.html"),
    ("liveshell_remote.html", "gaelanilive_remote.html"),
    ("liveshell_daemon.cpp", "gaelanilive_daemon.cpp"),
    ("liveshell_web.cpp", "gaelanilive_web.cpp"),
    ("liveshell_tile.cpp", "gaelanilive_tile.cpp"),
    ("liveshell_shellui.cpp", "gaelanilive_shellui.cpp"),
    ("liveshell.hpp", "gaelanilive.hpp"),
    ("liveshell.elf", "gaelanilive.elf"),
    # paths (PS5 + tmp + usb folder name + misc)
    ("/data/LiveShell", "/data/GaelaniLIVE"),
    ("/system_tmp/liveshell", "/system_tmp/gaelanilive"),
    ("/pic0.dds.liveshell", "/pic0.dds.gaelanilive"),
    ("liveshell.log", "gaelanilive.log"),
    ("liveshell.log".upper(), "GAELANILIVE.LOG"),
    # cmake project/targets
    ("project(liveshell", "project(gaelanilive"),
    ("add_subdirectory(liveshell)", "add_subdirectory(gaelanilive)"),
    ("add_executable(liveshell_shellui", "add_executable(gaelanilive_shellui"),
    ("add_executable(liveshell ", "add_executable(gaelanilive "),
    ("add_dependencies(liveshell_shellui", "add_dependencies(gaelanilive_shellui"),
    ("add_dependencies(liveshell ", "add_dependencies(gaelanilive "),
    ("target_liveshell", "target_gaelanilive"),
    ("OUTPUT_NAME \"liveshell_shellui.elf\"", "OUTPUT_NAME \"gaelanilive_shellui.elf\""),
    ("OUTPUT_NAME \"liveshell.elf\"", "OUTPUT_NAME \"gaelanilive.elf\""),
    ("--target liveshell", "--target gaelanilive"),
    ("source/liveshell", "source/gaelanilive"),
    ("\$BUILD/bin/liveshell.elf", "$BUILD/bin/gaelanilive.elf"),
    ("\$OUT/liveshell.elf", "$OUT/gaelanilive.elf"),
    ("sha256sum \"\$BUILD/bin/liveshell.elf\"", "sha256sum \"$BUILD/bin/gaelanilive.elf\""),
    # C++ namespace and identifiers
    ("namespace liveshell", "namespace gaelanilive"),
    ("liveshell::", "gaelanilive::"),
    ("using namespace liveshell", "using namespace gaelanilive"),
    # shellui embedded marker / internal protocol keys stay as-is
    # branding
    ("LiveShell Engine", "GaelaniLIVE Engine"),
    ("LiveShell", "GaelaniLIVE"),
    ("LIVESHELL", "GAELANILIVE"),
    ("liveshell", "gaelanilive"),
]

targets = []
for sub in ("src", "tools"):
    for dirpath, _, files in os.walk(os.path.join(ROOT, sub)):
        for fn in files:
            if fn.lower().endswith((".cpp", ".hpp", ".c", ".h", ".html", ".sh", ".bat", ".txt", ".cmake")) or fn == "CMakeLists.txt":
                targets.append(os.path.join(dirpath, fn))
# root cmake? liveshell has none besides src/CMakeLists.txt

changed = []
for p in targets:
    try:
        s = open(p, encoding="utf-8").read()
    except UnicodeDecodeError:
        continue
    orig = s
    for a, b in REPL:
        s = s.replace(a, b)
    if s != orig:
        open(p, "w", encoding="utf-8", newline="\n").write(s)
        changed.append(os.path.relpath(p, ROOT))
print("changed files:")
for c in changed:
    print("  ", c)

# leftover scan
print("\nleftover 'liveshell/LiveShell' occurrences:")
for p in targets:
    s = open(p, encoding="utf-8").read()
    for i, line in enumerate(s.splitlines(), 1):
        if re.search(r"liveshell|LiveShell|LIVESHELL", line, re.I):
            print(f"  {os.path.relpath(p, ROOT)}:{i}: {line.strip()[:120]}")
