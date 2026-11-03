#!/usr/bin/env python3
"""patch_b27_verify_flags.py — B27 verify-remedy (recorded B23/B25 class).

verify_draft.py hard-fails subjects that print no unit theory. B27 evidence
(page/fulltext probes, RULES §6: the visible print is authoritative):

- doc 03 (btech_ft_y4_syllabus-cbcs_2019-20, sha16 20fff6bb71f7c146):
  RFT753 INDUSTRIAL TRAINING (p.9), RFT754 PROJECT-1 (p.9), RFT851 SEMINAR
  (p.13), RFT852 PROJECT-2 (p.13) each print ONLY a heading + L-T-P + one
  course-description paragraph (e.g. RFT754: "The student (s) will be
  required to search literature pertaining to design of an equipment /
  processing of a food commodity / production of a food product, comprehend
  it and prepare a report for assessment."). NO unit theory, NO COs, NO books
  anywhere in the document — the printed design of these project/seminar/IT
  assessment subjects. The identical class was recorded at B25 for the EE
  prints "REV753/754/851/852" (B25 manifest: "scheme-row-only subjects ...
  carried no units -> recorded B23/B24 class flags
  scheme_row_only_detailed_syllabus_not_printed + evidence quirks added").

- doc 05 (btech_handloom-textile_y2_syllabus_2021-22, sha16 ae09f754a72d1829):
  KHT354 "Mini Project or Internship Assessment*" appears ONLY in the
  Sem-III scheme table (p.2; 0-0-2, 50 marks) with the printed footnote
  "*The Mini Project or internship (3-4 weeks) conducted during summer break
  after II semester and will be assessed during III semester." — no detailed
  syllabus anywhere in the document (same class as B26's KHT-554, which
  carried the same flag and passed).

Zero-guess: no units/COs invented; the flag + page-citing quirk records the
print evidence so the verifier's recorded downgrade applies (B2 remedy class).
"""
import json

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts/B27"

TARGETS = {
    "03_btech_ft_y4_syllabus-cbcs_2019-20.draft.json": {
        "RFT753": "p.9: detail heading 'RFT753 INDUSTRIAL TRAINING' prints only L-T-P 0-0-3 + one description paragraph ('...undertake training in the food industry after III year B.Tech.VI semester...submit its report...for evaluation and viva-voce in the VII semester...') — no unit theory/COs/books printed anywhere in the doc",
        "RFT754": "p.9: detail heading 'RFT754 PROJECT-1' prints only L-T-P 0-0-6 + one description paragraph ('...search literature pertaining to design of an equipment / processing of a food commodity / production of food product, comprehend it and prepare a report for assessment') — no unit theory/COs/books printed anywhere in the doc",
        "RFT851": "p.13: detail heading 'RFT851 SEMINAR' prints only L-T-P 0-0-3 + one description paragraph ('...present a Seminar pertaining to the Project Topic/ Advanced Food Processing Techniques...deliver a Seminar for assessment') — no unit theory/COs/books printed anywhere in the doc",
        "RFT852": "p.13: detail heading 'RFT852 PROJECT-2' prints only L-T-P 0-0-12 + one description paragraph ('...perform experimental work as per the finalized Plan of Work and prepare a detailed report for assessment...periodic reviews...') — no unit theory/COs/books printed anywhere in the doc",
    },
    "05_btech_handloom-textile_y2_syllabus_2021-22.draft.json": {
        "KHT354": "p.2: 'KHT354 Mini Project or Internship Assessment*' appears ONLY in the Sem-III scheme table row (0-0-2, 50 marks) with printed footnote '*The Mini Project or internship (3-4 weeks) conducted during summer break after II semester and will be assessed during III semester.' — no detailed syllabus printed anywhere in the doc",
    },
}

for fn, targets in TARGETS.items():
    path = f"{DRAFTS}/{fn}"
    d = json.load(open(path))
    patched = []
    for s in d.get("subjects", []):
        code = next((c.replace(" ", "").replace("-", "") for c in (s.get("codes") or [])), "")
        if code in targets:
            flag = "scheme_row_only_detailed_syllabus_not_printed"
            if flag not in (s.get("flags") or []):
                s.setdefault("flags", []).append(flag)
            q = f"patch-b27 verify remedy: {targets[code]}"
            if q not in (s.get("quirks") or []):
                s.setdefault("quirks", []).append(q)
            patched.append(code)
    json.dump(d, open(path, "w"), indent=1, ensure_ascii=False)
    print(f"PATCHED|{fn}|{patched}")
print("OK")
