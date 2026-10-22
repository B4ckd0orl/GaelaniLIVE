#!/usr/bin/env python3
"""Full offline analysis of the LiveShell ELF (PS5 payload, x86-64).

Produces: header/section report, dynsym+reloc import map, extracted embedded
assets (PNG, HTML pages), a categorized strings file and a complete annotated
disassembly of .text (Capstone). Read-only with respect to the input ELF.
"""
import json
import os
import re
import struct
import sys

import capstone

ELF = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\SysVoid\Desktop\PS5 PAYLOAD\LIVEPS5\liveshell.elf"
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

ANALYSIS = os.path.join(OUT, "analysis")
DISASM = os.path.join(OUT, "disasm")
os.makedirs(ANALYSIS, exist_ok=True)
os.makedirs(os.path.join(ANALYSIS, "assets"), exist_ok=True)
os.makedirs(DISASM, exist_ok=True)

d = open(ELF, "rb").read()
report = []
log = lambda s: (report.append(s), print(s))

# ---- ELF header ----
assert d[:4] == b"\x7fELF" and d[4] == 2 and d[5] == 1
e_type, e_machine, e_version = struct.unpack_from("<HHI", d, 16)
e_entry, e_phoff, e_shoff = struct.unpack_from("<QQQ", d, 24)
e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHHHHH", d, 52)
log("== ELF header ==")
log(f"entry=0x{e_entry:x} type={e_type} (DYN/PIE) machine={e_machine} (x86-64) phnum={e_phnum} shnum={e_shnum}")

# ---- sections ----
shs = []
for i in range(e_shnum):
    o = e_shoff + i * e_shentsize
    name, typ, flags, addr, off, size, link, info, align, entsize = struct.unpack_from("<IIQQQQIIQQ", d, o)
    shs.append(dict(name=name, typ=typ, flags=flags, addr=addr, off=off, size=size, link=link, info=info, entsize=entsize))
strtab = shs[e_shstrndx]
def sname(idx):
    o = strtab["off"] + idx
    return d[o:d.index(b"\0", o)].decode("ascii", "replace")
log("\n== Sections ==")
for s in shs:
    s["nm"] = sname(s["name"])
    log(f"{s['nm']:<24} type={s['typ']:<3} addr=0x{s['addr']:08x} off={s['off']:<8} size={s['size']:<8} link={s['link']}")

# ---- program headers ----
log("\n== Program headers ==")
for i in range(e_phnum):
    o = e_phoff + i * e_phentsize
    p_type, p_flags, p_off, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = struct.unpack_from("<IIQQQQQQ", d, o)
    log(f"phdr{i}: type={p_type} flags={p_flags} off={p_off} vaddr=0x{p_vaddr:x} filesz={p_filesz} memsz={p_memsz}")

# ---- dynsym + dynstr + rela.dyn ----
dynsym = next(s for s in shs if s["nm"] == ".dynsym")
dynstr = next(s for s in shs if s["nm"] == ".dynstr")
rela = next(s for s in shs if s["nm"] == ".rela.dyn")
def cstr(o):
    return d[o:d.index(b"\0", o)].decode("utf-8", "replace")
symbols = {}
for i in range(0, dynsym["size"], 24):
    st_name, st_info, st_other, st_shndx, st_value, st_size = struct.unpack_from("<IBBHQQ", d, dynsym["off"] + i)
    nm = cstr(dynstr["off"] + st_name)
    if nm:
        symbols[st_value] = (nm, st_size, st_info)
imports = []  # (offset_addr, symbol)
for i in range(0, rela["size"], 24):
    r_offset, r_info, r_addend = struct.unpack_from("<QQq", d, rela["off"] + i)
    r_sym = r_info >> 32
    st_name = struct.unpack_from("<I", d, dynsym["off"] + r_sym * 24)[0]
    imports.append((r_offset, cstr(dynstr["off"] + st_name)))
log(f"\ndynsym entries: {len(symbols)}  rela.dyn entries: {len(imports)}")
with open(os.path.join(ANALYSIS, "imports_relocs.txt"), "w", encoding="utf-8") as f:
    for addr, nm in sorted(imports):
        f.write(f"0x{addr:08x}  {nm}\n")
with open(os.path.join(ANALYSIS, "dynsym.txt"), "w", encoding="utf-8") as f:
    for v in sorted(symbols):
        nm, sz, info = symbols[v]
        f.write(f"0x{v:08x} size={sz:<6} bind={info>>4} type={info&0xf} {nm}\n")

# ---- embedded assets: PNG + HTML ----
assets = os.path.join(ANALYSIS, "assets")
png_i = d.find(b"\x89PNG\r\n\x1a\n")
png_end = d.find(b"IEND\xaeB`\x82", png_i) + 8 if png_i >= 0 else -1
if png_i >= 0:
    open(os.path.join(assets, "embedded_icon0.png"), "wb").write(d[png_i:png_end])
    log(f"embedded PNG: 0x{png_i:x}-0x{png_end:x} ({png_end-png_i} bytes) -> assets/embedded_icon0.png")
for m in re.finditer(rb"<!DOCTYPE html[^\0]{0,200}|<html[ >][\s\S]{0,200}?</html>", d, re.I):
    pass
# pages are full html docs; find <html ...> ... </html>
for idx, m in enumerate(re.finditer(rb"<html[ \r\n][\s\S]*?</html>", d, re.I)):
    start, end = m.start(), m.end()
    if end - start < 10000:
        continue
    path = os.path.join(assets, f"embedded_page{idx}.html")
    open(path, "wb").write(d[start:end])
    log(f"embedded HTML page{idx}: 0x{start:x}-0x{end:x} ({end-start} bytes)")

# ---- strings categorized ----
strs = [m.group(0).decode("ascii", "replace") for m in re.finditer(rb"[ -~]{5,}", d)]
cats = {
    "paths": lambda s: s.startswith("/data/") or s.startswith("/system_tmp/") or s.startswith("/mnt") or s.startswith("/usb") or ".elf" in s and "/" in s,
    "versions": lambda s: re.search(r"v\d+\.\d+|1\.5\.0|LiveShell Engine", s),
    "urls": lambda s: "http" in s.lower() or "github" in s.lower(),
    "api": lambda s: s.startswith("/api/") or s.startswith("GET ") or s.startswith("POST "),
    "sce": lambda s: s.startswith("sce") or s.startswith("Sce"),
}
with open(os.path.join(ANALYSIS, "strings_categorized.txt"), "w", encoding="utf-8") as f:
    for cat, pred in cats.items():
        f.write(f"== {cat} ==\n")
        for s in sorted(set(x for x in strs if pred(x))):
            f.write(f"  {s[:300]}\n")
    f.write("== all_strings ==\n")
    for s in sorted(set(strs)):
        f.write(f"  {s[:300]}\n")

# ---- disassembly of .text ----
text = next(s for s in shs if s["nm"] == ".text")
code = d[text["off"]:text["off"] + text["size"]]
base = text["addr"]
rela_map = dict(imports)
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
md.detail = False
out = os.path.join(DISASM, "liveshell_full.asm")
log(f"\ndisassembling .text 0x{base:x}+{text['size']} ...")
n_insns = 0
with open(out, "w", encoding="utf-8", errors="replace") as f:
    f.write(f"; Full disassembly of {os.path.basename(ELF)} .text (vaddr 0x{base:x}, {text['size']} bytes)\n")
    f.write(f"; functions from dynsym: {len(symbols)}; external relocs: {len(imports)}\n\n")
    func_addrs = sorted(v for v in symbols if base <= v < base + text["size"])
    for i, fa in enumerate(func_addrs):
        nm, sz, _ = symbols[fa]
        end = fa + sz if sz else (func_addrs[i + 1] if i + 1 < len(func_addrs) else base + text["size"])
        f.write(f"\n; ==== FUNCTION {nm} @ 0x{fa:x} size={sz} ====\n")
        off = fa - base
        chunk = code[off:off + (end - fa)]
        for insn in md.disasm(chunk, fa):
            n_insns += 1
            note = ""
            if insn.mnemonic == "call":
                m2 = re.search(r"\[rip(?:\+0x[0-9a-f]+)?(?:-0x[0-9a-f]+)?\]", insn.op_str)
                if "rip" in insn.op_str:
                    mm = re.search(r"([+-])0x([0-9a-f]+)", insn.op_str)
                    disp = 0
                    if mm:
                        disp = int(mm.group(2), 16) * (1 if mm.group(1) == "+" else -1)
                    tgt = insn.address + insn.size + disp
                    if tgt in rela_map:
                        note = f"  ; -> {rela_map[tgt]}"
                    elif tgt in symbols:
                        note = f"  ; -> {symbols[tgt][0]}"
            f.write(f"0x{insn.address:08x}:  {insn.mnemonic:<8} {insn.op_str}{note}\n")
        # leftovers between symbols (thunks etc.)
    # sweep any bytes not covered (align gaps / non-symbol code)
    log(f"instructions written: {n_insns}")
    f.write("\n; ---- linear sweep remainder (bytes not inside dynsym functions) ----\n")
    covered = set()
    for i, fa in enumerate(func_addrs):
        nm, sz, _ = symbols[fa]
        end = fa + sz if sz else (func_addrs[i + 1] if i + 1 < len(func_addrs) else base + text["size"])
        covered.update(range(fa, end))
    pos = base
    end_addr = base + text["size"]
    while pos < end_addr:
        if pos in covered:
            pos += 1
            continue
        # find next covered
        nxt = pos
        while nxt < end_addr and nxt not in covered:
            nxt += 1
        chunk = code[pos - base:nxt - base]
        for insn in md.disasm(chunk, pos):
            n_insns += 1
            f.write(f"0x{insn.address:08x}:  {insn.mnemonic:<8} {insn.op_str}\n")
        pos = nxt
    log(f"total instructions: {n_insns}")

with open(os.path.join(ANALYSIS, "elf_report.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(report))
print("done ->", ANALYSIS, DISASM)
