#!/usr/bin/env python3
"""Generate DECISION_OVERRIDES entries for the B05 re-ladder's 122 cross-era
code TIEs. Target selection (never guess): the TIE candidate row whose
source_syllabus citation chain contains the DRAFT'S OWN sha16 (the row
ingested from the same document — the draft is re-ingesting its own doc's
subjects). Fallback: unique row with effective_session_latest == draft
session. Ambiguous -> reported for manual review, no override emitted.

Output: python dict-literal text to paste into merge_draft.py's
DECISION_OVERRIDES (appended by this script directly with a marked block).
"""
import json, re, glob, os, csv, sys

BASE = "/home/z/my-project/work/pipeline_v2"
LOG = f"{BASE}/tmp_decisions_b05b.log"


def M_SLUG_NORM(s):
    import re as _re
    return _re.sub(r"[^a-z0-9 ]", "", str(s or "").lower()).strip()

def M_ISLAB(s):
    toks = set(M_SLUG_NORM(s).split())
    return bool(toks & {"lab", "laboratory", "practical", "project"})

rows = list(csv.DictReader(open("/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv")))
row_by_sid = {r["subject_id"]: r for r in rows if r.get("row_kind") == "subject"}

# draft sha16 per stem
sha_by_stem = {}
for p in glob.glob(f"{BASE}/drafts/*.draft.json"):
    try:
        d = json.load(open(p))
    except Exception:
        continue
    if d.get("sha16") and d.get("pdf_rel"):
        sha_by_stem[os.path.basename(p)[:-11]] = (d.get("sha16"), d.get("session"), d.get("course"))

ties = []
for line in open(LOG):
    m = re.match(r"PLAN\|([^|]+)::(\d+)::([^|]+)\|T(\d)\|TIE\|([^|]+)\|", line)
    if m:
        ties.append((m.group(1), int(m.group(2)), m.group(4), [t for t in m.group(5).split(";") if t]))

print(f"TIE plans: {len(ties)}")
overrides = {}
skipped = []
for stem, idx, tier, targets in ties:
    key = f"{stem}::{idx:02d}::{slug_fix}" if False else None
    # rebuild the exact ladder key: f'{stem}::{idx:02d}::{slug(name)}'
    d = json.load(open(f"{BASE}/drafts/{stem}.draft.json"))
    s = d["subjects"][idx]
    from merge_draft import slug
    key = f"{stem}::{idx:02d}::{slug(s.get('name', ''))}"
    sha, session, course = sha_by_stem[stem]
    cands = [row_by_sid[t] for t in targets if t in row_by_sid]
    same_doc = [r for r in cands if sha in str(r.get("source_syllabus", ""))]
    if len(same_doc) > 1:
        # refine 1: normalized-name equality (2026-27 elective pools print ONE
        # pool code over many member courses, each with its own same-doc row)
        nm = M_SLUG_NORM(s.get("name", ""))
        by_name = [r for r in same_doc if M_SLUG_NORM(r.get("subject_name", "")) == nm]
        if len(by_name) == 1:
            same_doc = by_name
        else:
            # refine 2: practical/theory consistency (T/P print split is law, R1)
            is_lab = bool(M_ISLAB(s.get("name", "")))
            by_kind = [r for r in same_doc if is_lab == bool(M_ISLAB(r.get("subject_name", "")))]
            if len(by_kind) == 1:
                same_doc = by_kind
    if len(same_doc) == 1:
        tgt, why = same_doc[0], f"same-doc row (source_syllabus cites this draft's sha16 {sha})"
    elif len(same_doc) == 0:
        same_sess = [r for r in cands if (r.get("effective_session_latest") or "") == (session or "")]
        if len(same_sess) == 1:
            tgt, why = same_sess[0], f"no same-doc citation among candidates; unique candidate with matching session {session}"
        else:
            skipped.append((key, stem, idx, s.get("name"), targets, "no same-doc row / session fallback ambiguous"))
            continue
    else:
        skipped.append((key, stem, idx, s.get("name"), targets, f"{len(same_doc)} same-doc rows"))
        continue
    overrides[key] = ("UPDATE", tgt["subject_id"],
                      f"B05 re-ladder cross-era code TIE: candidates {', '.join(targets)}; resolved to "
                      f"{tgt['subject_id']} — {why} (RULES §3: the draft re-ingests its own document's "
                      f"subjects; other-era same-code rows are different curriculum prints kept separate "
                      f"per the B04 code-reuse model).")

print(f"resolved: {len(overrides)} | skipped-for-review: {len(skipped)}")
for k, stem, idx, name, targets, why in skipped:
    print(f"  SKIP {key if False else stem}::{idx:02d} {name!r} targets={targets} — {why}")

# splice into merge_draft.py DECISION_OVERRIDES
src = open("/home/z/my-project/scripts/pipeline_v2/merge_draft.py").read()
marker = "# ---- B05 TIE adjudications (generated) ----"
if marker in src:
    print("overrides already spliced — remove the old block first")
    sys.exit(1)
m = re.search(r"(DECISION_OVERRIDES\s*=\s*\{)", src)
assert m, "DECISION_OVERRIDES not found"
block = "\n" + marker + "\n"
for k, (action, sid, reason) in overrides.items():
    block += f"    {json.dumps(k)}: {json.dumps((action, sid, reason))},\n"
block += "    # ---- end B05 TIE adjudications ----\n"
src = src[:m.end()] + block + src[m.end():]
open("/home/z/my-project/scripts/pipeline_v2/merge_draft.py", "w").write(src)
print(f"spliced {len(overrides)} overrides into merge_draft.py DECISION_OVERRIDES")
