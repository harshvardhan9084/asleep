#!/usr/bin/env python3
"""t10_quality_probe.py — quality-test cascade T10 (owner plan 2026-11-11), batch CRON-20261112-B86.

T10 = CO duplication across rows (P3, expected yield: low).
  Stage 1: cluster subject rows by their stored course-outcome texts
           (co1_text..co6_text, normalized: lowercase, punctuation squashed,
           whitespace collapsed; signature = ordered tuple of all non-empty
           slots, MIN_CO=3 to avoid trivial single-sentence collisions).
             exact clusters    — identical full CO-set across >=2 rows;
             near-dup clusters — token-Jaccard >= 0.85 on the concatenated CO
                                 text, not exact (weaker, reported separately).
           Context recorded per cluster: same-program vs cross-program members
           (shared electives like IoT/ML/Python print identical COs across
           BTech/BCA/MCA docs — duplication is only a defect when the row's OWN
           doc does not print it).
  Stage 2: for EVERY member row of every cluster, own-cited-doc page evidence
           (fitz text layer, cited pages first then whole doc, same sha index
           as T1/T3/T7/T8): locate the row's CO1 print fragment (first ~10
           words squashed; extended with CO2 when too short).
             found, and sibling rows' docs print the same text
                                      -> attested_print_duplication
                                         (print wins per 6b/B76; shared-course
                                          composition, no fix)
             found in exactly one member's doc, other members'
             own docs do NOT print it  -> drafting_side_duplication_review
                                         (stored COs copied beyond the print;
                                          fix/flag candidate for a LATER batch)
             no member's doc yields the print -> co_print_unverified_review
             unresolvable sha / no citation   -> inconclusive classes.

LEDGER-ONLY: writes work/pipeline_v2/probes/t10_probe_ledger.json (+ copy into
syllabus_catalog/owner_requests/). No CSV write, no quality_flags change
(standing mechanics: multi-stage confirmation first). Never invents a value —
every candidate carries stored + printed evidence.
"""
import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
PROBE_DIR = "/home/z/my-project/work/pipeline_v2/probes"
REPO = "/home/z/my-project/work/repo_asleep"
RUN_ID = "CRON-20261112-B86"

MIN_CO = 3        # non-empty CO slots needed for a comparable signature
JAC_NEAR = 0.85   # token-Jaccard threshold for near-dup clusters


def squash(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def norm_co(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()


def row_cos(r):
    """ordered non-empty normalized CO texts (co1..co6, header order quirk ignored)."""
    return [norm_co(r.get(f"co{i}_text")) for i in range(1, 7)
            if norm_co(r.get(f"co{i}_text"))]


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
    """squashed per-page text cache, built lazily per sha."""

    def __init__(self, idx):
        self.idx = idx
        self.cache = {}

    def pages(self, sha):
        if sha in self.cache:
            return self.cache[sha]
        p = self.idx.get(sha)
        if not p:
            self.cache[sha] = None
            return None
        import fitz
        doc = fitz.open(p)
        texts = [squash(pg.get_text("text")) for pg in doc]
        doc.close()
        self.cache[sha] = texts
        return texts

    def locate(self, sha, frag, pages):
        texts = self.pages(sha)
        if texts is None:
            return "doc_unresolvable", None, ""
        n = len(texts)
        scan = [p for p in pages if 1 <= p <= n] or list(range(1, n + 1))
        for pg in scan:
            t = texts[pg - 1]
            i = t.find(frag)
            if i >= 0:
                return "co_print_found", pg, t[max(0, i - 40):i + 160]
        return "co_print_not_found", None, ""


def co_fragment(cos):
    """search fragment: first ~10 words of CO1 squashed; extend with CO2 if short."""
    words = cos[0].split()
    frag = squash(" ".join(words[:10]))
    if len(frag) < 25 and len(cos) > 1:
        frag2 = squash(cos[0] + cos[1])
        if len(frag2) >= 25:
            return frag2
    return frag if len(frag) >= 25 else squash(cos[0])


def jaccard(a, b):
    A, B = set(a.split()), set(b.split())
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


# ---------------------------------------------------------------- main
def main():
    os.makedirs(PROBE_DIR, exist_ok=True)
    with open(CSV_PATH) as f:
        rows = [r for r in csv.DictReader(f) if r["row_kind"] == "subject"]

    have = [(i, r) for i, r in enumerate(rows) if len(row_cos(r)) >= MIN_CO]
    skipped_lt3 = sum(1 for r in rows
                      if 0 < len(row_cos(r)) < MIN_CO
                      or (any(norm_co(r.get(f"co{i}_text")) for i in range(1, 7))
                          and len(row_cos(r)) < MIN_CO))

    # ---- stage 1: exact clusters by full ordered signature
    sig = defaultdict(list)
    for i, r in have:
        sig[tuple(row_cos(r))].append((i, r))
    exact = {k: v for k, v in sig.items() if len(v) > 1}

    # ---- near-dup pairs (Jaccard on concatenated CO text, not exact)
    joined = {i: " ".join(row_cos(r)) for i, r in have}
    toks = {i: set(joined[i].split()) for i in joined}
    cand_pairs = set()
    for a in range(len(have)):
        ia, ra = have[a]
        for b in range(a + 1, len(have)):
            ib, rb = have[b]
            shared = len(toks[ia] & toks[ib])
            if shared >= 8 and shared / min(len(toks[ia]), len(toks[ib])) >= 0.7:
                cand_pairs.add((min(ia, ib), max(ia, ib)))
    near = []
    for ia, ib in cand_pairs:
        if tuple(row_cos(rows[ia])) == tuple(row_cos(rows[ib])):
            continue
        j = jaccard(joined[ia], joined[ib])
        if j >= JAC_NEAR:
            near.append((j, ia, ib))
    near.sort(reverse=True)
    # union near-dup pairs into clusters (only among rows not already exact-clustered)
    parent = {i: i for i, _ in have}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for j, ia, ib in near:
        parent[find(ia)] = find(ib)
    exact_rows = {i for v in exact.values() for i, _ in v}
    near_clusters = defaultdict(list)
    for i, r in have:
        if i in exact_rows:
            continue
        near_clusters[find(i)].append((i, r))
    near_clusters = [v for v in near_clusters.values() if len(v) > 1]

    # ---- stage 2: page evidence for every member row of every cluster
    idx = sha_index()
    dt = DocTexts(idx)
    cands = []

    def member_record(r, cluster_kind, shared_with):
        cos = row_cos(r)
        frag = co_fragment(cos)
        ev = []
        seen = set()
        for field_name in ("source_scheme_line", "source_syllabus"):
            for sha, pages, stem in cite_docs(r[field_name]):
                if sha in seen:
                    continue
                seen.add(sha)
                v, pg, ctx = dt.locate(sha, frag, pages)
                ev.append({"src": field_name, "sha16": sha, "doc": stem,
                           "doc_session": doc_session(stem), "cited_pages": pages,
                           "verdict": v, "found_page": pg, "print_ctx": ctx})
        found = any(e["verdict"] == "co_print_found" for e in ev)
        any_nf = any(e["verdict"] == "co_print_not_found" for e in ev)
        if any(e["verdict"] == "doc_unresolvable" for e in ev) and not found:
            v = "inconclusive_doc_unresolved"
        elif found:
            v = "co_print_found"
        elif any_nf and ev:
            v = "co_print_not_found"
        else:
            v = "no_citation"
        return {"sid": r["subject_id"], "course": r["course_name"],
                "primary_code": r["primary_code"],
                "subject_name": r["subject_name"][:90],
                "effective_session_latest": r["effective_session_latest"],
                "co_count": r["co_count"], "n_co_slots": len(cos),
                "cluster_kind": cluster_kind,
                "cluster_size": len(shared_with),
                "co1_stored": cos[0][:120],
                "verdict": v,
                "page_evidence": ev}

    for k, mem in sorted(exact.items(), key=lambda x: -len(x[1])):
        recs = [member_record(r, "exact", mem) for _, r in mem]
        found = [m for m in recs if m["verdict"] == "co_print_found"]
        nf = [m for m in recs if m["verdict"] == "co_print_not_found"]
        if len(found) >= 2:
            cv = "attested_print_duplication"
        elif len(found) == 1 and nf:
            cv = "drafting_side_duplication_review"
        elif len(found) == 1:
            cv = "inconclusive_partial"
        elif nf:
            cv = "co_print_unverified_review"
        elif any(m["verdict"] == "inconclusive_doc_unresolved" for m in recs):
            cv = "inconclusive_doc_unresolved"
        else:
            cv = "no_citation"
        cands.append({"cluster": "exact", "cluster_verdict": cv,
                      "n_rows": len(recs),
                      "courses": sorted({m["course"] for m in recs}),
                      "cross_program": len({m["course"] for m in recs}) > 1,
                      "members": recs})

    for mem in near_clusters:
        recs = [member_record(r, "near", mem) for _, r in mem]
        found = [m for m in recs if m["verdict"] == "co_print_found"]
        nf = [m for m in recs if m["verdict"] == "co_print_not_found"]
        if len(found) >= 2:
            cv = "attested_print_duplication"
        elif len(found) == 1 and nf:
            cv = "drafting_side_duplication_review"
        elif len(found) == 1:
            cv = "inconclusive_partial"
        elif nf:
            cv = "co_print_unverified_review"
        elif any(m["verdict"] == "inconclusive_doc_unresolved" for m in recs):
            cv = "inconclusive_doc_unresolved"
        else:
            cv = "no_citation"
        cands.append({"cluster": "near(J>=0.85)", "cluster_verdict": cv,
                      "n_rows": len(recs),
                      "courses": sorted({m["course"] for m in recs}),
                      "cross_program": len({m["course"] for m in recs}) > 1,
                      "members": recs})

    led = {
        "run_id": RUN_ID,
        "test": "T10 CO duplication across rows",
        "policy": "LEDGER-ONLY stage-1+2; no CSV/quality_flags change; print wins per 6b/B76",
        "rule": {
            "signature": "ordered tuple of normalized non-empty co1..co6 texts, MIN_CO>=3",
            "exact_cluster": ">=2 rows identical signature",
            "near_cluster": "token-Jaccard >= 0.85 on concatenated CO text, not exact, prefilter shared>=8 tokens & >=70% of smaller set",
            "stage2": "own-cited-doc CO1 fragment search (squashed, cited pages first then whole doc); cluster attested only when >=2 member docs print the same shared text",
        },
        "counts": {
            "subject_rows": len(rows),
            "rows_with_co>=3": len(have),
            "rows_skipped_lt3co": skipped_lt3,
            "exact_clusters": len(exact),
            "exact_rows": sum(len(v) for v in exact.values()),
            "near_clusters": len(near_clusters),
            "near_rows": sum(len(v) for v in near_clusters),
        },
        "candidates_stage2": cands,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    out = os.path.join(PROBE_DIR, "t10_probe_ledger.json")
    json.dump(led, open(out, "w"), indent=1)

    vc = Counter(c["cluster_verdict"] for c in cands)
    mv = Counter(m["verdict"] for c in cands for m in c["members"])
    print(f"T10 stage1: exact {len(exact)} clusters/"
          f"{sum(len(v) for v in exact.values())} rows + near {len(near_clusters)}/"
          f"{sum(len(v) for v in near_clusters)} rows "
          f"(pool {len(have)} of {len(rows)}; skipped_lt3co={skipped_lt3})")
    print("cluster verdicts:", dict(vc))
    print("member verdicts:", dict(mv))
    for c in cands:
        for m in c["members"]:
            print(f"  - {m['sid']} {m['primary_code']} [{c['cluster']}|"
                  f"{'+'.join(x[:4] for x in c['courses'])}] {m['verdict']} :: "
                  f"{m['co1_stored'][:60]}")


if __name__ == "__main__":
    main()
