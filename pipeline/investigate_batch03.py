#!/usr/bin/env python3
"""investigate_batch03.py — root-cause the verify failures (protocol step 5).

For each (draft, subject) interest:
- print the subject's flags/codes and unit keys;
- for the worst-coverage unit: locate the best matching fulltext region and
  print the longest UNCOVERED needle chunks next to the fulltext context, so
  the failure class (garble / OCR-recovered / wrong-page / column-scramble)
  becomes visible;
- for no-units subjects: grep the fulltext for the subject's code + name and
  print the surrounding lines (what did the print actually give?).
"""
import json, re, sys, os

BASE = "/home/z/my-project/work/pipeline_v2"
CODE_RE = re.compile(r"\b([A-Z]{2,4})\s?-?(\d{3})([A-Z]?)\b")


def norm_al(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def strip_deep(pagetext):
    kept = [l for l in pagetext.splitlines() if re.fullmatch(r"\s*\d{1,4}\s*", l) is None]
    return "\n".join(kept)


def analyze(stem, want_names):
    rec = json.load(open(f"{BASE}/parsed/{stem}.json"))
    draft = json.load(open(f"{BASE}/drafts/{stem}.draft.json"))
    page_texts = [p["text"] for p in rec["pages"]]
    full_joined = norm_al(strip_deep("\n".join(page_texts)))
    by_page = {p["no"]: norm_al(strip_deep(p["text"])) for p in rec["pages"]}
    print(f"\n########## {stem} ##########")
    for s in draft["subjects"]:
        nm = s.get("name", "?")
        if not any(w.lower() in nm.lower() for w in want_names):
            continue
        codes = s.get("codes", [])
        flags = s.get("flags", [])
        units = s.get("units") or {}
        exps = s.get("experiments") or []
        print(f"\n--- {nm} | codes={codes} | units={sorted(units)} | exps={len(exps)}")
        print(f"    flags={flags}")
        if units:
            # worst unit by coverage using the same window method
            import importlib.util
            spec = importlib.util.spec_from_file_location("vd", "/home/z/my-project/scripts/pipeline_v2/verify_draft.py")
            vd = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(vd)
            worst_k, worst_c = None, 1.1
            for uk, ut in sorted(units.items()):
                cov = vd.cover_text("\n".join(page_texts), ut, pages=page_texts)
                if cov < worst_c:
                    worst_k, worst_c = uk, cov
            print(f"    worst unit{worst_k} coverage={worst_c:.2f}")
            if worst_c < 0.85:
                a = norm_al(units[worst_k])
                # find uncovered chunks
                hit = [False] * len(a)
                for ptext in [strip_deep(p) for p in page_texts]:
                    b = norm_al(ptext)
                    if not b:
                        continue
                    for w in vd.windows(b):
                        if not w:
                            continue
                        chunk = w[:40]
                        start = 0
                        while True:
                            i = a.find(chunk, start)
                            if i < 0:
                                break
                            take = min(len(w), len(a) - i)
                            if w[:take] == a[i:i + take]:
                                for k in range(i, i + take):
                                    hit[k] = True
                            start = i + 1
                            if start >= len(a):
                                break
                # longest uncovered runs
                runs, i = [], 0
                while i < len(a):
                    if not hit[i]:
                        j = i
                        while j < len(a) and not hit[j]:
                            j += 1
                        runs.append((i, j))
                        i = j
                    else:
                        i += 1
                runs.sort(key=lambda r: r[1] - r[0], reverse=True)
                print(f"    uncovered runs (top 5 of {len(runs)}):")
                for i0, j0 in runs[:5]:
                    frag = a[i0:j0]
                    print(f"      [{i0}:{j0}] ({j0-i0} ch) …{frag[:110]}…")
                    # locate best fulltext context for this fragment's head
                    head = frag[:35]
                    pos = full_joined.find(head[:12])
                    if pos >= 0:
                        print(f"        fulltext@{pos}: …{full_joined[max(0,pos-40):pos+140]}…")
                    else:
                        pos2 = full_joined.find(frag[: min(12, len(frag))])
                        print(f"        head12 {'FOUND' if pos2>=0 else 'NOT-FOUND'} in joined text")
        else:
            # no units: show what the print gives around the code/name
            for c in codes:
                for pno, b in by_page.items():
                    pass
                # search raw pages
            raw = "\n".join(page_texts)
            for c in codes:
                for m in re.finditer(re.escape(c[:3]) + r"\s?-?\s?" + re.escape(c[3:]), raw):
                    st = raw.rfind("\n", 0, m.start() - 200)
                    en = raw.find("\n", m.end() + 200)
                    seg = raw[max(0, st):en if en > 0 else m.end() + 200]
                    seg = re.sub(r"\n{2,}", "\n", seg)[:600]
                    print(f"    [code {c} @ raw offset {m.start()}]")
                    print("      " + seg.replace("\n", "\n      ")[:600])
                    break  # first occurrence per code


if __name__ == "__main__":
    which = sys.argv[1]
    if which == "08":
        analyze("08_bpharm_scheme-syllabus_2026-27",
                ["Pharmacy Practice", "Scientific Writing", "Bio-similars",
                 "Advanced Pharmacognosy", "Internship", "Research Project",
                 "Professional Skills", "Analytical Method Development",
                 "Pharmaceutical Analysis", "Pharmaceutical Quality Assurance",
                 "Basics of Python", "Human Anatomy, Physiology and Pathophysiology I"])
    elif which == "10":
        analyze("10_bpharm_y1-4_syllabus_2019-20",
                ["COMMUNIUCATION", "HOSPITAL TRAINING", "INDUSTRIAL TRAINING",
                 "PRACTICE SCHOOL", "PROJECT WORK", "INDUSTRIAL TOUR"])
    elif which == "03":
        analyze("03_bca_y1_syllabus_2025-26", ["Sports and Yoga"])
