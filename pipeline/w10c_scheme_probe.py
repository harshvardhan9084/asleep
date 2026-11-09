#!/usr/bin/env python3
"""w10c_scheme_probe.py — W10c (2026-11-10, B74): TYPE_EMPTY corpus round.

W10b (B71) filled 136 TYPE_EMPTY rows from name-print evidence and deferred
the rest to "corpus page reads of the cited scheme PDFs". This wave does
exactly that, zero-guess (RULES §4/§6b):

  probe — for every TYPE_EMPTY row: locate the printed scheme row for the
      primary_code in the cited docs first (source_syllabus/source_history
      shas), then the global corpus squash-index (W9a machinery). For each
      hit page the GOVERNING section header is tracked: the nearest
      standalone category header above the code line on the same page, else
      the nearest header anywhere earlier in the same doc (AKTU scheme
      tables are contiguous sections). Header grammar is TIGHT (standalone
      category prints only; acronym forms like OEC/DE-I never match;
      title-text words like '... and Practice' cannot match).
      verdicts: print_category (same-page governing header) /
      cross_page_section (doc-continuity governing header) / ambiguous /
      no_code_print_found / raster_only / sha_unresolved.

  apply — verdicts mapping EXACTLY into committed vocab (W10b L4 + W8c/W9c
      committed classes) get subject_type + norm mirror + corrections_json
      {before,after,rule,evidence page cite} + verification_status=corrected
      + change_note + durable notes marker "W10c probe:". All other rows get
      the durable probe note only. Zero primary-field writes; notes/corrections
      are the only changes. Gates G1/G2/G3/G6 by the caller. T2T 0.
"""
import json
import os
import pickle
import re
import sys

import fitz

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

BASE = WC.BASE
CORPUS = json.load(open(f"{BASE}/corpus_map.json"))
PAGE_INDEX = f"{BASE}/w9a_page_index.pkl"
MARK = "W10c probe:"

HEADERS = [
    (re.compile(r"^\W*(open\s+electives?)(\W*(courses?|pool)\W*)?$", re.I), "open-elective"),
    (re.compile(r"^\W*(departmental\s+electives?|department\s+electives?|deptt\.?\s+electives?)(\W*(?:courses?|[ivx]+|\d+)?\W*)?$", re.I), "departmental-elective"),
    (re.compile(r"^\W*(professional\s+cores?|cores?\s+courses?)\W*$", re.I), "core"),
    (re.compile(r"^\W*(value\s+added\s+courses?|mandatory\s+courses?)\W*$", re.I), "value-added-mandatory"),
    (re.compile(r"^\W*(electives?)(\W*[ivx]+)?\W*$", re.I), "elective"),
    (re.compile(r"^\W*(practical\s+courses?|lab\s+courses?|laboratory\s+courses?)\W*$", re.I), "practical"),
]
HONOR_RE = re.compile(r"^\W*(honou?rs?|minor(?:\s+degrees?)?|mooc[s]?|audit)\W*$", re.I)


def code_variants(pc):
    out = {pc}
    m = re.match(r"^([A-Z]{2,4})(\d{3}[A-Z]?)$", pc)
    if m:
        out.add(f"{m.group(1)}-{m.group(2)}")
        out.add(f"{m.group(1)} {m.group(2)}")
    return out


def governing_header(text, pos):
    """nearest standalone category header at/before pos on this page"""
    up = text[:pos]
    best = None
    for ln in up.splitlines():
        for hre, cat in HEADERS:
            if hre.match(ln.strip()) and not HONOR_RE.match(ln.strip()):
                best = cat
    return best


def doc_header_track(path):
    """(page_no, category) list of last headers per page, for doc-continuity"""
    out = []
    try:
        d = fitz.open(path)
    except Exception:
        return out
    for i in range(d.page_count):
        t = d[i].get_text() or ""
        last = None
        for ln in t.splitlines():
            for hre, cat in HEADERS:
                if hre.match(ln.strip()) and not HONOR_RE.match(ln.strip()):
                    last = cat
        if last:
            out.append((i + 1, last))
    d.close()
    return out


def shas_for(r):
    out, seen = [], set()
    for col in ("source_syllabus", "source_history"):
        for m in re.finditer(r"#([0-9a-f]{12,16})", r.get(col, "") or ""):
            sha = m.group(1)
            if sha not in seen:
                seen.add(sha)
                out.append(sha)
    return out[:6]


def main():
    rows = WC.load_rows()
    by_id = {r["subject_id"]: r for r in rows}
    fl = json.load(open(f"{BASE}/audit_flags.json"))["rows"]
    targets = [sid for sid, f in fl.items()
               if any(x["rule"] == "TYPE_EMPTY" for x in f)]
    print(f"W10C|targets={len(targets)}")

    idx = {}
    if os.path.exists(PAGE_INDEX):
        idx = pickle.load(open(PAGE_INDEX, "rb"))

    # cached doc header tracks
    _tracks = {}
    _texts = {}

    def page_text(path, pno):
        key = (path, pno)
        if key not in _texts:
            try:
                d = fitz.open(path)
                _texts[key] = d[pno - 1].get_text() or ""
                d.close()
            except Exception:
                _texts[key] = ""
        return _texts[key]

    results = {}
    n_probe = 0
    for sid in targets:
        r = by_id[sid]
        pc = (r.get("primary_code") or "").strip().upper()
        if not pc:
            results[f"{sid}"] = {"status": "no_code_print_found",
                                 "evidence": "", "why": "no primary_code"}
            continue
        variants = code_variants(pc)
        pat = re.compile(r"\b(" + "|".join(re.escape(v) for v in variants) + r")\b", re.I)
        hit = None
        # cited docs first
        for sha in shas_for(r):
            path = CORPUS.get(sha) or (CORPUS.get([k for k in CORPUS if k.startswith(sha)][0])
                                       if [k for k in CORPUS if k.startswith(sha)] else None)
            if not path or not os.path.exists(path):
                results[f"{sid}"] = {"status": "sha_unresolved", "evidence": sha}
                hit = "stop"
                continue
            if hit == "stop":
                continue
            try:
                d = fitz.open(path)
            except Exception:
                continue
            found = None
            for i in range(d.page_count):
                t = d[i].get_text() or ""
                m = pat.search(t)
                if m:
                    cat = governing_header(t, m.start())
                    found = (i + 1, cat, t, m.start())
                    break
            d.close()
            if found:
                ev = f"{os.path.basename(path)}#{sha} p.{found[0]}"
                if found[1]:
                    results[f"{sid}"] = {"status": "print_category",
                                         "category": found[1],
                                         "evidence": ev}
                else:
                    tr = _tracks.setdefault(path, doc_header_track(path))
                    prev = [c for (p, c) in tr if p < found[0]]
                    if prev:
                        results[f"{sid}"] = {"status": "cross_page_section",
                                             "category": prev[-1],
                                             "evidence": ev + f" (section continues from p.{[p for (p, c) in tr if p < found[0]][-1]})"}
                    else:
                        results[f"{sid}"] = {"status": "no_header_above",
                                             "evidence": ev}
                n_probe += 1
                hit = "done"
        if hit == "done" or hit == "stop":
            continue
        # global index fallback (text-layer pages keyed by squash)
        if idx:
            sqs = [re.sub(r"[^a-z0-9]", "", v.lower()) for v in variants]
            hits = []
            for key, sq in idx.get("idx", {}).items():
                if any(s in sq for s in sqs):
                    hits.append(key)
                    if len(hits) >= 12:
                        break
            for key in hits[:12]:
                sha, _, pno = key.partition(":p")
                path = idx["paths"].get(sha)
                if not path:
                    continue
                t = page_text(path, int(pno))
                m = pat.search(t)
                if not m:
                    continue
                cat = governing_header(t, m.start())
                if cat:
                    results[f"{sid}"] = {"status": "print_category",
                                         "category": cat,
                                         "evidence": f"{os.path.basename(path)}#{sha} p.{pno}"}
                    n_probe += 1
                    hit = "done"
                    break
        if hit == "done":
            continue
        if f"{sid}" not in results:
            results[f"{sid}"] = {"status": "no_code_print_found",
                                 "evidence": "", "pages_probed": "text-layer"}

    from collections import Counter
    dist = Counter(v["status"] for v in results.values())
    print(f"W10C_PROBE|{len(results)}|{dict(dist)}")
    json.dump({"results": results}, open(f"{BASE}/w10c_ckpt.json", "w"), indent=1)
    cats = Counter(v.get("category") for v in results.values() if v.get("category"))
    print(f"W10C_CATS|{dict(cats)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
