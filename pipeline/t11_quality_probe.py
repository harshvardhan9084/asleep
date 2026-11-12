#!/usr/bin/env python3
"""t11_quality_probe.py — quality-test cascade T11 (owner plan 2026-11-11), batch CRON-20261112-B87.

T11 = cross-course same-code consistency (P2, expected yield: low).
  Stage 1: two deterministic lenses over the code space (never invents — the
           corpus alone decides what counts):
             Lens A (primary key): primary_code groups whose rows span >=2
               distinct course_name values. Pairwise identity via normalized
               subject-name ratio (>=0.8 same_identity, else collision suspect).
             Lens B (code-field membership, plan columns all_codes +
               code_history_all): a code that is some row's PRIMARY in course X
               and appears in another row's code fields in course Y. Identity
               split identical to Lens A; mismatch = xref suspect.
           Same-course code sharing is T1's domain (already adjudicated there) —
           skipped here by construction (both lenses require course_name to
           differ). Pool families are NOT skipped: cross-course pool-code reuse
           (GP/NGP) is exactly what stage 2 must print-verify.
  Stage 2: for every involved row, own-cited-doc page evidence (fitz text
           layer, cited pages first then whole doc, same sha index and
           name_near method as T1/T3/T7/T8): locate the code and check the
           printed subject name against the row's stored name.
             both sides' docs print the code, names consistent
                                      -> attested_cross_course_shared
             the other course's doc prints the code for a DIFFERENT subject
                                      -> print_confirms_distinct
                                         (code collision; fix/flag candidate
                                          for a LATER multi-confirmed batch)
             print absent / sha unresolvable / no citation -> unverified classes.

LEDGER-ONLY: writes work/pipeline_v2/probes/t11_probe_ledger.json (+ copy into
syllabus_catalog/owner_requests/). No CSV write, no quality_flags change
(standing mechanics: multi-stage confirmation first). Never invents a value —
every candidate carries stored + printed evidence.
"""
import csv
import difflib
import hashlib
import json
import os
import re
from collections import defaultdict, Counter
from datetime import datetime, timezone

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
PROBE_DIR = "/home/z/my-project/work/pipeline_v2/probes"
REPO = "/home/z/my-project/work/repo_asleep"
RUN_ID = "CRON-20261112-B87"

IDENTITY_RATIO = 0.8   # normalized subject-name ratio for "same identity"


def squash(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def norm_name(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()


def row_codes(r):
    out = set()
    for f in ("primary_code", "all_codes", "code_history_all"):
        for c in re.split(r"[;,]", r[f] or ""):
            c = squash(c)
            if c:
                out.add(c)
    return out


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


def code_regex(code):
    parts = [re.escape(ch) for ch in re.sub(r"[^A-Za-z0-9]", "", code)]
    if not parts:
        return None
    return re.compile(r"[-\s.:()/]*".join(parts), re.IGNORECASE)


STOPW = {"and", "of", "the", "for", "in", "i", "ii", "iii", "iv", "v", "lab",
         "practical", "theory", "a", "its", "with"}


def name_near(stored_norm, lines, i):
    win = " ".join(lines[max(0, i - 1):i + 6]).lower()
    wt = {t for t in re.split(r"[^a-z0-9]+", win) if len(t) >= 4}
    st = [t for t in stored_norm.split() if t not in STOPW and len(t) >= 3]
    if not st:
        return False
    hit = sum(1 for t in st
              if any(w.startswith(t[:4]) or t.startswith(w[:4]) for w in wt))
    return hit / len(st) >= 0.6 or (hit >= 2 and len(st) <= 3)


def locate_code(pdf, code_re, pages, stored_norm):
    import fitz
    doc = fitz.open(pdf)
    n = doc.page_count
    scan = [p for p in pages if 1 <= p <= n] or list(range(1, n + 1))
    for pg in scan:
        lines = [l.strip() for l in doc[pg - 1].get_text("text").splitlines() if l.strip()]
        for i, l in enumerate(lines):
            if not code_re.search(l.replace(" ", "")):
                continue
            n_codes = len({m.group(0) for m in re.finditer(r"[A-Z]{2,4}[-\s]?\d{2,4}", l.upper())})
            if n_codes >= 2 and not name_near(stored_norm, lines, i):
                continue
            ctx = l
            for j in range(i + 1, min(i + 4, len(lines))):
                ctx += " || " + lines[j]
            doc.close()
            return ("found", pg, ctx[:320])
    doc.close()
    return ("code_not_in_doc", None, "")


def page_check(r, code, idx):
    ev = []
    seen = set()
    for field_name in ("source_scheme_line", "source_syllabus"):
        for sha, pages, stem in cite_docs(r[field_name]):
            if sha in seen:
                continue
            seen.add(sha)
            pdf = idx.get(sha)
            if not pdf:
                ev.append({"src": field_name, "sha16": sha, "doc": stem,
                           "doc_session": doc_session(stem),
                           "verdict": "doc_unresolvable"})
                continue
            cre = code_regex(code)
            if not cre:
                ev.append({"src": field_name, "sha16": sha, "doc": stem,
                           "verdict": "no_code"})
                continue
            v, pg, ctx = locate_code(pdf, cre, pages, norm_name(r["subject_name"]))
            ev.append({"src": field_name, "sha16": sha, "doc": stem,
                       "doc_session": doc_session(stem), "cited_pages": pages,
                       "found_page": pg, "verdict": v, "print": ctx})
    return ev


# ---------------------------------------------------------------- main
def main():
    os.makedirs(PROBE_DIR, exist_ok=True)
    with open(CSV_PATH) as f:
        rows = [r for r in csv.DictReader(f) if r["row_kind"] == "subject"]

    # ---------------- Lens A: cross-course primary_code groups
    g = defaultdict(list)
    for r in rows:
        k = squash(r["primary_code"])
        if k:
            g[k].append(r)
    lens_a = []
    a_skipped_same_course = 0
    for k, v in sorted(g.items()):
        courses = {r["course_name"] for r in v}
        if len(courses) < 2:
            continue
        for i in range(len(v)):
            for j in range(i + 1, len(v)):
                a, b = v[i], v[j]
                if a["course_name"] == b["course_name"]:
                    a_skipped_same_course += 1
                    continue
                ratio = difflib.SequenceMatcher(
                    None, norm_name(a["subject_name"]), norm_name(b["subject_name"])).ratio()
                lens_a.append({"code": k, "pair": [a["subject_id"], b["subject_id"]],
                               "courses": [a["course_name"], b["course_name"]],
                               "names": [a["subject_name"][:60], b["subject_name"][:60]],
                               "name_ratio": round(ratio, 3),
                               "class": "same_identity" if ratio >= IDENTITY_RATIO
                                        else "identity_mismatch"})

    # ---------------- Lens B: code primary-owned in course X, referenced in course Y
    primary = {squash(r["primary_code"]): r for r in rows if squash(r["primary_code"])}
    lens_b = []
    b_skipped_same_course = 0
    b_same_identity = 0
    for r in rows:
        cr = r["course_name"]
        for c in sorted(row_codes(r)):
            p = primary.get(c)
            if p is None or p["course_name"] == cr or p["subject_id"] == r["subject_id"]:
                continue
            ratio = difflib.SequenceMatcher(
                None, norm_name(p["subject_name"]), norm_name(r["subject_name"])).ratio()
            if ratio >= IDENTITY_RATIO:
                b_same_identity += 1
                continue
            lens_b.append({"code": c, "owner_sid": p["subject_id"],
                           "owner_course": p["course_name"],
                           "owner_name": p["subject_name"][:60],
                           "ref_sid": r["subject_id"], "ref_course": cr,
                           "ref_name": r["subject_name"][:60],
                           "name_ratio": round(ratio, 3),
                           "class": "xref_identity_mismatch"})
    lens_b.sort(key=lambda x: x["code"])

    # ---------------- stage 2: page evidence
    idx = sha_index()
    by_sid = {r["subject_id"]: r for r in rows}
    checked_sids = {}
    cands = []

    def check_row(sid, code):
        if sid not in checked_sids:
            r = by_sid[sid]
            ev = page_check(r, code, idx)
            found = [e for e in ev if e.get("verdict") == "found"]
            if found:
                v = "code_print_found"
            elif any(e.get("verdict") == "doc_unresolvable" for e in ev):
                v = "inconclusive_doc_unresolved"
            elif ev:
                v = "code_print_not_found"
            else:
                v = "no_citation"
            checked_sids[sid] = {"sid": sid, "course": by_sid[sid]["course_name"],
                                 "primary_code": by_sid[sid]["primary_code"],
                                 "subject_name": by_sid[sid]["subject_name"][:90],
                                 "checked_code": code, "verdict": v,
                                 "page_evidence": ev}
        return checked_sids[sid]

    for a in lens_a:
        m = [check_row(a["pair"][0], a["code"]), check_row(a["pair"][1], a["code"])]
        f = [x for x in m if x["verdict"] == "code_print_found"]
        if a["class"] == "same_identity":
            cv = ("attested_cross_course_shared"
                  if len(f) == 2 else "unverified_shared_pair")
        elif len(f) == 2:
            # both docs print the code: compare PRINTED names across the two
            # courses (print wins per 6b) — a stored-name variant is NOT a
            # collision; only prints that name genuinely different subjects are.
            x_lines = next(e["print"].split(" || ") for x in f for e in x["page_evidence"]
                           if e.get("verdict") == "found")
            y_lines = next(e["print"].split(" || ") for x in reversed(f)
                           for e in x["page_evidence"] if e.get("verdict") == "found")
            cross = (name_near(norm_name(m[0]["subject_name"]), y_lines, 0)
                     or name_near(norm_name(m[1]["subject_name"]), x_lines, 0))
            cv = ("attested_cross_course_shared" if cross
                  else "print_confirms_distinct")
        else:
            cv = ("needs_print_verification" if f else "unverified_pair")
        cands.append({"lens": "A(primary_key)", "code": a["code"],
                      "class": a["class"], "name_ratio": a["name_ratio"],
                      "names": a["names"], "verdict": cv, "rows": m})

    for b in lens_b:
        m = [check_row(b["owner_sid"], b["code"]), check_row(b["ref_sid"], b["code"])]
        # lens-B findings are CODE-FIELD LISTING anomalies (course-Y row lists a
        # code primary-owned in course X) — prints of both rows can be perfectly
        # coherent; the print never "confirms distinct" here. Record as review.
        cv = "xref_listing_review"
        cands.append({"lens": "B(code_fields)", "code": b["code"],
                      "class": b["class"], "name_ratio": b["name_ratio"],
                      "names": [b["owner_name"], b["ref_name"]],
                      "verdict": cv, "rows": m})

    led = {
        "run_id": RUN_ID,
        "test": "T11 cross-course same-code consistency",
        "policy": "LEDGER-ONLY stage-1+2; no CSV/quality_flags change; print wins per 6b/B76",
        "rule": {
            "lens_A": "primary_code groups spanning >=2 course_name values; pairwise identity = normalized name ratio >=0.8",
            "lens_B": "code primary-owned in course X and listed in all_codes/code_history_all of a course-Y row; identity split identical",
            "stage2": "own-cited-doc code locate + printed-name check per row (fitz text layer, cited pages first)",
        },
        "counts": {
            "subject_rows": len(rows),
            "lensA_cross_course_pairs": len(lens_a),
            "lensA_same_identity": sum(1 for a in lens_a if a["class"] == "same_identity"),
            "lensA_identity_mismatch": sum(1 for a in lens_a if a["class"] == "identity_mismatch"),
            "lensA_same_course_pairs_skipped": a_skipped_same_course,
            "lensB_xref_mismatch": len(lens_b),
            "lensB_same_identity_refs": b_same_identity,
            "lensB_same_course_skipped": b_skipped_same_course,
        },
        "candidates_stage2": cands,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    out = os.path.join(PROBE_DIR, "t11_probe_ledger.json")
    json.dump(led, open(out, "w"), indent=1)

    print(f"T11 stage1: lensA {len(lens_a)} cross-course pairs "
          f"({led['counts']['lensA_same_identity']} same / "
          f"{led['counts']['lensA_identity_mismatch']} mismatch); "
          f"lensB {len(lens_b)} xref-mismatch refs ({b_same_identity} same-identity refs skipped)")
    print("verdicts:", dict(Counter(c["verdict"] for c in cands)))
    for c in cands:
        print(f"  - {c['code']} [{c['lens']}|{c['class']}] r={c['name_ratio']} "
              f":: {' vs '.join(n[:28] for n in c['names'])} -> {c['verdict']}")
        for m in c["rows"]:
            print(f"      {m['sid']} {m['primary_code']} [{m['course']}] {m['verdict']}")


if __name__ == "__main__":
    main()
