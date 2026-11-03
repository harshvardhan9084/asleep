#!/usr/bin/env python3
"""B04 step-4 closeout: validate all 10 drafts (top-level vs batch04_run snapshot)."""
import json, os, sys

D = "/home/z/my-project/work/pipeline_v2/drafts"
RUN = os.path.join(D, "batch04_run")

EXPECT = [
    ("01", "bca_y3_syllabus_2026-27",              "aea8d72d902a0edb"),
    ("02", "bpharm_ordinances_2019-20",            "2269c86dd1036ef3"),
    ("03", "bpharm_regulations-ordinances_2026-27", "eb106a432de287f9"),
    ("04", "bpharm_scheme-syllabus_2026-27",        "97b5d901f34c75a4"),
    ("05", "bpharm_y1-2_syllabus_2013-14",          "17afa8fcb939837c"),
    ("06", "bpharm_y1-4_syllabus_2019-20",          "28cd10357b812c41"),
    ("07", "bpharm_y1_scheme_2016-17",              "9362eee0de49feea"),
    ("08", "bpharm_y1_syllabus_2017-18",            "2a058fb8112db1e5"),
    ("09", "bpharm_y2_scheme-syllabus_2017-18",     "328b747839564a48"),
    ("10", "bpharm_y2_scheme-syllabus_2017-18_2",   "580404afef9ae8d6"),
]

def load(p):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception as e:
        return {"__error__": str(e)}

def summary(doc):
    if "__error__" in doc:
        return f"PARSE-ERROR {doc['__error__']}"
    subs = doc.get("subjects", [])
    nsr = doc.get("non_subject_rows", [])
    meta = doc.get("meta", {}) or {}
    codes = []
    for s in subs:
        c = s.get("code") or s.get("subject_code") or "?"
        codes.append(str(c))
    return (f"subj={len(subs)} nsr={len(nsr)} sha16={meta.get('sha16','?')} "
            f"course={meta.get('course','?')} session={meta.get('session','?')} "
            f"first3={codes[:3]} last2={codes[-2:]}")

problems = []
for nn, stem, sha in EXPECT:
    top_p = os.path.join(D, f"{nn}_{stem}.draft.json")
    run_p = os.path.join(RUN, f"{nn}_{stem}.draft.json")
    top = load(top_p) if os.path.exists(top_p) else None
    run = load(run_p) if os.path.exists(run_p) else None
    print(f"== {nn}_{stem} (expect sha16 {sha})")
    if top is None:
        print("   TOP: MISSING"); problems.append(f"{nn}: top missing")
    else:
        st = summary(top)
        print(f"   TOP: {st}")
        if "__error__" not in top:
            m = top.get("meta", {}) or {}
            if str(m.get("sha16", "")) != sha:
                problems.append(f"{nn}: top sha16 mismatch {m.get('sha16')} != {sha}")
    if run is None:
        print("   RUN: (no snapshot)")
    else:
        print(f"   RUN: {summary(run)}")
        if "__error__" not in run and "__error__" not in top:
            tc = {str(s.get("code") or s.get("subject_code")) for s in top.get("subjects", [])}
            rc = {str(s.get("code") or s.get("subject_code")) for s in run.get("subjects", [])}
            only_top, only_run = tc - rc, rc - tc
            t_len, r_len = len(top.get("subjects", [])), len(run.get("subjects", []))
            tn, rn = len(top.get("non_subject_rows", [])), len(run.get("non_subject_rows", []))
            print(f"   DIFF: only_top={sorted(only_top)[:8]}{'...' if len(only_top)>8 else ''} "
                  f"only_run={sorted(only_run)[:8]}{'...' if len(only_run)>8 else ''} "
                  f"subj {t_len}->{r_len} nsr {tn}->{rn}")
            if rc >= tc and rn >= tn and (r_len > t_len or rn > tn):
                print("   VERDICT: RUN is a superset -> promote")
            elif rc == tc and rn == tn:
                print("   VERDICT: equivalent (differ only in bytes/fields)")
            else:
                print("   VERDICT: DIVERGENT -> manual inspection needed")
                problems.append(f"{nn}: divergent top vs run")
print("\nPROBLEMS:", problems if problems else "none")
sys.exit(1 if problems else 0)
