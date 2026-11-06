#!/usr/bin/env python3
"""b45_repair4.py —
  1. KMBIB04 (doc 10): validated re-extraction (units keys numeric + containment
     >= 0.85 vs slice); fallback = deterministic 'Unit N' split of the pages
     (zero-guess, verbatim).
  2. RMT451 (doc 02) + KMTT408 (doc 06): numbered-prose note pages — transcribe
     verbatim into notes_print, flag practical_turns_notes_only (B29 v17 class).
  3. KMTT-307 (doc 06): add the missed objectives_only flag (dash-bug fix).
"""
import json, re, sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as me

PARSED = "/home/z/my-project/work/pipeline_v2/parsed"
DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"


def norm(c):
    return re.sub(r"[^A-Z0-9]", "", (c or "").upper())


def pg(ft, pn):
    m = re.search(r"===== PAGE %d =====\n(.*?)(?=\n===== PAGE|\Z)" % pn, ft, re.S)
    return m.group(1) if m else ""


def contained(t, corpus):
    tn = re.sub(r"\s+", " ", (t or "").lower()).strip()
    cn = re.sub(r"\s+", " ", corpus.lower())
    return 1.0 if (tn and tn in cn) else 0.0


# ---------- 1. KMBIB04 ----------
stem = "10_mba_y2_model-curriculum-rev-aicte_2019-20"
ft = open(f"{PARSED}/{stem}.fulltext.txt").read()
slice_txt = "\n\n".join(pg(ft, p) for p in (53, 54))
draft = json.load(open(f"{DRAFTS}/{stem}.draft.json"))
idx = next(i for i, s in enumerate(draft["subjects"]) if "KMBIB04" in [norm(c) for c in (s.get("codes") or [])])
obj = None
for attempt in (1, 2):
    try:
        _, cand = me.extract_one("mba_y2_model-curriculum-rev-aicte_2019-20.pdf", slice_txt, {}, {"class": "detail", "code_print": "KMBIB04", "name_print": "International Trade Law", "page": 53}, "2019-20", "MBA")
        us = cand.get("units") or {}
        keys_ok = all(re.fullmatch(r"[1-9]", k) for k in us) and len(us) >= 4
        cont_ok = all(contained(v, slice_txt) >= 0.85 for v in us.values()) if us else False
        print(f"KMBIB04 attempt {attempt}: keys_ok={keys_ok} cont_ok={cont_ok} units={len(us)}")
        if keys_ok and cont_ok:
            obj = cand
            break
    except Exception as e:
        print(f"KMBIB04 attempt {attempt} EXC: {repr(e)[:100]}")
if obj is None:
    # deterministic hand-split (zero-guess): pages 53-54, split at Unit N markers
    txt = slice_txt
    marks = [(m.group(1), m.start()) for m in re.finditer(r"Unit\s+(\d)\b", txt)]
    units = {}
    for j, (uk, st) in enumerate(marks):
        en = marks[j + 1][1] if j + 1 < len(marks) else len(txt)
        body = txt[st:en]
        body = body.split("\n", 1)[1] if "\n" in body else body  # drop the 'Unit N' marker line
        units[uk] = re.sub(r"[ \t]*\n[ \t]*", " ", body).strip()
    obj = {"name": "International Trade Law", "name_print": "International Trade Law",
           "codes": ["KMBIB04"], "semester": 4, "units": units,
           "quirks": ["units hand-split from the pp.53-54 print at the printed 'Unit N' markers "
                      "after the model returned echoed-reasoning junk (B44 KMT207 junk class); "
                      "text verbatim, line breaks normalized"],
           "flags": ["hand_split_units_verbatim"]}
    print(f"KMBIB04 HAND-SPLIT units={len(units)} cont={[round(contained(v, slice_txt),2) for v in units.values()]}")
obj.setdefault("name_print", "International Trade Law")
obj.setdefault("codes", ["KMBIB04"])
draft["subjects"][idx] = obj
json.dump(draft, open(f"{DRAFTS}/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)

# ---------- 2. notes-only rows ----------
def transcribe_notes(stem, code, page, start_re):
    ft = open(f"{PARSED}/{stem}.fulltext.txt").read()
    t = pg(ft, page)
    m = re.search(start_re, t, re.S)
    if not m:
        print(f"NOTES-FAIL {stem[:2]} {code}: start not found")
        return
    note = re.sub(r"[ \t]*\n[ \t]*", " ", m.group(1)).strip()
    note = re.sub(r" {2,}", " ", note)
    draft = json.load(open(f"{DRAFTS}/{stem}.draft.json"))
    for s in draft["subjects"]:
        if code.replace("-", "") in [c.replace("-", "") for c in (s.get("codes") or [])]:
            s["notes_print"] = note
            fl = s.setdefault("flags", [])
            if "practical_turns_notes_only_no_units_printed" not in fl:
                fl.append("practical_turns_notes_only_no_units_printed")
            s.setdefault("quirks", []).append(
                f"detailed page (p.{page}) prints a numbered prose note (evaluation/project rules) only; "
                "transcribed verbatim under notes_print; no unit theory, no experiment list printed "
                "(B29 v17 notes-only class)")
            json.dump(draft, open(f"{DRAFTS}/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)
            print(f"NOTES {stem[:2]} {code}: {len(note)} chars")
            return
    print(f"NOTES-FAIL {stem[:2]} {code}: row not found")


transcribe_notes("02_mba_tourism-mgmt_syllabus_2017-18", "RMT451", 6,
                 r"(1\. In fourth semester, the candidates will have to submit.*?)(?:\Z)")
transcribe_notes("06_mba_travel-tourism_y2_syllabus_2021-22", "KMTT408", 30,
                 r"(1\. In fourth semester, the candidates will have to submit.*?)(?:\Z)")

# ---------- 3. KMTT-307 flag ----------
stem = "06_mba_travel-tourism_y2_syllabus_2021-22"
draft = json.load(open(f"{DRAFTS}/{stem}.draft.json"))
for s in draft["subjects"]:
    if "KMTT307" in [norm(c) for c in (s.get("codes") or [])]:
        fl = s.setdefault("flags", [])
        if "objectives_only_no_units_printed" not in fl:
            fl.append("objectives_only_no_units_printed")
            s.setdefault("quirks", []).append(
                "detailed page prints course objectives / evaluation criteria only; no unit-wise "
                "syllabus printed in this document (RULES §6; B44 objectives-only class)")
            print("KMTT-307 objectives_only flag added")
json.dump(draft, open(f"{DRAFTS}/{stem}.draft.json", "w"), indent=1, ensure_ascii=False)
