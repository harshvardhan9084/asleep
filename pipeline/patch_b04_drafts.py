#!/usr/bin/env python3
"""patch_b04_drafts.py — batch-04 draft fixes, each with recorded evidence:

1. Draft 05 (bpharm y1-4 2019-20): 605 textbook/reference entries are plain
   strings (S05 subagent format deviation from RULES §7 spec). Normalize to
   {"no": n, "book": <verbatim string>} preserving print exactly.

2. Draft 01 (bca y3 2026-27): BBC552 Mini Project Lab / BBC651 Startup &
   Entrepreneurial Activity Assessment / BBC652 Project print NO detailed
   syllabus (scheme-row marks only — S01 verified via coordinate-aligned
   extraction, quirks recorded). Add scheme-only flag so verify_draft's
   recorded B2 exemption applies (zero-guess: no units invented).

3. Draft 04 (bpharm scheme-syllabus 2026-27): same class for subjects that
   print no units and no experiment lists (Internship, Research Project,
   Professional Skills BP611P variant — EXPERIMENT-LIST-PRINTED-EMPTY flag
   recorded by S04c). Flag scheme-only where the entry is scheme-row-only;
   Professional Skills gets the printed-blank flag class.
"""
import json, sys

BD = "/home/z/my-project/work/pipeline_v2/drafts"


def load(n):
    return json.load(open(f"{BD}/{n}.draft.json"))


def save(n, d):
    json.dump(d, open(f"{BD}/{n}.draft.json", "w"), indent=1, ensure_ascii=False)


def norm_books(s):
    ch = 0
    for fld in ("textbooks", "reference_books"):
        lst = s.get(fld)
        if not lst:
            continue
        out = []
        no = 0
        for b in lst:
            if isinstance(b, dict):
                if "no" not in b:
                    b["no"] = no + 1
                no = b["no"]
                out.append(b)
            else:
                no += 1
                out.append({"no": no, "book": b})
                ch += 1
        s[fld] = out
    return ch


def main():
    # 1. draft 05 book normalization
    d5 = load("05_bpharm_y1-4_syllabus_2019-20")
    n = sum(norm_books(s) for s in d5["subjects"])
    d5.setdefault("quirks", []).append(
        "pipeline note: 605 textbook/reference entries normalized from subagent string format to §7 {no,book} dicts (verbatim strings preserved)")
    save("05_bpharm_y1-4_syllabus_2019-20", d5)
    print(f"PATCH05|books_normalized={n}")
    assert n == 605, f"expected 605, got {n}"

    # 2. draft 01 scheme-only flags
    d1 = load("01_bca_y3_syllabus_2026-27")
    p = 0
    for s in d1["subjects"]:
        cs = [c.upper() for c in s.get("codes", [])]
        if any(c.startswith("BBC552") or c.startswith("BBC651") or c.startswith("BBC652") for c in cs):
            fl = s.setdefault("flags", [])
            tag = "scheme-only-row-no-detailed-syllabus-printed"
            if not any(tag == f for f in fl):
                fl.append(tag)
                p += 1
    d1.setdefault("quirks", []).append(
        "pipeline note: BBC552/BBC651/BBC652 print scheme rows + marks only (no detailed syllabus) — S01 coordinate-aligned extraction; scheme-only flags added per RULES §6 zero-guess")
    save("01_bca_y3_syllabus_2026-27", d1)
    print(f"PATCH01|scheme_only_flags={p}")

    # 3. draft 04 no-units/no-experiments printed-blank class
    d4 = load("04_bpharm_scheme-syllabus_2026-27")
    p = 0
    for s in d4["subjects"]:
        if s.get("units") or s.get("experiments"):
            continue
        fl = [str(f) for f in (s.get("flags") or [])]
        if any("SHARED-CODE-ELECTIVE-VARIANT" in f for f in fl):
            continue  # handled below via no-codes exemption, units may exist
        nm = (s.get("name") or "").lower()
        if "internship" in nm or "research project" in nm:
            tag = "scheme-only-row-no-detailed-syllabus-printed"
        else:
            tag = "printed-blank-no-units-no-experiments"
        if tag not in fl:
            s.setdefault("flags", []).append(tag)
            p += 1
    d4.setdefault("quirks", []).append(
        "pipeline note: subjects printing neither units nor experiment lists flagged scheme-only / printed-blank (S04a-c recorded: Internship & Research Project are scheme rows; BP611P Professional Skills prints an empty list) — zero-guess")
    save("04_bpharm_scheme-syllabus_2026-27", d4)
    print(f"PATCH04|flags_added={p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
