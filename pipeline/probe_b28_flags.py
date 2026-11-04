#!/usr/bin/env python3
"""probe_b28_flags.py — evidence probe for the B28 merge flags (15 to adjudicate:
8 code-identity TIEs + 7 TIER2 fuzzies) + sanity listing of the recorded autos.
Methodology per recorded B27 class: token overlap + best per-unit Jaccard +
direct print probes of contested code slots."""
import csv, json, re, sys, glob
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import merge_draft as M

rows = list(csv.DictReader(open(M.CSV_PATH, newline="", encoding="utf-8")))
drafts = {}
for p in sorted(glob.glob("/home/z/my-project/work/pipeline_v2/drafts/*.draft.json")):
    d = json.load(open(p))
    drafts[d["stem"]] = d

report = json.load(open("/home/z/my-project/work/pipeline_v2/decisions_report.json"))
seen = set()
for f in report["flags"]:
    key, kind, info = f
    if key in seen:
        continue
    seen.add(key)
    doc, idx, slug = key.split("::")
    d = drafts.get(doc)
    if d is None:
        print(f"### {key} | {kind} | DOC NOT FOUND")
        continue
    sub = next((s for s in d["subjects"] if M.slug(s.get("name", "")) == slug), None)
    if sub is None:
        cands = [s for s in d["subjects"] if slug in M.slug(s.get("name", ""))]
        sub = cands[0] if cands else None
    if sub is None:
        print(f"### {key} | {kind} | DRAFT SUBJECT NOT FOUND")
        continue
    print(f"### {key} | {kind} | {info}")
    print(f"    draft: name={sub.get('name')!r} codes={sub.get('codes')} sem={sub.get('semester')} sess={d.get('session')}")
    u = sub.get("units") or {}
    if u:
        print(f"    u1head: {' '.join(list(u.values())[0].split())[:90]!r}")
    dcodes = {M.norm_code(c) for c in (sub.get("codes") or [])}
    if "code identity" in info:
        for r in rows:
            hit = dcodes & M.row_owned_codes(r)
            if hit and r.get("row_kind") == "subject":
                u1 = (r.get("unit1_text") or "")[:70]
                print(f"    OWNER: {r['subject_id']} | {r['subject_name'][:52]!r} | pc={r['primary_code']} | sess={r.get('effective_session_latest')} | hit={sorted(hit)} | branch={r.get('branch_names','')[:28]!r}")
                if u1:
                    print(f"           u1: {' '.join(u1.split())[:70]!r}")
    else:
        course = d.get("course")
        dv = M.draft_vocab(sub)
        cands = []
        for r in rows:
            if r.get("row_kind") != "subject" or M.canon_course(r.get("course_name")) != course:
                continue
            sc = M.token_set_ratio(sub.get("name", ""), r.get("subject_name", ""))
            if sc < 85:
                continue
            if M.is_lab_name(sub.get("name", "")) != M.is_lab_name(r.get("subject_name", "")):
                continue
            if M.serial_variant(sub.get("name", ""), r.get("subject_name", "")):
                continue
            ov = len(dv & M.row_vocab(r))
            if sc >= 92 or (sc >= 85 and ov >= 3):
                best = 0.0
                if u:
                    for ut in u.values():
                        for rt in (r.get("unit1_text"), r.get("unit2_text"), r.get("unit3_text"), r.get("unit4_text"), r.get("unit5_text")):
                            if ut and rt:
                                a = set(M.norm_name(ut).split()); b = set(M.norm_name(rt).split())
                                if a and b:
                                    best = max(best, len(a & b) / len(a | b))
                cands.append((sc, ov, r, best))
        for sc, ov, r, best in sorted(cands, key=lambda x: (-x[0], -x[1]))[:4]:
            print(f"    CAND: sc={sc:.0f} ov={ov} bestJacc={best:.2f} | {r['subject_id']} | {r['subject_name'][:48]!r} | pc={r['primary_code']} | sess={r.get('effective_session_latest')} | branch={r.get('branch_names','')[:40]!r} | codes={r.get('all_codes','')[:60]}")
    print()
