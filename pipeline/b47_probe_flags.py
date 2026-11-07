#!/usr/bin/env python3
"""b47_probe_flags.py — build evidence-recorded TIER2_OVERRIDES entries for B47.

For every TIER2 flag key: locate the draft subject, the planned target row
(from the decisions dry-run PLAN lines), verify same-course (RULES §1b) and
unit-I vocabulary evidence, then emit the dict block to append to
TIER2_OVERRIDES in merge_draft.py. Zero-guess: any flag whose evidence fails
the check is printed as NEEDS-EYES instead of being auto-allowed.
"""
import csv, json, re, subprocess, sys

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"
CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"

rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
by_sid = {r["subject_id"]: r for r in rows}

dec = subprocess.run(
    ["python3", "/home/z/my-project/scripts/pipeline_v2/merge_draft.py",
     "decisions", DRAFTS], capture_output=True, text=True).stdout

plans, flags = {}, {}
for line in dec.splitlines():
    m = re.match(r"PLAN\|(\S+?)\|(T\d)\|(UPDATE|APPEND|SKIP|TIE)\|(\S*?)\|(.*?)\s*$", line)
    if m:
        plans[m.group(1)] = (m.group(2), m.group(3), m.group(4), m.group(5))
    m = re.match(r"FLAG\|(\S+?)\|TIER2 fuzzy (\d+) overlap (\d+)", line)
    if m:
        flags[m.group(1)] = (int(m.group(2)), int(m.group(3)))

def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower())

out, need_eyes = [], []
for key in sorted(flags):
    stem, idx, slug = key.split("::")
    fuzzy, overlap = flags[key]
    d = json.load(open(f"{DRAFTS}/{stem}.draft.json"))
    subj = d["subjects"][int(idx)]
    name = subj.get("name") or subj.get("name_print") or ""
    code = (subj.get("codes") or [""])[0]
    sess = d.get("session", "")
    u1 = (subj.get("units") or {}).get("1", "")
    tier, act, tsid, tname = plans.get(key, ("?", "?", "?", "?"))
    row = by_sid.get(tsid, {})
    rcourse = row.get("course_name", "?")
    dcourse = d.get("course", "?")
    rcode = row.get("primary_code", "")
    ralls = (row.get("all_codes", "") or "")[:60]
    rsess = row.get("effective_session_latest", "")
    same_course = rcourse == dcourse
    # unit-I distinctive-term overlap between draft and row (evidence)
    ru1 = row.get("unit1", "") or ""
    dt = set(w for w in norm(u1).split() if len(w) > 5)
    rt = set(w for w in norm(ru1).split() if len(w) > 5)
    shared = len(dt & rt)
    verdict = "OK" if (same_course and tier == "T2" and act == "UPDATE"
                       and fuzzy >= 85 and (overlap >= 3 or shared >= 3)) else "NEEDS-EYES"
    rec = {
        "key": key, "draft": name, "code": code, "session": sess,
        "target": tsid, "target_name": tname, "target_course": rcourse,
        "target_code": rcode, "fuzzy": fuzzy, "overlap": overlap,
        "unit1_shared_terms": shared, "verdict": verdict,
    }
    (out if verdict == "OK" else need_eyes).append(rec)

json.dump({"ok": out, "needs_eyes": need_eyes},
          open("/tmp/b47_probe.json", "w"), indent=1)
for r in out:
    print("OK|%(key)s|%(code)s|f%(fuzzy)d/o%(overlap)d/u%(unit1_shared_terms)d -> %(target)s (%(target_course)s, %(target_code)s, sess %(rsess)s)" % dict(r, rsess=by_sid.get(r["target"], {}).get("effective_session_latest", "?")))
for r in need_eyes:
    print("NEEDS-EYES|%(key)s|%(code)s|f%(fuzzy)d/o%(overlap)d/u%(unit1_shared_terms)d -> %(target)s (%(target_course)s) tier=%(tier)s act=%(act)s" % dict(r, tier=plans.get(r["key"], ("?",))[0], act=plans.get(r["key"], ("", "?",))[1] if False else "?"))
print(f"OK={len(out)} NEEDS-EYES={len(need_eyes)}")
