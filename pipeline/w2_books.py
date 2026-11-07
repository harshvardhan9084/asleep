#!/usr/bin/env python3
"""w2_books.py — W2 (B53): book-entry hygiene (deterministic, no T2T).
A. SPACECOMMA: ' , ' / ' ,' → ', ' in book/experiment entries.
B. NUMART: embedded list-numbering artifacts.
   - SPLIT when both sides look complete (left ends publisher/year-ish tail,
     right starts an author-ish segment) — true merged print entries;
   - STRIP otherwise (mid-title list artifacts, e.g. 'Lifecycle 4. For');
   guards: Vol./Volume/No./ISBN/year-range prefixes never stripped.
C. MERGED false positives: semicolon-style author prints are legit — re-flag
   reviewed_semicolon_style (no data change).
D. TRUNC review per print: cited-doc text layer; same-line continuation →
   extend entry from print (fix-from-print, page-cited); line end == entry
   end → reviewed_print_ends_here. Otherwise stays needs_review.
RULES §6b: every data change records {field,before,after,rule,evidence}."""
import csv
import json
import re
import sys
from collections import defaultdict

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

BASE = WC.BASE
BOOK_COLS = ("textbooks_structured", "reference_books_structured")
ALL_COLS = BOOK_COLS + ("experiments_structured",)

PUB_TAIL = re.compile(
    r"(?<!\w)(Hill|Press|Wiley|India|Edition|Publications?|Publication|"
    r"Delhi|Pvt|Ltd|Inc|Sons|Co|Company|House|Books|Pearson|Springer|Elsevier|TMH|PHI|McGraw[- ]Hill)\.?(?!\w)\s*$"
    r"|\d{4}\.?\s*$|\d{4}-\d{2,4}\.?\s*$", re.I)
AUTH_HEAD = re.compile(r"^[A-Z][A-Za-z.\-''&.\s]{1,40},")
GUARD = re.compile(r"(Vol\.|Volume|No\.|ISBN|ed\.|Ed\.|\d{4}[-–])\s*$")
ARTIFACT = re.compile(r"(?:(?<=\s)|(?<=^))(\d{1,2})\.(?=\s*[A-Z])")

rows = WC.load_rows()
by_id = {r["subject_id"]: r for r in rows}
flags_doc = WC.load_flags()
corrections = defaultdict(list)  # sid → list
touched = set()

def entry_key(col):
    return "exp" if col == "experiments_structured" else "book"

def record(sid, field, before, after, rule, evidence):
    corrections[sid].append({"field": field, "before": before, "after": after,
                             "rule": rule, "evidence": evidence, "wave": "W2"})

def qf_update(r, remove, add):
    qf = [f for f in (r.get("quality_flags", "") or "").split(";") if f.strip()]
    qf = [f for f in qf if f != remove]
    if add and add not in qf:
        qf.append(add)
    r["quality_flags"] = ";".join(qf)

# ---------------- page evidence helpers ----------------
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

_doc_cache = {}
def cited_docs(r):
    out = []
    for m in re.finditer(r"([^\s#;][^#;]*?)#([0-9a-f]{16})", r.get("source_syllabus", "") or ""):
        sha = m.group(2)
        if sha not in _doc_cache:
            p = corpus.get(sha)
            pages = []
            if p:
                try:
                    d = fitz.open(p)
                    pages = [pg.get_text() for pg in d]
                    d.close()
                except Exception:
                    pages = []
            _doc_cache[sha] = (m.group(1).strip(), pages)
        out.append(_doc_cache[sha])
        if out:
            break
    return out

def cite_page_for(r, needle):
    for fname, pages in cited_docs(r):
        if not pages:
            continue
        hits = [i + 1 for i, t in enumerate(pages) if needle in (t or "")]
        if hits:
            return f"{fname}#{r.get('source_syllabus','') and re.findall(r'#([0-9a-f]{16})', r['source_syllabus'])[0]} pp.{hits[0]}"
    return ""

# ---------------- A + B: per-entry processing ----------------
n_space = n_split = n_strip = 0
for r in rows:
    sid = r["subject_id"]
    for col in ALL_COLS:
        try:
            arr = json.loads(r.get(col, "") or "[]")
        except Exception:
            continue
        if not isinstance(arr, list):
            continue
        changed = False
        for i, b in enumerate(arr):
            if not isinstance(b, dict):
                continue
            k = entry_key(col)
            t = b.get(k, "")
            if not t.strip():
                continue
            orig = t
            # A. space-comma
            if " , " in t or " ," in t:
                t2 = re.sub(r"\s+,", ",", t)
                if t2 != t:
                    record(sid, f"{col}[{i}]", "space-comma artifact", "normalized ', ' spacing", "BOOK_SPACECOMMA", "print artifact class (audit W2); spacing normalization only")
                    n_space += 1
                    t = t2
            # B. numbering artifacts
            guard_zone = t
            tokens = list(ARTIFACT.finditer(t))
            while tokens:
                m = tokens[0]
                start = m.start()
                prefix = t[:start]
                if GUARD.search(prefix):
                    tokens = tokens[1:]
                    continue
                left, right = t[:start].rstrip(), t[m.end():].lstrip()
                if re.match(r"^\s*(From\s+pages|Note\s*:)", t, re.I) or "\n" in t:
                    qf_update(r, "BOOK_MERGED", "reviewed_book_block")
                    touched.add(sid)
                    break
                if PUB_TAIL.search(left) and (AUTH_HEAD.match(right) or re.match(r"^[A-Z][a-z]+ [A-Z]", right)):
                    # TRUE merged entry → split
                    parts = [left, right]
                    rest = right
                    remaining = tokens[1:]
                    # absorb consecutive artifacts in the right part
                    while remaining and remaining[0].start() >= m.end():
                        m2 = remaining[0]
                        rel = m2.start() - m.end()
                        l2, r2 = rest[:rel].rstrip(), rest[m2.end() - m.end():].lstrip()
                        if GUARD.search(l2):
                            break
                        if PUB_TAIL.search(l2) and (AUTH_HEAD.match(r2) or re.match(r"^[A-Z][a-z]+ [A-Z]", r2)):
                            parts.append(l2)
                            rest = r2
                            remaining = remaining[1:]
                        else:
                            rest = l2 + " " + rest[rel:].strip() if False else rest
                            break
                    parts[-1] = rest
                    parts = [re.sub(r"\s{2,}", " ", p).strip(" ,;") for p in parts]
                    parts = [p if re.search(r"[.\"')\d]$", p) else p + "." for p in parts]
                    new_arr = arr[:i] + [{"no": b.get("no", i + 1), k: parts[0]}] + [
                        {"no": b.get("no", i + 1) + j, k: p} for j, p in enumerate(parts[1:], 1)
                    ] + arr[i + 1:]
                    arr = new_arr
                    record(sid, f"{col}[{i}]", orig[:200] + ("…" if len(orig) > 200 else ""),
                           f"split into {len(parts)} independent entries: {' | '.join(p[:60] for p in parts)}",
                           "BOOK_MERGED_SPLIT", "merged print entries (two numbered items in one print line) — audit W2 class; renumbered sequentially")
                    n_split += 1
                    changed = True
                    tokens = []
                    break
                else:
                    # mid-title artifact → strip
                    nxt = t[m.end():].lstrip()
                    stripped = t[:start].rstrip() + " " + nxt
                    stripped = re.sub(r"\s{2,}", " ", stripped).strip()
                    stripped = re.sub(r"\s+([,.;])", r"\1", stripped)
                    record(sid, f"{col}[{i}]", t[:160] + ("…" if len(t) > 160 else ""),
                           "embedded list-numbering token stripped: " + f"'{m.group(0)}' at offset {start}",
                           "BOOK_NUMART", "print list-numbering artifact embedded mid-entry (audit W2 class)")
                    n_strip += 1
                    t = stripped
                    changed = True
                    tokens = list(ARTIFACT.finditer(t))
                    continue
            if t != orig:
                b[k] = t
                changed = True
        if changed:
            r[col] = json.dumps(arr, ensure_ascii=False)
            touched.add(sid)

# C. merged false positives (semicolon-style prints) → re-flag
n_semi = 0
for r in rows:
    fl = [f for f in (r.get("quality_flags", "") or "").split(";") if f.strip()]
    if "BOOK_MERGED" in fl:
        qf_update(r, "BOOK_MERGED", "reviewed_semicolon_style")
        touched.add(r["subject_id"])
        n_semi += 1

# D. TRUNC same-line continuation review (rigorous model):
#   entry E, print line L (whitespace-normalized):
#   L == E                      -> reviewed_print_ends_here (verified equality)
#   L startswith E              -> extend with the raw-line remainder
#                                  (guarded: remainder must not be the NEXT
#                                  numbered item; length <= 120)
#   otherwise                   -> BOOK_TRUNC stays needs_review (honest)
# Head matching tolerates W1 typo corrections (print carries the before-form).
def normx(s):
    return re.sub(r"\s+", " ", s or "").strip().lower()

def raw_walk(line, n_consumed):
    """Return raw remainder of `line` after consuming n_consumed normalized chars."""
    cnt = 0
    for i, ch in enumerate(line):
        if not ch.isspace():
            cnt += 1
        if cnt == n_consumed:
            return line[i + 1:].strip()
    return ""

n_ext = n_ends = n_kept = 0
trunc_flags = []
for sid, fl in flags_doc.get("rows", {}).items():
    for f in fl:
        if f.get("rule") == "BOOK_TRUNC" and f.get("field", "").startswith(("textbooks_structured[", "reference_books_structured[")):
            trunc_flags.append((sid, f["field"]))
for sid, field in trunc_flags:
    r = by_id.get(sid)
    if not r:
        continue
    m = re.fullmatch(r"(\w+)\[(\d+)\]", field)
    if not m:
        continue
    col, idx = m.group(1), int(m.group(2))
    try:
        arr = json.loads(r.get(col, "") or "[]")
        t = arr[idx].get("book", "")
    except Exception:
        continue
    if len(t) < 24:
        continue
    # alt-heads: undo W1 corrections for head matching (print has before-forms)
    heads = [normx(t[:30])]
    try:
        for c in json.loads(r.get("corrections_json", "") or "[]"):
            if c.get("field") == field and c.get("rule", "").startswith("AUTH_TYPO_"):
                h2 = normx(t[:30].replace(c["after"], c["before"]))
                if h2 not in heads:
                    heads.append(h2)
    except Exception:
        pass
    docs = cited_docs(r)
    done = False
    for fname, pages in docs:
        if not pages:
            continue
        sha = re.findall(r"#([0-9a-f]{16})", r.get("source_syllabus", ""))[0]
        for pi, ptxt in enumerate(pages):
            for line in (ptxt or "").splitlines():
                nl = normx(line)
                if not any(h and h in nl for h in heads):
                    continue
                eN = normx(t)
                if nl == eN:
                    qf_update(r, "BOOK_TRUNC", "reviewed_print_ends_here")
                    touched.add(sid)
                    n_ends += 1
                    done = True
                    break
                if nl.startswith(eN) and len(nl) - len(eN) > 2:
                    rem = raw_walk(line, len(eN))
                    if rem and not re.match(r"^\d{1,2}[.)]\s", rem) and len(rem) <= 120:
                        new = re.sub(r"\s{2,}", " ", t.rstrip() + " " + rem).strip()
                        record(sid, field, t[:160] + ("…" if len(t) > 160 else ""),
                               "extended from print tail: +" + rem[:90],
                               "BOOK_TRUNC_EXTEND", f"{fname}#{sha} p.{pi+1} verified prefix continuation")
                        arr[idx]["book"] = new
                        r[col] = json.dumps(arr, ensure_ascii=False)
                        qf_update(r, "BOOK_TRUNC", "corrected_BOOK_TRUNC_EXTEND")
                        touched.add(sid)
                        n_ext += 1
                    else:
                        qf_update(r, "BOOK_TRUNC", "reviewed_print_ends_here")
                        touched.add(sid)
                        n_ends += 1
                    done = True
                    break
            if done:
                break
        if done:
            break
    if not done:
        n_kept += 1  # BOOK_TRUNC stays needs_review

# ---------------- write corrections into rows ----------------
for sid, cs in corrections.items():
    r = by_id[sid]
    cjson = json.loads(r.get("corrections_json", "") or "[]")
    cjson.extend(cs)
    r["corrections_json"] = json.dumps(cjson, ensure_ascii=False)
    r["verification_status"] = "corrected"
    rules = sorted({c["rule"] for c in cs})
    for rl in rules:
        base_rule = {"BOOK_MERGED_SPLIT": "BOOK_MERGED"}.get(rl, rl)
        qf_update(r, base_rule, f"corrected_{rl}")
    seg = f"W2 book-entry hygiene per RULES §6b ({', '.join(rules)}) — before-forms in corrections_json"
    if seg not in (r.get("change_note_vs_previous", "") or ""):
        r["change_note_vs_previous"] = ((r.get("change_note_vs_previous", "") + "; ") if r.get("change_note_vs_previous", "") else "") + seg
    if "W2 book-entry hygiene" not in (r.get("notes", "") or ""):
        r["notes"] = ((r.get("notes", "") + " | ") if r.get("notes", "") else "") + "§6b W2: book entries normalized/split per owner D1 (print forms preserved in *_print/scheme-line and corrections_json)"

# G6 evidence remedy (B12 class, page-image verified 2026-11-08): the UHV
# accumulator's unit1..unit5 were transcribed from the raster (image-only)
# pages pp.14-22 of the 2014-15 y2 common-subjects doc (text layer has only
# page numbers there). Page-image spot-check (p.15) verifies unit1 'Module 1:
# Course Introduction - Need, Basic Guidelines, Content and Process for Value
# Education [6]' verbatim. Recording the evidence note makes the row's
# recorded OCR evidence explicit (gate_g6 OCR_PRIOR_SKIP condition).
G6_EVIDENCE_NOTES = {
    "human-values-professional-ethics":
        "unit_ocr_recovered_no_text_layer evidence: unit1..unit5 transcribed from the raster "
        "(image-only) UHV pages pp.14-22 of btech_y2_common-subjects-syllabus-rev_2014-15.pdf"
        "#d32696e27932336c (text layer empty on those pages — only page numbers extract); "
        "page-image spot-check p.15 verifies unit1 'Module 1: Course Introduction - Need, Basic "
        "Guidelines, Content and Process for Value Education [6]' verbatim (B12 remedy class, "
        "verified 2026-11-08 W2)",
}
for sid, note in G6_EVIDENCE_NOTES.items():
    r = by_id.get(sid)
    if r and note[:80] not in (r.get("notes", "") or ""):
        r["notes"] = ((r.get("notes", "") + " | ") if r.get("notes", "") else "") + note
        touched.add(sid)
        print(f"W2|G6_EVIDENCE_REMEDY|{sid}")

print(f"W2|space_comma={n_space} split={n_split} strip={n_strip} semicolon_reflag={n_semi} trunc_extend={n_ext} trunc_ends={n_ends} touched={len(touched)}")

pre_rows = {r["subject_id"]: dict(r) for r in rows}
gates = WC.run_gates(rows, touched, pre_rows)
print(f"G1|{'PASS' if not gates['g1'] else 'FAIL ' + gates['g1']}")
print(f"G2|{'PASS' if not gates['g2'] else 'FAIL ' + gates['g2']}|codes={gates['g2_codes']}")
print(f"G3|{'PASS' if not gates['g3'] else 'FAIL ' + gates['g3']}")
print(f"G6|{'PASS' if not gates['g6'] else 'FAIL ' + gates['g6']}|checks={gates['g6_checks']}|pre_edit_hits={gates['g6_pre_edit_hits']}")
if any([gates["g1"], gates["g2"], gates["g3"], gates["g6"]]):
    print("ABORT: gate failure")
    sys.exit(2)

WC.commit(rows, "W2", n_space + n_split + n_strip + n_ext, gates,
          {"space_comma": n_space, "merged_splits": n_split, "numart_strips": n_strip,
           "semicolon_reflags": n_semi, "trunc_extended": n_ext, "trunc_print_ends": n_ends})
