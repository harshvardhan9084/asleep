#!/usr/bin/env python3
"""b91_booktrunc_probe.py — remediation consolidation B91 (owner direction
2026-11-12: "i wanted the clean and faithful 'syllabus rich' CSV at first
place" -> convert completed T1-T13 cascade results into the concrete path to
the clean CSV).

Stage-1 dry-run, LEDGER-ONLY (no CSV write, no quality_flags change —
standing mechanics: multi-stage confirmation first).

Scope = the audit-of-record active set that is FIXABLE from print:
  BOOK_TRUNC 65 (stored book entry shorter / cut vs print)  -> restoration
      candidates located in the row's own cited docs' printed book block;
  DISPLAY_MISSING 2 (subject_name_display empty) -> display candidate from
      subject_name_print (print-attested field already in the CSV).

Not in scope (stays flagged, honest): TYPE_EMPTY 375 (field not stated by
print; filling = invention, forbidden per standing zero-guess rule), T12
citation shas (PDFs not in corpus), page-image queue (T6/T7/T9/T10 review
items) — tracked in the B91 plan workbook instead.

Verdicts per BOOK_TRUNC flag:
  restorable_from_print        exactly one distinct printed line span
                               strictly longer than the stored entry squash
  ambiguous_multi_candidate    several distinct printed spans match
  stored_matches_print         stored squash found, no strictly-longer
                               extension (flag appears stale -> review)
  not_in_text_layer            stored squash absent from all cited block pages
  doc_unresolvable / no_citation

Never invents a value: every candidate carries stored + printed raw evidence.
"""
import csv
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from t9_quality_probe import (norm_name, squash, parse_books, sha_index,
                              cite_docs, name_near, DocTexts)

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
PROBE_DIR = "/home/z/my-project/work/pipeline_v2/probes"
REPO = "/home/z/my-project/work/repo_asleep/syllabus_catalog/owner_requests"
RUN_ID = "CRON-20261112-B91"
BOOK_RE = re.compile(r"^\s*(\d{1,2})\s*[\.\)\-]\s+")


def slugify(s):
    return re.sub(r"\s+", "-", re.sub(r"[^a-z0-9 ]", "", (s or "").lower())).strip()


def parse_flag_detail(detail):
    """'possibly truncated entry: '<text>'' -> <text>."""
    m = re.search(r"entry:\s*'(.*)'\s*$", detail or "", re.S)
    return m.group(1) if m else (detail or "")


def block_lines(dt, sha, code, subj_norm):
    """raw lines of the row's own course-block pages in one doc."""
    pages = dt.course_block_pages(sha, code, subj_norm)
    if not pages or dt.pages(sha) is None:
        return None, pages or []
    lines_pp = dt.raw[sha]
    return lines_pp, pages


_sq_cache = {}


def page_sq(lines_pp, pi):
    if (id(lines_pp), pi) not in _sq_cache:
        sq_chars, line_of = [], []
        for li, l in enumerate(lines_pp[pi]):
            s = squash(l)
            sq_chars.extend(s)
            line_of.extend([li] * len(s))
        _sq_cache[(id(lines_pp), pi)] = ("".join(sq_chars), line_of)
    return _sq_cache[(id(lines_pp), pi)]


def find_printed_spans(lines_pp, page_idxs, entry_sq):
    """locate entry_sq inside squashed page text; return distinct full printed
    spans (entry + continuation lines until the next numbered item, max +3)."""
    spans = []
    for pi in page_idxs:
        if pi >= len(lines_pp):
            continue
        lines = lines_pp[pi]
        sq, line_of = page_sq(lines_pp, pi)
        start = 0
        while True:
            a = sq.find(entry_sq, start)
            if a < 0:
                break
            b = a + len(entry_sq)
            li_a, li_b = line_of[a], line_of[min(b, len(line_of) - 1)]
            end_li = li_b
            added = 0
            # extend BACKWARD: the author head of a head-cut entry may live on
            # the line above (only if that line is not itself a numbered item)
            back = 0
            k = li_a
            while k > 0 and back < 2 and not BOOK_RE.match(lines[k - 1]) \
                    and not re.match(r"^\s*\d+\s*$", lines[k - 1]):
                k -= 1
                back += 1
            li_a = k
            for j in range(li_b + 1, min(li_b + 4, len(lines))):
                if BOOK_RE.match(lines[j]) or re.match(r"^\s*\d+\s*$", lines[j]):
                    break
                if squash(lines[j]):
                    end_li = j
                    added += 1
                    if added >= 3:
                        break
            span = " ".join(lines[li_a:end_li + 1]).strip()
            # strip the entry's own leading numbering ("1. ", "12) ")
            span = re.sub(r"^\s*\d{1,2}\s*[\.\)\-]\s*", "", span)
            # cut a merged-in NEXT entry: first "\d{1,2}.\s+<Letter/quote>"
            # boundary whose left part still contains the stored entry squash
            for m in re.finditer(r"\s+\d{1,2}\.\s+(?=[A-Z\u201c\"(])", span):
                if entry_sq in squash(span[:m.start()]):
                    span = span[:m.start()].strip()
                    break
            spans.append(span)
            start = b
    uniq = {}
    for s in spans:
        uniq.setdefault(squash(s), s)
    return list(uniq.values())


def main():
    os.makedirs(PROBE_DIR, exist_ok=True)
    af = json.load(open("/home/z/my-project/work/pipeline_v2/audit_flags.json"))
    trunc, disp = {}, {}
    for key, flags in af["rows"].items():
        for f in flags:
            if f.get("rule") == "BOOK_TRUNC":
                trunc.setdefault(key, []).append(f)
            elif f.get("rule") == "DISPLAY_MISSING":
                disp.setdefault(key, []).append(f)
    print(f"active flags: BOOK_TRUNC rows={len(trunc)} flags="
          f"{sum(len(v) for v in trunc.values())} DISPLAY_MISSING rows={len(disp)}")

    with open(CSV_PATH) as f:
        csv_rows = list(csv.DictReader(f))
    by_slug = {}
    for r in csv_rows:
        k1 = slugify(r["subject_name"])
        k2 = squash(r["subject_name"])
        by_slug.setdefault(k1, []).append(r)
        if k2 != k1:
            by_slug.setdefault(k2, []).append(r)

    idx = sha_index()
    dt = DocTexts(idx)
    ledger_rows, verdicts = [], Counter()
    unmatched = []

    # ---- BOOK_TRUNC restoration dry-run
    processed = set()
    for key, flags in sorted(trunc.items()):
        rows_hit = by_slug.get(key) or by_slug.get(squash(key.replace("-", " "))) or []
        seen = set()
        dedup = []
        for r in rows_hit:
            k = r["subject_id"]
            if k in seen:
                continue
            seen.add(k)
            dedup.append(r)
        rows_hit = dedup
        if not rows_hit:
            unmatched.append({"audit_key": key, "n_flags": len(flags)})
        for f in flags:
            entry = parse_flag_detail(f.get("detail", ""))
            field = f.get("field", "")
            tb = field.startswith("textbooks")
            # the audit's detail is a display TAIL (t[-80:]); the field index
            # gives the exact stored entry — no fuzzy attribution needed
            mi = re.match(r"^\w+\[(\d+)\]$", field)
            placed = False
            for r in rows_hit:
                flist = parse_books(r["textbooks_structured"] if tb
                                    else r["reference_books_structured"])
                if mi and int(mi.group(1)) < len(flist):
                    match = flist[int(mi.group(1))]
                else:
                    match = next((s for s in flist if squash(s) == squash(entry)), None)
                if match is None:
                    continue
                placed = True
                fk = (r["subject_id"], field, squash(match))
                if fk in processed:
                    continue
                processed.add(fk)
                esq = squash(match)
                docs = cite_docs(r["source_syllabus"])
                cands, resolvable, page_ev, n_block = [], 0, [], 0
                for sha, pages, fname in docs:
                    if sha not in idx:
                        continue
                    resolvable += 1
                    lines_pp, block_pages = block_lines(dt, sha, r["primary_code"],
                                                        norm_name(r["subject_name"]))
                    if lines_pp is None:
                        continue
                    scope = block_pages
                    if block_pages:
                        n_block += 1
                    else:
                        scope = list(range(len(lines_pp)))  # whole-doc fallback
                    spans = find_printed_spans(lines_pp, scope, esq)
                    for s in spans:
                        cands.append(s)
                        p0 = (block_pages or [0])
                        page_ev.append(f"{fname} p.{p0[0] + 1}")
                longer = [c for c in cands if len(squash(c)) > len(esq)]
                equal = [c for c in cands if len(squash(c)) == len(esq)]
                if not resolvable:
                    v = "no_citation" if not docs else "doc_unresolvable"
                elif len(longer) == 1:
                    v = "restorable_from_print"
                elif len(longer) > 1:
                    v = "ambiguous_multi_candidate"
                elif equal:
                    v = "stored_matches_print"
                elif cands:
                    v = "stored_longer_than_print_review"
                elif n_block == 0:
                    v = "block_pages_not_found"
                else:
                    v = "not_in_text_layer"
                verdicts[v] += 1
                ledger_rows.append({
                    "subject_name": r["subject_name"], "primary_code": r["primary_code"],
                    "course": r["course_name"], "session": r["effective_session_latest"],
                    "field": field, "stored_entry": match, "verdict": v,
                    "printed_full": longer[0] if len(longer) == 1 else
                                    (equal[0] if len(equal) == 1 and v == "stored_matches_print"
                                     else "; || ".join((longer or equal)[:3])),
                    "n_candidates": len(cands), "n_block_pages": n_block,
                    "evidence": "; ".join(sorted(set(page_ev))[:3]),
                })
            if not placed:
                verdicts["entry_not_found_in_row"] += 1
                ledger_rows.append({
                    "subject_name": key, "primary_code": "", "course": "", "session": "",
                    "field": field, "stored_entry": entry,
                    "verdict": "entry_not_found_in_row", "printed_full": "",
                    "n_candidates": 0, "n_block_pages": 0, "evidence": "",
                })

    # ---- DISPLAY_MISSING dry-run (display candidate = subject_name_print)
    disp_rows = []
    for key, flags in sorted(disp.items()):
        for r in by_slug.get(key, []):
            for f in flags:
                cand = (r["subject_name_print"] or "").strip()
                disp_rows.append({
                    "subject_name": r["subject_name"], "primary_code": r["primary_code"],
                    "verdict": "restorable_from_print_col" if cand else "print_name_empty",
                    "proposed_display": cand,
                })

    out = {
        "run_id": RUN_ID, "generated_utc": datetime.now(timezone.utc).isoformat(),
        "csv_md5": __import__("hashlib").md5(open(CSV_PATH, "rb").read()).hexdigest(),
        "policy": "LEDGER-ONLY stage-1 dry-run; no CSV write; print-wins per RULES 6b",
        "book_trunc": {"rows": len(trunc), "flags_total": sum(len(v) for v in trunc.values()),
                       "flags_processed": len(processed), "verdicts": dict(verdicts),
                       "unmatched_audit_keys": unmatched, "items": ledger_rows},
        "display_missing": {"rows": len(disp), "items": disp_rows},
    }
    lp = os.path.join(PROBE_DIR, "b91_booktrunc_probe_ledger.json")
    json.dump(out, open(lp, "w"), indent=1, ensure_ascii=False)
    rp = os.path.join(REPO, "b91_booktrunc_probe_ledger.json")
    json.dump(out, open(rp, "w"), indent=1, ensure_ascii=False)
    print("verdicts:", dict(verdicts), "| flags processed:", len(processed))
    print("unmatched audit keys:", [(u["audit_key"], u["n_flags"]) for u in unmatched])
    print("DISPLAY_MISSING:", [(d["primary_code"], d["verdict"]) for d in disp_rows])
    print("ledger:", lp)


if __name__ == "__main__":
    main()
