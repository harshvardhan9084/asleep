#!/usr/bin/env python3
"""diag_08_containment.py — for each failing needle, print the UNCOVERED spans
against (text layer + OCR sidecar) so each hard failure can be adjudicated as
OCR-misread / draft-transcription issue / genuinely-dropped print."""
import json, re, sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
from verify_draft import norm_al, windows, strip_furniture_deep, cover_text  # noqa

PARSED = "/home/z/my-project/work/pipeline_v2/parsed"
STEM = "08_bpharm_scheme-syllabus_2026-27"

rec = json.load(open(f"{PARSED}/{STEM}.json"))
text_pages = [p["text"] for p in rec["pages"]]
ocr = json.load(open(f"{PARSED}/{STEM}.ocr.json"))
ocr_pages = [p["text"] for p in ocr["pages"]]
draft = json.load(open(f"/home/z/my-project/work/pipeline_v2/drafts/{STEM}.draft.json"))
rep = json.load(open(f"{PARSED}/verify_report.json"))[STEM]

HAY = [strip_furniture_deep(p) for p in text_pages] + [strip_furniture_deep(p) for p in ocr_pages]


def missing_spans(a, hay_norms, w=70, step=35):
    n = len(a)
    hit = [False] * n
    for b in hay_norms:
        for win in windows(b):
            if not win:
                continue
            start = 0
            chunk = win[:40]
            while True:
                i = a.find(chunk, start)
                if i < 0:
                    break
                take = min(len(win), n - i)
                if win[:take] == a[i:i + take]:
                    for k in range(i, i + take):
                        hit[k] = True
                start = i + 1
                if start >= n:
                    break
    spans, s = [], None
    for i, h in enumerate(hit):
        if not h and s is None:
            s = i
        elif h and s is not None:
            spans.append((s, i))
            s = None
    if s is not None:
        spans.append((s, n))
    return spans


hay_norms = [norm_al(h) for h in HAY]
fails = [p for p in rep["problems"] if "containment" in p]
for f in fails:
    m = re.match(r"(.+?): (unit(\d)|CO(\d)) containment ([\d.]+)", f)
    name, kind, un, cn = m.group(1), m.group(2), m.group(3), m.group(4)
    sub = next((s for s in draft["subjects"] if s.get("name") == name), None)
    if not sub:
        print(f"!! {name}: subject not found"); continue
    if kind.startswith("unit"):
        needle = (sub.get("units") or {}).get(un) or (sub.get("units") or {}).get(int(un))
    else:
        co = next((c for c in sub.get("cos", []) if str(c.get("no")) == cn), {})
        needle = co.get("text")
    if not needle:
        print(f"!! {name} {kind}: no needle"); continue
    a = norm_al(needle)
    spans = missing_spans(a, hay_norms)
    print(f"== {name} {kind} cov={m.group(5)} len={len(a)} missing_spans={len(spans)}")
    for s, e in spans[:6]:
        seg = needle[max(0, s - 0):e]
        print(f"   [{s}:{e}] '{seg[:130]}'")
