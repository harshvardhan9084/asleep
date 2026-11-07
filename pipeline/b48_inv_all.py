#!/usr/bin/env python3
"""b48_inv_all.py — B48 inventory pre-seed + validation (B43/B45/B47 lesson).

Runs engine.inventory() per doc (if not cached), saves the inv cache, then
cross-checks every code_print against a fulltext code-token scan. Junk class
(B47: docs 01/04 on small/older MCA books) = low found-ratio -> prints JUNK
and leaves the cache for hand-rebuild. Never extracts.

Usage: python3 b48_inv_all.py [<stem> ...]   (default: all 10 B48 stems)
"""
import json, os, re, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as E

PARSED = "/home/z/my-project/work/pipeline_v2/parsed"
INVD = "/home/z/my-project/work/pipeline_v2/inv"
STEMS = [
    "01_mca_y2_syllabus_2025-26",
    "02_mca_y3_syllabus_2010-11",
    "03_mca_y3_syllabus_2015-16",
    "04_mca_y3_syllabus_2018-19",
    "05_mca_y5_syllabus_2021-22",
    "06_bpharm_syllabus",
    "07_bpharm_y3_scheme-syllabus-cbcs-rev",
    "08_bpharm_y4_syllabus",
    "09_btech_ae_y4_syllabus_2016-17",
    "10_btech_ag_syllabus",
]

CODE_RE = re.compile(r"[A-Z]{2,4}[0-9]{2,3}[A-Z]?")


def fulltext(stem):
    return open(f"{PARSED}/{stem}.fulltext.txt", encoding="utf-8").read()


def validate(stem, subs):
    ft = fulltext(stem)
    toks = set(CODE_RE.findall(ft))
    n_ok = 0
    for s in subs:
        cp = re.sub(r"[^A-Za-z0-9*]", "", s.get("code_print", ""))
        if not cp or "*" in cp:
            n_ok += 1  # slot prints are validated by print, not token scan
            continue
        m = re.match(r"([A-Z]{2,4})([0-9]{2,3})([A-Z]?)", cp)
        if m and (m.group(1) + m.group(2)) in toks:
            n_ok += 1
    ratio = n_ok / len(subs) if subs else 0.0
    return ratio


def main():
    stems = sys.argv[1:] or STEMS
    os.makedirs(INVD, exist_ok=True)
    bad = []
    for stem in stems:
        INVP = f"{INVD}/{stem}.inv.json"
        if os.path.exists(INVP):
            try:
                subs = json.load(open(INVP))
                if subs:
                    r = validate(stem, subs)
                    print(f"INV|{stem}|{len(subs)} cached|ratio={r:.2f}"
                          + ("|JUNK" if r < 0.8 else ""))
                    if r < 0.8:
                        bad.append(stem)
                    continue
            except Exception:
                pass
        rec = json.load(open(f"{PARSED}/{stem}.json"))
        meta = rec.get("meta", rec)
        pdf_name = meta.get("file", stem + ".pdf")
        session, course = "", "BTech"
        qe = E.queue_meta_for(stem, {"pdf_path": pdf_name})
        if qe:
            session = qe.get("session", "") or ""
            course = qe.get("course", "") or "BTech"
        inv, subs = E.inventory(pdf_name, fulltext(stem), session, course)
        json.dump(subs, open(INVP, "w"), indent=1, ensure_ascii=False)
        r = validate(stem, subs)
        nd = sum(1 for s in subs if s.get("class") == "detail")
        print(f"INV|{stem}|{len(subs)} (detail {nd}, scheme_only {len(subs)-nd})|ratio={r:.2f}"
              + ("|JUNK" if r < 0.8 else ""), flush=True)
        if r < 0.8:
            bad.append(stem)
    print("INV_BAD|" + (",".join(bad) if bad else "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
