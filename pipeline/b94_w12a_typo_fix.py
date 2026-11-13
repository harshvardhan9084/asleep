#!/usr/bin/env python3
"""b94_w12a_typo_fix.py — CRON-20261113-B94 (W12a owner directive D2, 2026-11-13).

Owner complaint: the `notes` column documents printed typos ("kept as-is") that
RULES §6b (directive D1, 2026-11-08) already required to be FIXED in primary
fields. No wave ever swept noted-typos vs §6b compliance, so the noted typos
went stale in unit/co/book/experiment text. This batch executes the owner's
directive: fix every NOTED, unambiguous misspelling in primary fields only.

Scope rules:
- Curated fix map (high-confidence world knowledge: famous algorithm/author
  names + unambiguous English words). NO guesses: context-dependent tokens
  (Deprecation) are row-gated to rows whose own notes flag them.
- Evidence surfaces stay verbatim forever (§6b): notes/*_print untouched;
  each changed row's notes gets ONE appended W12a status clause.
- Every change appends corrections_json {"field","before","after","rule",
  "evidence"} — printed spelling preserved in "before".
- G6 guard: unit1_text[:40] is the gate's print-containment needle; any fix
  overlapping that window in unit1_text is skipped there (kept print-faithful)
  and counted.
- Gates G1/G2/G3/G6 (merge_draft functions, b81 pattern) must PASS before the
  CSV write is kept; audit must stay 0 flags.

Usage: python3 b94_w12a_typo_fix.py [--apply]   (default = dry-run counts)
"""
import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import merge_draft as MD  # gate_g1/g2/g3/g6, REF_HEADER (stdlib-only import)

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
FLAGS_PATH = "/home/z/my-project/work/pipeline_v2/audit_flags.json"
PARSED_DIR = "/home/z/my-project/work/pipeline_v2/parsed"
BACKUP_DIR = "/home/z/my-project/work/pipeline_v2/backup"
RESULT_PATH = "/home/z/my-project/work/pipeline_v2/b94_result.json"
AUDIT = "/home/z/my-project/scripts/pipeline_v2/audit_rules.py"
EXPECT_MD5 = "e21e81fba24bbcf2ae7851565c8c78f3"

# (pattern, replacement, kind) — kind: re_i = \b regex case-insensitive,
# re_s = \b regex case-SENSITIVE, lit = literal case-sensitive substring.
FIXES = [
    # famous algorithm / CS names (unambiguous world knowledge)
    ("Ardunio", "Arduino", "re_i"),
    ("Warshal", "Warshall", "re_i"),
    ("Dijikstra", "Dijkstra", "re_i"),
    ("Insertation", "Insertion", "re_i"),
    ("Hopcraft", "Hopcroft", "re_i"),
    ("Halestead", "Halstead", "re_i"),
    ("Compuitng", "Computing", "re_i"),
    ("perceptran", "perceptron", "re_i"),
    ("Mc-Clusky", "McCluskey", "re_i"),
    ("serializablity", "serializability", "re_i"),
    ("Mutimodal", "Multimodal", "re_i"),
    ("Gestrual", "Gestural", "re_i"),
    ("DIMENTIONALITY", "DIMENSIONALITY", "re_i"),
    ("MOFET", "MOSFET", "re_i"),
    ("muti-degree", "multi-degree", "lit"),
    # famous authors / publishers (unambiguous)
    ("Tannenbaum", "Tanenbaum", "re_i"),
    ("Tenanuanbaum", "Tanenbaum", "re_i"),
    ("Addision", "Addison", "re_i"),
    ("Schieldt", "Schildt", "re_i"),
    ("Siman Haykin", "Simon Haykin", "lit"),
    ("Apaydin", "Alpaydin", "re_i"),
    ("Normal Maltoff", "Norman Matloff", "lit"),
    ("Lijedehl", "Liljedahl", "re_i"),
    ("Considyne", "Considine", "re_i"),
    ("Krishnawamy", "Krishnaswamy", "re_i"),
    ("willey", "Wiley", "re_i"),
    ("Wiely", "Wiley", "re_i"),
    ("P fleeger", "Pfleeger", "lit"),
    ("Pearson Educaiton", "Pearson Education", "lit"),
    ("Educaiton", "Education", "re_i"),
    ("Siddeshswar", "Siddheshwar", "re_i"),
    ("Crommwell", "Cromwell", "re_i"),
    ("Michacl", "Michael", "re_i"),
    # unambiguous English/domain words
    ("pozzolona", "pozzolana", "re_i"),
    ("Pozzolona", "Pozzolana", "re_i"),
    ("thickners", "thickeners", "re_i"),
    ("Trainning", "Training", "re_i"),
    ("confectionary", "confectionery", "re_i"),
    ("Paranayama", "Pranayama", "re_i"),
    ("Meditaion", "Meditation", "re_i"),
    ("Mitrochondria", "Mitochondria", "re_i"),
    ("Technolgy", "Technology", "re_i"),
    ("Distributory", "Distributary", "re_i"),
    ("Banglore", "Bangalore", "re_i"),
    ("CATOLOGUE", "CATALOGUE", "re_i"),
    ("Ccontext", "Context", "re_i"),
    ("Debantures", "Debentures", "re_i"),
    ("characterstics", "characteristics", "re_i"),
    ("Farbics", "Fabrics", "re_i"),
    ("Terylyne", "Terylene", "re_i"),
    ("Sillimani", "Sillimanite", "re_i"),
    ("Hasselbach", "Hasselbalch", "re_i"),
    ("Mangement", "Management", "re_i"),
    ("leagal", "legal", "re_i"),
    ("Editon", "Edition", "re_i"),
    ("editon", "edition", "re_i"),
    ("Entreprenurship", "Entrepreneurship", "re_i"),
    ("Enterpreneurship", "Entrepreneurship", "re_i"),
    ("Blooms Taxenomy", "Bloom's Taxonomy", "lit"),
    ("Taxenomy", "Taxonomy", "re_i"),
    ("Co-planer", "Co-planar", "re_i"),
    ("Enginnering", "Engineering", "re_i"),
    ("Intoduction", "Introduction", "re_i"),
    ("Publlications", "Publications", "re_i"),
    ("Poke Yoke", "Poka Yoke", "lit"),
    ("Poke-Yoke", "Poka-Yoke", "lit"),
    ("Field Hand book", "Field Handbook", "lit"),
    ("Anal yze", "Analyze", "lit"),
    ("Life predication", "Life prediction", "lit"),
    ("removal by setting", "removal by settling", "lit"),
    ("for ecasting", "forecasting", "lit"),
    ("difference jobs", "different jobs", "lit"),
    ("WHCHIMPLEMENTS", "WHICH IMPLEMENTS", "lit"),
    ("pacBAGing", "packaging", "lit"),
    # casing-only, case-sensitive
    ("SQl", "SQL", "re_s"),
    ("Lscm", "LSCM", "re_s"),
    # context-dependent: row-gated to rows whose own notes flag it
    ("Deprecation", "Depreciation", "rowgate"),
]

UNIT_COLS = [f"unit{i}_text" for i in range(1, 6)]
CO_COLS = [f"co{i}_text" for i in range(1, 7)]
STRUCT_COLS = ["textbooks_structured", "reference_books_structured",
               "experiments_structured"]
G6_WINDOW = 40  # gate_g6 needle = unit1_text[:40]


def build_matchers():
    out = []
    for pat, rep, kind in FIXES:
        if kind == "re_i":
            rx = re.compile(r"\b" + re.escape(pat) + r"\b", re.I)
        elif kind == "re_s":
            rx = re.compile(r"\b" + re.escape(pat) + r"\b")
        else:
            rx = re.compile(re.escape(pat))
        out.append((pat, rep, rx, kind))
    return out


def apply_to_value(val, matchers, rowgate=False, guard_prefix=None):
    """Return (new_val, {token: n}). guard_prefix: in unit1_text, fixes whose
    match overlaps [0, guard_prefix) are skipped (G6 needle region)."""
    changed = {}
    new = val
    for pat, rep, rx, kind in matchers:
        if rowgate is False and kind == "rowgate":
            continue
        def _sub(m, _rep=rep, _pat=pat):
            changed[_pat] = changed.get(_pat, 0) + 1
            return _rep
        if guard_prefix is not None:
            pieces, pos, skipped = [], 0, False
            for m in rx.finditer(new):
                if m.start() < guard_prefix:
                    skipped = True
                    continue
                pieces.append(new[pos:m.start()])
                pieces.append(_sub(m))
                pos = m.end()
            pieces.append(new[pos:])
            if skipped and pat not in changed:
                continue
            new2 = "".join(pieces)
        else:
            new2 = rx.sub(_sub, new)
        if new2 != new:
            new = new2
    return new, changed


def row_str_fields(row):
    """Yield (field_label, getter, setter) for all primary text surfaces."""
    for c in UNIT_COLS + CO_COLS:
        yield c, lambda r, c=c: r.get(c, ""), None
    for c in STRUCT_COLS:
        try:
            arr = json.loads(row.get(c, "") or "[]")
        except Exception:
            continue
        for i, b in enumerate(arr):
            for bk, vv in list(b.items()):
                if isinstance(vv, str) and vv.strip():
                    yield f"{c}[{i}].{bk}", None, (c, i, bk)


def main():
    apply_mode = "--apply" in sys.argv
    rows = list(csv.DictReader(open(CSV_PATH)))
    header = list(rows[0].keys())
    assert len(rows) == 3080, f"row count {len(rows)} != 3080"
    matchers = build_matchers()
    stats = {"changes": {}, "rows_changed": 0, "note_clauses": 0,
             "g6_window_skips": {}, "per_field": {}}
    touched = set()
    corrected = []

    for row in rows:
        sid = row.get("subject_id", "")
        row_notes = (row.get("notes", "") or "").lower()
        row_changed = {}
        # unit/co text columns
        for c in UNIT_COLS + CO_COLS:
            val = row.get(c, "") or ""
            if not val.strip():
                continue
            guard = G6_WINDOW if c == "unit1_text" else None
            rowgate = "deprecation" in row_notes
            new, ch = apply_to_value(val, matchers, rowgate=rowgate,
                                     guard_prefix=guard)
            if ch:
                if c == "unit1_text":
                    for k in ch:
                        stats["g6_window_skips"].setdefault(k, 0)
                row[c] = new  # write back the fixed unit/co text
                row_changed[c] = (val, new, ch)
        # structured entries
        for c in STRUCT_COLS:
            try:
                arr = json.loads(row.get(c, "") or "[]")
            except Exception:
                continue
            arr_changed = False
            for i, b in enumerate(arr):
                for bk, vv in list(b.items()):
                    if not (isinstance(vv, str) and vv.strip()):
                        continue
                    rowgate = "deprecation" in row_notes
                    new, ch = apply_to_value(vv, matchers, rowgate=rowgate)
                    if ch:
                        b[bk] = new
                        row_changed[f"{c}[{i}].{bk}"] = (vv, new, ch)
                        arr_changed = True
            if arr_changed:
                row[c] = json.dumps(arr, ensure_ascii=False)
        if not row_changed:
            continue
        touched.add(sid)
        stats["rows_changed"] += 1
        # corrections_json per changed field (§6b)
        try:
            cj = json.loads(row.get("corrections_json", "") or "[]")
        except Exception:
            cj = []
        for fld, (before, after, ch) in row_changed.items():
            for tok in ch:
                cj.append({"field": fld, "before": before, "after": after,
                           "rule": "W12A_NOTED_TYPO_FIXED",
                           "evidence": (f"owner directive D2 2026-11-13: noted "
                                        f"typo '{tok}' fixed per RULES §6b; "
                                        f"printed spelling preserved in "
                                        f"'before' + verbatim quirk note")})
                stats["changes"][tok] = stats["changes"].get(tok, 0) + 1
        row["corrections_json"] = json.dumps(cj, ensure_ascii=False)
        # one appended W12a clause on notes (evidence surface stays verbatim)
        fixed_toks = sorted({t for (_, _, ch) in row_changed.values() for t in ch})
        row["notes"] = (row.get("notes", "") or "").rstrip()
        row["notes"] += (" | W12a (owner directive D2 2026-11-13): noted "
                         "typo(s) " + ", ".join(f"{t}" for t in fixed_toks)
                         + " FIXED in primary fields per RULES §6b — note text "
                         "above retained verbatim as the print record; printed "
                         "spellings preserved in corrections_json 'before'.")
        stats["note_clauses"] += 1
        corrected.append(sid)

    print(f"rows_changed={stats['rows_changed']} tokens={dict(sorted(stats['changes'].items()))}")
    print(f"g6_window_skips(token->unit1 occurrences left print-faithful)={stats['g6_window_skips']}")
    if not apply_mode:
        print("DRY-RUN — rerun with --apply to write.")
        return 0

    import hashlib
    pre_md5 = hashlib.md5(open(CSV_PATH, "rb").read()).hexdigest()
    assert pre_md5 == EXPECT_MD5, f"pre-write md5 {pre_md5} != expected"
    os.makedirs(BACKUP_DIR, exist_ok=True)
    bkp = os.path.join(BACKUP_DIR, "syllabus_preB94.csv")
    if not os.path.exists(bkp):
        import shutil as _s
        _s.copy2(CSV_PATH, bkp)

    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MD.REF_HEADER, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    # gates (b81 pattern)
    g1 = MD.gate_g1(MD.REF_HEADER)
    g2, ncodes = MD.gate_g2(rows)
    g3 = MD.gate_g3(rows)
    g6, checks = MD.gate_g6(rows, touched, PARSED_DIR)
    gates = {"G1": g1 or "PASS", "G2": (g2 or f"PASS codes={ncodes}"),
             "G3": g3 or "PASS", "G6": (g6 or f"PASS containment_checks={checks}")}
    print("GATES|" + " | ".join(f"{k} {v}" for k, v in gates.items()))
    if any(not v.startswith("PASS") for v in gates.values()):
        print("GATE_FAIL — restoring backup")
        import shutil as _s
        _s.copy2(bkp, CSV_PATH)
        return 3

    # audit re-scan
    rc = subprocess.run([sys.executable, AUDIT, "--csv", CSV_PATH,
                         "--out", FLAGS_PATH, "--quiet"],
                        capture_output=True, text=True, timeout=600)
    if rc.returncode != 0:
        print("AUDIT|FAIL", rc.stderr[-400:])
        return 2
    new = json.load(open(FLAGS_PATH))
    stats["flags_after"] = new.get("total_flags")
    stats["summary_after"] = new.get("summary")
    stats["gates"] = gates
    stats["touched_rows"] = len(touched)
    stats["applied_utc"] = datetime.now(timezone.utc).isoformat()
    stats["backup"] = bkp
    json.dump(stats, open(RESULT_PATH, "w"), indent=1)
    print(f"B94|done|flags_after={stats['flags_after']}|rows={stats['rows_changed']}")
    print("SUMMARY|" + json.dumps(new.get("summary")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
