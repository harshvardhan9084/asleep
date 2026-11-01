#!/usr/bin/env python3
"""patch_b24_verify_flags.py — B24 evidence-recorded verify remedies.

Classes (all with printed evidence, RULES §6 zero-guess):
1. scheme_row_only_detailed_syllabus_not_printed — 7 subjects across docs
   04/09/10 print ONLY scheme-table rows (code + L-T-P + marks); no detailed
   section exists anywhere in the document (page-range evidence recorded per
   doc). Recorded B23 class ("59 scheme-row-only -> detailed_syllabus_not_printed").
2. doc06 BEE652 Microprocessor Lab — the printed doc uses the recorded
   two-list convention (B23 doc-08/09 evidence): main list 1-14 + 'PART B
   SUGGESTIVE LIST OF EXPERIMENTS (Through Virtual Lab Link)' 1-10 RESTART.
   The first extraction pass carried PART-B only inside a quirk string, so the
   scheme-line token RS232 (PART-B item 10 print, p.35) failed the GAP check.
   Remedy: append the 10 PART-B items VERBATIM (printed nos 1-10 restart kept,
   list marker recorded) — same repair as the B23 BEE652 recovery.
"""
import json, os, sys

D = "/home/z/my-project/work/pipeline_v2/drafts"

SCHEME_ONLY = {
    "04_btech_ei_y4_syllabus-cbcs_2019-20": ["RIC753", "RIC754", "RIC851", "RIC852"],
    "09_btech_electronics-computer_y4_syllabus-rev_2022-23": ["KECZ-751C"],
    "10_btech_electronics-computer_y4_syllabus_2025-26": ["BECZ752", "BECZ753"],
}

PART_B = [
    (1, "Write a program using 8085 Microprocessor for Decimal, Hexadecimal addition and subtraction of two Numbers. (Through Virtual Lab Link)."),
    (2, "Write a program using 8085 Microprocessor for addition and subtraction of two BCD numbers. (Through Virtual Lab Link)"),
    (3, "To perform multiplication and division of two 8 bit numbers using 8085. (Through Virtual Lab Link)"),
    (4, "To find the largest and smallest number in an array of data using 8085 instruction set."),
    (5, "To write a program using 8086 to arrange an array of data in ascending and descending order. (Through Virtual Lab Link)"),
    (6, "To convert given Hexadecimal number into its equivalent ASCII number and vice versa using 8086 instruction set."),
    (7, "To convert given Hexadecimal number into its equivalent BCD number and vice versa using 8086 instruction set."),
    (8, "To interface 8253 programmable interval timer and verify the operation of 8253 in six different modes."),
    (9, "To write a program to initiate 8251 and to check the transmission and reception of character."),
    (10, "Serial communication between two 8085 through RS-232 C port."),
]


def norm(c):
    return c.replace("-", "").upper()


def main():
    n_flag = n_exp = 0
    for stem, codes in SCHEME_ONLY.items():
        path = f"{D}/{stem}.draft.json"
        d = json.load(open(path))
        want = {norm(c) for c in codes}
        for s in d["subjects"]:
            sc = {norm(c) for c in s.get("codes", [])}
            if sc & want:
                fl = s.setdefault("flags", [])
                tag = "scheme_row_only_detailed_syllabus_not_printed"
                if tag not in fl:
                    fl.append(tag)
                    s.setdefault("quirks", []).append(
                        "Scheme-row-only subject: printed ONLY in the scheme table "
                        "(code + L-T-P + marks row); no detailed syllabus section "
                        "printed anywhere in this document — flag recorded, not a "
                        "draft omission (B23 recorded class).")
                    n_flag += 1
        json.dump(d, open(path, "w"), indent=1, ensure_ascii=False)
    # doc06 BEE652 PART-B
    path = f"{D}/06_btech_electrical-computer_y3_syllabus_2024-25.draft.json"
    d = json.load(open(path))
    for s in d["subjects"]:
        if s.get("name") == "Microprocessor Lab" and "BEE652" in {norm(c) for c in s.get("codes", [])}:
            exps = s.setdefault("experiments", [])
            have = {norm(e.get("exp", ""))[:30] for e in exps}
            for no, txt in PART_B:
                if norm(txt)[:30] in have:
                    continue
                exps.append({"no": no, "exp": txt,
                             "list": "PART B SUGGESTIVE LIST OF EXPERIMENTS (Through Virtual Lab Link)"})
                n_exp += 1
            s.setdefault("quirks", []).append(
                "Two-list convention (recorded B23 BEE652/KEE651-652 class): main list "
                "prints nos 1-14; 'PART B SUGGESTIVE LIST OF EXPERIMENTS (Through Virtual "
                "Lab Link)' prints nos 1-10 RESTART (pp.34-35; item 10 = RS-232 C port "
                "serial communication). PART-B items carried as experiments with their "
                "printed restart numbering + list marker.")
    json.dump(d, open(path, "w"), indent=1, ensure_ascii=False)
    print(f"PATCHED|scheme_only_flags={n_flag}|partb_experiments={n_exp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
