#!/usr/bin/env python3
"""b37_verify_fix.py — targeted repairs for the B37 verify findings (all
zero-guess, print-anchored):
  A. strip ORPHAN codes (draft codes absent from the PDF text — verifier logic);
  B. split compound code prints at '/' when both atoms print in the PDF;
  C. remove template-garbage-name rows (model template echoes);
  D. add literal 'no code printed in document' flag to no-code rows (verifier
     v10 downgrade class) + move MOOCs note rows to non_subject_rows;
  E. scheme_row_only flag for rows whose subject prints no detail beyond the
     scheme table (per-doc name search outside scheme pages);
  F. re-extract rows whose detail pages exist but extraction failed/empty."""
import json, re, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as me

BASE = "/home/z/my-project/work/pipeline_v2"
GARBAGE_MARKERS = ("<canonical", "canonical spelling", "title of the course", "<verbatim", "<codes")

def pdf_atomic(text):
    out = set()
    for m in re.finditer(r"\b([A-Z]{2,4})((?:\s*[-\u2013]?\s*\d{3}[A-Z]?\s*(?:[/,&+()]|and\b)\s*)+\d{3}[A-Z]?|(?:\s*[-\u2013]?\s*\d{3}[A-Z]?))", text):
        for d in re.findall(r"\d{3}", m.group(2)):
            out.add(m.group(1) + d)
    return out

def norm_al(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def load(stem):
    d = json.load(open(f"{BASE}/drafts_B37/{stem}.draft.json"))
    full = open(f"{BASE}/parsed/{stem}.fulltext.txt").read()
    pa = pdf_atomic(full)
    return d, full, pa

def save(d, stem):
    json.dump(d, open(f"{BASE}/drafts_B37/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)

def row_codes(s):
    return [re.sub(r"[^A-Z0-9]", "", (c or "").upper()) for c in (s.get("codes") or []) if c]

def common(d, full, pa, stem):
    log = []
    # A. orphans + B. compound split + C. garbage names
    keep = []
    for s in d["subjects"]:
        nm = (s.get("name") or s.get("name_print") or "")
        low = nm.lower()
        if any(mk in low for mk in GARBAGE_MARKERS):
            log.append(f"C:removed template-garbage row {[row_codes(s)]}")
            continue
        cs = row_codes(s)
        atoms = []
        for c in cs:
            if c in pa or c in full.replace(" ", ""):
                atoms.append(c)
            elif "/" in (s.get("codes") or [""])[cs.index(c)] or len(c) > 6 and c[:3] in pa and c[3:6] in pa:
                a, b = c[:len(c) // 2], c[len(c) // 2:]
                if a in pa and b in pa:
                    atoms.extend([a, b])
                else:
                    # tolerant: prefix + each digit-triple printed after it
                    pre = re.match(r"[A-Z]+", c).group(0)
                    tris = re.findall(r"\d{3}", c)
                    if all(re.search(re.escape(pre) + r"[\s\-]*" + t, full) for t in tris):
                        atoms.extend(pre + t for t in tris)
                    else:
                        log.append(f"A:stripped orphan {c} from {nm[:26]}")
            else:
                log.append(f"A:stripped orphan {c} from {nm[:26]}")
        if cs and not atoms:
            log.append(f"A:dropped row with no provable codes {nm[:26]}")
            continue
        if atoms and set(atoms) != set(cs):
            s["codes"] = atoms
        keep.append(s)
    d["subjects"] = keep
    # D. no-code flags + MOOCs move
    still = []
    for s in d["subjects"]:
        cs = row_codes(s)
        nm = (s.get("name") or s.get("name_print") or "")
        fl = [str(f).lower() for f in (s.get("flags") or [])]
        if not cs:
            if re.search(r"MOOC|honours", nm, re.I):
                d.setdefault("non_subject_rows", []).append(
                    {"kind": "moocs-note", "print": nm, "locator": "draft subject row (no code printed)"})
                log.append(f"D:MOOCs row -> non_subject_rows ({nm[:32]})")
                continue
            if not any("no code" in f for f in fl + [str(q).lower() for q in (s.get("quirks") or [])]):
                s.setdefault("flags", []).append("no code printed in document (elective/DE/OE slot family)")
                log.append(f"D:no-code flag on {nm[:32]}")
        still.append(s)
    d["subjects"] = still
    return d, log

def has_detail(full, name, scheme_pages):
    """does the name print beyond the scheme table pages?"""
    pat = re.escape(norm_al(name))[:20]
    for pno, ptext in me.pages_of(full):
        if pno in scheme_pages:
            continue
        if pat and pat in norm_al(ptext):
            return pno
    return None

def scheme_pages_of(full):
    return {p for p, t in me.pages_of(full) if re.search(r"Evaluation\s+Scheme|Study\s+and\s+Evaluation|Scheme of Teaching", t, re.I)}

def reextract(stem, d, full, targets):
    """targets: list of (row, page) — re-extract via extract_one, replace in place"""
    PAGES = me.pages_of(full)
    det_pages = sorted({p for _, p in targets})
    for row, page in targets:
        nxt = next((q for q in det_pages if q > page), None)
        sl = "\n\n".join(t for pp, t in PAGES if pp >= page and (nxt is None or pp < nxt))
        try:
            code, obj = me.extract_one(stem + ".pdf", sl, {"file": stem + ".pdf"},
                                       {"class": "detail", "code_print": ",".join(row.get("codes") or []),
                                        "name_print": row.get("name") or row.get("name_print") or "", "page": page},
                                       d.get("session", ""), d.get("course", "BTech"))
        except Exception as e:  # noqa: BLE001
            print(f"  reextract-fail {row.get('name','')[:24]}: {repr(e)[:80]}")
            continue
        if isinstance(obj, list):
            obj = next((x for x in obj if isinstance(x, dict)), {})
        if obj.get("scheme_row_only"):
            row.setdefault("flags", []).append("scheme_row_only_detailed_syllabus_not_printed")
            row.setdefault("quirks", []).append("detail re-extraction returned scheme-row-only (print evidence)")
            continue
        for k in ("units", "experiments", "cos", "objectives_print", "textbooks", "reference_books", "marks", "ltp", "credit"):
            if obj.get(k):
                row[k] = obj[k]
        row.setdefault("quirks", []).append(f"re-extracted from detail page p.{page} (B37 verify repair)")
        print(f"  reextract OK {row.get('name','')[:30]} units={len(row.get('units') or {})} exp={len(row.get('experiments') or [])}")

if __name__ == "__main__":
    print("helper module ok")
