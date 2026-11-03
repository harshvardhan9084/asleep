#!/usr/bin/env python3
"""contain_diff.py <stem> <subject_name> <unit_key> — show which windows of a draft value
fail containment against the parsed fulltext and print the nearest fulltext context."""
import json, re, sys

BASE = "/home/z/my-project/work/pipeline_v2/parsed"


def norm(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def main():
    stem, target, unit_key = sys.argv[1], sys.argv[2].lower(), sys.argv[3]
    tnorm = norm(target)
    draft = json.load(open(f"/home/z/my-project/work/pipeline_v2/drafts/{stem}.draft.json", encoding="utf-8"))
    st = next(s for s in draft["subjects"] if tnorm in norm(s.get("subject_name", "")))
    val = (st.get("units") or {}).get(unit_key) or ""
    hay = norm(open(f"{BASE}/{stem}.fulltext.txt", encoding="utf-8").read())
    nv = norm(val)
    w, step = 70, 35
    misses = []
    for i in range(0, max(1, len(nv) - w + 1), step):
        win = nv[i:i + w]
        if win not in hay:
            misses.append((i, win))
    print(f"value norm len={len(nv)} misses={len(misses)}")
    for i, win in misses[:6]:
        print(f"\n--- miss at {i}: ...{win[:70]}...")
        # locate best context: try the first 25 chars
        probe = win[:25]
        j = hay.find(probe)
        if j < 0:
            probe = win[:12]
            j = hay.find(probe)
        if j >= 0:
            print("HAY :", hay[max(0, j - 20):j + 110])
        else:
            print("HAY : <probe not found>")


if __name__ == "__main__":
    main()
