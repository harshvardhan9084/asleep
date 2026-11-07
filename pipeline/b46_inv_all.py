#!/usr/bin/env python3
"""b46_inv_all.py — B46 inventory pre-seed + validation (B43/B45 lesson).

Runs engine.inventory() per doc (if not cached), saves the inv cache, then
cross-checks every code_print against a fulltext code-token scan. Junk class
(B45: doc 05 2/19 codes, doc 10 1/37 codes) = low found-ratio -> prints JUNK
and leaves the cache for hand-rebuild. Never extracts.
"""
import json, os, re, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as E

PARSED = "/home/z/my-project/work/pipeline_v2/parsed"
INVD = "/home/z/my-project/work/pipeline_v2/inv"
STEMS = [
    "01_mba_y2_syllabus_2013-14",
    "02_mca-dd_y4-5_syllabus_2016-17",
    "03_mca-integrated_y1_scheme-syllabus_2017-18",
    "04_mca-integrated_y1_syllabus_2024-25",
    "05_mca-integrated_y2_syllabus_2018-19",
    "06_mca-integrated_y2_syllabus_2025-26",
    "07_mca-integrated_y3_syllabus-cbcs_2019-20",
    "08_mca-integrated_y3_syllabus_2026-27",
    "09_mca-integrated_y4_syllabus_2020-21",
    "10_mca_non-credit-bridge-elementary-maths-syllabus_2024-25",
]

CODE_RE = re.compile(r"[A-Z]{2,4}[0-9]{2,3}[A-Z]?")


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def main():
    os.makedirs(INVD, exist_ok=True)
    report = []
    for stem in STEMS:
        invp = f"{INVD}/{stem}.inv.json"
        fulltext = open(f"{PARSED}/{stem}.fulltext.txt", encoding="utf-8").read()
        nhay = norm(fulltext)
        rec = json.load(open(f"{PARSED}/{stem}.json"))
        meta = rec.get("meta", rec)
        pdf_name = meta.get("file", stem + ".pdf")
        q = json.load(open("/home/z/my-project/work/pipeline_v2/queue.json"))
        session, course = "", "BTech"
        for e in q["entries"]:
            if os.path.basename(e["rel"]) in (os.path.basename(pdf_name), stem + ".pdf",
                                              re.sub(r"^\d+_", "", stem) + ".pdf"):
                session, course = e.get("session", ""), e.get("course", "BTech")
                break
        if os.path.exists(invp):
            try:
                subs = json.load(open(invp))
                print(f"INVENTORY|{stem}|{len(subs)} (cached)")
            except Exception:
                subs = None
        else:
            inv, subs = E.inventory(pdf_name, fulltext, session, course)
            json.dump(subs, open(invp, "w"), indent=1, ensure_ascii=False)
            print(f"INVENTORY|{stem}|{len(subs)} (fresh; title={inv.get('doc_title_print','')[:60]!r})")
        # validation: code-token scan
        tot = found = 0
        missing = []
        detail = sum(1 for s in subs if s.get("class") == "detail")
        scheme_only = len(subs) - detail
        for s in subs:
            cp = norm(s.get("code_print", ""))
            codes = CODE_RE.findall(cp)
            if not codes:
                continue
            tot += 1
            if any(c in nhay for c in codes):
                found += 1
            else:
                missing.append(s.get("code_print", ""))
        ratio = (found / tot) if tot else 1.0
        junk = tot >= 3 and ratio < 0.5
        report.append((stem, len(subs), detail, scheme_only, tot, found, round(ratio, 2),
                       "JUNK" if junk else "ok"))
        print(f"VALID|{stem}|codes_scanned={tot} found={found} ratio={ratio:.2f} "
              f"detail={detail} scheme_only={scheme_only} -> {'JUNK' if junk else 'ok'}")
        if missing:
            print(f"  missing: {', '.join(missing[:12])}")
    print("\n=== SUMMARY ===")
    for r in report:
        print("|".join(str(x) for x in r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
