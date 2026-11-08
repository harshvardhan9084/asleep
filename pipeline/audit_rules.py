#!/usr/bin/env python3
"""audit_rules.py — deterministic per-row audit flag engine (Phase 2 of the
owner-approved correction plan; extends scripts/claude_audit_scan.py).

Every row gets a machine flag list. Each flag = {rule, action, field?, detail}
where action is either:
  * "fix:<wave>"  — a deterministic correction rule owned by a named wave
                    (W1 typos / W2 books / W3 co_kls / W4 type+display /
                     W6 artifacts) — the wave scripts consume these;
  * "needs_review" — evidence-inconclusive, left untouched (RULES §4/§6b.3),
                    surfaced in quality_flags for the owner / W5-style waves.

Read-only over the registry. Output: work/pipeline_v2/audit_flags.json
  {"rows": {sid: [flags...]}, "summary": {rule: count}, "ts": ...}
Usage: python3 audit_rules.py [--csv PATH] [--out PATH] [--quiet]
"""
import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone

CSV_DEFAULT = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
OUT_DEFAULT = "/home/z/my-project/work/pipeline_v2/audit_flags.json"

# ---------------------------------------------------------------- W1 dictionary
# evidence types: xrow = same author/algorithm printed correctly elsewhere in
# the corpus (cross-row consistency); ref = standard published spelling.
W1_DICT = {
    "Deshpandey":  {"fix": "Deshpande",  "ev": "ref: standard Marathi surname 'Deshpande' (D. Deshpande, Solid State / EDC texts); print-typo class", "wave": "W1"},
    "Trembley":    {"fix": "Tremblay",   "ev": "xrow: corpus prints 'Tremblay' correctly on 9 other rows (J.-P. Tremblay & P. Manohar, Discrete Mathematical Structures)", "wave": "W1"},
    "Liptschutz":  {"fix": "Lipschutz",  "ev": "ref: Schaum's Outline author Seymour Lipschutz; xrow corpus check at run time", "wave": "W1"},
    "Liptzutz":    {"fix": "Lipschutz",  "ev": "ref: Seymour Lipschutz (Schaum's)", "wave": "W1"},
    "Parahami":    {"fix": "Parhami",    "ev": "ref: Behrooz Parhami, Computer Architecture (Oxford)", "wave": "W1"},
    "Vravice":     {"fix": "Vranesic",   "ev": "ref: Hamacher–Vranesic–Zaky, Computer Organization; entry co-authors confirm", "wave": "W1"},
    "Dijikstra":   {"fix": "Dijkstra",   "ev": "xrow: corpus prints 'Dijkstra' correctly on 7 other rows (E. W. Dijkstra, shortest path)", "wave": "W1"},
    "Warshal":     {"fix": "Warshall",   "pat": r"\bWarshal\b|\bWarshalll\b", "ev": "ref: Stephen Warshall (transitive closure); word-bounded so the correct 'Warshall' (2 l's) never matches; xrow: corpus prints 'Warshall' correctly on 5+ rows", "wave": "W1"},
    "Geoftrey":    {"fix": "Geoffrey",    "ev": "xrow: corpus prints 'Geoffrey' correctly on 15 rows (Geoffrey Gordon, System Simulation, PHI)", "wave": "W1"},
    "Insertation": {"fix": "Insertion",  "ev": "ref: standard operation name 'Insertion' (sorting)", "wave": "W1"},
    "Boothbub":    {"fix": None,         "ev": None, "wave": None},  # placeholder: no auto-fix
}
W1_TERMS = {k: v for k, v in W1_DICT.items() if v["fix"]}

# fields the correction waves may touch (primary data fields, RULES §6b)
TEXT_FIELDS = ([f"unit{i}_text" for i in range(1, 6)]
               + [f"co{i}_text" for i in range(1, 7)]
               + ["objectives_print", "prerequisites"])
JSON_FIELDS = ["textbooks_structured", "reference_books_structured", "experiments_structured"]

CONTROLLED_TYPES = {"theory", "lab", "practical", "core", "departmental-elective",
                    "open-elective", "elective", "value-added-mandatory"}
CODE_RE = re.compile(r"^[A-Z]{2,4}[0-9]{3}[A-Z]?$")
MATH_BLOCK = re.compile(r"[𝐀-𝟿\U0001D400-\U0001D7FF]")


def jload(s):
    try:
        return json.loads(s) if s and str(s).strip() else None
    except Exception:
        return "ERR"


def num(x):
    try:
        return float(x) if str(x).strip() else None
    except Exception:
        return None


def iter_book_strings(r):
    for col in JSON_FIELDS:
        arr = jload(r.get(col, "") or "")
        if isinstance(arr, list):
            for i, b in enumerate(arr):
                t = b.get("book", "") if isinstance(b, dict) else str(b)
                if t.strip():
                    yield col, i, t


def audit_row(r, primary_owners):
    flags = []
    sid = r.get("subject_id", "")
    subj = r.get("row_kind", "") == "subject"

    def add(rule, action, detail, field=None):
        f = {"rule": rule, "action": action, "detail": detail[:240]}
        if field:
            f["field"] = field
        flags.append(f)

    # --- W1: dictionary typos in primary text + book entries
    hay = {}
    for c in TEXT_FIELDS:
        v = r.get(c, "") or ""
        if v:
            hay[c] = v
    for col, i, t in iter_book_strings(r):
        hay[f"{col}[{i}]"] = t
    for fld, text in hay.items():
        for wrong, meta in W1_TERMS.items():
            pat = meta.get("pat") or re.escape(wrong)
            if re.search(pat, text, re.IGNORECASE):
                add("AUTH_TYPO_" + wrong.lower(), f"fix:{meta['wave']}",
                    f"{wrong!r} → {meta['fix']!r} ({meta['ev']})", field=fld)

    # --- W2: book-entry hygiene
    for col, i, t in iter_book_strings(r):
        # entry-start list numbering only — 'Vol. N.' / 'NNNN-NN.' / mid-entry
        # citation numbers are legitimate print (W8a adjudication of the W2
        # leftovers: 32 of 33 residual flags were volume/year false positives)
        if re.match(r"^\s*\d{1,2}[\.\)]\s*[^\s]", t):
            add("BOOK_NUMART", "fix:W2", f"entry-start numbering artifact: {t[:90]!r}", field=f"{col}[{i}]")
        if " , " in t or re.search(r"\s,;", t):
            add("BOOK_SPACECOMMA", "fix:W2", "space-comma artifact in entry", field=f"{col}[{i}]")
        # merged entries: 2+ 'author, title' blocks joined by '; ' with distinct surnames
        if re.search(r"[a-z]\)\s*[A-Z][a-z]+,\s*[A-Z]", t) or re.search(r";\s*[A-Z][a-z]+,\s*[A-Z][a-z]+.*(?:Delhi|Publishing|Publication|Publishers|Edition)", t):
            add("BOOK_MERGED", "needs_review", f"possible merged print entry: {t[:90]!r}", field=f"{col}[{i}]")
        if (re.search(r"(New Delhi|Publishers?|Edition|Publications)\.?$", t) is None
                and re.search(r"\b(Concepts|Techniques|Fundamentals|Systems|Analysis|Theory)\b", t)
                and not t.rstrip().endswith((".", "?", ")", '"'))):
            add("BOOK_TRUNC", "needs_review", f"possibly truncated entry: {t[-80:]!r}", field=f"{col}[{i}]")

    # --- W6: punctuation / unicode artifacts
    for fld, text in hay.items():
        if re.search(r"\.,|,,|,\s*,", text):
            add("PUNCT_ARTIFACT", "fix:W6", "stray '.,'/',,' punctuation", field=fld)
        if MATH_BLOCK.search(text):
            add("MATH_ITALIC", "fix:W6", "math-italic Unicode decode artifact", field=fld)
        if re.search(r"\(\d{1,2}\)\s+[a-z]", text):
            add("TOKEN_N_LOWER", "needs_review", "(n) lowercase stray token", field=fld)
    nm = r.get("subject_name", "") or ""
    if re.search(r"\.,|,,|  ", nm):
        add("NAME_ARTIFACT", "fix:W6", "artifact in subject_name", field="subject_name")

    if not subj:
        return flags

    # --- W3: co_kls backfill
    try:
        cc = int(r.get("co_count", "") or 0)
    except Exception:
        cc = 0
    kls = jload(r.get("co_kls", "") or "")
    ncos = sum(1 for i in range(1, 7) if (r.get(f"co{i}_text", "") or "").strip())
    if ncos and cc == 0:
        add("COCOUNT_MISSING", "needs_review", f"{ncos} CO fields but co_count empty", field="co_count")
    if ncos and isinstance(kls, list):
        if len(kls) < ncos:
            add("KLS_SHORT", "fix:W3", f"co_kls has {len(kls)} of {ncos} K-levels", field="co_kls")
        # printed K-ranges ('K1/K2' = the doc prints K1 or K2) are legitimate
        # print (W8a adjudication: all 140 residual flags were ranges) — only
        # values outside K1-K6 tokens/ranges are bad
        bad = [k for k in kls if k is not None and
               not (isinstance(k, str) and re.fullmatch(r"K[1-6](/K[1-6])*", k.strip()))]
        # None entries are RECORDED honest nulls ('K not printed for this CO',
        # W3 partial backfills) — evidence, not errors
        if bad:
            add("KLS_BADVAL", "needs_review", f"K-levels outside K1-K6 tokens/ranges: {bad[:6]}", field="co_kls")
    elif ncos and not isinstance(kls, list):
        add("KLS_MISSING", "fix:W3", f"{ncos} COs but co_kls empty", field="co_kls")

    # --- W4: subject_type normalization + display
    st = (r.get("subject_type", "") or "").strip()
    if st and st.lower() not in CONTROLLED_TYPES:
        add("TYPE_RAW", "fix:W4", f"raw subject_type {st!r} outside controlled vocab", field="subject_type")
    if not st:
        add("TYPE_EMPTY", "fix:W4", "subject_type empty — infer from name/-lab suffix + scheme category", field="subject_type")
    if not (r.get("subject_name_display", "") or "").strip():
        add("DISPLAY_MISSING", "fix:W4", "subject_name_display empty", field="subject_name_display")

    # --- W5: marks/credit formula variance (needs_review by design; per-row
    #     evidence reads decide faithful-print keep+flag vs extraction-error fix)
    L, T, P, cr = num(r.get("L")), num(r.get("T")), num(r.get("P")), num(r.get("credit"))
    if None not in (L, T, P, cr) and abs(cr - (L + T + P / 2)) > 0.01:
        add("CREDIT_FORMULA", "needs_review", f"credit {cr:g} != L+T+P/2 = {L + T + P/2:g} (W5: faithful-print keep+flag vs fix-from-print)", field="credit")
    stt, ese, tm = num(r.get("sessional_total")), num(r.get("ese_te_pe")), num(r.get("total_marks"))
    if None not in (stt, ese, tm) and abs(tm - (stt + ese)) > 0.01:
        add("MARKS_SUM", "needs_review", f"total {tm:g} != sessional {stt:g} + ese {ese:g} (W5)", field="total_marks")
    ct, ta = num(r.get("sessional_ct")), num(r.get("sessional_ta"))
    if None not in (ct, ta, stt) and abs(stt - (ct + ta)) > 0.01:
        add("SESS_SUM", "needs_review", f"sessional_total {stt:g} != ct {ct:g} + ta {ta:g} (W5)", field="sessional_total")

    # --- consistency / codes
    a, b = r.get("effective_session_latest", "") or "", r.get("first_introduced_session", "") or ""
    if a and b and a < b:
        add("SESS_ORDER", "needs_review", f"effective_session_latest {a} < first_introduced {b}")
    ck = r.get("course_name", "") or ""
    own = set()
    for tok in (r.get("all_codes", "") or "").split(";"):
        tok = tok.strip().upper()
        if CODE_RE.match(tok):
            own.add(tok)
    pc = (r.get("primary_code", "") or "").strip().upper()
    if pc and CODE_RE.match(pc) and pc not in own:
        add("PRIMARY_NOT_OWNED", "needs_review", "primary_code not in all_codes (G3 would fail)")
    if pc and CODE_RE.match(pc):
        po = primary_owners.get((ck, pc))
        if po and po != sid:
            add("DUP_PRIMARY", "needs_review", f"primary_code {pc} also primary of {po} (same course)")
    for tok in sorted(own):
        if tok != pc:
            po = primary_owners.get((ck, tok))
            if po and po != sid:
                add("CODE_CROSS", "needs_review", f"all_codes token {tok} primary-owned by {po} (same course)")
    return flags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=CSV_DEFAULT)
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.csv, newline="", encoding="utf-8")))
    # same-course primary-code owner index (G2 semantics)
    primary_owners = {}
    for r in rows:
        pc = (r.get("primary_code", "") or "").strip().upper()
        if CODE_RE.match(pc):
            key = (r.get("course_name", "") or "", pc)
            if key not in primary_owners:
                primary_owners[key] = r.get("subject_id", "")

    out, summary = {}, Counter()
    for r in rows:
        fl = audit_row(r, primary_owners)
        if fl:
            out[r.get("subject_id", f"row{len(out)}")] = fl
            for f in fl:
                summary[f["rule"]] += 1

    res = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "csv": a.csv, "rows_scanned": len(rows),
           "rows_flagged": len(out), "total_flags": sum(summary.values()),
           "summary": dict(summary.most_common()), "rows": out}

    # W8b probe evidence override (zero data change): rows whose cited docs were
    # probe-read (text-layer + OCR raster) without a recoverable printed K
    # sequence keep the flag but as needs_review with the probe verdict, not
    # fix:W3 — no further extraction attempt is warranted without new documents.
    try:
        import os
        ck = json.load(open("/home/z/my-project/work/pipeline_v2/w8b_ocr_ckpt.json"))
        probe = ck.get("results", {})
    except Exception:
        probe = {}
    n_probe = 0
    if probe:
        for sid, fl in out.items():
            pr = probe.get(sid)
            if not pr:
                continue
            for f in fl:
                if f.get("rule") in ("KLS_MISSING", "KLS_SHORT"):
                    if pr.get("status") == "no_clean_sequence":
                        f["action"] = "needs_review"
                        f["detail"] = (f"{f['detail'][:150]} | W8b probe: no recoverable printed "
                                       f"K sequence in cited docs ({pr.get('pages_probed', 0)} pages: "
                                       "text-layer + OCR raster)")
                        n_probe += 1
                    elif pr.get("status") == "sha_unresolved":
                        f["action"] = "needs_review"
                        f["detail"] = (f"{f['detail'][:150]} | W8b probe: cited doc sha not locally "
                                       "resolvable post-reset — re-supply PDF to resume")
                        n_probe += 1
        if n_probe:
            res["w8b_probe_reclassified"] = n_probe
    with open(a.out, "w") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)
    if not a.quiet:
        print(f"AUDIT|rows={len(rows)} flagged={len(out)} flags={sum(summary.values())} → {a.out}")
        for k, v in summary.most_common():
            print(f"  {k:22s} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
