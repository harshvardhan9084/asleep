#!/usr/bin/env python3
"""concat_seg08.py — deterministically merge _seg08a.._seg08g into the doc-08 draft.

Segments are page-domain slices of ONE document (08_bpharm_scheme-syllabus_
2026-27, 295pp): a=pp1-33 Sem-I, b=34-64 Sem-II, c=65-93 Sem-III, d=94-119
Sem-IV, e=120-148 Sem-V, f=149-199 Sem-VI+VII, g=200-295 Sem-VIII+appendix
electives. Concat order = segment order (page order). Headers taken from the
first segment (all identical by construction); non_subject_rows/quirks/flags
concatenated with segment tags preserved where present.
"""
import json, os, sys

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"
SEGS = ["a", "b", "c", "d", "e", "f", "g"]
OUT = os.path.join(DRAFTS, "08_bpharm_scheme-syllabus_2026-27.draft.json")


def main():
    merged = None
    n_sub = n_nsr = n_q = 0
    for s in SEGS:
        fp = os.path.join(DRAFTS, f"_seg08{s}.json")
        d = json.load(open(fp))
        if merged is None:
            merged = {
                "pdf_rel": d["pdf_rel"],
                "session": d["session"],
                "course": d["course"],
                "sha16": d["sha16"],
                "stem": d["stem"],
                "subjects": [],
                "non_subject_rows": [],
                "quirks": [],
                "flags": [],
                "segments": [],
            }
        # header consistency guard (zero-guess: abort on mismatch)
        for k in ("pdf_rel", "session", "course", "sha16", "stem"):
            if d.get(k) != merged[k]:
                print(f"HDR-MISMATCH seg{s} {k}: {d.get(k)!r} != {merged[k]!r}")
                return 1
        merged["segments"].append(
            {"segment": d.get("segment", f"08{s}"), "pages": d.get("pages"),
             "subjects": len(d.get("subjects", []))})
        for sub in d.get("subjects", []):
            sub.setdefault("quirks", [])
            segtag = d.get("segment", f"08{s}")
            # annotate segment origin once per subject for provenance
            sub.setdefault("flags", []).append(f"segment:{segtag}")
            merged["subjects"].append(sub)
        for r in d.get("non_subject_rows", []):
            r.setdefault("segment", d.get("segment", f"08{s}"))
            merged["non_subject_rows"].append(r)
        for q in d.get("quirks", []):
            merged["quirks"].append(f"[{d.get('segment', f'08{s}')}] {q}")
        for f in d.get("flags", []):
            merged["flags"].append(f if f.startswith("segment:") else f"segment:{d.get('segment', f'08{s}')}: {f}")
        n_sub += len(d.get("subjects", []))
        n_nsr += len(d.get("non_subject_rows", []))
        n_q += len(d.get("quirks", []))

    with open(OUT, "w") as fh:
        json.dump(merged, fh, indent=1, ensure_ascii=False)
    print(f"CONCAT|{OUT}")
    print(f"subjects={len(merged['subjects'])} (expected {n_sub}) non_subject_rows={len(merged['non_subject_rows'])} quirks={len(merged['quirks'])} flags={len(merged['flags'])}")
    codes = []
    for s in merged["subjects"]:
        codes.extend(s.get("codes") or [])
    print(f"code tokens={len(codes)} unique={len(set(codes))}")
    dups = {c for c in codes if codes.count(c) > 1}
    if dups:
        print("DUP-CODES|" + ",".join(sorted(dups)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
