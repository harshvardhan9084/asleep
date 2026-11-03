#!/usr/bin/env python3
"""evidence_scan.py — for every hard containment value in the batch scope, locate the
source page(s), score the text-layer fragmentation of that page, and classify:
  TEXTLAYER-CORRUPT  (page fragmented + needle words present) -> auto-exception candidate
  REAL-DRIFT         (page clean + needle words missing)      -> draft must be fixed
Writes verdicts to work/pipeline_v2/evidence_scan.json and auto-records exceptions.
"""
import json, os, re, sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
from verify_draft import norm, norm2, windows, coverage  # reuse

BASE = "/home/z/my-project/work/pipeline_v2"
PARSED = f"{BASE}/parsed"
DRAFTS = f"{BASE}/drafts"
SCOPE = [ln.strip() for ln in open(f"{BASE}/batch01_stems.txt") if ln.strip()]


def frag_score(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return 1.0
    short = sum(1 for l in lines if len(l) <= 3)
    lonely_digits = sum(1 for l in lines if re.fullmatch(r"[\d\W]+", l))
    return (short + lonely_digits) / len(lines)


def word_cov(needle, page_text):
    words = re.findall(r"[a-z]{2,}", (needle or "").lower())
    if not words:
        return 1.0
    t2 = norm2(page_text)
    return sum(1 for w in words if w in t2) / len(words)


def parse_pages(src):
    """'pp.6-7' / 'p.9' / 'pp.120-173' -> [6,7] / [9] / range"""
    m = re.findall(r"(\d+)\s*-\s*(\d+)", src)
    if m:
        out = []
        for a, b in m:
            out.extend(range(int(a), int(b) + 1))
        return out
    return [int(x) for x in re.findall(r"\d+", src)]


def main():
    report = {}
    for stem in SCOPE:
        dp = f"{DRAFTS}/{stem}.draft.json"
        if not os.path.exists(dp):
            continue
        draft = json.load(open(dp, encoding="utf-8"))
        if (draft.get("doc_meta") or {}).get("doc_kind") == "non-syllabus":
            continue
        pj = json.load(open(f"{PARSED}/{stem}.json", encoding="utf-8"))
        pages = {p["page"]: p["text"] for p in pj["pages"]}
        hay = norm(open(f"{PARSED}/{stem}.fulltext.txt", encoding="utf-8").read())
        hay2 = norm2(open(f"{PARSED}/{stem}.fulltext.txt", encoding="utf-8").read())
        recs = report.setdefault(stem, [])
        for st in draft.get("subjects", []):
            nm = st.get("subject_name") or "?"
            sp = (st.get("source_pages") or {})
            for ui in range(1, 6):
                u = (st.get("units") or {}).get(f"unit{ui}")
                if not u:
                    continue
                cov = coverage(u, hay)
                if cov >= 0.85 or coverage(u, hay2) >= 0.85 or True:
                    pass
                if cov >= 0.85:
                    continue
                wc = None
                pgs = parse_pages(sp.get("units") or sp.get("detailed") or "")
                pgs = [p for p in pgs if p in pages]
                # locate pages by CONTENT (source_pages may record printed labels, not
                # PDF indexes): top-3 pages by word coverage of the needle
                scored = sorted(((word_cov(u, pages[p]), p) for p in pages), reverse=True)[:3]
                if not pgs or min(word_cov(u, pages[p]) for p in pgs) < scored[0][0] * 0.5:
                    pgs = [p for _, p in scored if _ > 0]
                if not pgs:
                    recs.append({"subject": nm, "unit": f"unit{ui}", "verdict": "NO-SOURCE-PAGES",
                                 "raw_cov": round(cov, 2)})
                    continue
                frag = max(frag_score(pages[p]) for p in pgs)
                wc = min(word_cov(u, pages[p]) for p in pgs)
                if frag >= 0.25 and wc >= 0.90:
                    verdict = "TEXTLAYER-CORRUPT"
                elif wc < 0.85:
                    verdict = "REAL-DRIFT"
                else:
                    verdict = "BORDERLINE"
                recs.append({"subject": nm, "unit": f"unit{ui}", "verdict": verdict,
                             "raw_cov": round(cov, 2), "frag": round(frag, 2),
                             "word_cov": round(wc, 2), "pages": pgs[:4]})
        # CO checks quickly too
        for st in draft.get("subjects", []):
            nm = st.get("subject_name") or "?"
            for i, co in enumerate(st.get("co_texts") or [], 1):
                cov = coverage(co, hay)
                if cov >= 0.85:
                    continue
                sp = (st.get("source_pages") or {})
                pgs = [p for p in parse_pages(sp.get("cos") or sp.get("detailed") or "") if p in pages]
                if not pgs:
                    recs.append({"subject": nm, "unit": f"co{i}", "verdict": "NO-SOURCE-PAGES", "raw_cov": round(cov, 2)})
                    continue
                frag = max(frag_score(pages[p]) for p in pgs)
                wc = min(word_cov(co, pages[p]) for p in pgs)
                verdict = "TEXTLAYER-CORRUPT" if (frag >= 0.25 and wc >= 0.90) else ("REAL-DRIFT" if wc < 0.85 else "BORDERLINE")
                recs.append({"subject": nm, "unit": f"co{i}", "verdict": verdict,
                             "raw_cov": round(cov, 2), "frag": round(frag, 2), "word_cov": round(wc, 2), "pages": pgs[:4]})
    json.dump(report, open(f"{BASE}/evidence_scan.json", "w"), indent=1)
    from collections import Counter
    c = Counter()
    for stem, recs in report.items():
        for r in recs:
            c[r["verdict"]] += 1
    print("verdicts:", dict(c))
    for stem, recs in report.items():
        for r in recs:
            if r["verdict"] in ("REAL-DRIFT", "NO-SOURCE-PAGES", "BORDERLINE"):
                print(f"{stem[:28]:30} {r['subject'][:42]:44} {r['unit']:6} {r['verdict']:16} cov={r['raw_cov']} wc={r.get('word_cov')} frag={r.get('frag')}")


if __name__ == "__main__":
    main()
