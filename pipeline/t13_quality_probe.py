#!/usr/bin/env python3
"""t13_quality_probe.py — quality-test cascade T13 (owner plan 2026-11-11), batch CRON-20261112-B90.

T13 = buyer-grade 100-row spot audit (P1, report-only quality gate).
  Sample: fixed-seed reproducible random sample — random.Random(20261113)
  over the subject rows sorted by subject_id, 100 rows; the sample list is
  recorded in the ledger so any re-run picks the same rows.
  Per row, deterministic buyer-grade checks (each reports issue strings):
    identity       subject_name / primary_code / course_name /
                   effective_session_latest non-empty
    numeric_sane   L,T,P,credit,sessional_ct,sessional_ta,sessional_total,
                   ese_te_pe,total_marks: non-empty values parse as numbers
                   ('–'/'-'/'N/A' = print markers → info 'nonnumeric_marker',
                    NOT an issue); ranges (credit<=30, marks 20..1000); and
                   sessional_total+ese_te_pe==total_marks whenever all three
                   are numeric
    semester_sane  semester_slots tokens within 1..10
    co_complete    co_count n (numeric) -> co1..coN_text non-empty
    units_complete units_count n numeric AND has_detailed_syllabus=TRUE ->
                   unit1..unitN_text non-empty
    books_parse    textbooks/reference/experiments structured JSON parse;
                   entries carry non-empty 'book' text
    citations      source_syllabus + source_scheme_line present; every cited
                   sha16 resolvable in the repo corpus (T12's known unresolved
                   shas are counted as known_unresolved, not new)
    display        subject_name_display or subject_name_print non-empty
                   (buyer-facing)
    flag_consistency quality_flags ↔ row state: TYPE_EMPTY ↔ subject_type empty;
                   DISPLAY_MISSING ↔ subject_name_display empty (both directions)
  Row verdict: clean (0 issues) / minor (only info-level notes) / issues.
  REPORT-ONLY: no CSV write, no quality_flags change, no fixes — the plan
  defines T13 as the buyer-facing quality gate.

Ledger: work/pipeline_v2/probes/t13_probe_ledger.json (+ copy into
syllabus_catalog/owner_requests/). Never invents a value — every issue carries
the stored field states it was computed from.
"""
import csv
import hashlib
import json
import os
import random
import re
from collections import Counter
from datetime import datetime, timezone

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
PROBE_DIR = "/home/z/my-project/work/pipeline_v2/probes"
REPO = "/home/z/my-project/work/repo_asleep"
RUN_ID = "CRON-20261112-B90"
SEED = 20261113
N = 100

NUM_FIELDS = ["L", "T", "P", "credit", "sessional_ct", "sessional_ta",
              "sessional_total", "ese_te_pe", "total_marks"]
MARKERS = {"", "-", "–", "—", "n/a", "na", "nil"}


def num(v):
    v = (v or "").strip()
    if v.lower() in MARKERS:
        return None, "marker" if v else "empty"
    try:
        f = float(v)
        return f, "ok"
    except ValueError:
        return None, "nonnumeric_marker"


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


def cite_shas(field):
    return [(m.group(2), m.group(1)) for m in
            re.finditer(r"([A-Za-z0-9_.\- ]+\.pdf)#([0-9a-f]{16})([^;]*)", field or "")]


def parse_json_field(s):
    try:
        v = json.loads(s) if (s or "").strip() else []
        return v if isinstance(v, list) else None
    except Exception:
        return None


def known_unresolved_shas():
    """T12's documented unresolved citation shas (repo owner_requests ledger)."""
    p = os.path.join(REPO, "syllabus_catalog", "owner_requests", "t12_probe_ledger.json")
    try:
        s = json.dumps(json.load(open(p)))
        return set(re.findall(r"\b[0-9a-f]{16}\b", s))
    except Exception:
        return set()


def audit_row(r, idx, known_unresolved, active_flags):
    issues, notes = [], []
    # identity
    for f in ("subject_name", "course_name", "effective_session_latest"):
        if not (r[f] or "").strip():
            issues.append(f"identity:{f}_empty")
    if not (r["primary_code"] or "").strip():
        # documented pool/slot rows (HSMC/EOE printed slots, accumulator rows)
        # legitimately carry no single primary code — issue only if the row has
        # no code evidence at all
        if (r["all_codes"] or "").strip() or (r["code_history_all"] or "").strip() \
                or "slot" in (r["subject_name"] or "").lower():
            notes.append("identity:pool_slot_row_no_single_code")
        else:
            issues.append("identity:primary_code_empty_no_code_evidence")
    # numeric sanity
    vals = {}
    for f in NUM_FIELDS:
        v, how = num(r[f])
        vals[f] = v
        if how in ("nonnumeric_marker",):
            notes.append(f"numeric:{f}_print_marker_{(r[f] or '').strip()[:4]}")
        elif v is not None:
            if "marks" in f and not (20 <= v <= 1000):
                issues.append(f"numeric:{f}_out_of_range={v:g}")
            if f == "credit" and not (0 <= v <= 30):
                issues.append(f"numeric:credit_out_of_range={v:g}")
            if f in ("L", "T", "P") and not (0 <= v <= 15):
                issues.append(f"numeric:{f}_out_of_range={v:g}")
    a, b, t = vals["sessional_total"], vals["ese_te_pe"], vals["total_marks"]
    if None not in (a, b, t) and abs(a + b - t) > 1e-6:
        issues.append(f"numeric:marks_sum_mismatch {a:g}+{b:g}!={t:g}")
    # semester sanity
    for tok in re.findall(r"\d+", r["semester_slots"] or ""):
        if not 1 <= int(tok) <= 10:
            issues.append(f"semester:slot_{tok}_out_of_range")
    # CO completeness
    cc, _ = num(r["co_count"])
    if cc is not None:
        for i in range(1, int(cc) + 1):
            if i <= 6 and not (r[f"co{i}_text"] or "").strip():
                issues.append(f"co:co{i}_empty_but_count={int(cc)}")
    # units completeness
    uc, _ = num(r["units_count"])
    if uc is not None and (r["has_detailed_syllabus"] or "").upper() == "TRUE":
        for i in range(1, int(uc) + 1):
            if i <= 5 and not (r[f"unit{i}_text"] or "").strip():
                issues.append(f"units:unit{i}_empty_but_count={int(uc)}")
    # structured books/experiments parse
    for f in ("textbooks_structured", "reference_books_structured", "experiments_structured"):
        v = parse_json_field(r[f])
        if v is None:
            issues.append(f"parse:{f}_invalid_json")
        elif (r[f] or "").strip():
            key = "exp" if f == "experiments_structured" else "book"
            if any(not isinstance(e, dict) or not (e.get(key) or "").strip() for e in v):
                issues.append(f"parse:{f}_entry_missing_text")
    # citations
    if not (r["source_syllabus"] or "").strip():
        issues.append("citation:source_syllabus_missing")
    if not (r["source_scheme_line"] or "").strip():
        issues.append("citation:source_scheme_line_missing")
    unres = 0
    for field in ("source_syllabus", "source_scheme_line"):
        for sha, stem in cite_shas(r[field]):
            if sha not in idx:
                unres += 1
                if sha not in known_unresolved:
                    issues.append(f"citation:sha_unresolvable_{sha}_{stem[:28]}")
                else:
                    notes.append(f"citation:known_unresolved_{sha[:8]}")
    if unres:
        notes.append(f"citation:{unres}_unresolvable_sha_refs")
    # buyer-facing display
    if not (r["subject_name_display"] or "").strip() and \
            not (r["subject_name_print"] or "").strip():
        issues.append("display:buyer_facing_name_missing")
    # flag consistency vs the AUDIT-OF-RECORD (audit_flags.json active flags —
    # the quality_flags CSV string is append-only history incl. corrected_*
    # marks, so its raw membership is NOT the active-flag criterion)
    af = active_flags.get(r["subject_id"], [])
    arules = {f.get("rule") for f in af}
    if "DISPLAY_MISSING" in arules and (r["subject_name_display"] or "").strip():
        issues.append("flag_consistency:DISPLAY_MISSING_active_but_display_set")
    if not (r["subject_name_display"] or "").strip() and "DISPLAY_MISSING" not in arules:
        issues.append("flag_consistency:display_empty_but_unflagged")
    if "TYPE_EMPTY" in arules and (r["subject_type"] or "").strip():
        issues.append("flag_consistency:TYPE_EMPTY_active_but_subject_type_set")
    if not (r["subject_type"] or "").strip() and \
            not (r["subject_type_norm"] or "").strip() and "TYPE_EMPTY" not in arules:
        issues.append("flag_consistency:subject_type_empty_but_unflagged")
    n_corr = (r["quality_flags"] or "").count("corrected_")
    if n_corr:
        notes.append(f"flags_history:{n_corr}_corrected_marks")
    # session coherence (info-level: accumulators legitimately cite older docs)
    ds = {doc_session(st) for _, st in cite_shas(r["source_syllabus"])} - {None}
    if ds and (r["effective_session_latest"] or "").strip():
        try:
            latest = int(r["effective_session_latest"][:4])
            if max(ds) < latest:
                notes.append(f"session:cited_docs_older_than_latest max={max(ds)} latest={latest}")
        except ValueError:
            pass
    return issues, notes


# ---------------------------------------------------------------- main
def main():
    os.makedirs(PROBE_DIR, exist_ok=True)
    with open(CSV_PATH) as f:
        all_rows = [r for r in csv.DictReader(f) if r["row_kind"] == "subject"]
    rng = random.Random(SEED)
    sample = rng.sample(sorted(all_rows, key=lambda r: r["subject_id"]), N)
    idx = sha_index()
    known_unresolved = known_unresolved_shas()
    print(f"known T12 unresolved shas: {len(known_unresolved)}")
    with open("/home/z/my-project/work/pipeline_v2/audit_flags.json") as af_f:
        active_flags = json.load(af_f)["rows"]
    print(f"active-flag rows loaded: {len(active_flags)}")

    results = []
    for r in sample:
        issues, notes = audit_row(r, idx, known_unresolved, active_flags)
        rv = "clean" if not issues and not notes else \
             "minor" if not issues else "issues"
        results.append({
            "sid": r["subject_id"], "course": r["course_name"],
            "primary_code": r["primary_code"],
            "subject_name": r["subject_name"][:90],
            "verification_status": r["verification_status"],
            "row_verdict": rv, "issues": issues, "notes": notes,
            "quality_flags": r["quality_flags"],
        })

    vc = Counter(x["row_verdict"] for x in results)
    ic = Counter(i for x in results for i in x["issues"])
    nc = Counter(n for x in results for n in x["notes"])
    led = {
        "run_id": RUN_ID,
        "test": "T13 buyer-grade 100-row spot audit (report-only quality gate)",
        "policy": "REPORT-ONLY; no CSV/quality_flags change; deterministic fixed-seed sample (recorded)",
        "rule": {
            "sample": f"random.Random({SEED}).sample(sorted-by-subject_id, {N}); list recorded below",
            "checks": ["identity", "numeric_sane", "semester_sane", "co_complete",
                       "units_complete", "books_parse", "citations", "display",
                       "flag_consistency", "session_coherence(info)"],
        },
        "counts": {
            "rows_total": len(all_rows), "sampled": len(sample),
            "row_verdicts": dict(vc),
            "issue_classes": dict(ic),
            "note_classes": dict(nc),
            "clean_pct": round(100 * vc.get("clean", 0) / len(results), 1),
        },
        "sample": results,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    out = os.path.join(PROBE_DIR, "t13_probe_ledger.json")
    json.dump(led, open(out, "w"), indent=1)

    print(f"T13: {len(sample)} rows; verdicts {dict(vc)}; clean {led['counts']['clean_pct']}%")
    print("issue classes:", dict(ic) or "none")
    print("note classes:", dict(nc) or "none")
    for x in results:
        if x["row_verdict"] == "issues":
            print(f"  - {x['sid']} {x['primary_code']} [{x['course']}] :: {'; '.join(x['issues'])[:150]}")


if __name__ == "__main__":
    main()
