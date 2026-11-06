#!/usr/bin/env python3
"""b45_probe_flags.py — evidence probe for every B45 flag: draft subject vs
candidate registry rows (T0 owner, name-matches, fuzzy targets) with unit-I
snippets, codes, sessions. Zero-guess adjudication input."""
import csv, json, re, sys

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"


def norm_code(c):
    return re.sub(r"[^A-Z0-9]", "", (c or "").upper())


def norm_name(n):
    n = re.sub(r"[^a-z0-9]+", " ", (n or "").lower()).strip()
    return re.sub(r"\s+", " ", n)


rows = list(csv.DictReader(open(CSV_PATH)))
by_sid = {r["subject_id"]: r for r in rows}


def row_owned(r):
    toks = set()
    for f in ("primary_code", "all_codes", "code_history_all"):
        for c in (r.get(f, "") or "").split(";"):
            c = norm_code(c)
            if c:
                toks.add(c)
    return toks


def u1(r):
    return re.sub(r"\s+", " ", (r.get("unit1_text", "") or ""))[:180]


def show(sid, mark=""):
    r = by_sid.get(sid)
    if not r:
        print(f"    {mark} MISSING ROW {sid}")
        return
    print(f"    {mark} {sid} [{r.get('subject_name')}] codes={r.get('primary_code')};{r.get('all_codes')[:60]} sess={r.get('effective_session_latest')} u1={u1(r)[:130]}")


FLAGS = [l.strip() for l in open("/tmp/dry45.txt") if l.startswith("FLAG|") and "::" in l.split("|")[1]]
for fl in FLAGS:
    parts = fl.split("|")
    key = parts[1]
    stem, idx, _ = key.split("::")
    d = json.load(open(f"{DRAFTS}/{stem}.draft.json"))
    s = d["subjects"][int(idx)]
    print(f"== FLAG {key} [{parts[2]}]")
    print(f"    DRAFT [{s.get('name')}] codes={s.get('codes')} sess={d['session']} u1={re.sub(chr(10),' ',(list((s.get('units') or {}).values()) or [''])[0])[:130]}")
    # tier-0 code owners
    dcodes = {norm_code(c) for c in (s.get("codes") or [])}
    for r in rows:
        if r.get("row_kind") != "subject" or r.get("course_name") != "MBA":
            continue
        if dcodes & row_owned(r):
            show(r["subject_id"], "T0owner:")
    # name matches
    nn = norm_name(s.get("name"))
    for r in rows:
        if r.get("row_kind") != "subject" or r.get("course_name") != "MBA":
            continue
        if norm_name(r.get("subject_name")) == nn:
            show(r["subject_id"], "NAMEmatch:")
    print()

# ---- fuzzy top-3 for TIER2/TIE flags ----
from difflib import SequenceMatcher

def tsr(a, b):
    A = set(re.findall(r"[a-z0-9]+", (a or "").lower()))
    B = set(re.findall(r"[a-z0-9]+", (b or "").lower()))
    if not A or not B:
        return 0
    seq = SequenceMatcher(None, " ".join(sorted(A)), " ".join(sorted(B))).ratio()
    return round(seq * 100)

print("\n===== FUZZY CANDIDATES =====")
import glob, os
for fl in FLAGS:
    parts = fl.split("|")
    key = parts[1]
    if "TIER2 fuzzy" not in fl and "TIE" not in parts[2]:
        continue
    stem, idx, _ = key.split("::")
    d = json.load(open(f"{DRAFTS}/{stem}.draft.json"))
    s = d["subjects"][int(idx)]
    print(f"== FUZZY {key} [{s.get('name')}]")
    cands = []
    for r in rows:
        if r.get("row_kind") != "subject" or r.get("course_name") != "MBA":
            continue
        sc = tsr(s.get("name"), r.get("subject_name"))
        if sc >= 80:
            cands.append((sc, r))
    for sc, r in sorted(cands, reverse=True)[:3]:
        show(r["subject_id"], f"fz{sc}:")
    print()
