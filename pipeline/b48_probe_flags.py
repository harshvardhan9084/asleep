#!/usr/bin/env python3
"""b48_probe_flags.py — build evidence-recorded TIER2_OVERRIDES entries for B48.

For every TIER2 flag key: locate the draft subject + the planned target row
(from the decisions dry-run PLAN lines), verify same-course (RULES §1b) and
unit-I vocabulary evidence, then emit the dict block for TIER2_OVERRIDES.
TIE keys (2+ candidates) are probed against BOTH candidates: the verdict is
RETARGET to the best-evidence row (code family / unit overlap) or
FORCE_APPEND when the draft is a different subject (wrong-subject name
family, B28 class). Zero-guess: any flag whose evidence fails the check is
printed as NEEDS-EYES instead of being auto-allowed.
"""
import csv, json, re, subprocess, sys

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"
CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"

rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
by_sid = {r["subject_id"]: r for r in rows}

dec = subprocess.run(
    ["python3", "/home/z/my-project/scripts/pipeline_v2/merge_draft.py",
     "decisions", DRAFTS], capture_output=True, text=True).stdout
open("/home/z/my-project/work/pipeline_v2/tmp/b48_dryrun2.txt", "w").write(dec)

plans, flags = {}, {}
for line in dec.splitlines():
    m = re.match(r"PLAN\|(\S+?)\|(T\d)\|(UPDATE|APPEND|SKIP|TIE)\|(\S*?)\|(.*?)\s*$", line)
    if m:
        plans[m.group(1)] = (m.group(2), m.group(3), m.group(4), m.group(5))
    m = re.match(r"FLAG\|(\S+?)\|TIER2 fuzzy (\d+) overlap (\d+)", line)
    if m:
        flags[m.group(1)] = ("TIER2", int(m.group(2)), int(m.group(3)))
    m = re.match(r"FLAG\|(\S+?)\|TIE TIE fuzzy (.*?)$", line)
    if m:
        flags[m.group(1)] = ("TIE", m.group(2), None)


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower())


def unit_terms(txt):
    return set(w for w in norm(txt).split() if len(w) > 5)


out, need_eyes = [], []
for key in sorted(flags):
    kind, fuzzy, overlap = flags[key]
    stem, idx, slug = key.split("::")
    d = json.load(open(f"{DRAFTS}/{stem}.draft.json"))
    subj = d["subjects"][int(idx)]
    name = subj.get("name") or subj.get("name_print") or ""
    code = (subj.get("codes") or [""])[0]
    sess = d.get("session", "")
    u1 = (subj.get("units") or {}).get("1", "")
    exps = subj.get("experiments") or []
    tier, act, tsid, tname = plans.get(key, ("?", "?", "?", "?"))
    cand = [by_sid.get(s, {}) for s in (tsid.split(";") if tsid and tsid != "?" else []) if s]
    dcourse = d.get("course", "?")

    # score every candidate: same-course guard + unit-I shared terms
    scored = []
    for r in cand:
        if not r:
            continue
        ru1 = (r.get("unit1_text", "") or "")
        dt, rt = unit_terms(u1), unit_terms(ru1)
        shared = len(dt & rt)
        same = r.get("course_name", "?") == dcourse
        scored.append((shared if same else -1, r))
    scored.sort(key=lambda x: -x[0])
    best = scored[0] if scored else None

    rec = {"key": key, "kind": kind, "draft": name[:50], "code": code,
           "session": sess, "course": dcourse, "tier": tier, "act": act,
           "cands": [(r.get("subject_id"), r.get("course_name"), r.get("primary_code"),
                      r.get("effective_session_latest"), s) for s, r in scored]}
    # verdict rules
    if kind == "TIER2":
        r = cand[0] if cand else {}
        same = r.get("course_name") == dcourse
        ok = same and tier == "T2" and act == "UPDATE" and fuzzy >= 85 and (overlap >= 3 or (best and best[0] >= 3))
        rec["shared_u1"] = best[0] if best else 0
        rec["verdict"] = "OK" if ok else "NEEDS-EYES"
    else:  # TIE
        if len(scored) < 2:
            rec["verdict"] = "NEEDS-EYES"
        else:
            (sA, rA), (sB, rB) = scored[0], scored[1]
            # clear winner on unit evidence AND same course -> RETARGET
            if rA.get("course_name") == dcourse and sA > 0 and sA >= sB + 3:
                rec["verdict"] = "RETARGET:" + rA["subject_id"]
            elif rA.get("course_name") == dcourse and sA > 0 and sA == sB:
                # unit evidence equal -> decide by name similarity + code family
                rec["verdict"] = "TIE-EQUAL"
            else:
                rec["verdict"] = "REVIEW"
    out.append(rec)

json.dump(out, open("/home/z/my-project/work/pipeline_v2/tmp/b48_probe.json", "w"), indent=1)
for r in out:
    if r["verdict"] == "OK":
        continue
    print(f"{r['verdict']:14} | {r['key']} | {r['draft']} | code={r['code']} | sess={r['session']}")
    for c in r["cands"]:
        print(f"    cand {c}")
print(f"\nTOTAL={len(out)} OK={sum(1 for r in out if r['verdict']=='OK')} "
      f"RETARGET={sum(1 for r in out if str(r['verdict']).startswith('RETARGET'))} "
      f"OTHER={sum(1 for r in out if r['verdict'] not in ('OK',) and not str(r['verdict']).startswith('RETARGET'))}")
