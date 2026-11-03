#!/usr/bin/env python3
"""B04-repair — surgical field-level repair of the published registry (GitHub
189ba64), propagating ONLY the session's post-commit evidence repairs:

R1. 2019-20 doc (draft 06): unit texts embedded the printed lecture-count cell
    ("10 Hours ...") at the unit-row start — 248 units stripped into the
    CSV-established lectures_per_unit dict format (B02 BPharm precedent).
    The 18:39 UTC commit pre-dated the cleanup, so 66 unitN_text cells still
    carry the prefix and their lectures_per_unit is empty.
R2. BP708T Bio-similars: units I-V re-transcribed from PAGE IMAGES (printed
    pp.265-266; text layer drops line-initial bullet words) — committed row
    still holds the fragmentary text-layer copy.
R3. BP106RMT Remedial Mathematics unit1: limit formula completed from PAGE
    IMAGE (printed p.27) — committed row holds the bracket annotation.
R4. evidence flags added this session for the six 2019-20 training slots,
    BP611P (Practical) and RPH309P are appended to the matching rows' notes.

Matching discipline (never guess): a draft subject matches a row ONLY if
  (a) the draft's sha16 appears in the row's source_syllabus citation chain,
  (b) normalized subject name equals the draft name,
  (c) at least one of the row's codes (primary/all) is in the draft codes,
  (d) row course_name == draft course (§1b).
Ambiguous match -> hard error, no write. Deltas limited to unit1..5_text,
lectures_per_unit, notes. Gates G1/G2/G3/G6 (imported from merge_draft) run on
the repaired row set before anything is written.
"""
import csv, json, re, sys, hashlib, shutil, os
from datetime import datetime

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import merge_draft as M

CSV_PATH = M.CSV_PATH
BASE = M.BASE
DRAFTS = [
    "01_bca_y3_syllabus_2026-27", "02_bpharm_ordinances_2019-20",
    "03_bpharm_regulations-ordinances_2026-27", "04_bpharm_scheme-syllabus_2026-27",
    "05_bpharm_y1-2_syllabus_2013-14", "06_bpharm_y1-4_syllabus_2019-20",
    "07_bpharm_y1_scheme_2016-17", "08_bpharm_y1_syllabus_2017-18",
    "09_bpharm_y2_scheme-syllabus_2017-18", "10_bpharm_y2_scheme-syllabus_2017-18_2",
]

rows = list(csv.DictReader(open(CSV_PATH)))
header = list(rows[0].keys())

def norm_name(s):
    return M.norm_name(s or "")

def row_codes(r):
    out = set()
    for f in ("primary_code", "all_codes"):
        for c in re.split(r"[;,]", r.get(f, "") or ""):
            c = M.norm_code(c.strip())
            if c:
                out.add(c)
    for m in M.CODE_RE.finditer(r.get("k_era_pool_codes", "") or ""):
        out.add(m.group(1) + m.group(2) + (m.group(3) or ""))
    return out

REPAIR_NOTE = ("B04-repair (2026-10-29): unit texts re-normalized against the surviving draft after "
               "page-image verification — printed lecture-count cells ('N Hours') moved from unitN_text "
               "to lectures_per_unit (2019-20 print layout: count at unit-row start); BP708T units I-V "
               "re-transcribed from PAGE IMAGE pp.265-266 and BP106RMT unit1 limit formula completed from "
               "PAGE IMAGE p.27 per RULES §6 (text layer drops bullet line-initial words / garbles the "
               "fraction). No names, codes, credits or marks changed.")

plan = []
touched_ids = set()
for stem in DRAFTS:
    dd = json.load(open(f"{M.BASE}/drafts/{stem}.draft.json"))
    sha = dd.get("sha16", "")
    dcourse = dd.get("course", "")
    for idx, s in enumerate(dd.get("subjects", [])):
        units = s.get("units") or {}
        if not isinstance(units, dict):
            continue
        dname = s.get("name", "")
        if not dname:
            continue
        dcodes = {M.norm_code(str(c)) for c in (s.get("codes") or []) if str(c).strip()}
        # candidate rows
        cands = []
        for r in rows:
            if r.get("row_kind") != "subject":
                continue
            if r.get("course_name", "") != dcourse:
                continue
            if sha not in str(r.get("source_syllabus", "")):
                continue
            if norm_name(r.get("subject_name", "")) != norm_name(dname):
                continue
            if not (dcodes & row_codes(r)):
                continue
            cands.append(r)
        if len(cands) > 1:
            print(f"AMBIGUOUS {stem}::{idx} {dname!r} codes={sorted(dcodes)} -> "
                  f"{[c['subject_id'] for c in cands]}"); sys.exit(2)
        if not cands:
            continue
        r = cands[0]
        deltas = {}
        for n in range(1, 6):
            f = f"unit{n}_text"
            newv = str(units.get(str(n), "") or "")
            oldv = r.get(f, "") or ""
            if newv and newv != oldv:
                deltas[f] = (oldv, newv)
        new_lpu = str(s.get("lectures_per_unit") or "")
        old_lpu = r.get("lectures_per_unit", "") or ""
        if new_lpu and new_lpu != old_lpu:
            deltas["lectures_per_unit"] = (old_lpu, new_lpu)
        note_adds = []
        dflags = [str(x) for x in (s.get("flags") or [])]
        existing_notes = r.get("notes", "") or ""
        for fl in dflags:
            tok = fl.split(":")[0].strip()
            if tok and tok not in existing_notes and tok in (
                    "detailed_syllabus_not_printed", "experiments_only_no_units"):
                note_adds.append(fl)
        if note_adds:
            deltas["notes"] = (existing_notes, (existing_notes + (" | " if existing_notes else "") + "flags: " + ", ".join(note_adds))[:400])
        if deltas:
            plan.append({"stem": stem, "idx": idx, "sid": r["subject_id"], "name": dname,
                         "codes": sorted(dcodes), "deltas": {k: v for k, v in deltas.items()}})

print(f"REPAIR PLAN: {len(plan)} rows")
for p in plan:
    ds = p["deltas"]
    kind = ",".join(ds.keys())
    preview = ""
    if "unit1_text" in ds:
        preview = " u1: " + repr(ds["unit1_text"][1][:60]) + " <- " + repr(ds["unit1_text"][0][:60])
    print(f"  {p['stem']}::{p['idx']:02d} {p['sid']} ({p['name'][:40]}) [{kind}]{preview}")

# APPLY
for p in plan:
    r = next(x for x in rows if x["subject_id"] == p["sid"])
    for f, (oldv, newv) in p["deltas"].items():
        r[f] = newv
    # provenance note (idempotent)
    if REPAIR_NOTE.split(":")[0] not in (r.get("change_note_vs_previous", "") or ""):
        prev = r.get("change_note_vs_previous", "") or ""
        r["change_note_vs_previous"] = (prev + (" | " if prev else "") + REPAIR_NOTE)[:900]
    touched_ids.add(r["subject_id"])

# GATES on the repaired row set
g1 = M.gate_g1(header)
g2, ncodes = M.gate_g2(rows)
g3 = M.gate_g3(rows)
g6, checks = M.gate_g6(rows, touched_ids, f"{BASE}/parsed")
print(f"\nGATES: G1={g1} G2={g2} (codes={ncodes}) G3={g3} G6={g6} (spot-checks={checks})")
if not (g1 and g2 and g3 and g6):
    print("GATE FAILURE — no write"); sys.exit(3)

ts = datetime.utcnow().strftime("%Y-%m-%dT%H%M%Sp0000")
bkp = f"{BASE}/backup/pre_repair_{ts}.csv"
shutil.copy2(CSV_PATH, bkp)
with open(CSV_PATH, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=header)
    w.writeheader()
    w.writerows(rows)
md5 = hashlib.md5(open(CSV_PATH, "rb").read()).hexdigest()
print(f"\nWROTE {CSV_PATH}")
print(f"backup: {bkp}")
print(f"rows: {len(rows)} | md5: {md5} | repaired: {len(touched_ids)}")
json.dump({"ts": ts, "mode": "repair", "repaired": len(touched_ids), "rows_after": len(rows),
           "md5": md5, "backup": bkp, "repair_ids": sorted(touched_ids)},
          open(f"{BASE}/last_repair.json", "w"), indent=1)
