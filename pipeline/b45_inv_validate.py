#!/usr/bin/env python3
"""b45_inv_validate.py — B43 lesson: cross-check every model inventory against
a code-token scan of the fulltext BEFORE extraction. Reports codes found in
text but missing from the inventory (and inventory codes not found in text),
with page anchors for the missing ones."""
import json, re, sys
from collections import Counter

PARSED = "/home/z/my-project/work/pipeline_v2/parsed"
INV = "/home/z/my-project/work/pipeline_v2/inv"
STEMS = [
    "01_mba_tourism-mgmt_syllabus_2016-17",
    "02_mba_tourism-mgmt_syllabus_2017-18",
    "03_mba_tourism-mgmt_y2_model-curriculum_2019-20",
    "04_mba_tourism_syllabus_2014-15",
    "05_mba_travel-tourism_y1_syllabus_2020-21",
    "06_mba_travel-tourism_y2_syllabus_2021-22",
    "07_mba_y1_model-curriculum_2018-19",
    "08_mba_y1_scheme_2008-09",
    "09_mba_y1_scheme_2016-17",
    "10_mba_y2_model-curriculum-rev-aicte_2019-20",
]

CODE_RE = re.compile(r"\b([A-Z]{2,5})[ \-]?(\d{2,3})([A-Z]?)\b(?!\d)")
# generic token: 2-5 letters + 2-3 digits + optional single letter suffix


def norm(c):
    return re.sub(r"[^A-Z0-9]", "", c.upper())


def pages(fulltext):
    return [(m.group(1), m.group(2)) for m in re.finditer(
        r"\f?===== PAGE (\d+) =====\n(.*?)(?=\n===== PAGE \d+ =====|\Z)", fulltext, re.S)]


def scan(stem):
    fulltext = open(f"{PARSED}/{stem}.fulltext.txt").read()
    pgs = pages(fulltext)
    hits = {}  # norm -> [(page, context)]
    # common false positives to drop
    DROP = {"TM", "MBA", "AKTU", "AICTE", "MCA", "BBA", "BSC", "BTECH", "LTP", "CO", "PO",
            "MT", "ST", "UT", "L", "T", "P", "PC", "IT", "HR", "MK", "FM", "IB", "OP"}
    for pn, txt in pgs:
        for m in CODE_RE.finditer(txt):
            letters, digits, suf = m.groups()
            tok = letters + digits + suf
            if tok in DROP:
                continue
            hits.setdefault(tok, []).append((pn, txt[max(0, m.start()-45):m.end()+45].replace("\n", " ")))
    inv = json.load(open(f"{INV}/{stem}.inv.json"))
    inv_codes = {}
    for s in inv:
        c = norm(s.get("code_print", ""))
        if c:
            inv_codes.setdefault(c, s)
    print(f"== {stem}: inv {len(inv)} entries, {len(inv_codes)} codes; text-scan {len(hits)} tokens")
    missing = [c for c in hits if c not in inv_codes]
    extra = [c for c in inv_codes if c not in hits]
    if missing:
        print(f"  MISSING FROM INV ({len(missing)}):")
        for c in sorted(missing):
            pgs_seen = sorted({p for p, _ in hits[c]})[:6]
            ctx = hits[c][0][1][:90]
            print(f"    {c} pp{pgs_seen} | {ctx}")
    if extra:
        print(f"  INV NOT IN TEXT ({len(extra)}): {sorted(extra)}")
    # detail coverage: count detail entries vs detailed pages
    det = [s for s in inv if s.get("class") == "detail"]
    print(f"  detail {len(det)}: {[norm(s.get('code_print','')) or s.get('name_print','')[:10] for s in det]}")
    print(f"  scheme_only {len(inv)-len(det)}: {[(norm(s.get('code_print','')) or s.get('name_print','')[:12]) for s in inv if s.get('class')!='detail']}")


for st in STEMS:
    scan(st)
    print()
