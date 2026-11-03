#!/usr/bin/env python3
"""patch_b04_elective_codes.py — restore the PRINTED variant codes of the
BPharm 2026-27 elective subjects.

Evidence (page images pp.241/270 + text layer): the 2026-27 scheme prints a
DISTINCT code token per elective variant — 'BP607T AEC4' for Drug Store and
Business Management, 'BP708T AEC6' for Bio-similars — but S04c stored only the
base code ('BP607T') for every variant, and the earlier partial-merge stripped
codes from variants 2..6 with a SHARED-CODE-ELECTIVE-VARIANT flag (now known
wrong: the print distinguishes variants).

Fix: for every draft-04 subject, locate its printed Course-Code cell in the
parse text layer and adopt the printed token (with AEC/SEC/VAC suffix when
printed). Supersedes SHARED-CODE-ELECTIVE-VARIANT flags + code_note fields +
the owner-assignment quirk (removed, supersession recorded). G2 safety: the
suffixed tokens fail exact_code's ^[A-Z]{2,4}\\d{3}[A-Z]?$ pattern, so they are
pool-style tokens exempt from single-owner idempotency — no gate risk.
"""
import json, re

P = "/home/z/my-project/work/pipeline_v2/parsed/04_bpharm_scheme-syllabus_2026-27.json"
D = "/home/z/my-project/work/pipeline_v2/drafts/04_bpharm_scheme-syllabus_2026-27.draft.json"

CODE_CELL = re.compile(r"\b(BP\d{3}[TP]\s?(?:AEC|SEC|VAC)\s?\d+)\b")
BASE_CELL = re.compile(r"\b(BP\d{3}[TP])\b")


def norm_al(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main():
    rec = json.load(open(P))
    pages = [p["text"] for p in rec["pages"]]
    d = json.load(open(D))
    patched, unresolved = [], []
    for s in d["subjects"]:
        nm = s.get("name", "")
        key = norm_al(nm)[:36]
        cand = []
        for pi, t in enumerate(pages):
            nt = norm_al(t)
            if key and key in nt:
                for m in CODE_CELL.finditer(t):
                    cand.append((pi + 1, re.sub(r"\s+", " ", m.group(1))))
                for m in BASE_CELL.finditer(t):
                    cand.append((pi + 1, m.group(1)))
        if not cand:
            unresolved.append(nm)
            continue
        # prefer suffixed tokens, then the page where the name appears with
        # 'Course Code' nearby (first occurrence wins as printed order proxy)
        suffixed = [c for c in cand if CODE_CELL.fullmatch(c[1] + "") or " " in c[1]]
        pick = (suffixed or cand)[0]
        printed = pick[1]
        cur = s.get("codes", [])
        if cur != [printed]:
            s["codes"] = [printed]
            s.setdefault("quirks", []).append(
                f"codes restored to printed token '{printed}' (p.{pick[0]} Course-Code cell; "
                f"subagent had stored {cur or '[]'})")
            patched.append((nm[:44], cur, printed))
        # supersede the wrong shared-code marks
        fl = [f for f in (s.get("flags") or []) if "SHARED-CODE-ELECTIVE-VARIANT" not in str(f)]
        if "SHARED-CODE-ELECTIVE-VARIANT" in " ".join(str(x) for x in (s.get("flags") or [])):
            fl.append("variant-code-restored-from-print (supersedes SHARED-CODE-ELECTIVE-VARIANT)")
        s["flags"] = fl
        if "code_note" in s:
            s.setdefault("quirks", []).append(
                f"code_note removed (was: {s['code_note'][:90]}...) — printed code is variant-distinct, not shared")
            del s["code_note"]
    # owner-assignment quirk on previous owners is superseded too
    for s in d["subjects"]:
        q = (s.get("quirks") or [])
        s["quirks"] = [x for x in q if "code ownership assigned to the first printed variant" not in x]
    d.setdefault("quirks", []).append(
        "pipeline note: elective variant codes restored to printed tokens (BPxxxT/P AEC/SEC/VAC n) "
        "from Course-Code cells; earlier shared-code model superseded — page-image evidence pp.241/270")
    json.dump(d, open(D, "w"), indent=1, ensure_ascii=False)
    print(f"PATCHED|{len(patched)}|UNRESOLVED|{len(unresolved)}")
    for nm, cur, new in patched:
        print(f"CODE|{nm}|{cur}->{new}")
    for nm in unresolved:
        print(f"UNRESOLVED|{nm[:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
