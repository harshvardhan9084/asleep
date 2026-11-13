#!/usr/bin/env python3
"""resolve_year_plan.py — the owner's #1 use case.

Input:  course (+ optional branch substring) + the academic session the
        student is studying in (+ optional year 1-4).
Output: the semester-wise subject lists AS PRINTED in that era's scheme
        document (~6+6 subjects for a year).

Usage:
  python3 resolve_year_plan.py --course BTech --branch "Computer Science & Engineering" \
      --session 2024-25 [--year 3]
  python3 resolve_year_plan.py --demo
"""
import argparse
import csv
import re
import sys

DF = "/home/z/my-project/download/art_d_final/df_year_plan.csv"


def norm_txt(s):
    s = (s or "").lower().replace("&", " and ")
    s = re.sub(r"\bengg\.?\b", "engineering", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load():
    return list(csv.DictReader(open(DF)))


def resolve(rows, course, branch, session, year=None):
    nb = norm_txt(branch)
    # docs of this course+session whose cover lists the branch
    docs = {}
    for r in rows:
        # pdf-scheme-page rows are exact; draft-fallback rows carry the same
        # grain for docs whose PDFs never got committed (MCA/BPharm/older eras)
        if norm_txt(r["course"]) != norm_txt(course):
            continue
        if session and r["session"] != session:
            continue
        if nb and nb not in norm_txt(r["doc_branches"]) \
                and norm_txt(r["doc_branches"]):
            continue
        docs.setdefault(r["doc_file"], []).append(r)
    out = []
    for f, rs in sorted(docs.items()):
        sems = sorted({int(r["semester_int"]) for r in rs
                       if str(r["semester_int"]).strip().isdigit()})
        if year:
            want = {2 * year - 1, 2 * year}
            sems = [s for s in sems if s in want]
            if not sems:
                continue
        out.append({"doc": f, "branches": rs[0]["doc_branches"],
                    "sems": {s: [r for r in rs
                                 if str(r["semester_int"]) == str(s)
                                 and r["row_kind"] == "subject"]
                             for s in sems},
                    "slots": {s: [r for r in rs
                                  if str(r["semester_int"]) == str(s)
                                  and r["row_kind"] == "elective-slot"]
                              for s in sems}})
    return out


def show(plan):
    for p in plan:
        print(f"  doc: {p['doc']}")
        print(f"  branches on cover: {p['branches']}")
        for s in sorted(p["sems"]):
            subs = p["sems"][s]
            print(f"  ---- semester {s}: {len(subs)} printed subject rows ----")
            for r in subs:
                cr = r["credit"] or "?"
                sid = (r["subject_id"].split(";")[0]
                       if r["subject_id"] else "-")
                print(f"    {r['sn']:>2s}. {r['codes']:<16s} "
                      f"{r['subject_name_print'][:46]:<48s} "
                      f"LTP {r['L'] or '-'}-{r['T'] or '-'}-{r['P'] or '-'} "
                      f"cr {cr:>3s}  -> {sid}")
            sl = p["slots"].get(s) or []
            if sl:
                print(f"    elective slots: "
                      + "; ".join(r["subject_name_print"] for r in sl))
        print()


def demo():
    rows = load()
    print("=== DEMO 1: BTech, Computer Science & Engineering, session 2024-25, year 3 ===")
    show(resolve(rows, "BTech", "Computer Science & Engineering", "2024-25", 3))
    print("=== DEMO 2: MBA, session 2024-25, year 1 (no branch) ===")
    show(resolve(rows, "MBA", "", "2024-25", 1))
    print("=== DEMO 3: MCA, Master of Computer Applications, session 2020-21, year 1 ===")
    show(resolve(rows, "MCA", "Master of Computer Applications", "2020-21", 1))
    print("=== DEMO 4: BPharm, session 2021-22, year 2 ===")
    show(resolve(rows, "BPharm", "", "2021-22", 2))
    print("=== DEMO 5: BTech, Mechanical Engineering, session 2021-22, year 4 ===")
    show(resolve(rows, "BTech", "Mechanical Engineering", "2021-22", 4))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", default="")
    ap.add_argument("--branch", default="")
    ap.add_argument("--session", default="")
    ap.add_argument("--year", type=int, default=None)
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    rows = load()
    if a.demo:
        demo()
    else:
        plan = resolve(rows, a.course, a.branch, a.session, a.year)
        if not plan:
            print("NO MATCH — try a broader branch substring or another session")
        show(plan)
