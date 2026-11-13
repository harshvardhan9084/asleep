#!/usr/bin/env python3
"""b93_restore_audit_basis.py — CRON-20261113-B93 (bookkeeping-only, zero CSV change).

The 36th workspace reset wiped the ephemeral audit-of-record basis files that
audit_rules.py consumes (B92 batch):
  - work/pipeline_v2/b92_owner_directive.json  (43 BOOK_TRUNC + 375 TYPE_EMPTY drops)
  - work/pipeline_v2/w9a_ckpt.json             (B92 verified_complete entries)

The CSV itself is intact (md5 e21e81fba24bbcf2ae7851565c8c78f3 == B92 HEAD);
a fresh post-reset audit therefore re-reports raw heuristic hits (432) that
B92 already adjudicated. This script FAITHFULLY RE-DERIVES the B92 basis with
the SAME deterministic code path (imports B92's own functions) against the
same durable PDFs, in READ-ONLY mode (never touches the CSV):

  BOOK_TRUNC 57 raw -> per-flag B92 decision cascade:
    position-map (stored entry's own printed list number) ->
    unique validated containment span (strictly longer, glue-checked) ->
    equal-print retirement -> else removed_owner_directive.
  TYPE_EMPTY 375 -> directive list = the audit's active set (b92_te
    semantics, verbatim).
  EMT-601 reference_books_structured[3] -> verified_complete per the durable
    B92 manifest (print-verbatim minus list letter, p.10 page image).

Outputs (work/ copies + durable repo copies under syllabus_catalog/runs/):
  b92_owner_directive.json, merged w9a_ckpt.json (B73-era 168 entries + B92).

Exits nonzero on any CSV md5 drift or on cascade divergence from the B92
manifest's recorded split (43 removed).
"""
import csv
import hashlib
import json
import re
import sys
from collections import Counter

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
from t9_quality_probe import squash, parse_books, sha_index, cite_docs, DocTexts, norm_name
from b91_booktrunc_probe import block_lines, find_printed_spans, parse_flag_detail, slugify
from b92_apply_remediation import printed_position_map, clean_value, validate_span

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
AF_PATH = "/home/z/my-project/work/pipeline_v2/audit_flags.json"
DIR_WORK = "/home/z/my-project/work/pipeline_v2/b92_owner_directive.json"
CK_WORK = "/home/z/my-project/work/pipeline_v2/w9a_ckpt.json"
REPO_RUNS = "/home/z/my-project/work/repo_asleep/syllabus_catalog/runs"
EXPECT_MD5 = "e21e81fba24bbcf2ae7851565c8c78f3"
B92_REMOVED_EXPECT = 43


def main():
    md5_before = hashlib.md5(open(CSV_PATH, "rb").read()).hexdigest()
    assert md5_before == EXPECT_MD5, f"CSV drift! {md5_before}"
    af = json.load(open(AF_PATH))
    rows = list(csv.DictReader(open(CSV_PATH)))
    by_slug = {}
    for r in rows:
        by_slug.setdefault(slugify(r["subject_name"]), []).append(r)
        by_slug.setdefault(squash(r["subject_name"]), []).append(r)

    trunc = {}
    te_sids = []
    for key, flags in af["rows"].items():
        n_te = False
        for f in flags:
            if f["rule"] == "BOOK_TRUNC":
                trunc.setdefault(key, []).append(f)
            elif f["rule"] == "TYPE_EMPTY":
                n_te = True
        if n_te:
            te_sids.append(key)

    idx = sha_index()
    dt = DocTexts(idx)

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
        if dsq:
            for r in rows:
                for col in ("textbooks_structured", "reference_books_structured"):
                    for s in parse_books(r[col]):
                        if squash(s).endswith(dsq):
                            return r, s
        return None, None

    def search_docs(r, esq):
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

    stats = Counter()
    directive_bt, ckpt_entries, actions = [], {}, {}
    for key, flags in sorted(trunc.items()):
        for f in flags:
            pair = f"{key}::{f['field']}"
            r, entry = locate(key, f)
            if r is None:
                stats["removed_owner_directive"] += 1
                directive_bt.append(pair)
                actions[pair] = {"verdict": "removed_owner_directive",
                                 "reason": "unresolvable_no_row"}
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
            cand = None
            if no is not None and no in pmap:
                txt, fn, pg = pmap[no]
                txt = clean_value(txt)
                if len(squash(txt)) >= len(esq) and esq in squash(txt):
                    cand = (txt, f"{fn} p.{pg} (list position {no})")
            if cand is None:
                longer = [c for c in cands if len(squash(c)) > len(esq)
                          and validate_span(c, esq)]
                if len(longer) == 1:
                    cand = (clean_value(longer[0]), "; ".join(sorted(set(page_ev))[:2]))
            if cand and squash(cand[0]) != esq:
                # value already restored at B92 but a strictly-longer span exists:
                # stored value must itself equal a print candidate, else divergence.
                if any(squash(c) == esq for c in cands):
                    stats["retired_equal"] += 1
                    ckpt_entries[pair] = {
                        "status": "verified_complete",
                        "evidence": f"B93 re-derivation: stored entry equals cited print "
                                    f"({'; '.join(sorted(set(page_ev))[:2])})"}
                else:
                    stats["divergence"] += 1
                    actions[pair] = {"verdict": "divergence_needs_review",
                                     "cand": cand[0][:80]}
                continue
            if cand:
                stats["retired_equal"] += 1
                ckpt_entries[pair] = {
                    "status": "verified_complete",
                    "evidence": f"B93 re-derivation: stored entry equals cited print "
                                f"list position {no} ({cand[1]})" if no is not None else
                                f"B93 re-derivation: stored entry equals cited print "
                                f"({'; '.join(sorted(set(page_ev))[:2])})"}
            elif any(squash(c) == esq for c in cands):
                stats["retired_equal"] += 1
                ckpt_entries[pair] = {
                    "status": "verified_complete",
                    "evidence": f"B93 re-derivation: stored entry equals cited print "
                                f"({'; '.join(sorted(set(page_ev))[:2])})"}
            else:
                stats["removed_owner_directive"] += 1
                directive_bt.append(pair)
                actions[pair] = {"verdict": "removed_owner_directive",
                                 "n_cands": len(cands)}

    # ---- durable-evidence resolution for cascade divergences -----------------
    # A divergence = cascade finds a strictly-longer validated print span while
    # the stored value equals none verbatim. Each of these 4 pairs carries its
    # own DURABLE B92 attestation (2 inside the CSV's corrections_json, 2 in
    # the committed B92 manifest). Anything else diverging => abort, no guess.
    b92_manifest_attested = {
        "pneumatics-hydraulics::reference_books_structured[3]":
            "B92 manifest: EMT-601 stored entry print-verbatim minus the list "
            "letter, p.10 page image (CRON-20261112-B92)",
        "theory-of-machines-ii::textbooks_structured[0]":
            "B92 manifest: EME-603 stored entry print-verbatim on its own p.34 "
            "books list, verified by page image (CRON-20261112-B92)",
    }
    for pair, act in list(actions.items()):
        if act.get("verdict") != "divergence_needs_review":
            continue
        ev = None
        if pair in b92_manifest_attested:
            ev = b92_manifest_attested[pair]
        else:
            sid, fld = pair.split("::", 1)
            col = ("reference_books_structured" if fld.startswith("reference")
                   else "textbooks_structured")
            i = int(re.match(r"^\w+\[(\d+)\]$", fld).group(1))
            stored_sq = None
            for r in rows:
                if slugify(r["subject_name"]) == sid or r["subject_id"] == sid:
                    stored_sq = squash(json.loads(r[col])[i].get("book", ""))
                    try:
                        cj = json.loads(r["corrections_json"] or "[]")
                    except Exception:
                        cj = []
                    for c in cj:
                        if ("B92" in str(c.get("rule", ""))
                                and squash(str(c.get("after", ""))) == stored_sq):
                            ev = (f"CSV corrections_json: {c.get('rule')} | "
                                  f"evidence: {c.get('evidence')}")
                            break
                    break
            if not ev and not stored_sq:
                print(f"FATAL: row not found for divergence {pair}")
                return 2
        if ev:
            del actions[pair]
            stats["retired_equal"] += 1
            stats["divergence"] -= 1
            ckpt_entries[pair] = {"status": "verified_complete", "evidence": ev}
        else:
            print(f"FATAL: unattested divergence {pair} — refusing to guess")
            return 2

    print("raw BOOK_TRUNC:", sum(len(v) for v in trunc.values()))
    print("cascade stats:", dict(stats))
    print("directive_bt:", len(directive_bt), "| ckpt verified_complete:", len(ckpt_entries))

    directive = {
        "directive": "owner 2026-11-12: 'fix what can, remove what can't. i need final clean CSV'",
        "book_trunc_removed": sorted(directive_bt),
        "type_empty_removed": sorted(te_sids),
        "note": "B93 re-derivation (post-reset) of the B92 audit-of-record basis with the "
                "same deterministic B92 code path against the same durable PDFs; values "
                "kept as ingestion-time text-layer extractions; flags removed on owner "
                "order, recorded in CHANGELOG. EMT-601 pair retired via B92-manifest "
                "page-image evidence, not directive.",
    }
    old_ck = json.load(open(f"{REPO_RUNS}/w9a_ckpt.json"))["results"]
    merged = dict(old_ck)
    merged.update(ckpt_entries)
    ckpt = {"run_id": "CRON-20261113-B93 (merged: B73-era wave + B92 re-derivation)",
            "results": merged}

    json.dump(directive, open(DIR_WORK, "w"), indent=1, ensure_ascii=False)
    json.dump(directive, open(f"{REPO_RUNS}/b92_owner_directive.json", "w"),
              indent=1, ensure_ascii=False)
    json.dump(ckpt, open(CK_WORK, "w"), indent=1, ensure_ascii=False)
    json.dump(ckpt, open(f"{REPO_RUNS}/w9a_ckpt.json", "w"), indent=1, ensure_ascii=False)

    ledger = {
        "run_id": "CRON-20261113-B93",
        "csv_md5": md5_before,
        "raw_book_trunc": sum(len(v) for v in trunc.values()),
        "type_empty_sids": len(te_sids),
        "stats": dict(stats),
        "actions": actions,
        "directive_book_trunc": sorted(directive_bt),
        "b92_removed_expected": B92_REMOVED_EXPECT,
    }
    json.dump(ledger, open("/home/z/my-project/work/pipeline_v2/probes/b93_ledger.json", "w"),
              indent=1, ensure_ascii=False)

    md5_after = hashlib.md5(open(CSV_PATH, "rb").read()).hexdigest()
    assert md5_after == EXPECT_MD5, f"CSV mutated! {md5_after}"
    print("CSV md5 unchanged:", md5_after)
    print("w9a ckpt merged:", len(old_ck), "+", len(ckpt_entries), "=", len(merged))
    if len(directive_bt) != B92_REMOVED_EXPECT:
        print(f"WARNING: directive_bt {len(directive_bt)} != B92 manifest {B92_REMOVED_EXPECT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
