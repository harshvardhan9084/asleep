#!/usr/bin/env python3
"""t8_quality_probe.py — quality-test cascade T8 (owner plan 2026-11-11), batch CRON-20261112-B84.

T8 = branch coherence (P2, expected yield: low).
  Stage 1: code family vs branch. Rule table is CORPUS-DERIVED, not hand-guessed:
           per-(course, family) histogram over the branch tokens of branch-bearing
           rows. A family is "established" for branch B when n>=10 rows carry
           branch data and B holds >=0.60 share. A family whose branch-bearing
           rows spread across >=8 distinct branches is a UNIVERSAL family
           (elective/service composition, e.g. BOE open electives) — never a
           mismatch candidate. Families with <10 branch-bearing rows cannot
           establish a rule honestly — suppressed as family_small_or_spread.
           A hit = row whose family is established for B but whose own branch
           token set has NO token compatible with B (compatibility = squash
           equality, containment, or common prefix >=12 chars — handles
           'Electrical Engg.' vs 'Electrical Engineering' and CSE(AI) suffixes).
  Stage 2: for hits ONLY, own-cited-doc page evidence (fitz text layer of the
           row's OWN cited scheme/syllabus docs — cited pages first, whole-doc
           fallback for pp.as-drafted citations, same method as T1/T3):
           locate the primary code, then scan the doc's title pages and the
           found page for branch mentions of the STORED branch vs the
           FAMILY-ESTABLISHED branch.
           print shows the stored branch  -> print_agrees_stored_attested
                                            (cross-branch service composition;
                                             print wins per 6b/B76, ledger note)
           print shows the family branch and never the stored branch
                                            -> print_proven_branch_incoherence
                                            (fix candidate for a LATER
                                             multi-confirmed batch)
           neither                          -> print_ambiguous_needs_fulldoc

Coverage honesty: 1,924 of 3,080 subject rows carry NO branch_names at all —
branch coherence is uncheckable for them (never invent a branch value); the
count is recorded as a coverage stat, not a pass. Only BTech (1,155 rows) and
MCA (1 row) carry branch data at all.

LEDGER-ONLY: writes work/pipeline_v2/probes/t8_probe_ledger.json (+ copy into
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
RUN_ID = "CRON-20261112-B84"

POOL_FAMS = {"BOE", "KOE", "ROE", "EOE", "NOE", "OE", "EAU", "KAU", "RAU", "NAU",
             "BAU", "AU", "NGP", "AGP", "GP", "VAC", "BVA", "NONCREDIT", "AUC",
             "ETAU", "O"}

UNIVERSAL_SPREAD = 8       # >=8 distinct branches on branch-bearing rows -> universal
EST_MIN_ROWS = 10          # family branch-bearing rows needed to establish a rule
EST_SHARE = 0.60           # top-branch share needed

# AKTU's own printed branch-name variants (recorded corpus spellings, e.g. the
# 2020-21 AG model-curriculum prints 'Agriculture Engineering' while scheme
# rows print 'Agricultural Engineering') — variant equality = same branch.
BRANCH_TOKEN_VARIANTS = {
    "agriculturalengineering": ["agricultureengineering", "agriculturalengg",
                                "agricultureengg"],
}


def squash(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def code_prefix(pc):
    m = re.match(r"^([A-Za-z]+)", (pc or "").strip())
    return m.group(1).upper() if m else ""


def branch_tokens(branch_names):
    toks = []
    for t in re.split(r"[;]", branch_names or ""):
        t = t.strip()
        if t:
            toks.append(squash(t))
    return toks


def compat(a, b):
    """branch-token compatibility: equality, containment, or shared prefix
    >=12 chars (Electrical 'Engg' vs 'Engineering'; CSE(AI) vs CSE)."""
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    return len(a) >= 12 and len(b) >= 12 and a[:12] == b[:12]


def expand_tokens(tokens):
    out = list(tokens)
    for t in tokens:
        out.extend(BRANCH_TOKEN_VARIANTS.get(t, []))
    return out


def set_has(tokens, target):
    return any(compat(t, target) for t in expand_tokens(tokens))


# ------------------------------------------------- corpus rule table
def build_branch_table(rows):
    tab = defaultdict(Counter)
    for r in rows:
        toks = branch_tokens(r["branch_names"])
        if not toks:
            continue
        f = code_prefix(r["primary_code"])
        if not f or f == "O" or f in POOL_FAMS:
            continue
        for t in set(toks):
            tab[(r["course_name"], f)][t] += 1
    return tab


def classify_family(entry):
    """(status, branch): 'tiny' | 'universal' | ('established', B) | 'spread'."""
    n = sum(entry.values())
    if n < EST_MIN_ROWS:
        return ("tiny", None)
    if len(entry) >= UNIVERSAL_SPREAD:
        return ("universal", None)
    b, cnt = entry.most_common(1)[0]
    if cnt / n >= EST_SHARE:
        return ("established", b)
    return ("spread", None)


# ------------------------------------------------- stage 2 page evidence
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
        out.append((m.group(2), pg))
    return out


def code_regex(code):
    parts = [re.escape(ch) for ch in re.sub(r"[^A-Za-z0-9]", "", code)]
    if not parts:
        return None
    return re.compile(r"[-\s.:()]*".join(parts), re.IGNORECASE)


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
            return ("found", pg, ctx[:320], doc, pages)
    return ("code_not_in_doc", None, "", doc, pages)


def doc_branch_scan(doc, stored_tokens, fam_branch):
    """whole-doc branch mention scan (fitz text layer, all pages, variant-aware).
    Returns (stored_hits, fam_hits, title_ctx)."""
    stored_hits, fam_hits = [], []
    title_ctx = ""
    n = doc.page_count
    for pg in range(1, min(n, 60) + 1):
        text = doc[pg - 1].get_text("text")
        sq = squash(text)
        # per-token scan (containment on squashed page text; variant-aware)
        for t in set(expand_tokens(stored_tokens)):
            if len(t) >= 10 and t in sq and (pg, t) not in stored_hits:
                stored_hits.append((pg, t))
        if fam_branch and len(fam_branch) >= 10 and fam_branch in sq \
                and (pg, fam_branch) not in fam_hits:
            fam_hits.append((pg, fam_branch))
        if pg == 1:
            title_ctx = " | ".join(
                l.strip() for l in text.splitlines() if l.strip())[:300]
    return stored_hits[:6], fam_hits[:6], title_ctx


def page_check(c, idx):
    ev = []
    stored_tokens = [t for t in c["branch_tokens"] if len(t) >= 8]
    for field_name in ("cites_scheme", "cites_syllabus"):
        for sha, pages in c[field_name]:
            pdf = idx.get(sha)
            if not pdf:
                ev.append({"src": field_name, "sha16": sha, "verdict": "doc_unresolvable"})
                continue
            v, pg, ctx, doc, cited = locate_code(pdf, code_regex(c["primary_code"]),
                                                 pages, c["subject_name"].lower())
            entry = {"src": field_name, "sha16": sha, "cited_pages": cited,
                     "found_page": pg, "verdict": v, "print": ctx}
            # title context is recorded for EVERY resolvable doc (even when the
            # code is absent from the text layer — title still shows which
            # branch scheme the citation comes from)
            t1 = doc[0].get_text("text") if doc.page_count else ""
            entry["doc_title"] = " | ".join(
                l.strip() for l in t1.splitlines() if l.strip())[:300]
            title_sq = squash(t1)
            entry["title_prints_stored_branch"] = any(
                len(t) >= 10 and t in title_sq
                for t in expand_tokens(stored_tokens))
            if v == "found":
                st, fh, title = doc_branch_scan(doc, stored_tokens, c["family_branch"])
                entry["doc_stored_branch_mentions"] = st
                entry["doc_family_branch_mentions"] = fh
                # does the FOUND page itself name a branch? (variant-aware)
                page_sq = squash(doc[pg - 1].get_text("text"))
                entry["found_page_has_stored_branch"] = any(
                    len(t) >= 10 and t in page_sq
                    for t in expand_tokens(stored_tokens))
                entry["found_page_has_family_branch"] = bool(
                    len(c["family_branch"]) >= 10 and c["family_branch"] in page_sq)
            ev.append(entry)
            if v == "found":
                return ev
    return ev


def classify_hit(ev):
    """stage-2 verdict from the evidence list (print wins per 6b/B76)."""
    found = [e for e in ev if e.get("verdict") == "found"]
    if not found:
        if any(e.get("verdict") == "doc_unresolvable" for e in ev):
            return "inconclusive_doc_unresolved"
        if ev:
            return "code_not_in_any_cited_doc"
        return "no_citation"
    e = found[0]
    if e.get("found_page_has_stored_branch") or e.get("doc_stored_branch_mentions"):
        return "print_agrees_stored_attested"
    if e.get("found_page_has_family_branch") or e.get("doc_family_branch_mentions"):
        return "print_proven_branch_incoherence"
    # code only in a doc of another branch's scheme — but if OTHER cited docs
    # print the stored branch in their titles, this is the era multi-scheme
    # service-row class (define-once row cited across schemes; nothing
    # contradicts the stored branch): composition, not incoherence.
    others = [x for x in ev if x is not e and x.get("title_prints_stored_branch")]
    if others:
        return "era_multi_scheme_service_row"
    return "print_ambiguous_needs_fulldoc"


# ---------------------------------------------------------------- main
def mk_cand(r, fam, fam_branch, toks):
    cs, sy = [], []
    for m in re.finditer(r"([A-Za-z0-9_.\- ]+\.pdf)#([0-9a-f]{16})([^;]*)",
                         r["source_scheme_line"] or ""):
        cs.append((m.group(2), [int(x) for x in re.findall(r"p{1,2}\.(\d+)", m.group(3))]))
    for m in re.finditer(r"([A-Za-z0-9_.\- ]+\.pdf)#([0-9a-f]{16})([^;]*)",
                         r["source_syllabus"] or ""):
        sy.append((m.group(2), [int(x) for x in re.findall(r"p{1,2}\.(\d+)", m.group(3))]))
    return {"sid": r["subject_id"], "course": r["course_name"],
            "primary_code": r["primary_code"], "family": fam,
            "family_branch": fam_branch, "branch_stored": r["branch_names"],
            "branch_tokens": toks,
            "subject_name": r["subject_name"], "subject_name_print": r["subject_name_print"],
            "all_codes": r["all_codes"], "code_history_all": r["code_history_all"],
            "effective_session_latest": r["effective_session_latest"],
            "cites_scheme": cs, "cites_syllabus": sy}


def main():
    os.makedirs(PROBE_DIR, exist_ok=True)
    rows = [r for r in csv.DictReader(open(CSV_PATH)) if r.get("row_kind") == "subject"]
    md5 = hashlib.md5(open(CSV_PATH, "rb").read()).hexdigest()

    tab = build_branch_table(rows)
    status = {k: classify_family(v) for k, v in tab.items()}
    established = {k: b for k, (s, b) in status.items() if s == "established"}
    universal = {k for k, (s, _) in status.items() if s == "universal"}

    no_branch = sum(1 for r in rows if not r["branch_names"].strip())
    candidates, suppressed = [], Counter()
    for r in rows:
        b = r["branch_names"].strip()
        if not b:
            continue  # coverage stat, not a skip-class (recorded separately)
        toks = branch_tokens(b)
        f = code_prefix(r["primary_code"])
        if not f:
            suppressed["no_prefix"] += 1
            continue
        if f == "O" or f in POOL_FAMS:
            suppressed["pool_family"] += 1
            continue
        k = (r["course_name"], f)
        st, fam_branch = status.get(k, ("tiny", None))
        if st == "universal":
            suppressed["universal_family"] += 1
            continue
        if st == "tiny":
            suppressed["family_small_branchdata"] += 1
            continue
        if st == "spread":
            suppressed["family_spread_no_majority"] += 1
            continue
        if set_has(toks, fam_branch):
            continue
        candidates.append(mk_cand(r, f, fam_branch, toks))

    idx = sha_index()
    stage2 = []
    for c in candidates:
        s2 = dict(c)
        ev = page_check(c, idx)
        s2["page_evidence"] = ev
        s2["verdict"] = classify_hit(ev)
        stage2.append(s2)

    ledger = {
        "test_id": "T8", "run_id": RUN_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "csv_md5": md5, "rows_scanned": len(rows),
        "coverage": {
            "subject_rows": len(rows),
            "branch_bearing_rows": len(rows) - no_branch,
            "rows_without_branch_names": no_branch,
            "note": ("branch coherence is uncheckable without a stored branch — "
                     "never invent one; only BTech+MCA carry branch data"),
            "courses_with_branch_data": sorted({r["course_name"] for r in rows
                                                if r["branch_names"].strip()}),
        },
        "families_established": {f"{c}|{f}": b for (c, f), b in sorted(established.items())},
        "families_universal": sorted(f"{c}|{f}" for (c, f) in universal),
        "families_table_size": len(tab),
        "stage1_skip_reasons": dict(suppressed),
        "stage1_candidates": len(candidates),
        "stage2_verdict_counts": dict(Counter(s["verdict"] for s in stage2)),
        "candidates_stage2": stage2,
        "note": ("ledger-only. rule table corpus-derived: family established for a "
                 "branch when n>=10 branch-bearing rows and top-branch share>=0.60; "
                 "spread>=8-branch families are universal composition (BOE/BCS "
                 "elective classes) and never candidates; <10-row families cannot "
                 "establish a rule honestly (suppressed, recorded); compat = squash "
                 "equality/containment/prefix>=12 (Engg/Engineering, CSE(AI) suffix); "
                 "stage-2 = own-cited-doc code locate + whole-doc branch-mention scan "
                 "(variant-aware: AKTU prints both 'Agricultural' and 'Agriculture' "
                 "Engineering); title context recorded for every resolvable doc even "
                 "when the code is text-layer-absent; print wins per 6b/B76: "
                 "print_agrees rows are recorded cross-branch service-composition "
                 "classes, era_multi_scheme_service_row = code printed in another "
                 "scheme's doc while other cited docs carry the stored branch in "
                 "their titles (define-once multi-scheme row, no contradiction), "
                 "print_proven rows would be fix candidates for a later "
                 "multi-confirmed batch — NO fixes, NO flags this batch."),
    }
    with open(f"{PROBE_DIR}/t8_probe_ledger.json", "w") as fh:
        json.dump(ledger, fh, indent=1)

    print(f"T8 stage1: {len(candidates)} candidates from {len(rows)} rows "
          f"({len(tab)} families, {len(established)} established, {len(universal)} universal)")
    print("coverage:", ledger["coverage"]["branch_bearing_rows"], "branch-bearing,",
          no_branch, "without branch_names")
    print("skips:", dict(suppressed))
    print("stage2 verdicts:", ledger["stage2_verdict_counts"])
    for s in stage2:
        print(f"  - {s['sid']} {s['primary_code']} [{s['family']}->{s['family_branch']}] "
              f"stored={s['branch_stored'][:42]!r} :: {s['subject_name'][:48]} -> {s['verdict']}")


if __name__ == "__main__":
    main()
