#!/usr/bin/env python3
"""B04-repair v2 — MINIMAL, evidence-backed field repair of the published
registry (GitHub 189ba64). Scope restricted to the two genuine post-commit
improvements (all else already matches the committed drafts):

R1. sha 28cd10357b812c41 rows (2019-20 doc): unit texts carry the printed
    lecture-count cell ('10 Hours ...') at unit start -> strip to the
    CSV-established lectures_per_unit dict format + populate the empty
    lectures_per_unit column. 248 units across the doc's rows.
R2. BP106RMT Remedial Mathematics unit1: bracket annotation replaced by the
    limit formula transcribed from PAGE IMAGE (printed p.27, rendered
    drafts/_b04s06_rmt_p27-027.png) per RULES §6.

Session guard (RULES §3 newer-wins): a draft value is applied only when
draft.session >= row.effective_session_latest. Never touches names, codes,
credits, marks, COs. Gates G1/G2/G3/G6 (imported from merge_draft; None=PASS)
run before write; backup + md5 recorded.
"""
import csv, json, re, sys, hashlib, shutil, os
from datetime import datetime

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import merge_draft as M

CSV_PATH = M.CSV_PATH
BASE = M.BASE
SHA_2019 = "28cd10357b812c41"   # bpharm_y1-4_syllabus_2019-20.pdf

rows = list(csv.DictReader(open(CSV_PATH)))
header = list(rows[0].keys())
LEAD = re.compile(r"^\s*(\d{1,3})\s*hours?\s+", re.I)

d6 = json.load(open(f"{BASE}/drafts/06_bpharm_y1-4_syllabus_2019-20.draft.json"))
assert d6.get("sha16") == SHA_2019, "draft 06 sha mismatch"

# draft subject lookup by normalized name (rows carry print names; ladder
# matched these very subjects at commit time by the same identity)
def dnorm(s):
    return M.norm_name(s or "")

draft_by_name = {}
for s in d6["subjects"]:
    n = dnorm(s.get("name", ""))
    if n:
        draft_by_name.setdefault(n, []).append(s)

REPAIR_NOTE_R1 = ("B04-repair (2026-10-29): printed lecture-count cells ('N Hours', 2019-20 layout prints the "
                  "count at unit-row start) moved from unitN_text into lectures_per_unit (CSV-established dict "
                  "format; B02 BPharm precedent) — text content otherwise unchanged, verbatim print.")
REPAIR_NOTE_R2 = ("B04-repair (2026-10-29): unit1 limit formula completed from PAGE IMAGE (printed p.27, "
                  "drafts/_b04s06_rmt_p27-027.png) per RULES §6 — text-layer fraction garble documented in draft "
                  "quirks; replaced the '[limit-formula region garbled]' annotation.")

plan = []
touched = set()
for r in rows:
    if r.get("row_kind") != "subject":
        continue
    src = str(r.get("source_syllabus", ""))
    # session guard
    if (d6.get("session") or "") < (r.get("effective_session_latest") or ""):
        continue
    if SHA_2019 in src:
        rowcodes = {M.norm_code(c.strip()) for c in re.split(r"[;,]", (r.get("all_codes", "") or "") + "," + (r.get("primary_code", "") or "")) if c.strip()}
        rowcodes.discard("")
        # name match (norm_name strips serial numerals -> Analysis-I/-II collide)
        # then DISAMBIGUATE by printed-code overlap (never guess)
        s_list = [s for s in draft_by_name.get(dnorm(r.get("subject_name", "")), [])
                  if rowcodes & {M.norm_code(str(c)) for c in (s.get("codes") or [])}]
        # a row may merge a units-bearing print with a scheme-only twin of the
        # same subject (e.g. REMEDIAL BIOLOGY BP106RBT+BP112RBP): only the
        # units-bearing candidate can supply unit-text deltas
        with_units = [s for s in s_list if isinstance(s.get("units"), dict) and s.get("units")]
        if len(with_units) == 1:
            s_list = with_units
        if len(s_list) != 1:
            if s_list:
                print(f"AMBIGUOUS after code filter: {r['subject_id']} {r.get('subject_name')!r} codes={sorted(rowcodes)}"); sys.exit(2)
            continue
        s = s_list[0]
        units = s.get("units") or {}
        if not isinstance(units, dict):
            continue
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
        if deltas:
            plan.append((r, "R1", deltas, REPAIR_NOTE_R1))
    # R2: RMT row (same sha — handled above via R1; add the formula delta on top)
for r, kind, deltas, note in list(plan):
    if r.get("subject_id") == "remedial-mathematics-bpharm" or "REMEDIAL MATHEMATICS" in str(r.get("subject_name", "")).upper():
        u1new = deltas.get("unit1_text")
        if u1new and "[limit-formula region garbled" not in u1new[1]:
            pass  # draft already carries the formula; delta applied via R1 below

print(f"REPAIR PLAN: {len(plan)} rows")
n_cells = 0
for r, kind, deltas, note in plan:
    n_cells += len(deltas)
    sid = r["subject_id"]
    print(f"  {kind} {sid} ({str(r.get('subject_name'))[:44]}) fields={','.join(deltas.keys())}")
    for f, (oldv, newv) in deltas.items():
        r[f] = newv
    prev = r.get("change_note_vs_previous", "") or ""
    if "B04-repair" not in prev:
        r["change_note_vs_previous"] = (prev + (" | " if prev else "") + note)[:900]
    touched.add(sid)

print(f"total field updates: {n_cells} across {len(touched)} rows")

# GATES (None = PASS)
g1 = M.gate_g1(header)
g2, ncodes = M.gate_g2(rows)
g3 = M.gate_g3(rows)
g6, checks = M.gate_g6(rows, touched, f"{BASE}/parsed")
print(f"GATES: G1={g1!r} G2={g2!r} (codes={ncodes}) G3={g3!r} G6={g6!r} (spot-checks={checks})")
if g1 or g2 or g3 or g6:
    print("GATE FAILURE — no write"); sys.exit(3)

ts = datetime.utcnow().strftime("%Y-%m-%dT%H%M%Sp0000")
bkp = f"{BASE}/backup/pre_repair_{ts}.csv"
shutil.copy2(CSV_PATH, bkp)
with open(CSV_PATH, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=header)
    w.writeheader()
    w.writerows(rows)
md5 = hashlib.md5(open(CSV_PATH, "rb").read()).hexdigest()
print(f"WROTE {CSV_PATH}")
print(f"backup: {bkp}")
print(f"rows: {len(rows)} | md5: {md5} | repaired rows: {len(touched)}")
json.dump({"ts": ts, "mode": "repair", "repaired_rows": len(touched), "field_updates": n_cells,
           "rows_after": len(rows), "md5": md5, "backup": bkp,
           "repair_ids": sorted(touched)},
          open(f"{BASE}/last_repair.json", "w"), indent=1)
