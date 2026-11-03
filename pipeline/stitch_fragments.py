#!/usr/bin/env python3
"""stitch_fragments.py — deterministic S05-pattern stitcher for batch 03 giants.

Concatenates drafts/fragments/<stem>_seg*.frag.json (sorted by seg number) into
drafts/<stem>.draft.json with a single header. Fragments carry identical header
fields; subjects / non_subject_rows / quirks / flags are concatenated; fragment
boundaries are recorded in a "segments" key. Idempotent: re-running overwrites
the stitched draft from the same fragments (append-once discipline lives in the
merge, not here).
"""
import glob, json, os, re, sys

BASE = "/home/z/my-project/work/pipeline_v2"


def main(stem):
    frags = sorted(glob.glob(f"{BASE}/drafts/fragments/{stem}_seg*.frag.json"),
                   key=lambda p: int(re.search(r"_seg(\d+)\.frag\.json$", p).group(1)))
    if not frags:
        print(f"STITCH|{stem}|NO_FRAGMENTS")
        return 1
    heads = []
    subjects, non_subject, quirks, flags, segments = [], [], [], [], []
    for fp in frags:
        d = json.load(open(fp))
        heads.append(d)
        subjects.extend(d.get("subjects", []))
        non_subject.extend(d.get("non_subject_rows", []))
        quirks.extend(d.get("quirks", []))
        flags.extend(d.get("flags", []))
        seg = re.search(r"_seg(\d+)\.frag\.json$", fp).group(1)
        segments.append({"seg": int(seg), "locator": d.get("locator", ""),
                         "subjects": len(d.get("subjects", [])),
                         "non_subject_rows": len(d.get("non_subject_rows", []))})
    h = heads[0]
    out = {"pdf_rel": h.get("pdf_rel", ""), "session": h.get("session", ""),
           "course": h.get("course", ""), "sha16": h.get("sha16", ""),
           "stem": h.get("stem", stem), "locator": "; ".join(s["locator"] for s in segments),
           "segments": segments,
           "subjects": subjects, "non_subject_rows": non_subject,
           "quirks": quirks, "flags": flags}
    dst = f"{BASE}/drafts/{stem}.draft.json"
    json.dump(out, open(dst, "w"), ensure_ascii=False, indent=1)
    print(f"STITCH|{stem}|frags={len(frags)} subjects={len(subjects)} "
          f"non_subject={len(non_subject)} quirks={len(quirks)} flags={len(flags)} -> {dst}")
    # duplicate-code sanity across fragments (informational; verifier GAP/ORPHAN will judge)
    seen = {}
    dups = []
    for s in subjects:
        for c in s.get("codes", []):
            k = re.sub(r"[^A-Z0-9]", "", c.upper())
            if k in seen:
                dups.append(f"{k}:{seen[k]}&{s.get('name','?')[:30]}")
            else:
                seen[k] = s.get("name", "?")[:30]
    if dups:
        print(f"STITCH|{stem}|CROSS-FRAG DUP CODES|{len(dups)}| " + "; ".join(sorted(set(dups))[:20]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
