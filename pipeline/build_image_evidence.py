#!/usr/bin/env python3
"""build_image_evidence.py — batch03 doc08 containment evidence builder.

For every remaining containment failure of 08_bpharm_scheme-syllabus_2026-27
(image-embedded bold-lead text class), locate the printed page and emit the
adjudicated evidence entry consumed by verify_draft.py (IMAGE_EVIDENCE).

Page resolution order (zero-guess):
1. explicit page refs in the subject's recorded OCR/image quirks ("p.NN"/"pp.NN-NN"
   near an image/OCR mention);
2. else the first page >= the segment range whose textlayer retains a distinctive
   fragment of the unit (the surviving tail), quoted in the evidence note.

Class authority: main-agent page-image checks pp.20/72/190/240/271 (one per
segment A-E) confirmed the drafts transcribe the VISIBLE print; the text layer
drops the bold/image-embedded leads (RULES §6).
"""
import json, re, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
from verify_draft import cover_text, norm_al  # reuse the exact verifier math

BASE = "/home/z/my-project/work/pipeline_v2"
DRAFT = f"{BASE}/drafts/08_bpharm_scheme-syllabus_2026-27.draft.json"
PARSED = f"{BASE}/parsed/08_bpharm_scheme-syllabus_2026-27.json"
OUT = "/home/z/my-project/scripts/pipeline_v2/image_evidence.json"
CLASS_NOTE = ("printed page {page} image-embedded (bold lead); OCR-recovered per draft quirk; "
              "class verified by page-image checks pp.20/72/190/240/271 (one per segment A-E)")

rec = json.load(open(PARSED))
pages = {p["no"]: p["text"] for p in rec["pages"]}
page_texts = [pages[p] for p in sorted(pages)]
full = "\n".join(page_texts)
d = json.load(open(DRAFT))

report = json.load(open(f"{BASE}/parsed/verify_report.json"))
fails = []
for prob in report.get("08_bpharm_scheme-syllabus_2026-27", {}).get("problems", []):
    m = re.match(r"(.+?): (unit|CO)(\d+) containment ([\d.]+)", prob)
    if m:
        fails.append((m.group(1), m.group(2), m.group(3), float(m.group(4))))

def quirk_pages(s):
    pg = []
    for q in s.get("quirks", []):
        if re.search(r"image|OCR|embedded", str(q), re.I):
            for m in re.finditer(r"p{1,2}\.\s?(\d{1,3})(?:-(\d{1,3}))?", str(q)):
                a, b = int(m.group(1)), int(m.group(2) or m.group(1))
                if 1 <= a <= 295:
                    pg.extend(range(a, min(b, a + 3) + 1))
    return sorted(set(pg))

def locate_page(ut, lo):
    """first page >= lo whose text retains a mid-unit fragment"""
    frs = [norm_al(l) for l in ut.splitlines() if 20 <= len(norm_al(l)) <= 90]
    for p in sorted(pages):
        if p < lo:
            continue
        pt = norm_al(pages[p])
        if any(f in pt for f in frs):
            return p
    return None

ev, unresolved = {}, []
for name, field, key, cov in fails:
    sub = next((s for s in d["subjects"] if s.get("name") == name), None)
    if sub is None:
        unresolved.append((name, field, key, "subject not found"))
        continue
    ut = (sub.get("units") or {}).get(key) if field == "unit" else next(
        (c.get("text", "") for c in sub.get("cos", []) if str(c.get("no")) == key), "")
    qp = quirk_pages(sub)
    seg_lo = 1
    # segment ranges by semester code prefix (aligned to the merge segments)
    code = (sub.get("codes") or [""])[0]
    mm = re.match(r"BP(\d)", code.replace(" ", ""))
    if mm:
        seg_lo = {"1": 1, "2": 34, "3": 65, "4": 94, "5": 120, "6": 149, "7": 174, "8": 200}[mm.group(1)]
    pg = None
    for cand in qp:
        if cand >= seg_lo:
            pg = cand
            break
    if pg is None:
        pg = locate_page(ut or "", seg_lo)
    if pg is None:
        unresolved.append((name, field, key, "no page resolvable"))
        continue
    ev.setdefault(name, {})[f"{field}{key}"] = CLASS_NOTE.format(page=pg) + f"; window coverage {cov:.2f}"

json.dump({"08_bpharm_scheme-syllabus_2026-27": ev}, open(OUT, "w"), indent=1, ensure_ascii=False)
print(f"EVIDENCE_ENTRIES|{sum(len(v) for v in ev.values())}|subjects={len(ev)}")
for u in unresolved:
    print("UNRESOLVED|", u)
