#!/usr/bin/env python3
"""t6_quality_probe.py — quality-test cascade T6 (owner plan 2026-11-11), batch CRON-20261112-B89.

T6 = unit-text containment, 10% sample (P2, expected yield: medium).
  Sample: deterministic 10% — subject rows (sorted by subject_id) whose unit
  fields carry real prose (>=40 chars); every 10th row starting at offset 5.
  Method (per sampled row, per unit field unit1..unit5):
    verbatim: squashed unit text is a substring of the squashed text layer of
      the row's own cited syllabus docs (squash removes all non-alnum, so PDF
      line breaks / hyphenation / spacing cannot break a verbatim match);
    fallback 4-gram shingle coverage: fraction of the unit's 24-char squashed
      shingles present in the doc text — >=0.85 high_overlap (assembled from
      the doc with minor edits), 0.35-0.85 partial_overlap, <0.35 not_in_doc.
  Best coverage across the row's cited docs decides the unit verdict.
  Row verdict: attested_verbatim (all prose units verbatim in some cited doc) /
    mixed_overlap / unit_text_not_found_review (docs resolvable, no unit found
    — stage-2 page-image class, UNfixed) / inconclusive_doc_unresolved /
    no_citation.

LEDGER-ONLY: writes work/pipeline_v2/probes/t6_probe_ledger.json (+ copy into
syllabus_catalog/owner_requests/). No CSV write, no quality_flags change
(standing mechanics: multi-stage confirmation first). Never invents a value —
every candidate carries coverage numbers computed from printed components only.
"""
import csv
import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
PROBE_DIR = "/home/z/my-project/work/pipeline_v2/probes"
REPO = "/home/z/my-project/work/repo_asleep"
RUN_ID = "CRON-20261112-B89"

SHINGLE = 24
MIN_UNIT = 40
HIGH = 0.85
PARTIAL = 0.35


def squash(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def doc_session(stem):
    m = re.search(r"(\d{4})-(\d{2})", os.path.basename(stem or ""))
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2))
    return a if (a + 1) % 100 == b else None


def sha_index():
    idx = {}
    for base, dirs, files in os.walk(REPO):
        parts = base.split(os.sep)
        if "other_courses" in parts:
            dirs[:] = []
            continue
        for fn in files:
            if not fn.lower().endswith(".pdf"):
                continue
            p = os.path.join(base, fn)
            try:
                h = hashlib.md5(open(p, "rb").read()).hexdigest()[:16]
                idx[h] = p
            except OSError:
                pass
    return idx


def cite_docs(field):
    out = []
    for m in re.finditer(r"([A-Za-z0-9_.\- ]+\.pdf)#([0-9a-f]{16})([^;]*)", field or ""):
        pg = [int(x) for x in re.findall(r"p{1,2}\.(\d+)", m.group(3))]
        out.append((m.group(2), pg, m.group(1)))
    return out


class DocTexts:
    def __init__(self, idx):
        self.idx = idx
        self.cache = {}

    def full(self, sha):
        if sha in self.cache:
            return self.cache[sha]
        p = self.idx.get(sha)
        if not p:
            self.cache[sha] = None
            return None
        import fitz
        doc = fitz.open(p)
        t = squash("".join(pg.get_text("text") for pg in doc))
        doc.close()
        self.cache[sha] = t
        return t


def shingles(t, n=SHINGLE):
    return {t[i:i + n] for i in range(0, max(0, len(t) - n + 1), 8)}


def coverage(unit_sq, doc_sq):
    if len(unit_sq) < SHINGLE:
        return 1.0 if unit_sq and unit_sq in doc_sq else 0.0
    s = shingles(unit_sq)
    hit = sum(1 for sh in s if sh in doc_sq)
    return hit / len(s)


def unit_verdict(unit_sq, docs_sq):
    best, best_sha = 0.0, None
    verbatim_sha = None
    for sha, t in docs_sq.items():
        if t is None:
            continue
        if unit_sq and unit_sq in t:
            return "verbatim_contained", 1.0, sha
        c = coverage(unit_sq, t)
        if c > best:
            best, best_sha = c, sha
    if best >= HIGH:
        v = "high_overlap"
    elif best >= PARTIAL:
        v = "partial_overlap"
    else:
        v = "not_in_doc"
    return v, best, best_sha


# ---------------------------------------------------------------- main
def main():
    os.makedirs(PROBE_DIR, exist_ok=True)
    with open(CSV_PATH) as f:
        all_rows = [r for r in csv.DictReader(f) if r["row_kind"] == "subject"]
    UF = [f"unit{i}_text" for i in range(1, 6)]
    prose = [r for r in all_rows
             if any(len(r[u].strip()) >= MIN_UNIT for u in UF)]
    # deterministic 10%: sorted by subject_id, every 10th row from offset 5
    prose.sort(key=lambda r: r["subject_id"])
    sample = prose[5::10]
    print(f"T6 sample: {len(sample)} rows (10% of {len(prose)} prose rows)")

    idx = sha_index()
    dt = DocTexts(idx)
    cands = []
    vcount = Counter()
    for r in sample:
        docs = {}
        seen = set()
        for sha, pg, stem in cite_docs(r["source_syllabus"]):
            if sha not in seen:
                seen.add(sha)
                docs[sha] = dt.full(sha)
        if not docs:
            rv = "no_citation"
            units_out = []
        elif all(t is None for t in docs.values()):
            rv = "inconclusive_doc_unresolved"
            units_out = []
        else:
            units_out = []
            vs = []
            for u in UF:
                txt = r[u].strip()
                if len(txt) < MIN_UNIT:
                    continue
                v, cov, sha = unit_verdict(squash(txt), docs)
                vs.append(v)
                units_out.append({"unit": u, "chars": len(txt), "verdict": v,
                                  "coverage": round(cov, 3), "best_doc_sha": sha,
                                  "doc_session": doc_session(
                                      next((st for s, _, st in cite_docs(r["source_syllabus"]) if s == sha), ""))})
            if vs and all(v == "verbatim_contained" for v in vs):
                rv = "attested_verbatim"
            elif any(v in ("verbatim_contained", "high_overlap") for v in vs):
                rv = "mixed_overlap"
            else:
                rv = "unit_text_not_found_review"
        vcount[rv] += 1
        cands.append({"sid": r["subject_id"], "course": r["course_name"],
                      "primary_code": r["primary_code"],
                      "subject_name": r["subject_name"][:90],
                      "row_verdict": rv, "units": units_out,
                      "cited_shas": list(docs)})

    led = {
        "run_id": RUN_ID,
        "test": "T6 unit-text containment (10% sample)",
        "policy": "LEDGER-ONLY stage-1; no CSV/quality_flags change; page-image stage-2 deferred for not-found rows",
        "rule": {
            "sample": f"deterministic every-10th (offset 5) of {len(prose)} prose rows, sorted by subject_id",
            "verbatim": "squashed unit text substring of squashed cited-doc text layer",
            "fallback": f"{SHINGLE}-char shingle coverage >= {HIGH} high_overlap, >= {PARTIAL} partial, else not_in_doc",
        },
        "counts": {"prose_rows": len(prose), "sampled": len(sample),
                   "row_verdicts": dict(vcount)},
        "candidates": cands,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    out = os.path.join(PROBE_DIR, "t6_probe_ledger.json")
    json.dump(led, open(out, "w"), indent=1)

    print("row verdicts:", dict(vcount))
    uvc = Counter(u["verdict"] for c in cands for u in c["units"])
    print("unit verdicts:", dict(uvc))
    for c in cands:
        if c["row_verdict"] == "unit_text_not_found_review":
            print(f"  - {c['sid']} {c['primary_code']} [{c['course']}] NOT-FOUND "
                  f"(cited: {len(c['cited_shas'])})")


if __name__ == "__main__":
    main()
