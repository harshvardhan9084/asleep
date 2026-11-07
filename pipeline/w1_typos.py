#!/usr/bin/env python3
"""w1_typos.py — W1 (B52): dictionary typo fixes in primary fields.
Owners/algorithm/operation-name misspellings confirmed by the audit +
corpus cross-row / standard-reference evidence. Page-cited print evidence
resolved from the row's own source_syllabus sha16 → corpus PDF → pages.
RULES §6b: primary fixed, before-form kept in corrections_json; *_print and
source_scheme_line untouched; notes get a §6b quirk line."""
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

CSV = WC.CSV_PATH
BASE = WC.BASE

# term → (correct, evidence-ref). \\b both sides; case-insensitive match with
# case-preserving replacement. Insertation: 0 primary-field hits (notes-only) — excluded.
DICT = {
    "Deshpandey":  ("Deshpande", "ref: P. S. Deshpande, 'C and Data Structures', Wiley Dreamtech — standard author spelling"),
    "Trembley":    ("Tremblay",  "xrow: corpus prints 'Tremblay' (J.-P. Tremblay & R. Manohar / & P. G. Sorenson) on 9 other rows"),
    "Liptschutz":  ("Lipschutz", "ref: Seymour Lipschutz (Schaum's Discrete Mathematics); corpus pair 'Lipson' consistent"),
    "Parahami":    ("Parhami",   "ref: Behrooz Parhami, 'Computer Architecture', Oxford Univ. Press"),
    "Vravice":     ("Vranesic",  "ref: Hamacher–Vranesic–Zaky, 'Computer Organization' — entry co-authors Hamacher & Zaky printed on the same line"),
    "Dijikstra":   ("Dijkstra",  "xrow: corpus prints 'Dijkstra' on 7 other rows (E. W. Dijkstra shortest-path)"),
    "Warshal":     ("Warshall",  "ref: Stephen Warshall (transitive-closure algorithm); corpus prints 'Warshall's' on sibling rows"),
    "Coreman":     ("Cormen",    "ref: Thomas H. Cormen, Leiserson, Rivest ('Introduction to Algorithms', CLRS); xrow corpus 'Cormen'"),
    "Hopcraft":    ("Hopcroft",  "ref: J. E. Hopcroft, Motwani, Ullman ('Introduction to Automata Theory…')"),
    "Printice":    ("Prentice",  "ref: Prentice Hall of India — publisher imprint"),
    "Transistive": ("Transitive","ref: standard term; xrow: sibling rows print 'Transitive Closure'"),
}

TEXT_FIELDS = ([f"unit{i}_text" for i in range(1, 6)]
               + [f"co{i}_text" for i in range(1, 7)] + ["prerequisites"])
JF = ["textbooks_structured", "reference_books_structured", "experiments_structured"]


def preserve_case(wrong, right):
    if wrong.isupper():
        return right.upper()
    if wrong[0].isupper():
        return right[0].upper() + right[1:]
    return right


rows = WC.load_rows()
edits = []
term_rows = defaultdict(set)
for r in rows:
    sid = r["subject_id"]
    for c in TEXT_FIELDS:
        v = r.get(c, "") or ""
        for wrong, (right, ref) in DICT.items():
            if re.search(rf"\b{re.escape(wrong)}", v):
                edits.append({"sid": sid, "field": c, "before": wrong, "after": right,
                              "rule": f"AUTH_TYPO_{wrong.lower()}", "all": True,
                              "evidence": ref})  # page cite added below
                term_rows[wrong].add(sid)
    for col in JF:
        try:
            arr = json.loads(r.get(col, "") or "[]")
        except Exception:
            continue
        for i, b in enumerate(arr):
            t = b.get("exp" if col == "experiments_structured" else "book", "") if isinstance(b, dict) else str(b)
            for wrong, (right, ref) in DICT.items():
                if re.search(rf"\b{re.escape(wrong)}", t):
                    edits.append({"sid": sid, "field": f"{col}[{i}]", "before": wrong,
                                  "after": right, "rule": f"AUTH_TYPO_{wrong.lower()}",
                                  "all": True, "evidence": ref})
                    term_rows[wrong].add(sid)

print(f"W1|candidate edits={len(edits)} terms={ {k: len(v) for k, v in term_rows.items()} }")

# ---- page-cited print evidence: row's cited docs → per-page text scan
import fitz, hashlib, os
corpus = {}
for root in ("/home/z/my-project/work/repo_asleep/PDFs", "/home/z/my-project/upload",
             "/home/z/my-project/work/artd_v3/sources"):
    for dp, _d, fs in os.walk(root):
        for fn in fs:
            if fn.lower().endswith(".pdf"):
                p = os.path.join(dp, fn)
                try:
                    h = hashlib.md5()
                    with open(p, "rb") as fh:
                        for chunk in iter(lambda: fh.read(1 << 20), b""):
                            h.update(chunk)
                    corpus.setdefault(h.hexdigest()[:16], p)
                except Exception:
                    pass

page_cache = {}
def doc_pages(sha):
    if sha in page_cache:
        return page_cache[sha]
    txt = []
    p = corpus.get(sha)
    if p:
        try:
            d = fitz.open(p)
            txt = [pg.get_text() for pg in d]
            d.close()
        except Exception:
            txt = []
    page_cache[sha] = txt
    return txt

def cite_pages(r, wrong):
    cites = []
    for m in re.finditer(r"([^\s#;][^#;]*?)#([0-9a-f]{16})", r.get("source_syllabus", "") or ""):
        fname, sha = m.group(1).strip(), m.group(2)
        pages = doc_pages(sha)
        if not pages:
            continue
        hits = [i + 1 for i, t in enumerate(pages) if re.search(rf"\b{re.escape(wrong)}", t or "", re.I)]
        if hits:
            cites.append(f"{fname}#{sha} pp.{','.join(map(str, hits[:6]))} (printed form)")
        if cites:
            break
    return cites

by_id = {r["subject_id"]: r for r in rows}
n_cite = 0
for e in edits:
    cites = cite_pages(by_id[e["sid"]], e["before"])
    ev = e["evidence"]
    if cites:
        ev = "; ".join(cites) + " — " + ev
        n_cite += 1
    e["evidence"] = ev[:400]

print(f"W1|page-cited edits={n_cite}/{len(edits)}")
uncited = [f"{e['sid']}:{e['field']}:{e['before']}" for e in edits if e["evidence"].startswith(("ref:", "xrow:"))]
if uncited:
    print("W1|UNCITED (kept, ref-only evidence):", "; ".join(uncited[:12]))

pre_rows = {r["subject_id"]: dict(r) for r in rows}
flags_doc = WC.load_flags()
rows2, per_sid, skipped = WC.apply_edits(rows, edits, "W1", flags_doc,
    note_extra="§6b W1: printed typos corrected in primary fields per owner D1 (before-forms preserved in corrections_json; *_print/scheme-line verbatim unchanged)")
if skipped:
    print("W1|SKIPPED:", skipped[:10])
gates = WC.run_gates(rows2, set(per_sid.keys()), pre_rows)
print(f"G1|{'PASS' if not gates['g1'] else 'FAIL ' + gates['g1']}")
print(f"G2|{'PASS' if not gates['g2'] else 'FAIL ' + gates['g2']}|codes={gates['g2_codes']}")
print(f"G3|{'PASS' if not gates['g3'] else 'FAIL ' + gates['g3']}")
print(f"G6|{'PASS' if not gates['g6'] else 'FAIL ' + gates['g6']}|checks={gates['g6_checks']}|pre_edit_hits={gates['g6_pre_edit_hits']}")
if any([gates["g1"], gates["g2"], gates["g3"], gates["g6"]]):
    print("ABORT: gate failure")
    sys.exit(2)

WC.commit(rows2, "W1", len(edits), gates, {"terms": {k: len(v) for k, v in term_rows.items()},
                                            "rows_touched": len(per_sid)})
# refresh audit flags: consumed W1 rules
fixed_rules = {f"AUTH_TYPO_{k.lower()}" for k in DICT}
try:
    doc = json.load(open(f"{BASE}/audit_flags.json"))
    for sid in list(doc.get("rows", {})):
        doc["rows"][sid] = [f for f in doc["rows"][sid]
                            if not (f.get("rule", "").startswith("AUTH_TYPO_") and f["rule"] in fixed_rules)]
        if not doc["rows"][sid]:
            doc["rows"].pop(sid)
    json.dump(doc, open(f"{BASE}/audit_flags.json", "w"), indent=1, ensure_ascii=False)
except Exception as e:
    print("W1|flag-refresh warn:", e)
# evidence table for the manifest
print("W1|EVIDENCE_TABLE")
for wrong, sids in sorted(term_rows.items()):
    right = DICT[wrong][0]
    print(f"  {wrong} → {right}: {len(sids)} rows; e.g. {sorted(sids)[:3]}")
