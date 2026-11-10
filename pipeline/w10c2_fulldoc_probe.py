#!/usr/bin/env python3
"""w10c2_fulldoc_probe.py — W10c2 (2026-11-10, B76): TYPE_EMPTY full-document
re-probe (the B75-manifest "global-index fallback", cited-docs-only edition).

B74 stopped at the FIRST page hit per cited doc and its global squash-index
fallback never ran. This wave re-probes every non-written TYPE_EMPTY row by
scanning ALL pages of ALL cited docs (source_syllabus/source_history shas
only — a doc that legitimately speaks for the row; zero cross-doc writes):

  verdicts (same tight grammar as B74, no new patterns):
    print_category      — >=1 hit page has a same-page standalone governing
                          section header; ALL headered pages agree; category
                          in WRITEABLE vocab  ->  write subject_type
    conflicting_headers — headered pages disagree (or category outside
                          WRITEABLE)               ->  honest note, no write
    cross_page_section  — no same-page header anywhere, but a header earlier
                          in the doc continues to the hit page (B74 class,
                          demonstrated unsafe — never written)
    no_header_above     — code prints (pages listed) but no governing header
    no_code_print_found — code prints nowhere in any cited doc
    sha_unresolved      — cited sha not in corpus_map

apply mirrors w10c_apply.py exactly: subject_type + subject_type_norm +
corrections_json {before,after,rule,evidence} + verification_status=corrected
+ corrected_W10C_CATEGORY tag + change_note + durable "W10c2 probe:" note.
Gates G1/G2/G3/G6 then commit via wave_commit. T2T 0.
"""
import json
import os
import re
import sys
from collections import Counter

import fitz

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

BASE = WC.BASE
MARK = "W10c2 probe:"
PREV_MARK = "W10c probe:"
WRITEABLE = ("open-elective", "departmental-elective", "elective")

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


# wrap-continuation vocabulary: a line ending with one of these words followed
# by a candidate header line is a WRAPPED NAME CELL, not a section header
# (B76 discovery: "Science Based / Open Elective" and "Open / Elective/" name
# fragments masqueraded as headers in textile-era docs)
WRAP_WORDS = {"science", "based", "open", "deptt", "departmental", "department",
              "elective", "electives", "professional", "value", "added",
              "mandatory", "practical", "core", "cores", "lab", "labs"}
MAX_GAP = 8  # header must sit within 8 printed lines of the code hit


def governing_header_tight(text, pos):
    """same-page governing header with B76 tightening:
    (1) gap <= 8 lines between header line and code line;
    (2) wrap-continuation rejection (prev line ends with a WRAP_WORD);
    returns (cat, why_rejected) — cat None if rejected or absent."""
    up = text[:pos]
    lines = up.splitlines()
    code_ln = len(lines) - 1
    best = None
    best_ln = -1
    for i, ln in enumerate(lines):
        s = ln.strip()
        for hre, cat in HEADERS:
            if hre.match(s) and not HONOR_RE.match(s):
                best, best_ln = cat, i
    if best is None:
        return None, None
    gap = code_ln - best_ln
    if gap > MAX_GAP:
        return None, f"gap {gap} lines"
    prev = ""
    for j in range(best_ln - 1, -1, -1):
        if lines[j].strip():
            prev = lines[j].strip()
            break
    if prev:
        last = re.split(r"[^A-Za-z]+", prev)[-1].lower() if re.search(r"[A-Za-z]", prev) else ""
        if last in WRAP_WORDS:
            return None, f"wrap-continuation (prev line ends '{last}')"
    return best, None


def shas_for(r):
    out, seen = [], set()
    for col in ("source_syllabus", "source_history"):
        for m in re.finditer(r"#([0-9a-f]{12,16})", r.get(col, "") or ""):
            sha = m.group(1)
            if sha not in seen:
                seen.add(sha)
                out.append(sha)
    return out[:6]


def resolve(corpus, sha):
    if sha in corpus:
        return corpus[sha]
    pre = [k for k in corpus if k.startswith(sha)]
    return corpus[pre[0]] if pre else None


def main():
    rows = WC.load_rows()
    by_id = {r["subject_id"]: r for r in rows}
    fl = json.load(open(f"{BASE}/audit_flags.json"))["rows"]
    prev = json.load(open(f"{BASE}/w10c_ckpt.json")).get("results", {})
    corpus = json.load(open(f"{BASE}/corpus_map.json"))

    targets = [sid for sid, f in fl.items()
               if any(x["rule"] == "TYPE_EMPTY" for x in f)]
    # skip rows whose subject_type is already filled (31 from B74)
    targets = [s for s in targets if not (by_id[s].get("subject_type") or "").strip()]
    print(f"W10C2|targets={len(targets)} (non-written TYPE_EMPTY rows)")

    _docs = {}
    def doc_pages(path):
        if path not in _docs:
            try:
                d = fitz.open(path)
                _docs[path] = [(i + 1, d[i].get_text() or "") for i in range(d.page_count)]
                d.close()
            except Exception:
                _docs[path] = []
        return _docs[path]

    results = {}
    for sid in targets:
        r = by_id[sid]
        pc = (r.get("primary_code") or "").strip().upper()
        if not pc:
            results[sid] = {"status": "no_code_print_found", "evidence": "",
                            "why": "no primary_code"}
            continue
        variants = code_variants(pc)
        pat = re.compile(r"\b(" + "|".join(re.escape(v) for v in variants) + r")\b", re.I)
        hits = []          # (sha, page, cat, docbase)
        unresolved = []
        for sha in shas_for(r):
            path = resolve(corpus, sha)
            if not path or not os.path.exists(path):
                unresolved.append(sha)
                continue
            catpages, nocat, rejected = [], [], []
            for pno, t in doc_pages(path):
                m = pat.search(t)
                if not m:
                    continue
                cat, why = governing_header_tight(t, m.start())
                if cat:
                    catpages.append((pno, cat))
                elif why:
                    rejected.append((pno, why))
                else:
                    nocat.append(pno)
            for pno, cat in catpages:
                hits.append((sha, pno, cat, os.path.basename(path)))
            if not catpages and nocat:
                hits.append((sha, None, None, os.path.basename(path)))
            if nocat and catpages:
                results.setdefault(sid, {})["also_plain_pages"] = nocat
        if unresolved and not hits:
            results[sid] = {"status": "sha_unresolved", "evidence": ",".join(unresolved)}
            continue
        cats = {c for (_s, _p, c, _b) in hits if c}
        if len(cats) == 1 and cats & set(WRITEABLE):
            cat = next(iter(cats))
            ev = "; ".join(f"{b}#{s} p.{p}" for (s, p, c, b) in hits if c == cat)
            results[sid] = {"status": "print_category", "category": cat, "evidence": ev}
            continue
        if len(cats) > 1:
            ev = "; ".join(f"{b}#{s} p.{p}->{c}" for (s, p, c, b) in hits if c)
            results[sid] = {"status": "conflicting_headers", "evidence": ev}
            continue
        if cats and not (cats & set(WRITEABLE)):
            ev = "; ".join(f"{b}#{s} p.{p}->{c}" for (s, p, c, b) in hits if c)
            results[sid] = {"status": "conflicting_headers",
                            "evidence": ev + " (category outside writeable vocab)"}
            continue
        # no same-page header anywhere in cited docs — doc-continuity check
        plain = [h for h in hits if h[2] is None]
        if plain:
            tr = None
            evparts = []
            for (sha, pno, _c, base) in plain[:2]:
                path = resolve(corpus, sha)
                if tr is None:
                    tr = doc_header_track(path)
                prevs = [c for (p, c) in tr if pno and p < pno]
                if prevs:
                    evparts.append(f"{base}#{sha} p.{pno} (section continues from p.{[p for (p, c) in tr if p < pno][-1]} -> {prevs[-1]})")
                else:
                    evparts.append(f"{base}#{sha} p.{pno}")
            if any("continues" in e for e in evparts):
                results[sid] = {"status": "cross_page_section", "evidence": "; ".join(evparts)}
            else:
                results[sid] = {"status": "no_header_above",
                                "evidence": "; ".join(evparts)}
            if rejected:
                results[sid]["rejected_headers"] = [
                    f"p.{p}: {w}" for (p, w) in rejected[:6]]
            continue
        results[sid] = {"status": "no_code_print_found", "evidence": "",
                        "pages_probed": "cited docs full text layer"}
        if rejected:
            results[sid]["rejected_headers"] = [
                f"p.{p}: {w}" for (p, w) in rejected[:6]]
        if unresolved:
            results[sid]["why"] = f"sha_unresolved: {','.join(unresolved)}"

    dist = Counter(v["status"] for v in results.values())
    print(f"W10C2_PROBE|{len(results)}|{dict(dist)}")
    cats = Counter(v.get("category") for v in results.values() if v.get("category"))
    print(f"W10C2_CATS|{dict(cats)}")
    json.dump({"results": results}, open(f"{BASE}/w10c2_ckpt.json", "w"), indent=1)
    return 0


def doc_header_track(path):
    out = []
    try:
        d = fitz.open(path)
    except Exception:
        return out
    for i in range(d.page_count):
        t = d[i].get_text() or ""
        last = None
        for ln in t.splitlines():
            s = ln.strip()
            for hre, cat in HEADERS:
                if hre.match(s) and not HONOR_RE.match(s):
                    last = cat
        if last:
            out.append((i + 1, last))
    d.close()
    return out


if __name__ == "__main__":
    sys.exit(main())


def corpus_map_load():
    return json.load(open(f"{BASE}/corpus_map.json"))
