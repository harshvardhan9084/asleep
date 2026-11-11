#!/usr/bin/env python3
"""t1_quality_probe.py — owner directive 2026-11-11: "start working on quality tests".

Iterative light-marking cascade (no CSV writes; probes only, per the test-plan
standing mechanics):
  T1 duplicate-subject detection (owner's 3-check spec):
    Stage 0: partition by course_name — same name across BTech/BCA/MCA is NOT
             duplication (cross-course same-name subjects are by design).
    Stage 1: name-similarity candidates within course (exact normalized match,
             token-Jaccard >= 0.6, or difflib ratio >= 0.80 on token-hit pairs)
             — light mark only.
    Stage 2: for CANDIDATES ONLY, second mark = unit-text agreement
             (squash-normalized unit1..unit5, shared if equal or ratio >= 0.85)
             + code relation + session overlap. Multi-column agreement
             (course + name + units + codes) confirms; anything less stays a
             recorded candidate for the next stage of the cascade.
  T2 stage 1: same exact_code claimed by 2 rows within one course (G2
             re-measure; also session-overlap scoped pair list).
  T12 stage 1: every #sha16 cited in the CSV resolves to a repo-corpus PDF
             (md5[:16] index over work/repo_asleep/PDFs + upload).

Outputs (ledgers only): work/pipeline_v2/probes/{t1,t2,t12}_*.json + console
summary. quality_flags/CSV untouched this run (diagnostic cascade).
"""
import csv
import json
import hashlib
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
PROBE_DIR = "/home/z/my-project/work/pipeline_v2/probes"
REPO = "/home/z/my-project/work/repo_asleep"

STOP = {"", "and", "of", "the", "for", "in", "i", "ii", "iii", "iv", "lab", "practical"}


def squash(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def norm_name(s):
    s = (s or "").lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def toks(s):
    return {t for t in norm_name(s).split() if t not in STOP}


def jaccard(a, b):
    return len(a & b) / len(a | b) if (a or b) else 0.0


def load():
    rows = list(csv.DictReader(open(CSV_PATH)))
    return [r for r in rows if r.get("row_kind") == "subject"]


def unit_pairs(a, b):
    out = {}
    for i in range(1, 6):
        ua, ub = squash(a.get(f"unit{i}_text")), squash(b.get(f"unit{i}_text"))
        if not ua or not ub:
            continue
        r = 1.0 if ua == ub else SequenceMatcher(None, ua[:1200], ub[:1200]).ratio()
        out[i] = r
    return out


def code_rel(a, b):
    pa, pb = squash(a.get("primary_code")).upper(), squash(b.get("primary_code")).upper()
    ca = {squash(c).upper() for c in (a.get("all_codes") or "").split(";") if c.strip()}
    cb = {squash(c).upper() for c in (b.get("all_codes") or "").split(";") if c.strip()}
    if pa and pa == pb:
        return "same_primary"
    if ca & cb:
        return "codes_overlap"
    return "codes_disjoint"


def sess_overlap(a, b):
    sa = {a.get("effective_session_latest", ""), a.get("first_introduced_session", "")} - {""}
    sb = {b.get("effective_session_latest", ""), b.get("first_introduced_session", "")} - {""}
    return "overlap" if sa & sb else "disjoint"


def kind_of(name):
    n = norm_name(name)
    if "lab" in n.split() or "practical" in n.split() or "project" in n.split():
        return "practical"
    return "theory"


def verdict(name_a, name_b, name_r, units, crel, sess):
    shared = sum(1 for r in units.values() if r >= 0.85)
    u1eq = units.get(1, 0) >= 0.999
    tail = [r for i, r in units.items() if i >= 3]
    early = [r for i, r in units.items() if i <= 2]
    # theory-vs-lab/practical pairs are different subjects by kind, however
    # similar the shared intro units read (graphics theory vs graphics lab)
    if kind_of(name_a) != kind_of(name_b):
        return "distinct_by_kind(theory-vs-lab)"
    if crel != "codes_disjoint" and (shared >= 2 or (u1eq and len(units) >= 1 and name_r >= 0.8)):
        return "duplicate_confirmed"
    if shared >= 3 and name_r >= 0.9:
        return "duplicate_likely_code_gap"
    if early and all(r >= 0.85 for r in early) and tail and all(r < 0.6 for r in tail):
        return "same_core_diff_tail(B28class)"
    if shared == 0 and sess == "disjoint":
        return "era_variant_accumulator"
    return "candidate_unresolved"


def main():
    os.makedirs(PROBE_DIR, exist_ok=True)
    subs = load()
    by_course = defaultdict(list)
    for r in subs:
        by_course[r.get("course_name", "")].append(r)

    # ---------- T1
    pairs, cands = [], 0
    for course, rs in by_course.items():
        n = len(rs)
        for i in range(n):
            ti = toks(rs[i].get("subject_name"))
            ni = norm_name(rs[i].get("subject_name"))
            for j in range(i + 1, n):
                tj = toks(rs[j].get("subject_name"))
                nj = norm_name(rs[j].get("subject_name"))
                if ni == nj:
                    ratio, jac = 1.0, 1.0
                else:
                    jac = jaccard(ti, tj)
                    if jac < 0.6:
                        continue
                    ratio = SequenceMatcher(None, ni, nj).ratio()
                    if ratio < 0.80:
                        continue
                cands += 1
                a, b = rs[i], rs[j]
                units = unit_pairs(a, b)
                crel = code_rel(a, b)
                sess = sess_overlap(a, b)
                v = verdict(a.get("subject_name"), b.get("subject_name"), ratio, units, crel, sess)
                pairs.append({
                    "course": course,
                    "a": a["subject_id"], "b": b["subject_id"],
                    "name_a": a.get("subject_name"), "name_b": b.get("subject_name"),
                    "name_ratio": round(ratio, 3), "jaccard": round(jac, 3),
                    "unit_ratios": {k: round(v, 3) for k, v in units.items()},
                    "code_rel": crel, "session_rel": sess,
                    "year_a": a.get("program_year"), "year_b": b.get("program_year"),
                    "sem_a": a.get("semester_slots"), "sem_b": b.get("semester_slots"),
                    "verdict": v,
                })
    from collections import Counter
    vc = Counter(p["verdict"] for p in pairs)
    t1 = {"test": "T1 duplicate-subject (owner 3-check spec)", "subjects": len(subs),
          "courses": {k: len(v) for k, v in by_course.items()},
          "candidate_pairs": cands, "verdicts": dict(vc), "pairs": pairs,
          "generated_utc": datetime.now(timezone.utc).isoformat()}
    json.dump(t1, open(f"{PROBE_DIR}/t1_probe_ledger.json", "w"), indent=1)

    # ---------- T2 stage 1 (G2 re-measure, session-scoped)
    sys.path.insert(0, "/home/z/my-project/work/repo_asleep/pipeline")
    import merge_draft as MD
    all_rows = list(csv.DictReader(open(CSV_PATH)))
    g2, ncodes = MD.gate_g2(all_rows)
    t2 = {"test": "T2 code double-ownership stage1", "gate_g2": g2 or "PASS",
          "owned_codes": ncodes,
          "generated_utc": datetime.now(timezone.utc).isoformat()}
    json.dump(t2, open(f"{PROBE_DIR}/t2_probe_ledger.json", "w"), indent=1)

    # ---------- T12 stage 1 (citation integrity vs repo corpus)
    index = {}
    for root, _d, fs in os.walk(os.path.join(REPO, "PDFs")):
        for fn in fs:
            if fn.lower().endswith(".pdf"):
                p = os.path.join(root, fn)
                h = hashlib.md5()
                with open(p, "rb") as f:
                    for ch in iter(lambda: f.read(1 << 20), b""):
                        h.update(ch)
                index[h.hexdigest()[:16]] = os.path.relpath(p, REPO)
    for extra_root in ("/home/z/my-project/upload",
                       "/home/z/my-project/work/artd_v3/sources"):
        if os.path.isdir(extra_root):
            for dirpath, _dd, fs in os.walk(extra_root):
                for fn in fs:
                    if fn.lower().endswith(".pdf"):
                        p = os.path.join(dirpath, fn)
                        h = hashlib.md5()
                        with open(p, "rb") as f:
                            for ch in iter(lambda: f.read(1 << 20), b""):
                                h.update(ch)
                        index[h.hexdigest()[:16]] = "upload:" + os.path.relpath(p, extra_root)
    sha_re = re.compile(r"#([0-9a-f]{16})")
    cols = ("source_syllabus", "source_scheme_line", "source_history", "notes",
            "change_note_vs_previous", "corrections_json")
    cited, unresolved = set(), {}
    for r in all_rows:
        for c in cols:
            for m in sha_re.findall(r.get(c, "") or ""):
                cited.add(m)
                if m not in index and m not in unresolved:
                    unresolved[m] = r["subject_id"]
    t12 = {"test": "T12 citation integrity stage1", "corpus_pdfs_indexed": len(index),
           "distinct_sha_cited": len(cited), "unresolved": unresolved,
           "generated_utc": datetime.now(timezone.utc).isoformat()}
    json.dump(t12, open(f"{PROBE_DIR}/t12_probe_ledger.json", "w"), indent=1)

    print(f"T1|subjects={len(subs)}|candidate_pairs={cands}|verdicts={dict(vc)}")
    for p in pairs:
        if p["verdict"].startswith("duplicate_confirmed") or p["verdict"].startswith("duplicate_likely"):
            print(f"  DUP {p['verdict']} [{p['course']}] {p['a']} <-> {p['b']} "
                  f"({p['name_a']!r} / {p['name_b']!r}) units={p['unit_ratios']} {p['code_rel']} {p['session_rel']}")
    print(f"T2|g2={t2['gate_g2']}|codes={ncodes}")
    print(f"T12|cited={len(cited)}|corpus={len(index)}|unresolved={len(unresolved)}|list={dict(list(unresolved.items())[:5])}")


if __name__ == "__main__":
    main()
