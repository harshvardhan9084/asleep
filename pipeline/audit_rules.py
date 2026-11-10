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

# W4 controlled vocab (B56, owner-reviewed) — audit v19/v20 aligns the 8-value
# subset with the full W4 VOCAB (w4_type_display.py): project-or-capstone and
# non-credit are legitimate committed classes (W4 EXACT map: project/seminar/
# internship/dissertation/industrial-training -> project-or-capstone;
# audit/non-credit -> non-credit). W10b (B71) wrote the first
# project-or-capstone values from name-print evidence; flagging them TYPE_RAW
# was an audit-vocab inconsistency, not a data error.
CONTROLLED_TYPES = {"theory", "lab", "practical", "core", "departmental-elective",
                    "open-elective", "elective", "value-added-mandatory",
                    "project-or-capstone", "non-credit"}
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


# W9a (owner wave 2026-11-08): publisher-token ending whitelist from the
# corpus ending distribution of the 574 BOOK_TRUNC leftovers - entries ending
# with these tokens (or an edition-year / author-at-end form) are complete
# citation prints, not truncations. Mirrors w9a_book_trunc.py classify.
_PUB_SUFFIXES = (
    "new delhi", "mcgraw hill", "mcgraw-hill", "graw hill", "tata mcgraw",
    "prentice hall", "crc press", "morgan kaufmann", "addison wesley",
    "addision wesley", "universities press", "university press",
    "pearson education", "wiley india", "john wiley", "phi learning",
    "s. chand", "dhanpat rai", "khanna publishers", "himalaya publishing",
    "publishing house", "india publication", "oxford publication",
    "cengage learning", "learning publication", "jones and bartlett",
    "and sons", "& sons", "and co", "& co", "& company", "and company",
    "of india", "prentice-hall",
    "hill", "wiley", "phi", "tmh", "pearson", "springer", "kluwer", "narosa",
    "elsevier", "cambridge", "oxford", "cengage", "kaufmann", "wesley",
    "press", "publishers", "publication", "publications", "publishing",
    "delhi", "mumbai", "chand", "rai", "khanna", "katson", "education",
    "learning", "house", "hall", "sons", "company", "india", "university",
    "ibh", "galgotia", "wheeler", "prakashan", "international",
)


def iter_book_strings(r):
    for col in JSON_FIELDS:
        arr = jload(r.get(col, "") or "")
        if isinstance(arr, list):
            for i, b in enumerate(arr):
                t = b.get("book", "") if isinstance(b, dict) else str(b)
                if t.strip():
                    yield col, i, t


_ABBREV_WORDS = {"e.g", "i.e", "viz", "etc", "no", "inc", "ltd", "co", "corp", "pvt",
                 "sons", "bros", "dr", "mr", "mrs", "st", "vs", "vol", "pp", "fig",
                 "eq", "approx", "jr", "sr", "etc.", "al", "ed", "eds"}


def _abbrev_guard(text, dot_pos):
    """v17: same guard as w6_artifacts.is_abbrev (self-contained copy — that
    script is a wave runner with top-level side effects, not importable)."""
    start = max(text.rfind(" ", 0, dot_pos), text.rfind("\n", 0, dot_pos), 0)
    word = text[start:dot_pos].strip()
    if not word:
        return False
    if word.lstrip("(").lower() in _ABBREV_WORDS:
        return True
    if re.fullmatch(r"[A-Za-z]", word):
        return True
    if re.fullmatch(r"(?:[A-Za-z]\.)+[A-Za-z]", word):
        return True
    return False


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
    # v21 durability (2026-11-10, B73): durable W9a2 probe verdicts recorded in
    # the row's notes (evidence surface, survives resets) skip BOOK_TRUNC
    # emission per verified field — same recorded-honest class as the ckpt
    # drop below (kept as fallback for rows without notes coverage).
    _w9a2_vc = set(re.findall(r"W9a2 probe: verified_complete @ (\S+)",
                              r.get("notes", "") or ""))
    for col, i, t in iter_book_strings(r):
        # entry-start list numbering only — 'Vol. N.' / 'NNNN-NN.' / mid-entry
        # citation numbers are legitimate print (W8a adjudication of the W2
        # leftovers: 32 of 33 residual flags were volume/year false positives)
        if re.match(r"^\s*\d{1,2}[\.\)]\s*[^\s]", t):
            add("BOOK_NUMART", "fix:W2", f"entry-start numbering artifact: {t[:90]!r}", field=f"{col}[{i}]")
        if " , " in t or re.search(r"\s,;", t):
            add("BOOK_SPACECOMMA", "fix:W2", "space-comma artifact in entry", field=f"{col}[{i}]")
        # merged entries: 2+ 'author, title' blocks joined by '; ' with distinct surnames
        # v23 durability (2026-11-10, B77): W9c3 faithful-print verdicts recorded
        # in the row's notes (full entry squash-contained in the cited doc — the
        # 'merged' look is AKTU's own print) skip emission per verified field;
        # same recorded-honest class as v21 W9a2 / v22 W9b2.
        if not re.search(r"W9c3 probe: faithful-print " + re.escape(f"{col}[{i}]") + r"(?=\s|@|$)",
                         r.get("notes", "") or ""):
            if re.search(r"[a-z]\)\s*[A-Z][a-z]+,\s*[A-Z]", t) or re.search(r";\s*[A-Z][a-z]+,\s*[A-Z][a-z]+.*(?:Delhi|Publishing|Publication|Publishers|Edition)", t):
                add("BOOK_MERGED", "needs_review", f"possible merged print entry: {t[:90]!r}", field=f"{col}[{i}]")
        # W9a upgrade: publisher-whitelist / edition-year / author-at-end
        # endings are complete citation prints; a head-broken start
        # (lowercase / mid-word / year-led) still flags regardless of ending
        _start_bad = (re.match(r"^['\"“”]?[a-z]", t)
                      or re.match(r"^['\"“”]?(?:19|20)\d{2}\b.*,", t))
        _tail = re.sub(r"[.,;]?\s*['\"“”]*$", "", t.strip()).rstrip()
        _end_ok = (bool(re.search(r"(?:19|20)\d{2}[.,;)]?['\"“”]*$", _tail))
                   or bool(re.search(r"(?:19|20)\d{2},\s*\d{1,4}[.,;)]?['\"“”]*$", _tail))
                   or _tail.lower().endswith(_PUB_SUFFIXES)
                   or bool(re.search(r"\b(?:by|ed\.?|eds\.?)\s+[A-Za-z.\s]{1,40}$",
                                     _tail, re.I)))
        if (re.search(r"\b(Concepts|Techniques|Fundamentals|Systems|Analysis|Theory)\b", t)
                and (_start_bad or not _end_ok)
                and not t.rstrip().endswith((".", "?", ")", '"'))
                and f"{col}[{i}]" not in _w9a2_vc):
            add("BOOK_TRUNC", "needs_review", f"possibly truncated entry: {t[-80:]!r}", field=f"{col}[{i}]")

    # --- W6: punctuation / unicode artifacts
    # audit v20 (2026-11-09, W10d recorded-honest semantics): rows whose
    # w10d_token_n_faithful_print tag records that every (n)+lowercase span was
    # probed verbatim in the cited docs' text layers (printed inline
    # lecture-hour annotations / academic notation) are no longer flags — same
    # evidence-not-error class as the kls_not_printed entries (v19).
    _tokn_honest = "w10d_token_n_faithful_print" in (r.get("quality_flags", "") or "")
    # v17 remedy (W10a adjudication, W9a auditor-FP precedent): '.,' behind a
    # W6 abbreviation guard (etc., / i.e., / e.g., / viz., / No., / initials,
    # dotted initialisms) is legitimate print — the W6 fixer keeps it, so the
    # auditor must not flag it. Flag only a NON-guarded '.,' (or ',,').
    for fld, text in hay.items():
        _punct_bad = bool(re.search(r",,|,\s*,", text)) or any(
            not _abbrev_guard(text, m.start()) for m in re.finditer(r"\.,", text))
        if _punct_bad:
            add("PUNCT_ARTIFACT", "fix:W6", "stray '.,'/',,' punctuation", field=fld)
        if MATH_BLOCK.search(text):
            add("MATH_ITALIC", "fix:W6", "math-italic Unicode decode artifact", field=fld)
        if not _tokn_honest and re.search(r"\(\d{1,2}\)\s+[a-z]", text):
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
        # audit v19 (2026-11-09): a row whose cited docs' text layers carry NO
        # printed CO/K table (W3 scan verdict + mercury-3 REX zero-null,
        # recorded on the row as kls_not_printed / kls_raster_candidate) is a
        # RECORDED honest state — "K not printed for this subject" — the same
        # evidence-not-error class as the None entries below (RULES §6 blank
        # means printed-blank). Short/mid lists are no longer actionable
        # flags there: no print evidence exists to extend them (zero-guess).
        # kls_raster_candidate keeps a needs_review marker (image-only CO
        # pages exist; OCR page-image reads are a real pending evidence path).
        _kls_np = ("kls_not_printed" in (r.get("quality_flags", "") or "")
                   or "kls_raster_candidate" in (r.get("quality_flags", "") or ""))
        if len(kls) < ncos:
            if "kls_not_printed" in (r.get("quality_flags", "") or ""):
                pass  # OCR/text probe-confirmed no printed K table (W3+W8b) — recorded honest state
            elif "kls_raster_candidate" in (r.get("quality_flags", "") or ""):
                add("KLS_SHORT", "needs_review",
                    f"co_kls has {len(kls)} of {ncos} K-levels (image-only CO pages; OCR page-image read pending)",
                    field="co_kls")
            else:
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
        if "kls_not_printed" in (r.get("quality_flags", "") or ""):
            pass  # OCR/text probe-confirmed no printed K table (W3 + W8b OCR) — recorded honest state
        elif "kls_raster_candidate" in (r.get("quality_flags", "") or ""):
            add("KLS_MISSING", "needs_review",
                f"{ncos} COs but co_kls empty (image-only CO pages; OCR page-image read pending)",
                field="co_kls")
        else:
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
    # v22 (2026-11-10, B75): durable W9b2 accepted-print verdicts (printed
    # scheme row matches storage verbatim — AKTU's own table breaks the
    # arithmetic) are recorded-honest, same semantics as v21 W9a
    # verified_complete / v19 / v20: page-cited print evidence disproves the
    # error suspicion, zero data change, flags dropped (scan-side via notes
    # marker, ckpt drop kept as fallback).
    _w9b2_ap = "W9b2 probe: accepted-print" in (r.get("notes", "") or "")
    L, T, P, cr = num(r.get("L")), num(r.get("T")), num(r.get("P")), num(r.get("credit"))
    if None not in (L, T, P, cr) and abs(cr - (L + T + P / 2)) > 0.01 and not _w9b2_ap:
        add("CREDIT_FORMULA", "needs_review", f"credit {cr:g} != L+T+P/2 = {L + T + P/2:g} (W5: faithful-print keep+flag vs fix-from-print)", field="credit")
    stt, ese, tm = num(r.get("sessional_total")), num(r.get("ese_te_pe")), num(r.get("total_marks"))
    if None not in (stt, ese, tm) and abs(tm - (stt + ese)) > 0.01 and not _w9b2_ap:
        add("MARKS_SUM", "needs_review", f"total {tm:g} != sessional {stt:g} + ese {ese:g} (W5)", field="total_marks")
    ct, ta = num(r.get("sessional_ct")), num(r.get("sessional_ta"))
    if None not in (ct, ta, stt) and abs(stt - (ct + ta)) > 0.01 and not _w9b2_ap:
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

    # W9a probe evidence override (owner wave 2026-11-08): BOOK_TRUNC verdicts
    # from the printed-books-list probe (cited docs first, then global corpus
    # page index; text-layer + bounded OCR; raw-prefix cross-doc heal applied
    # in W9a apply). Zero data change here - actions/details updated only.
    try:
        ck9 = json.load(open("/home/z/my-project/work/pipeline_v2/w9a_ckpt.json"))
        pr9 = ck9.get("results", {})
    except Exception:
        pr9 = {}
    n9 = n9drop = 0
    drops9 = []
    if pr9:
        for sid, fl in out.items():
            for f in fl:
                if f.get("rule") != "BOOK_TRUNC":
                    continue
                pr = pr9.get(f"{sid}::{f.get('field', '')}")
                if not pr:
                    continue
                st = pr.get("status")
                ev = pr.get("evidence", "")
                if st == "verified_complete":
                    # v21 (2026-11-10, B73): printed entry verified complete
                    # (verbatim print at cited page) = auditor false positive
                    # recorded-honest — B66 accepted-print class, same
                    # semantics as v19 kls_not_printed / v20 TOKEN_N: the
                    # stored entry matches the print, so the truncation
                    # suspicion is disproven by page-cited evidence. Zero
                    # data change; flag dropped (evidence stays in w9a ckpt).
                    drops9.append((sid, f))
                    n9drop += 1
                elif st == "print_garbled":
                    f["action"] = "needs_review"
                    f["detail"] += f" | W9a probe: source print itself ends abruptly (print-faithful storage) at {ev}"
                    n9 += 1
                elif st == "corroborated_elsewhere":
                    f["action"] = "needs_review"
                    f["detail"] += f" | W9a probe: same book printed in a different form in {ev}; row's own print not recoverable - stored form kept"
                    n9 += 1
                elif st == "no_print_found":
                    f["action"] = "needs_review"
                    f["detail"] += f" | W9a probe: no printed books-list entry recovered ({pr.get('pages_probed', 0)} pages: text-layer + OCR + corpus index)"
                    n9 += 1
                elif st == "sha_unresolved":
                    f["action"] = "needs_review"
                    f["detail"] += " | W9a probe: cited doc sha not locally resolvable post-reset - re-supply PDF to resume"
                    n9 += 1
        for sid, f in drops9:
            lst = out.get(sid)
            if lst and f in lst:
                lst.remove(f)
                summary[f.get("rule", "BOOK_TRUNC")] -= 1
                if not lst:
                    out.pop(sid, None)
        if n9:
            res["w9a_probe_reclassified"] = n9
        if n9drop:
            res["w9a_probe_verified_complete_skipped"] = n9drop

    # W9b probe evidence override (owner wave 2026-11-08): scheme-adjudication
    # verdicts from the printed-scheme-row probe (provenance quotes + verbatim
    # pipe rows + code-anchored doc probe; invariant-gated unique repairs
    # applied in W9b apply). Zero data change here - actions/details only.
    try:
        adj = json.load(open("/home/z/my-project/work/pipeline_v2/w9b_adjudication.json"))
        vd = adj.get("verdicts", {})
    except Exception:
        vd = {}
    flag_rules = ("CREDIT_FORMULA", "SESS_SUM", "MARKS_SUM")
    n10 = n10drop = 0
    drops10 = []
    if vd:
        for sid, fl in out.items():
            if not any(f.get("rule") in flag_rules for f in fl):
                continue
            v = vd.get(sid)
            if not v:
                continue
            st = v.get("status")
            ev = v.get("evidence", "")
            if st == "accepted-print":
                # v22: printed scheme row matches storage verbatim =
                # recorded-honest (B67 class; zero data change; evidence in
                # w9b ckpt + durable notes marker W9b2).
                for f in fl:
                    if f.get("rule") in flag_rules:
                        drops10.append((sid, f))
                        n10drop += 1
                continue
            elif st == "no_print_found":
                note = " | W9b probe: no printed scheme row recoverable (quote has no numbers; cited scheme docs missing or code-anchored row not found)"
            elif st == "sha_unresolved":
                note = " | W9b probe: cited scheme docs not locally resolvable post-reset - re-supply PDF to resume"
            elif st == "stored_matches_no_print":
                note = f" | W9b probe: printed row found ({ev}) but its numbers do not support any invariant-consistent repair of the stored values - stored form kept (zero-guess)"
            elif st == "ambiguous":
                note = f" | W9b probe: multiple invariant-consistent repairs possible from the printed row ({ev}) - not adjudicable without the printed column header"
            else:
                continue
            for f in fl:
                if f.get("rule") in flag_rules:
                    f["action"] = "needs_review"
                    f["detail"] = f["detail"][:180] + note
                    n10 += 1
        for sid, f in drops10:
            lst = out.get(sid)
            if lst and f in lst:
                lst.remove(f)
                summary[f.get("rule")] -= 1
                if not lst:
                    out.pop(sid, None)
        if n10:
            res["w9b_probe_reclassified"] = n10
        if n10drop:
            res["w9b_probe_accepted_print_skipped"] = n10drop
    # v21: refresh snapshot fields after probe-evidence drops (rows/flags moved)
    res["rows_flagged"] = len(out)
    res["total_flags"] = sum(summary.values())
    res["summary"] = dict(summary.most_common())
    with open(a.out, "w") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)
    if not a.quiet:
        print(f"AUDIT|rows={len(rows)} flagged={len(out)} flags={sum(summary.values())} → {a.out}")
        for k, v in summary.most_common():
            print(f"  {k:22s} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
