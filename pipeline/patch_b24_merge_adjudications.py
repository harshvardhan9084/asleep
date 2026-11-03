#!/usr/bin/env python3
"""patch_b24_merge_adjudications.py — B24 evidence-recorded merge adjudications.

Doc07 printed-code conflicts (RULES §6: visible print is authoritative; the
doc itself carries copy-paste typos — adjudicated to the 2-vs-1 print
consensus, typos kept as quirk evidence):
  ::02 DBMS        page p.7 header 'Database Management System (KECZ-503)' +
                   DE-II pool print (KECZ-503) vs p.2 scheme table which
                   duplicates KECZ-502 on BOTH the DSP row and the DBMS row
                   (printed duplicate-code typo) -> codes=[KECZ-503].
  ::06 OCS         p.2 table + DE-I pool print KECZ-053; the p.11 subject-page
                   header duplicates KECZ-054 (copy-paste of the preceding
                   ADD-V page, whose p.10 header correctly prints KECZ-054)
                   -> codes=[KECZ-053].
  ::12 DSP Lab     p.19 header 'KECZ-552 / DIGITAL SIGNAL PROCESSING LAB' +
                   pool 'Database Management Systems Lab (KECZ-553)' vs the
                   p.2 table which swaps the two lab names -> codes=[KECZ-552].
  ::13 DBMS Lab    p.20 header 'Database Management Systems Lab (KECZ-553)'
                   (same table-swap evidence) -> codes=[KECZ-553].
  The four needs_review flags are adjudicated (RULES §4 brain clause:
  evidence conclusive — determine-then-fix, keep proof in quirks).
"""
import json, sys

D = "/home/z/my-project/work/pipeline_v2/drafts"

FIXES = {
    "07_btech_electronics-computer_y3_syllabus_2021-22": {
        2: ("KECZ-503",
            "Code adjudication (recorded B24 merge evidence): the p.2 scheme "
            "table prints KECZ-502 on BOTH the Digital Signal Processing row "
            "and this DBMS row (printed duplicate-code typo); the subject page "
            "p.7 header 'Database Management System (KECZ-503)' and the DE-II "
            "pool list print KECZ-503 — 2-vs-1 print consensus, codes pinned "
            "to KECZ-503; the duplicate table print kept here as quirk "
            "evidence (RULES §4/§6)."),
        6: ("KECZ-053",
            "Code adjudication (recorded B24 merge evidence): p.2 scheme "
            "table and DE-I pool print KECZ-053 for Optical Communication "
            "System; the p.11 subject-page header duplicates KECZ-054 "
            "(copy-paste of the preceding ADD-V page, whose p.10 header "
            "correctly prints KECZ-054) — codes pinned to KECZ-053; the "
            "duplicate page-header print kept as quirk evidence (RULES §4/§6)."),
        12: ("KECZ-552",
             "Code adjudication (recorded B24 merge evidence): p.19 subject-"
             "page header 'KECZ-552 / DIGITAL SIGNAL PROCESSING LAB' + pool "
             "print 'Database Management Systems Lab (KECZ-553)' vs the p.2 "
             "table which swaps the two V-sem lab names — 2-vs-1 consensus, "
             "codes pinned to KECZ-552; the swapped table print kept as quirk "
             "evidence (RULES §4/§6)."),
        13: ("KECZ-553",
             "Code adjudication (recorded B24 merge evidence): p.20 subject-"
             "page header 'Database Management Systems Lab (KECZ-553)' + pool "
             "print vs the p.2 table which swaps the two V-sem lab names — "
             "2-vs-1 consensus, codes pinned to KECZ-553; the swapped table "
             "print kept as quirk evidence (RULES §4/§6)."),
    },
}


def main():
    n = 0
    for stem, fixes in FIXES.items():
        path = f"{D}/{stem}.draft.json"
        d = json.load(open(path))
        for idx, (code, quirk) in fixes.items():
            s = d["subjects"][idx]
            s["codes"] = [code]
            s["quirks"] = [q for q in (s.get("quirks") or [])]
            s["quirks"].append(quirk)
            fl = [f for f in (s.get("flags") or [])
                  if not str(f).startswith("needs_review")]
            s["flags"] = fl
            n += 1
        json.dump(d, open(path, "w"), indent=1, ensure_ascii=False)
    print(f"PATCHED|doc07_code_adjudications={n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
