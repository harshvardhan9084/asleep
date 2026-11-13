#!/usr/bin/env python3
"""b96_build_year_plan.py — CRON-20261113-B96.

Rebuild the owner's #1 need: (course, branch, academic year) -> the ~6+6
subjects a student actually studies per semester. The deduplicated catalog
CSV lost the per-(doc, semester) grain, but it survives in:
  1. the 613 source PDFs (scheme tables on early pages, deterministic text
     layer — probed clean on 5-course NEP/CBCS docs), and
  2. the 109 surviving draft JSONs (per-subject semester + codes).

df_year_plan.csv = one row per PRINTED scheme line (doc x semester x SN):
doc, session, course, branch set (from the cover page), semester, SN, codes,
subject name, L/T/P, credit, row_kind, and the catalog subject_id link.

Zero writes to the of-record CSV.
"""
import csv
import glob
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict

import fitz

PDF_ROOT = "/home/z/my-project/work/repo_asleep/PDFs"
DRAFTS = "/home/z/my-project/work/repo_asleep/pipeline"
CATALOG = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
OUT = "/home/z/my-project/download/art_d_final/df_year_plan.csv"
REPO_OUT = "/home/z/my-project/work/repo_asleep/syllabus_catalog/df_year_plan.csv"
STATS = "/home/z/my-project/work/pipeline_v2/b96_stats.json"

COURSE_MAP = [("btech", "BTech"), ("mba", "MBA"), ("mca", "MCA"),
              ("bca", "BCA"), ("bpharm", "BPharm"), ("barch", "BArch"),
              ("mtech", "MTech"), ("bvoc", "BVoc"), ("bdes", "BDes"),
              ("bfad", "BFad"), ("bfa", "BFA")]

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7,
         "VIII": 8, "IX": 9, "X": 10}
PLACEHOLDER_RE = re.compile(
    r"^(OPENELECTIVE|DEPARTMENTALELECTIVE|DEPTTELECTIVE|ELECTIVE|OPENELEC)"
    r"[0-9IVX]*$|^OEMOPENELECTIVE", re.I)


def sem_int(v):
    v = str(v).strip().upper()
    if v.isdigit():
        return int(v)
    return ROMAN.get(v, "")

HEAD_RE = re.compile(r"SEMESTER\s*[-–]?\s*([0-9IVX]+)", re.I)
SN_RE = re.compile(r"^\d{1,2}$")
CODE_RE = re.compile(r"^[A-Z]{2,4}[0-9]{3}[A-Z]?[0-9]?$|^[A-Z]{2,4}[- ]?ELECTIVE|^[A-Z]{2,4}\d{3}[A-Z]?/")
INT_RE = re.compile(r"^\d+$")
ELEC_RE = re.compile(r"elective", re.I)


def sha16(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def course_of(fname):
    low = fname.lower()
    for tok, c in COURSE_MAP:
        if low.startswith(tok + "_") or low.startswith(tok + "-"):
            return c
    return "Other"


def cover_branches(doc, text0):
    """Branch set from the cover page: bullet lines (and the stray
    continuation tokens) between the programme line and 'Based On'."""
    branches = []
    lines = [l.strip() for l in text0.splitlines() if l.strip()]
    in_zone = False
    for l in lines:
        if re.search(r"SYLLABUS|SCHEME|STRUCTURE|ORDINANCE", l, re.I):
            in_zone = True
            continue
        if in_zone and re.search(r"Based\s*On|Effective\s*from|Choice Based", l, re.I):
            break
        if in_zone and l.startswith("•"):
            branches.append(l.lstrip("•").strip())
        elif in_zone and branches and not INT_RE.match(l) and len(l) < 70 \
                and not re.search(r"DR\.|UNIVERSITY|UTTAR|LUCKNOW", l, re.I):
            if l.startswith("/"):
                branches.append(l.lstrip("/").strip())
    return branches


def parse_scheme_page(page, text):
    """Layout-based scheme-table parser (final architecture).

    - Rows are delimited by SN entries (1-2 digit ints at the left edge),
      with midpoint y-boundaries (SNs are vertically centred on wrapped
      names).
    - Per token: code-like (CODE_RE) -> codes column; pure 1-3 digit ints
      -> numeric columns (data-driven x clusters); everything else -> name.
    - Numeric semantics anchored to header-zone spans: single-letter
      'L'/'T'/'P' spans (nearest cluster) and a 'credit'-containing span
      (nearest cluster); positional fallback: first three clusters L/T/P
      when 'Periods' prints in the header, last cluster = credit when
      'Credit' prints. Remaining clusters = marks, x-ordered.
    """
    out = []
    d = page.get_text("dict")
    lines = []
    for blk in d.get("blocks", []):
        for ln in blk.get("lines", []):
            spans = [(round(s["bbox"][0]), s["text"].strip())
                     for s in ln.get("spans", []) if s["text"].strip()]
            if not spans:
                continue
            spans.sort()
            lines.append((round(ln["bbox"][1]), spans,
                          " ".join(t for _, t in spans)))
    if not lines:
        return out
    lines.sort(key=lambda x: x[0])
    heads = []
    for y, spans, txt in lines:
        m = HEAD_RE.search(txt)
        if m and len(txt) < 60:
            heads.append((y, m.group(1)))
    low_full = (text or "").lower()
    for hi, (hy, sem) in enumerate(heads):
        y_end = heads[hi + 1][0] if hi + 1 < len(heads) else 1e9
        region = [(y, spans, txt) for (y, spans, txt) in lines
                  if hy < y < y_end]
        if not region:
            continue
        min_x = min(s[0] for _, spans, _ in region for s in spans[:1])
        sn_spans = []
        for y, spans, txt in region:
            for x, t in spans:
                if re.fullmatch(r"\d{1,2}", t) and x <= min_x + 25:
                    sn_spans.append((y, int(t)))
        if not sn_spans:
            continue
        sn_spans.sort()
        first_sn_y = sn_spans[0][0]
        # numeric clusters across the whole table
        num_cells = []
        for y, spans, txt in region:
            if y < first_sn_y - 20:
                continue
            for x, t in spans:
                if re.fullmatch(r"\d{1,3}", t) and x > min_x + 25:
                    num_cells.append((y, x, t))
        xs = sorted(x for _, x, _ in num_cells)
        clusters = []
        for x in xs:
            if clusters and x - clusters[-1][1] <= 6:
                clusters[-1][1] = x
            else:
                clusters.append([x, x])
        centers = [(a + b) / 2 for a, b in clusters]
        kinds = [None] * len(centers)
        # header-anchored semantics from spans ABOVE the first SN
        hdr = [(x, t) for y, spans, _ in lines if y < first_sn_y
               for x, t in spans]
        for x, t in hdr:
            tl = t.strip().lower()
            if tl in ("l", "t", "p") and centers:
                j = min(range(len(centers)), key=lambda k: abs(centers[k] - x))
                want = {"l": "L", "t": "T", "p": "P"}[tl]
                if kinds[j] is None:
                    kinds[j] = want
            elif "credit" in tl and len(tl) < 20 and centers:
                j = min(range(len(centers)),
                        key=lambda k: abs(centers[k] - x - len(t) * 2))
                if kinds[j] is None:
                    kinds[j] = "credit"
        used = {k for k in kinds if k in ("L", "T", "P")}
        if "period" in low_full and len(centers) >= 3 and len(used) < 3:
            for i in range(min(3, len(kinds))):
                if kinds[i] is None:
                    kinds[i] = ["L", "T", "P"][i]
        if ("credit" in low_full) and len(kinds) > 3 \
                and kinds[-1] is None:
            kinds[-1] = "credit"
        kinds = [k or "mark" for k in kinds]
        bounds = []
        for i in range(len(sn_spans)):
            top = (sn_spans[i - 1][0] + sn_spans[i][0]) / 2 if i else \
                first_sn_y - 25
            bot = (sn_spans[i][0] + sn_spans[i + 1][0]) / 2 \
                if i + 1 < len(sn_spans) else y_end
            bounds.append((top, bot))
        HEADER_VOCAB = {"sl.", "no.", "sl", "no", "codes", "code", "subject",
                        "periods", "evaluation", "scheme", "end", "semester",
                        "total", "credit", "l", "t", "p", "ct", "ta", "ps",
                        "te", "pe"}
        for (y0, y1), (sy, sn) in zip(bounds, sn_spans):
            cells = {"L": "", "T": "", "P": "", "credit": ""}
            marks, codes_w, name_w = [], [], []
            stop = False
            for y, spans, txt in region:
                if not (y0 <= y < y1):
                    continue
                for x, t in spans:
                    low = t.lower()
                    if y < first_sn_y and low in HEADER_VOCAB:
                        continue  # stacked header row overlaps row 1's band
                    if re.fullmatch(r"\d{1,2}", t) and x <= min_x + 25:
                        continue  # the row's own SN (or a sibling's)
                    if re.fullmatch(r"\d{1,3}", t) and x > min_x + 25:
                        if not centers:
                            continue
                        j = min(range(len(centers)),
                                key=lambda k: abs(centers[k] - x))
                        k = kinds[j]
                        if k in cells and not cells[k]:
                            cells[k] = t
                        else:
                            marks.append((x, t))
                        continue
                    if CODE_RE.match(t.rstrip("/")) and len(t) >= 5:
                        codes_w.append(t)
                        continue
                    if name_w and name_w[-1] == t:
                        continue
                    name_w.append(t)
                    if low.rstrip(":") == "total":
                        stop = True
                if stop:
                    break
            marks = [v for _, v in sorted(marks)]
            name = " ".join(name_w).strip(" /-")
            if stop and name.lower().endswith(" total"):
                name = name[:-6].rstrip(" /-")
            codes_s = "/".join(c.strip(" -./") for c in codes_w)
            joined = (codes_s + " " + name).lower()
            if "elective" in joined:
                codes_s = ""
                row_kind = "elective-slot"
                if not name:
                    name = "Elective slot"
            elif codes_s and not name:
                name = codes_s
                codes_s = ""
            if not name and not codes_s:
                continue  # stop alone is fine: the row itself is complete
            row_kind = "subject"
            if "elective" in joined:
                row_kind = "elective-slot"
            if re.search(r"mandatory|audit|non-?credit", joined):
                row_kind = "non-credit"
            out.append((sem, str(sn), codes_s, name,
                        cells["L"] or None, cells["T"] or None,
                        cells["P"] or None, cells["credit"] or None,
                        ";".join(marks), row_kind))
    return out


def resolve_draft_branches(d, doc_scope):
    s = str(d.get("sha16") or "")
    if s in doc_scope and doc_scope[s].get("branch_names"):
        return doc_scope[s]["branch_names"], "doc_scope"
    return "", "unresolved"


def main():
    sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
    import merge_draft as MD

    # catalog code -> subject_id link map
    cat = list(csv.DictReader(open(CATALOG)))
    code2sid = {}
    for r in cat:
        for c in (r["all_codes"] or "").split(";"):
            c = c.strip()
            if c:
                code2sid.setdefault(re.sub(r"[^A-Z0-9]", "", c.upper()), r["subject_id"])

    rows = []
    pdfs = sorted(glob.glob(os.path.join(PDF_ROOT, "**", "*.pdf"), recursive=True))
    no_text = 0
    parsed_docs = 0
    for p in pdfs:
        rel = os.path.relpath(p, PDF_ROOT)
        fname = os.path.basename(p)
        try:
            doc = fitz.open(p)
        except Exception:
            continue
        if len(doc) == 0:
            continue
        text0 = doc[0].get_text("text")
        if len(text0.strip()) < 40:
            no_text += 1
            continue
        session = os.path.basename(os.path.dirname(p))
        if not re.match(r"^\d{4}-\d{2}$", session):
            m = re.search(r"_(\d{4}-\d{2})\.pdf$", fname)
            session = m.group(1) if m else ""
        course = course_of(fname)
        branches = cover_branches(doc, text0)
        if not branches:
            s = sha16(p)
            if s in MD.DOC_SCOPE and MD.DOC_SCOPE[s].get("branch_names"):
                branches = MD.DOC_SCOPE[s]["branch_names"].split(";")
        got = []
        scan = list(range(0, min(6, len(doc))))
        for pno in scan:
            got += parse_scheme_page(doc[pno], doc[pno].get_text("text"))
        if got:
            parsed_docs += 1
        for (sem, sn, codes, name, l_, t_, p_, credit, nums, kind) in got:
            sids = []
            code_clean = ""
            if kind == "elective-slot":
                codes = ""
            for c in re.split(r"[/;]", codes):
                n = re.sub(r"[^A-Za-z0-9]", "", c)
                if not n:
                    continue
                if PLACEHOLDER_RE.match(n):
                    kind = "elective-slot"
                    continue
                code_clean = (code_clean + "/" + c.strip()).strip("/")
                sid = code2sid.get(n.upper())
                if sid:
                    sids.append(sid)
            rows.append({
                "source": "pdf-scheme-page", "doc_file": fname,
                "doc_sha16": sha16(p), "course": course, "session": session,
                "doc_branches": "; ".join(branches), "semester": sem,
                "semester_int": sem_int(sem), "sn": sn, "codes": code_clean,
                "subject_name_print": name,
                "L": l_ or "", "T": t_ or "", "P": p_ or "",
                "credit": credit if credit is not None else "",
                "row_kind": kind,
                "subject_id": ";".join(sorted(set(sids))),
                "nums_raw": nums, "doc_rel": rel,
            })
        doc.close()

    n_pdf_rows = len(rows)

    # ---- draft-sourced rows for docs where the PDF parse failed/absent ----
    files = sorted(glob.glob(os.path.join(DRAFTS, "**", "*.draft.json"),
                             recursive=True))
    seen_drafts = {}
    for f in files:
        d = json.load(open(f))
        seen_drafts.setdefault((d.get("stem", ""), str(d.get("sha16", ""))), d)
    shas_with_pdf = {r["doc_sha16"] for r in rows}
    per_doc_pdf = Counter(r["doc_sha16"] for r in rows)
    n_draft_rows = 0
    for (stem, s16), d in seen_drafts.items():
        subs = d.get("subjects", [])
        if not subs:
            continue
        # prefer pdf rows when the same doc already parsed >=3 rows
        if s16 in shas_with_pdf and per_doc_pdf[s16] >= 3:
            continue
        br, bsrc = resolve_draft_branches(d, MD.DOC_SCOPE)
        session = d.get("session", "")
        course = (d.get("course") or "BTech").strip()
        for idx, s in enumerate(subs):
            codes = ";".join(s.get("codes") or [])
            semv = s.get("semester")
            semv = "/".join(str(x) for x in semv) if isinstance(semv, list) \
                else (str(semv) if semv is not None else "")
            ltp = s.get("ltp") or {}
            if not isinstance(ltp, dict):
                ltp = {}
            sids = []
            for c in re.split(r"[;,/]", codes):
                c = re.sub(r"[^A-Za-z0-9]", "", c)
                if c:
                    sid = code2sid.get(c.upper())
                    if sid:
                        sids.append(sid)
            rows.append({
                "source": "draft-fallback", "doc_file": stem + ".pdf",
                "doc_sha16": s16, "course": course, "session": session,
                "doc_branches": br, "semester": semv,
                "semester_int": sem_int(semv) if semv else "", "sn": str(idx + 1),
                "codes": codes,
                "subject_name_print": (s.get("name") or "").strip(),
                "L": ltp.get("l", ""), "T": ltp.get("t", ""), "P": ltp.get("p", ""),
                "credit": s.get("credit", "") if s.get("credit") is not None else "",
                "row_kind": "subject",
                "subject_id": ";".join(sorted(set(sids))),
                "nums_raw": "", "doc_rel": stem,
            })
            n_draft_rows += 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    cols = ["source", "doc_file", "doc_sha16", "doc_rel", "course", "session",
            "doc_branches", "semester", "semester_int", "sn", "codes",
            "subject_name_print", "L", "T", "P", "credit", "row_kind",
            "subject_id", "nums_raw"]
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    import shutil
    shutil.copy2(OUT, REPO_OUT)

    # ---- stats ----
    st = {"pdfs_total": len(pdfs), "pdfs_no_text_layer": no_text,
          "docs_with_parsed_scheme_rows": parsed_docs,
          "rows_pdf": n_pdf_rows, "rows_draft": n_draft_rows,
          "rows_total": len(rows),
          "by_course": dict(Counter(r["course"] for r in rows)),
          "by_source": dict(Counter(r["source"] for r in rows)),
          "by_kind": dict(Counter(r["row_kind"] for r in rows)),
          "rows_semester_int": sum(1 for r in rows if str(r["semester_int"]).strip() != ""),
          "rows_linked_subject_id": sum(1 for r in rows if r["subject_id"]),
          "docs_by_session": dict(Counter(r["session"] for r in rows if r["source"] == "pdf-scheme-page")),
          }
    json.dump(st, open(STATS, "w"), indent=1)
    print(json.dumps(st, indent=1))
    print("WROTE", OUT, len(rows), "rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
