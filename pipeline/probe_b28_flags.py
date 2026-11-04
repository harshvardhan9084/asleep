#!/usr/bin/env python3
"""probe_b28_flags.py — evidence probes for B28 adjudications (B27 probe class).

Probes (recorded evidence for TIER2_OVERRIDES / flag review):
  1. doc05::14 information-theory-and-coding (REC406, 2017-18) vs doc06::08
     information-theory-and-coding (NEC408, 2014-15) vs the existing CSV rows —
     are these the SAME subject (would duplicate rows) or different?
  2. doc09::00 computer-aided-design-cad (NME-701) fuzzy target — unit identity?
  3. doc09::03 quality-control (NPI-801) fuzzy target — unit identity?
  4. doc04::04 object-oriented-systems (ECS-302) fuzzy target — unit identity?
  5. 'gp' row existence for doc01 NGP501/NGP601 name-identity transfers.
"""
import csv, json, re, sys
from difflib import SequenceMatcher

CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
D = "/home/z/my-project/work/pipeline_v2/drafts/B28"


def norm_al(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def toks(s, stoplen=3):
    words = re.findall(r"[a-z]+", (s or "").lower())
    return {w for w in words if len(w) > stoplen}


def unit_jaccard(units_a, units_b):
    """best per-unit Jaccard over normalized unit text"""
    ua = [norm_al(v) for v in (units_a or {}).values() if v]
    ub = [norm_al(v) for v in (units_b or {}).values() if v]
    if not ua or not ub:
        return 0.0
    best = 0.0
    for a in ua:
        for b in ub:
            if not a or not b:
                continue
            j = SequenceMatcher(None, a, b).quick_ratio()
            # cheap pre-filter then real ratio on the best candidates
            if j > 0.6:
                j = SequenceMatcher(None, a, b).ratio()
            else:
                continue
            best = max(best, j)
    return best


rows = {}
with open(CSV, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r.get("row_kind") == "subject":
            rows[r["subject_id"]] = r

drafts = {}
import glob, os
for p in glob.glob(f"{D}/*.draft.json"):
    d = json.load(open(p))
    drafts[os.path.basename(p).replace(".draft.json", "")] = d


def get_sub(stem, idx):
    return drafts[stem]["subjects"][idx]


def probe(name, draft_sub, candidate_ids):
    print(f"\n### {name}: draft name={draft_sub.get('name')!r} codes={draft_sub.get('codes')}")
    dv = toks(json.dumps(draft_sub.get("units", {})) + " " + json.dumps(draft_sub.get("cos", [])))
    for sid in candidate_ids:
        r = rows.get(sid)
        if not r:
            print(f"  {sid}: NOT IN CSV")
            continue
        rv = toks((r.get("unit1_text", "") or "") + (r.get("unit2_text", "") or "")
                  + (r.get("unit3_text", "") or "") + (r.get("unit4_text", "") or "")
                  + (r.get("unit5_text", "") or ""))
        shared = len(dv & rv)
        denom = len(dv | rv) or 1
        du = {}
        for k in ("unit1_text", "unit2_text", "unit3_text", "unit4_text", "unit5_text"):
            if r.get(k):
                du[str(k)[4]] = r[k]
        j = unit_jaccard(draft_sub.get("units", {}), du)
        print(f"  {sid}: name={r.get('subject_name')!r} session={r.get('effective_session_latest')} "
              f"vocab={shared}/{len(dv)} ({shared/denom:.2f}) best-unit-J={j:.2f}")


# 1. Information Theory & Coding triangle
s05 = get_sub("05_btech_it_y2_scheme-syllabus_2017-18", 14)
s06 = get_sub("06_btech_it_y2_syllabus-rev_2014-15", 8)
itc_ids = [sid for sid, r in rows.items()
           if "information theory" in (r.get("subject_name") or "").lower()
           or "information-theory" in sid]
print("existing ITC-ish rows:", itc_ids)
probe("05::14 REC406 2017-18", s05, itc_ids)
probe("06::08 NEC408 2014-15", s06, itc_ids)

# 2-4. fuzzy targets from the ladder — find candidates by name similarity
def fuzzy_cands(draft_sub):
    from difflib import SequenceMatcher
    dn = (draft_sub.get("name") or "").lower()
    scored = []
    for sid, r in rows.items():
        if r.get("course_name") != "BTech":
            continue
        rn = (r.get("subject_name") or "").lower()
        sc = SequenceMatcher(None, sorted(set(dn.split())), sorted(set(rn.split()))).ratio() * 100
        if sc >= 80:
            scored.append((sc, sid))
    scored.sort(reverse=True)
    return [sid for _, sid in scored[:4]]


for stem, idx, label in [
    ("09_btech_me-ind-pe-ipe_y4_syllabus_2016-17", 0, "09::00 CAD NME-701 2016-17"),
    ("09_btech_me-ind-pe-ipe_y4_syllabus_2016-17", 3, "09::03 Quality Control 2016-17"),
    ("04_btech_it_y2_scheme-syllabus_2009-10", 4, "04::04 Object-Oriented Systems ECS-302"),
    ("10_btech_me-ind_syllabus_2020-21", 8, "10::08 Finite Element Methods"),
]:
    s = get_sub(stem, idx)
    probe(label, s, fuzzy_cands(s))

# 5. gp row
gp_ids = [sid for sid in rows if sid in ("gp", "general-proficiency", "general-proficiency-lab", "ngp")]
for sid in gp_ids:
    r = rows[sid]
    print(f"\ngp-row {sid}: name={r.get('subject_name')!r} codes={r.get('primary_code')}/{r.get('all_codes')} "
          f"session={r.get('effective_session_latest')}")
