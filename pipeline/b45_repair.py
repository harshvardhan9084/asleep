#!/usr/bin/env python3
"""b45_repair.py — recorded-class repairs for batch 45 drafts:
  1. REX (re-extract) empty-name/zero-unit detail rows via page slices (B44 class).
  2. doc 08: drop the prompt-echo junk row (B43 class); clean dotted-leader
     scheme names (name clean, name_print verbatim, quirk recorded).
  3. doc 07: dedup the duplicated NONCREDIT scheme row (B44 class).
Usage: python3 b45_repair.py
"""
import json, re, sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as me

PARSED = "/home/z/my-project/work/pipeline_v2/parsed"
INV = "/home/z/my-project/work/pipeline_v2/inv"
DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"


def norm(c):
    return re.sub(r"[^A-Z0-9]", "", (c or "").upper())


def pages_of(fulltext):
    return [(int(m.group(1)), m.group(2)) for m in re.finditer(
        r"===== PAGE (\d+) =====\n(.*?)(?=\n===== PAGE \d+ =====|\Z)", fulltext, re.S)]


REX = {
    "03_mba_tourism-mgmt_y2_model-curriculum_2019-20": ["KMT301", "KMT402"],
    "05_mba_travel-tourism_y1_syllabus_2020-21": ["KMTT203"],
    "06_mba_travel-tourism_y2_syllabus_2021-22": ["KMTT404", "KVE303"],
    "07_mba_y1_model-curriculum_2018-19": ["KMB102"],
    "10_mba_y2_model-curriculum-rev-aicte_2019-20": ["KMB301", "KMBIB04", "KMBOM05", "KMBMK04"],
}

for stem, codes in REX.items():
    meta = json.load(open(f"{PARSED}/{stem}.json"))
    meta = meta.get("meta", meta)
    pdf_name = meta.get("file", stem.split("_", 1)[1] + ".pdf")
    fulltext = open(f"{PARSED}/{stem}.fulltext.txt").read()
    PGS = pages_of(fulltext)
    inv = json.load(open(f"{INV}/{stem}.inv.json"))
    det_pages = sorted({int(s.get("page") or 0) for s in inv if s.get("class") == "detail" and s.get("page")})
    draft = json.load(open(f"{DRAFTS}/{stem}.draft.json"))
    session, course = draft["session"], draft["course"]
    for code in codes:
        sub = next((s for s in inv if norm(s.get("code_print")) == code), None)
        if not sub:
            print(f"REX-SKIP|{stem}|{code}|not-in-inv")
            continue
        p = int(sub.get("page") or 0)
        nxt = next((q for q in det_pages if q > p), None)
        slice_txt = "\n\n".join(t for pp, t in PGS if pp >= p and (nxt is None or pp < nxt))
        try:
            _, obj = me.extract_one(pdf_name, slice_txt, meta, sub, session, course)
        except Exception as e:
            print(f"REX-FAIL|{stem}|{code}|{repr(e)[:100]}")
            continue
        obj.setdefault("name", obj.get("name_print", ""))
        obj.setdefault("codes", [code])
        idx = next((i for i, s in enumerate(draft["subjects"]) if code in [norm(c) for c in (s.get("codes") or [])]), None)
        if idx is None:
            print(f"REX-APPEND|{stem}|{code}|{obj.get('name','')[:40]}|units={len(obj.get('units') or {})}")
            draft["subjects"].append(obj)
        else:
            old = draft["subjects"][idx]
            draft["subjects"][idx] = obj
            print(f"REX|{stem}|{code}|{old.get('name','')[:20]!r}->{obj.get('name','')[:40]}|units={len(obj.get('units') or {})}")
        json.dump(draft, open(f"{DRAFTS}/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)

# ---- doc 08: drop junk echo row + clean dotted-leader scheme names ----
stem = "08_mba_y1_scheme_2008-09"
dp = f"{DRAFTS}/{stem}.draft.json"
draft = json.load(open(dp))
before = len(draft["subjects"])
draft["subjects"] = [s for s in draft["subjects"]
                     if not any("codes exactly as printed" in str(c) or "pool/slot print" in str(c)
                                for c in (s.get("codes") or []))]
junk_dropped = before - len(draft["subjects"])
DOTS = re.compile(r"[\.…]{2,}\s*(\(I{1,3}V? Sem(ester)?\))?\s*$|\(I{1,3}V? Sem(ester)?\)\s*$")
for s in draft["subjects"]:
    nm = (s.get("name") or "").strip()
    if "…" in nm or re.search(r"\(IV? Sem", nm):
        clean = DOTS.sub("", nm).strip(" .…")
        clean = re.sub(r"\s{2,}", " ", clean)
        if clean and clean != nm:
            s.setdefault("quirks", []).append(
                "scheme table prints dotted leaders / semester annotation after the title; "
                "name field cleaned, verbatim print kept in name_print (B44 2004-05 dots class)")
            s["name_print"] = s.get("name_print") or nm
            if "…" in (s.get("name_print") or "") or "(" in (s.get("name_print") or ""):
                s["name"] = clean
            else:
                s["name"] = nm
draft.setdefault("quirks", []).append(
    f"1 prompt-echo junk row dropped (codes field echoed the prompt's code-format instruction; B43 class)")
json.dump(draft, open(dp, "w"), indent=1, ensure_ascii=False)
print(f"DOC08|junk_dropped={junk_dropped}|subjects={len(draft['subjects'])}")

# ---- doc 07: dedup NONCREDIT pair ----
stem = "07_mba_y1_model-curriculum_2018-19"
dp = f"{DRAFTS}/{stem}.draft.json"
draft = json.load(open(dp))
seen, out, dups = set(), [], 0
for s in draft["subjects"]:
    key = (norm("".join(s.get("codes") or [])) or norm(s.get("name")), norm(s.get("name")))
    if key in seen and not any(norm(c) for c in (s.get("codes") or [])):
        dups += 1
        continue
    seen.add(key)
    out.append(s)
if dups:
    out[-1].setdefault("quirks", []).append(
        "model listed this non-credit scheme row twice; single row kept (B44 dedup class)")
draft["subjects"] = out
json.dump(draft, open(dp, "w"), indent=1, ensure_ascii=False)
print(f"DOC07|dedup={dups}|subjects={len(out)}")

# ---- final state scan ----
import glob
tot = 0
for f in sorted(glob.glob(f"{DRAFTS}/[0-9][0-9]_mba_*.draft.json")):
    b = f.split("/")[-1][:2]
    # only B45 stems (tourism/travel/scheme/curriculum)
    if not any(k in f for k in ("tourism", "travel", "y1_scheme", "y1_model-curriculum", "model-curriculum-rev-aicte", "y2_model-curriculum")):
        continue
    d = json.load(open(f))
    bad = [(s.get("codes"), (s.get("name") or "")[:30], len(s.get("units") or {}))
           for s in d["subjects"] if not (s.get("name") or "").strip() or not (s.get("units") or {})]
    tot += len(d["subjects"])
    print(f"FINAL|{b}|{len(d['subjects'])} subj|non_subj {len(d.get('non_subject_rows') or [])}|zero/empty: {bad if bad else '-'}")
print("TOTAL", tot)
