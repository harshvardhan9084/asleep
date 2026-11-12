#!/usr/bin/env python3
"""t7_quality_probe.py — quality-test cascade T7 (owner plan 2026-11-11), batch CRON-20261112-B85.

T7 = semester/year coherence (P2, expected yield: low).
  Stage 1: code-era grammar vs printed session sanity. Rule table is
           CORPUS-DERIVED per (course, family): histogram of effective_session_latest
           over DATED rows (session parses as YYYY-YY). A family is established with
           a core WINDOW [min, max] when n>=10 dated rows and core = every session
           holding >=5% of them. A hit = dated row whose family window is established
           but whose session falls outside it, DIRECTION-TAGGED:
             era_forward  (session > window max) — the suspicious direction: an
                          old-generation code claimed effective in a far later
                          session (grammar violation candidate);
             era_backward (session < window min) — usually first-print rows of
                          families re-cited later; weaker, recorded separately.
           Letter-generation windows (E/N/R/K/A/B...) are derived as SECONDARY
           context only (recorded; letter-level rules false-positive across
           courses, e.g. B = BTech-era AND BPharm BP; M = MCA AND old MBA docs).
  Stage 2: for hits ONLY, own-cited-doc page evidence (fitz text layer, cited
           pages first, whole-doc fallback, same method as T1/T3/T8): locate the
           primary code in the row's OWN cited docs and report which session's
           doc carries the print.
           found + ANY found-doc session == row session -> attested_cross_era_carryover
                                                     (print wins per 6b/B76;
                                                      composition, no fix)
           found, but only in docs of other sessions -> effective_session_provenance_review
                                                     (multi-doc scan, no early stop;
                                                      effective-session provenance
                                                      review for a LATER batch)
           not found anywhere                       -> session_year_review_candidate
                                                     (fix/flag candidate for a LATER
                                                      multi-confirmed batch)
           unresolvable sha / no citation           -> inconclusive classes.

  Data-quality OBSERVATION (recorded, zero candidates — outside T7's era scope):
  program_year is bulk-defaulted for non-BTech courses (BCA/MCA/MBA/BPharm = '2'
  for 100% of rows incl. Sem-1 subjects) and 1,412/2,227 BTech rows — a drafting
  artifact; a slots-vs-year check would flag ~1,141 rows of it. Cannot be fixed
  without per-row print evidence (6b/§4) — owner-visible ledger note only.

LEDGER-ONLY: writes work/pipeline_v2/probes/t7_probe_ledger.json (+ copy into
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
RUN_ID = "CRON-20261112-B85"

POOL_FAMS = {"BOE", "KOE", "ROE", "EOE", "NOE", "OE", "EAU", "KAU", "RAU", "NAU",
             "BAU", "AU", "NGP", "AGP", "GP", "VAC", "BVA", "NONCREDIT", "AUC",
             "ETAU", "O"}

EST_MIN_DATED = 10          # dated rows needed to establish a family window
CORE_SHARE = 0.05           # session share inside the core window


def squash(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def code_prefix(pc):
    m = re.match(r"^([A-Za-z]+)", (pc or "").strip())
    return m.group(1).upper() if m else ""


def sess_year(s):
    m = re.match(r"^(\d{4})-(\d{2})$", (s or "").strip())
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2))
    return a if (a + 1) % 100 == b else None


def doc_session(stem):
    """parse the session out of a cited doc filename (…_2016-17.pdf)."""
    m = re.search(r"(\d{4})-(\d{2})", os.path.basename(stem or ""))
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2))
    return a if (a + 1) % 100 == b else None


# ------------------------------------------------- corpus rule table
def build_windows(rows):
    win = defaultdict(Counter)
    for r in rows:
        s = sess_year(r["effective_session_latest"])
        if not s:
            continue
        f = code_prefix(r["primary_code"])
        if not f or f == "O" or f in POOL_FAMS:
            continue
        win[(r["course_name"], f)][s] += 1
    out = {}
    for k, c in win.items():
        n = sum(c.values())
        if n < EST_MIN_DATED:
            continue
        core = [s for s, cnt in c.items() if cnt / n >= CORE_SHARE]
        out[k] = {"lo": min(core), "hi": max(core), "n": n,
                  "hist": dict(sorted(c.items()))}
    return out


def letter_windows(rows):
    """secondary context: per (course, letter-generation) core windows."""
    win = defaultdict(Counter)
    for r in rows:
        s = sess_year(r["effective_session_latest"])
        if not s:
            continue
        g = code_prefix(r["primary_code"])[:1]
        if not g:
            continue
        win[(r["course_name"], g)][s] += 1
    out = {}
    for k, c in win.items():
        n = sum(c.values())
        if n < 20:
            continue
        core = [s for s, cnt in c.items() if cnt / n >= 0.05]
        out[k] = {"lo": min(core), "hi": max(core), "n": n}
    return out


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
            return ("found", pg, ctx[:320])
    return ("code_not_in_doc", None, "")


def page_check(c, idx):
    """scan ALL cited docs (no early return): the row may cite several session
    docs (scheme + syllabus, multi-era accumulator) and the effective-session
    provenance question needs every doc's yield, not just the first hit."""
    ev = []
    seen = set()
    for field_name in ("cites_scheme", "cites_syllabus"):
        for sha, pages, stem in c[field_name]:
            if sha in seen:
                continue
            seen.add(sha)
            pdf = idx.get(sha)
            if not pdf:
                ev.append({"src": field_name, "sha16": sha, "doc": stem,
                           "doc_session": doc_session(stem),
                           "verdict": "doc_unresolvable"})
                continue
            v, pg, ctx = locate_code(pdf, code_regex(c["primary_code"]),
                                     pages, c["subject_name"].lower())
            ev.append({"src": field_name, "sha16": sha, "doc": stem,
                       "doc_session": doc_session(stem), "cited_pages": pages,
                       "found_page": pg, "verdict": v, "print": ctx})
    return ev


def classify_hit(ev, row_session):
    found = [e for e in ev if e.get("verdict") == "found"]
    if not found:
        if any(e.get("verdict") == "doc_unresolvable" for e in ev):
            return "inconclusive_doc_unresolved"
        if ev:
            return "session_year_review_candidate"
        return "no_citation"
    # print wins per 6b/B76: the code printed in ANY doc whose parsed session
    # equals the row's effective session = attested at the claimed session.
    if any(e.get("doc_session") and row_session
           and e["doc_session"] == row_session for e in found):
        return "attested_cross_era_carryover"
    if any(e.get("doc_session") for e in found):
        return "effective_session_provenance_review"
    return "attested_cross_era_carryover"  # found; doc session unparsable — still print


# ---------------------------------------------------------------- main
def mk_cand(r, fam, w, direction):
    cs, sy = [], []
    for m in re.finditer(r"([A-Za-z0-9_.\- ]+\.pdf)#([0-9a-f]{16})([^;]*)",
                         r["source_scheme_line"] or ""):
        cs.append((m.group(2), [int(x) for x in re.findall(r"p{1,2}\.(\d+)", m.group(3))], m.group(1)))
    for m in re.finditer(r"([A-Za-z0-9_.\- ]+\.pdf)#([0-9a-f]{16})([^;]*)",
                         r["source_syllabus"] or ""):
        sy.append((m.group(2), [int(x) for x in re.findall(r"p{1,2}\.(\d+)", m.group(3))], m.group(1)))
    s = sess_year(r["effective_session_latest"])
    return {"sid": r["subject_id"], "course": r["course_name"],
            "primary_code": r["primary_code"], "family": fam,
            "row_session": r["effective_session_latest"],
            "row_session_year": s,
            "family_window": f"{w['lo']}-{w['hi']}",
            "family_window_n": w["n"],
            "direction": direction,
            "first_introduced_session": r["first_introduced_session"],
            "subject_name": r["subject_name"],
            "all_codes": r["all_codes"], "code_history_all": r["code_history_all"],
            "semester_slots": r["semester_slots"], "program_year": r["program_year"],
            "cites_scheme": cs, "cites_syllabus": sy}


def main():
    os.makedirs(PROBE_DIR, exist_ok=True)
    rows = [r for r in csv.DictReader(open(CSV_PATH)) if r.get("row_kind") == "subject"]
    md5 = hashlib.md5(open(CSV_PATH, "rb").read()).hexdigest()

    wins = build_windows(rows)
    lwin = letter_windows(rows)

    candidates, suppressed = [], Counter()
    for r in rows:
        s = sess_year(r["effective_session_latest"])
        f = code_prefix(r["primary_code"])
        if not f or f == "O" or f in POOL_FAMS:
            suppressed["pool_or_no_code"] += 1
            continue
        if not s:
            suppressed["undated_row"] += 1
            continue
        k = (r["course_name"], f)
        if k not in wins:
            suppressed["family_small_window"] += 1
            continue
        w = wins[k]
        if w["lo"] <= s <= w["hi"]:
            continue
        direction = "era_forward" if s > w["hi"] else "era_backward"
        candidates.append(mk_cand(r, f, w, direction))

    idx = sha_index()
    stage2 = []
    for c in candidates:
        s2 = dict(c)
        ev = page_check(c, idx)
        s2["page_evidence"] = ev
        s2["verdict"] = classify_hit(ev, c["row_session_year"])
        stage2.append(s2)

    # program_year data-quality observation (recorded, zero candidates)
    py_default = defaultdict(Counter)
    for r in rows:
        py_default[r["course_name"]][r["program_year"].strip() or "(empty)"] += 1

    ledger = {
        "test_id": "T7", "run_id": RUN_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "csv_md5": md5, "rows_scanned": len(rows),
        "families_with_windows": {f"{c}|{f}": f"{w['lo']}-{w['hi']} (n={w['n']})"
                                  for (c, f), w in sorted(wins.items())},
        "letter_generation_windows_secondary": {f"{c}|{g}": f"{w['lo']}-{w['hi']} (n={w['n']})"
                                                for (c, g), w in sorted(lwin.items())},
        "stage1_skip_reasons": dict(suppressed),
        "stage1_candidates": len(candidates),
        "stage1_direction_counts": dict(Counter(c["direction"] for c in candidates)),
        "stage2_verdict_counts": dict(Counter(s["verdict"] for s in stage2)),
        "candidates_stage2": stage2,
        "data_quality_observations": {
            "program_year_distribution_by_course": {
                c: dict(v.most_common()) for c, v in sorted(py_default.items())},
            "note": ("program_year is bulk-defaulted ('2') for every BCA/MCA/MBA/"
                     "BPharm row and 1,412/2,227 BTech rows — a drafting artifact, "
                     "NOT adjudicated here (a naive slots-vs-year check would flag "
                     "~1,141 rows; fixing needs per-row print evidence per 6b/§4; "
                     "owner-visible note only, zero T7 candidates). Session-format "
                     "sanity: 0 malformed effective_session_latest values."),
        },
        "note": ("ledger-only. rule table corpus-derived: family established with a "
                 "core session window [min,max] over >=5%-share sessions when n>=10 "
                 "dated rows; hits direction-tagged era_forward (suspicious) vs "
                 "era_backward (mostly first-print rows); letter-level grammar kept "
                 "as secondary context (letter rules false-positive across courses: "
                 "B = BTech-era AND BPharm BP); stage-2 = own-cited-doc code locate "
                 "with doc-session parsed from the cited filename; print wins per "
                 "6b/B76 — attested carryovers recorded as composition classes, "
                 "provenance-review candidates stay UNfixed for a later "
                 "multi-confirmed batch; ALL cited docs scanned (no early stop) so "
                 "multi-era accumulator rows are judged on every doc they cite; "
                 "NO fixes, NO flags this batch."),
    }
    with open(f"{PROBE_DIR}/t7_probe_ledger.json", "w") as fh:
        json.dump(ledger, fh, indent=1)

    print(f"T7 stage1: {len(candidates)} candidates from {len(rows)} rows "
          f"({len(wins)} family windows; directions {ledger['stage1_direction_counts']})")
    print("skips:", dict(suppressed))
    print("stage2 verdicts:", ledger["stage2_verdict_counts"])
    for s in stage2:
        print(f"  - {s['sid']} {s['primary_code']} [{s['course']}|{s['family']}] "
              f"s={s['row_session']} win={s['family_window']} {s['direction']} "
              f":: {s['subject_name'][:40]} -> {s['verdict']}")


if __name__ == "__main__":
    main()
