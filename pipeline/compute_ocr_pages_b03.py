#!/usr/bin/env python3
"""compute_ocr_pages_b03.py — locate OCR candidate pages for doc 08's failing units.

For every containment-failing unit/CO needle (verify_report.json), find the
text-layer pages that carry the needle's present fragments (the dropped lines
sit in the same page neighborhood), then emit those pages ±1. Targeted OCR:
only what the containment proofs need, not all 295 pages.
"""
import json, re, sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
from verify_draft import norm_al, windows, strip_furniture_deep  # noqa: E402

PARSED = "/home/z/my-project/work/pipeline_v2/parsed"
STEM = "08_bpharm_scheme-syllabus_2026-27"


def main():
    rep = json.load(open(f"{PARSED}/verify_report.json"))[STEM]
    draft = json.load(open(f"/home/z/my-project/work/pipeline_v2/drafts/{STEM}.draft.json"))
    rec = json.load(open(f"{PARSED}/{STEM}.json"))
    pages = [p["text"] for p in rec["pages"]]
    npages = {norm_al(strip_furniture_deep(t)): i for i, t in enumerate(pages, 1)}
    page_norms = [norm_al(strip_furniture_deep(t)) for t in pages]

    fails = rep["problems"]
    needles = {}
    for f in fails:
        m = re.match(r"(.+?): (unit(\d)|CO(\d)) containment ([\d.]+)", f)
        if not m:
            continue
        name, kind, un, cn, cov = m.group(1), m.group(2), m.group(3), m.group(4), float(m.group(5))
        sub = next((s for s in draft["subjects"] if s.get("name") == name), None)
        if not sub:
            continue
        if kind.startswith("unit"):
            needle = (sub.get("units") or {}).get(un) or (sub.get("units") or {}).get(int(un))
        else:
            co = next((c for c in sub.get("cos", []) if str(c.get("no")) == cn), {})
            needle = co.get("text")
        if needle:
            needles[f"{name}::{kind}"] = needle

    out = set()
    unmatched = []
    for key, needle in needles.items():
        a = norm_al(needle)
        if len(a) < 30:
            unmatched.append(f"{key}: needle too short")
            continue
        # find the page with the max window-hit coverage of the needle
        best, bestcov = None, -1.0
        for i, b in enumerate(page_norms):
            if not b:
                continue
            hit = sum(1 for w in windows(b) if w and w[:40] in a)
            tot = max(1, len(list(windows(b))))
            cov = hit / tot
            if cov > bestcov:
                bestcov, best = cov, i
        if best is None or bestcov <= 0:
            unmatched.append(f"{key}: no in-layer anchor")
            continue
        for p in (best - 1, best, best + 1):     # 0-based page index
            if 0 <= p < len(pages):
                out.add(p + 1)                   # 1-based
    out = sorted(out)
    with open(f"{PARSED}/{STEM}.ocr_pages.txt", "w") as f:
        f.write(" ".join(map(str, out)))
    print(f"OCR_PAGES|{len(out)} pages: {out}")
    if unmatched:
        print("UNMATCHED:")
        for u in unmatched:
            print("  ", u)


if __name__ == "__main__":
    main()
