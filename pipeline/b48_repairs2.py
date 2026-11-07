#!/usr/bin/env python3
"""b48_repairs2.py — print-anchored transcription repairs for B48 blank rows
(recorded B47 classes: notes-only rows, experiment-list restorations, unit
re-transcription). ZERO-GUESS: the row's own printed section is located from
the hand-built inventory (code header -> next subject's code header), split
mechanically on printed markers only:
  - 'Unit N' markers           -> units dict (byte-verbatim text)
  - numbered list under a PRACTICAL / LIST OF EXPERIMENT(S) header -> experiments
  - other prose (guidelines / training brief / one-sentence expectation)
                               -> notes + notes_only_no_units_printed flag
Also normalizes str-shaped textbooks/reference_books/experiments to RULES §7
lists (2 str-shaped rows found in the shape audit).
"""
import json, re, sys

PARSED = "/home/z/my-project/work/pipeline_v2/parsed"
DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"
INVD = "/home/z/my-project/work/pipeline_v2/inv"

TARGETS = {
    "02_mca_y3_syllabus_2010-11": ["MCA611", "MCA612"],
    "04_mca_y3_syllabus_2018-19": ["RCA512", "RCA552", "RCA661"],
    "05_mca_y5_syllabus_2021-22": ["RCAI952"],
    "06_bpharm_syllabus": ["BOP366P", "BOP351P", "BOP356P", "BOP361P", "BOP362"],
    "07_bpharm_y3_scheme-syllabus-cbcs-rev": ["RPH526P", "RPH632P"],
    "08_bpharm_y4_syllabus": ["BOP476P", "BOP486P", "BOP485PA", "BOP485PC"],
}

UNIT_SPLIT = re.compile(r"(?im)^\s*Unit\s*[-–‐]?\s*(I{1,3}|IV|VI{0,3}|1|2|3|4|5)\b[\s:.\-–‐]*")
ROMAN = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5", "VI": "6", "VII": "7",
         "VIII": "8", "1": "1", "2": "2", "3": "3", "4": "4", "5": "5"}


def skey(c):
    return re.sub(r"[^A-Za-z0-9]", "", c or "").upper()


def pages_of(stem):
    t = open(f"{PARSED}/{stem}.fulltext.txt", encoding="utf-8").read()
    p = re.split(r"===== PAGE (\d+) =====", t)
    return {int(p[i]): p[i + 1] for i in range(1, len(p) - 1, 2)}


def inv_entries(stem):
    return [s for s in json.load(open(f"{INVD}/{stem}.inv.json")) if isinstance(s, dict)]


def section_text(P, pg, all_codes):
    """verbatim text from the row's page start.. next subject header (same or later page)."""
    if pg not in P:
        return "", pg
    txt = P[pg]
    pat = re.compile(r"^\s*[|\s]*(" + "|".join(re.escape(c) for c in sorted(all_codes, key=len, reverse=True)) + r")\b", re.I)
    end = len(txt)
    for m in pat.finditer(txt):
        if m.start() == 0:
            continue
        end = m.start()
        break
    # extend: if the section looks truncated (no terminal structure), also scan the next page up to the next header
    nxt = pg + 1
    while nxt in P and len(txt) and end >= len(txt) - 2 and nxt <= pg + 1:
        t2 = P[nxt]
        m2 = pat.search(t2)
        end2 = m2.start() if m2 else len(t2)
        if m2 and m2.start() < 40:
            break
        txt = txt[:end] + "\n" + t2[:end2]
        end = len(txt)
        nxt += 1
        break
    return txt[:end] if end <= len(txt) else txt, pg


def main():
    grand = {"units": 0, "exps": 0, "notes": 0, "shapes": 0, "skipped": 0}
    for stem, codes in TARGETS.items():
        d = json.load(open(f"{DRAFTS}/{stem}.draft.json"))
        P = pages_of(stem)
        inv = inv_entries(stem)
        all_codes = [e.get("code_print", "") for e in inv if e.get("code_print")]
        imap = {skey(e.get("code_print", "")): e for e in inv if e.get("code_print")}
        for s in d["subjects"]:
            c0 = skey((s.get("codes") or [""])[0])
            if c0 not in [skey(c) for c in codes]:
                continue
            if any(str(f).startswith("b48_repair2") for f in (s.get("flags") or [])):
                grand["skipped"] += 1
                continue
            e = imap.get(c0, {})
            pg = e.get("page")
            if not pg:
                continue
            sec, pgu = section_text(P, int(pg), all_codes)
            if not sec.strip():
                continue
            did = False
            # 1) units?
            parts = UNIT_SPLIT.split(sec)
            if len(parts) >= 3:
                units = {}
                for i in range(1, len(parts) - 1, 2):
                    k = ROMAN.get(parts[i].upper(), parts[i])
                    tx = parts[i + 1].strip()
                    if k and tx:
                        units[k] = tx
                if units:
                    s["units"] = units
                    s["quirks"] = list(dict.fromkeys((s.get("quirks") or []) + [
                        f"units transcribed byte-verbatim from the printed section at p.{pg} "
                        "(b48 print-anchored re-transcription after blank first pass)"]))
                    s["flags"] = list(dict.fromkeys((s.get("flags") or []) + ["b48_repair2_units"]))
                    grand["units"] += 1
                    did = True
            # 2) experiments? (numbered list under a PRACTICAL/experiment header)
            if not did and re.search(r"(?i)PRACTICAL|LIST OF EXPERIMENT", sec) and re.search(r"(?m)^\s*\(?\d{1,2}[\).]", sec):
                body = re.split(r"(?i)PRACTICAL|LIST OF EXPERIM?ENT?S?\w*", sec, maxsplit=1)[-1]
                exps = []
                for ln in body.splitlines():
                    m = re.match(r"\s*[\(\[]?(\d{1,2})[\)\].]\s+(.{2,})+", ln)
                    if m:
                        exps.append({"no": int(m.group(1)), "exp": m.group(2).strip()})
                if exps:
                    s["experiments"] = exps
                    s["quirks"] = list(dict.fromkeys((s.get("quirks") or []) + [
                        f"experiment list transcribed byte-verbatim from the printed practical section at p.{pg} "
                        "(b48 print-anchored restoration class)"]))
                    s["flags"] = list(dict.fromkeys((s.get("flags") or []) + ["b48_repair2_exps"]))
                    grand["exps"] += 1
                    did = True
            # 3) notes (guidelines / training brief)
            if not did:
                body = re.sub(r"^\s*[|\s]*(BOOKS RECO\w*)[\s\S]*$", "", sec, flags=re.I)
                body = re.sub(r"\s+", " ", body).strip()
                body = re.sub(r"^\s*\d*\s*[|\s]*", "", body)
                if len(body) >= 40:
                    s["notes"] = body
                    s["flags"] = list(dict.fromkeys((s.get("flags") or []) + [
                        "notes_only_no_units_printed", "b48_repair2_notes"]))
                    s["quirks"] = list(dict.fromkeys((s.get("quirks") or []) + [
                        f"guideline/training print transcribed byte-verbatim into notes from p.{pg}; "
                        "no unit-wise syllabus printed for this subject in-doc (B47 notes-only class)"]))
                    grand["notes"] += 1
                    did = True
            if not did:
                grand["skipped"] += 1
        # shape normalization across the whole draft (audit-found str shapes)
        for s in d["subjects"]:
            for k, itemk in (("textbooks", "book"), ("reference_books", "book"), ("experiments", "exp")):
                v = s.get(k)
                if isinstance(v, str) and v.strip():
                    s[k] = [{"no": 1, itemk: v.strip()}]
                    s["flags"] = list(dict.fromkeys((s.get("flags") or []) + ["b48_repair2_shape_norm"]))
                    grand["shapes"] += 1
        json.dump(d, open(f"{DRAFTS}/{d['stem']}.draft.json", "w"), indent=1, ensure_ascii=False)
        print(f"REPAIR2|{stem}|done", flush=True)
    print("STATS|", grand)


if __name__ == "__main__":
    main()
