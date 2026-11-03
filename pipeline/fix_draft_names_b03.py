#!/usr/bin/env python3
"""fix_draft_names_b03.py — disambiguate same-name theory/practical pairs.

Evidence: the 2013-14/2019-20 BPharm documents print each subject's type in the
SCHEME ROW ("Biochemistry – Theory" / "Biochemistry – Practical") while the
detail-page headers print the bare title, so the subagents recorded identical
`name` strings for the theory subject and its practical pair (e.g. draft 10
#17 BP203T and #18 BP209P are both "BIOCHEMISTRY"). The registry's G3 gate
requires unique (subject_name, course_name) and §3 keeps labs as distinct rows,
so the pair names must be distinguished. Remedy: within each draft, when 2+
subjects share a normalized name, append the printed type — " (Theory)" for
subjects carrying unit texts and no experiments, " (Practical)" for subjects
carrying experiments and no units — exactly the type the scheme rows print for
those codes. name_print stays untouched (verbatim print); the derivation is
recorded as a quirk on each renamed subject.
"""
import json, re

BASE = "/home/z/my-project/work/pipeline_v2/drafts"


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()


def main():
    total = 0
    for n in range(1, 11):
        import glob
        for fp in sorted(glob.glob(f"{BASE}/{n:02}_*.draft.json")):
            d = json.load(open(fp))
            subs = d.get("subjects", [])
            groups = {}
            for s in subs:
                groups.setdefault(norm(s.get("name", "")), []).append(s)
            changed = 0
            for key, members in groups.items():
                if len(members) < 2 or not key:
                    continue
                for s in members:
                    nm = s.get("name", "")
                    low = nm.lower()
                    units = s.get("units") or {}
                    exps = s.get("experiments") or []
                    if "(theory)" in low or "(practical)" in low:
                        continue
                    if units and not exps:
                        suffix = " (Theory)"
                    elif exps and not units:
                        suffix = " (Practical)"
                    else:
                        s.setdefault("quirks", []).append(
                            "same-name group member with ambiguous content shape (units and "
                            "experiments both present/absent) — name left unsuffixed; flagged "
                            "for owner review")
                        s.setdefault("flags", []).append("ambiguous_name_shape")
                        continue
                    s["name"] = nm + suffix
                    s.setdefault("quirks", []).append(
                        f"name disambiguated to '{nm}{suffix}': the document prints the same "
                        f"bare title for the theory and practical pair (type is printed only in "
                        f"the scheme rows); suffix derived from the printed content shape "
                        f"(units vs experiments), matching the scheme row's printed type")
                    changed += 1
            if changed:
                json.dump(d, open(fp, "w"), ensure_ascii=False, indent=1)
                print(f"NAMES|{fp.split('/')[-1]}|fixed={changed}")
                total += changed
    print(f"NAMES|total={total}")


if __name__ == "__main__":
    main()
