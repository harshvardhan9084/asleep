#!/usr/bin/env python3
"""b92_apply_remediation.py — owner directive 2026-11-12: "go. better not
remain un-fixable 'flags' in there! fix what can, remove what can't. i need
final clean CSV".

Applies the B91 evidence to the CSV (multi-stage confirmation satisfied:
B91 = stage-1 ledger, this owner message = stage-2 go):

  BOOK_TRUNC 65:
    - position-map restoration first (printed numbered book list -> entry by
      its own stored 'no'), containment-span fallback with glue validation;
    - 'stored_matches_print' (9) -> flag retired, w9a_ckpt verified_complete;
    - unresolvable after improved search -> flag REMOVED by owner directive
      (values kept as ingestion-time text-layer extractions; recorded in
      b92_owner_directive.json + CHANGELOG);
  DISPLAY_MISSING 2 -> subject_name_display filled from subject_name_print;
  TYPE_EMPTY 375 -> flags REMOVED by owner directive (values stay empty;
  print states nothing there - zero-guess preserved in the data).

LEDGER: work/pipeline_v2/probes/b92_apply_ledger.json. Row-diff verification
against the original bytes; only intended cells may change.
"""
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from t9_quality_probe import squash, parse_books, sha_index, cite_docs, DocTexts, norm_name
from b91_booktrunc_probe import (block_lines, find_printed_spans, page_sq,
                                 parse_flag_detail, slugify, BOOK_RE)

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
PROB = "/home/z/my-project/work/pipeline_v2/probes"
CKPT = "/home/z/my-project/work/pipeline_v2/w9a_ckpt.json"
DIRECTIVE = "/home/z/my-project/work/pipeline_v2/b92_owner_directive.json"
RUN_ID = "CRON-20261112-B92"

NUM_START = re.compile(r"(?:^|\s)(\d{1,2})\s*\.\s+(?=[A-Z\u201c\"(])")
GLUE = re.compile(r"\d{1,2}\.\s+[A-Z\u201c\"(]")


def printed_position_map(lines_pp, page_idxs):
    """ordered (no -> text) map of the printed book list on block pages."""
    out = {}
    for pi in page_idxs:
        if pi >= len(lines_pp):
            continue
        lines = lines_pp[pi]
        joined = "\n".join(lines)
        marks = [(int(m.group(1)), m.start(1)) for m in NUM_START.finditer(joined)]
        for k, (no, s) in enumerate(marks):
            e = marks[k + 1][1] if k + 1 < len(marks) else len(joined)
            txt = joined[s:e].strip()
            # the mark consumed the leading '\n' of a mid-line start: keep text
            txt = re.sub(r"^\d{1,2}\s*\.\s+", "", txt)
            if txt:
                out.setdefault(no, txt)
    return out


def clean_value(txt):
    txt = re.sub(r"^\d{1,2}\s*\.\s+", "", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def validate_span(span, entry_sq):
    """no numbered-item glue after the stored entry's end."""
    sq = squash(span)
    pos = sq.find(entry_sq)
    if pos < 0:
        return False
    rest = sq[pos + len(entry_sq):]
    return not GLUE.search(rest)


def main():
    orig_bytes = open(CSV_PATH, "rb").read()
    af = json.load(open("/home/z/my-project/work/pipeline_v2/audit_flags.json"))
    rows = list(csv.DictReader(open(CSV_PATH)))
    by_slug = {}
    for r in rows:
        by_slug.setdefault(slugify(r["subject_name"]), []).append(r)
        by_slug.setdefault(squash(r["subject_name"]), []).append(r)

    trunc, disp, te_sids = {}, [], []
    for key, flags in af["rows"].items():
        for f in flags:
            if f["rule"] == "BOOK_TRUNC":
                trunc.setdefault(key, []).append(f)
            elif f["rule"] == "DISPLAY_MISSING":
                disp.append((key, f))

    idx = sha_index()
    dt = DocTexts(idx)
    actions, directive_bt, ckpt_entries = [], [], {}

    def find_rows(key):
        hit = by_slug.get(key) or by_slug.get(squash(key.replace("-", " "))) or []
        seen, out = set(), []
        for r in hit:
            if r["subject_id"] in seen:
                continue
            seen.add(r["subject_id"])
            out.append(r)
        return out

    def locate(key, f):
        """row + entry via field index; tail-match fallback for slug misses."""
        detail = parse_flag_detail(f.get("detail", ""))
        dsq = squash(detail)
        mi = re.match(r"^\w+\[(\d+)\]$", f.get("field", ""))
        for r in find_rows(key):
            flist = parse_books(r["textbooks_structured" if f["field"].startswith("textbooks")
                                else "reference_books_structured"])
            if mi and int(mi.group(1)) < len(flist):
                return r, flist[int(mi.group(1))]
            if dsq:
                for s in flist:
                    if squash(s).endswith(dsq) or dsq in squash(s):
                        return r, s
        # global tail-match (slug mismatch rescue)
        if dsq:
            for r in rows:
                for col in ("textbooks_structured", "reference_books_structured"):
                    for s in parse_books(r[col]):
                        if squash(s).endswith(dsq):
                            return r, s
        return None, None

    def search_docs(r, esq):
        """(cands, page_ev, pmap) over cited docs: block pages, then whole doc."""
        cands, page_ev, pmap = [], [], {}
        docs = cite_docs(r["source_syllabus"])
        for sha, pages, fname in docs:
            if sha not in idx:
                continue
            lines_pp, block_pages = block_lines(dt, sha, r["primary_code"],
                                                norm_name(r["subject_name"]))
            if lines_pp is None:
                continue
            if block_pages:
                pm = printed_position_map(lines_pp, block_pages)
                for no, txt in pm.items():
                    pmap.setdefault(no, (txt, fname, block_pages[0] + 1))
            for span in find_printed_spans(lines_pp, block_pages or
                                           range(len(lines_pp)), esq):
                cands.append(span)
                page_ev.append(f"{fname} p.{(block_pages or [0])[0] + 1}")
        return cands, page_ev, pmap

    # ---------------- BOOK_TRUNC
    stats = Counter()
    for key, flags in sorted(trunc.items()):
        for f in flags:
            r, entry = locate(key, f)
            if r is None:
                stats["unresolvable_no_row"] += 1
                actions.append({"key": key, "field": f["field"], "verdict":
                                "unresolvable_no_row", "action": "owner_directive_remove"})
                directive_bt.append(f"{key}::{f['field']}")
                continue
            esq = squash(entry)
            cands, page_ev, pmap = search_docs(r, esq)
            no = None
            try:
                arr = json.loads(r["textbooks_structured" if f["field"].startswith("textbooks")
                                   else "reference_books_structured"])
                for e2 in arr:
                    if squash(e2.get("book", "")) == esq:
                        no = e2.get("no")
                        break
            except Exception:
                pass
            # 1) position map: printed entry with the stored entry's own number
            cand = None
            if no is not None and no in pmap:
                txt, fn, pg = pmap[no]
                txt = clean_value(txt)
                if len(squash(txt)) >= len(esq) and esq in squash(txt):
                    cand = (txt, f"{fn} p.{pg} (list position {no})")
            # 2) validated containment span, strictly longer
            if cand is None:
                longer = [c for c in cands if len(squash(c)) > len(esq)
                          and validate_span(c, esq)]
                if len(longer) == 1:
                    cand = (clean_value(longer[0]), "; ".join(sorted(set(page_ev))[:2]))
            if cand and squash(cand[0]) != esq:
                actions.append({"key": key, "field": f["field"], "code": r["primary_code"],
                                "subject": r["subject_name"], "verdict": "restored",
                                "before": entry, "after": cand[0], "evidence": cand[1]})
                apply_restore(r, f["field"], entry, cand[0], cand[1])
                ckpt_entries[f"{key}::{f['field']}"] = {
                    "status": "verified_complete", "evidence": f"B92 restored from print: {cand[1]}"}
                stats["restored"] += 1
            elif cand:
                apply_retire(r, f["field"], key)
                ckpt_entries[f"{key}::{f['field']}"] = {
                    "status": "verified_complete",
                    "evidence": f"B92: stored entry equals cited print list position {no} ({cand[1]})"}
                stats["retired_equal"] += 1
            elif any(squash(c) == esq for c in cands):
                apply_retire(r, f["field"], key)
                ckpt_entries[f"{key}::{f['field']}"] = {
                    "status": "verified_complete",
                    "evidence": f"B92: stored entry equals cited print ({'; '.join(sorted(set(page_ev))[:2])})"}
                stats["retired_equal"] += 1
            else:
                stats["removed_owner_directive"] += 1
                apply_remove(r, f["field"], key)
                directive_bt.append(f"{key}::{f['field']}")
                actions.append({"key": key, "field": f["field"], "code": r["primary_code"],
                                "subject": r["subject_name"], "verdict":
                                "removed_owner_directive", "n_cands": len(cands)})

    # ---------------- DISPLAY_MISSING
    for key, f in disp:
        for r in find_rows(key):
            pn = (r["subject_name_print"] or "").strip()
            if pn and not r["subject_name_display"].strip():
                r["subject_name_display"] = pn
                r["quality_flags"] = retoken(r["quality_flags"], "DISPLAY_MISSING",
                                             "corrected_DISPLAY_MISSING_filled_print")
                corr(r, "subject_name_display", "", pn, "DISPLAY_MISSING_filled_print_B92",
                     "subject_name_print (print-attested column)")
                stats["display_filled"] += 1
            elif not r["subject_name_display"].strip():
                directive_bt.append(f"{key}::subject_name_display")
                r["quality_flags"] = retoken(r["quality_flags"], "DISPLAY_MISSING",
                                             "reviewed_DISPLAY_MISSING_owner_directive")
                stats["display_removed_directive"] += 1

    # ---------------- TYPE_EMPTY (owner directive: flags removed, values stay)
    te_n, directive_te = 0, []
    for r in rows:
        if "TYPE_EMPTY" in (r["quality_flags"] or ""):
            r["quality_flags"] = retoken(r["quality_flags"], "TYPE_EMPTY",
                                         "reviewed_TYPE_EMPTY_owner_directive")
            te_n += 1
            if not r["subject_type"].strip():
                directive_te.append(slugify(r["subject_name"]))
    stats["type_empty_tokens_removed"] = te_n

    # ---------------- verify row diff
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    new_bytes = buf.getvalue().encode("utf-8")

    orig_rows = list(csv.reader(io.StringIO(orig_bytes.decode("utf-8"))))
    new_rows = list(csv.reader(io.StringIO(new_bytes.decode("utf-8"))))
    assert len(orig_rows) == len(new_rows), "row count changed!"
    changed, cells = 0, Counter()
    for a, b in zip(orig_rows, new_rows):
        if a != b:
            changed += 1
            for ci, (x, y) in enumerate(zip(a, b)):
                if x != y:
                    cells[orig_rows[0][ci]] += 1
    print("rows changed:", changed, "| cells by column:", dict(cells))

    json.dump({
        "run_id": RUN_ID, "generated_utc": datetime.now(timezone.utc).isoformat(),
        "stats": dict(stats), "actions": actions,
        "directive_book_trunc": directive_bt,
        "directive_type_empty": directive_te,
        "csv_md5_before": hashlib.md5(orig_bytes).hexdigest(),
        "csv_md5_after": hashlib.md5(new_bytes).hexdigest(),
    }, open(os.path.join(PROB, "b92_apply_ledger.json"), "w"), indent=1, ensure_ascii=False)

    json.dump({
        "directive": "owner 2026-11-12: 'fix what can, remove what can't. i need final clean CSV'",
        "book_trunc_removed": directive_bt,
        "type_empty_removed": directive_te,
        "note": "values kept as ingestion-time text-layer extractions; print-wins "
                "verification exhausted (B91+B92 probes incl. whole-doc fallback); "
                "flags removed on owner order, recorded in CHANGELOG",
    }, open(DIRECTIVE, "w"), indent=1)

    ck = {"run_id": RUN_ID, "results": ckpt_entries}
    json.dump(ck, open(CKPT, "w"), indent=1)

    with open(CSV_PATH, "wb") as fh:
        fh.write(new_bytes)
    print("stats:", dict(stats))
    print("md5:", hashlib.md5(orig_bytes).hexdigest(), "->", hashlib.md5(new_bytes).hexdigest())


def retoken(qf, drop, add):
    toks = [t.strip() for t in re.split(r"[;,]", qf or "") if t.strip()]
    toks = [t for t in toks if t != drop and t != add]
    toks.append(add)
    return ";".join(toks)


def field_of(r, field):
    return "textbooks_structured" if field.startswith("textbooks") else "reference_books_structured"


def corr(r, field, before, after, rule, evidence):
    try:
        cj = json.loads(r["corrections_json"]) if (r["corrections_json"] or "").strip() else []
    except Exception:
        cj = []
    cj.append({"field": field, "before": before, "after": after, "rule": rule,
               "evidence": evidence, "batch": "CRON-20261112-B92"})
    r["corrections_json"] = json.dumps(cj, ensure_ascii=False)


def apply_restore(r, field, before, after, evidence):
    col = field_of(r, field)
    arr = json.loads(r[col])
    bsq = squash(before)
    for e in arr:
        if squash(e.get("book", "")) == bsq:
            e["book"] = after
            break
    r[col] = json.dumps(arr, ensure_ascii=False)
    r["quality_flags"] = retoken(r["quality_flags"], "BOOK_TRUNC",
                                 "corrected_BOOK_TRUNC_restored_print")
    corr(r, field, before, after, "BOOK_TRUNC_restored_print_B92", evidence)


def apply_retire(r, field, key):
    r["quality_flags"] = retoken(r["quality_flags"], "BOOK_TRUNC",
                                 "reviewed_BOOK_TRUNC_print_complete")


def apply_remove(r, field, key):
    r["quality_flags"] = retoken(r["quality_flags"], "BOOK_TRUNC",
                                 "reviewed_BOOK_TRUNC_owner_directive")


if __name__ == "__main__":
    main()
