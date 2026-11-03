#!/usr/bin/env python3
"""fix_draft08_electives.py — post-stitch remediation for draft 08 (BPharm 2026-27).

Evidence (parsed pages, visible print authoritative per RULES §6):
- Appendix table pp.220-221 + detail headers pp.222-295 print each elective as a
  COMPOUND code: slot code + option tag, e.g. "BP212P SEC1", "BP708T AEC4",
  "BP809P VAC3". The bare slot code (BP212P etc.) belongs to the SCHEME SLOT row
  ("SEC* – Elective 1 (Practical)"), exactly as printed in the semester tables.
- The seg-8 subagent recorded appendix electives with the bare slot code; left
  as-is they would (a) collide at G2 (several rows owning BP212P) and (b) be
  merged into the slot row at Tier-0. Fix: rewrite their codes to the printed
  compound form (33 subjects).
- The sem-8 scheme table (p.200) prints slot rows "BP806T AEC* – Elective 7
  (Theory)" and "BP809P VAC* – Elective 8 (Practical)" but seg-8 created no
  subject rows for these two slots (unlike segs 2/3/6/7 for BP212P/BP312P/
  BP607T/BP610P/BP611P/BP708T). Fix: add the two scheme-only slot rows so the
  bare codes are owned exactly once (zero-GAP, one owner per code).
- p.199 detail header prints "BP710RP Research Project" while the sem-8 scheme
  row prints "BP810RP Research Project" — one subject, two printed forms in the
  same document. Fix: own BOTH codes on the single row, keep the mismatch as a
  print quirk (brain clause: determine-then-fix, keep proof).
"""
import json, re, sys

DRAFT = "/home/z/my-project/work/pipeline_v2/drafts/08_bpharm_scheme-syllabus_2026-27.draft.json"

# (slot_code, tag, title-substring) — verbatim from appendix table pp.220-221 /
# detail headers pp.222-295 (segment-8 range).
COMPOUND = [
    ("BP212P", "SEC1", "communication skills"),
    ("BP212P", "SEC2", "mental well-being"),
    ("BP212P", "SEC3", "fundamentals of computer operations"),
    ("BP312P", "AEC1", "nutraceuticals and functional foods"),
    ("BP312P", "AEC2", "food analysis"),
    ("BP312P", "AEC3", "yoga and life sciences"),
    ("BP607T", "AEC1", "green chemistry"),
    ("BP607T", "AEC2", "materiovigilance"),
    ("BP607T", "AEC3", "scientific writing"),
    ("BP607T", "AEC4", "drug store and business management"),
    ("BP607T", "AEC5", "career building in cultivation"),
    ("BP607T", "AEC6", "active pharmaceutical ingredients"),
    ("BP610P", "SEC1", "computer aided drug design"),
    ("BP610P", "SEC2", "analytical method development"),
    ("BP610P", "SEC3", "principles of preclinical studies"),
    ("BP611P", "VAC1", "professional skills"),
    ("BP611P", "VAC2", "process analytical technology"),
    ("BP708T", "AEC1", "cgmp"),
    ("BP708T", "AEC2", "pharmaceutical automation"),
    ("BP708T", "AEC3", "modern techniques in cellular biology"),
    ("BP708T", "AEC4", "medical devices"),
    ("BP708T", "AEC5", "transformation of food waste"),
    ("BP708T", "AEC6", "bio-similars"),
    ("BP708T", "AEC7", "precision medicine"),
    ("BP806T", "AEC1", "pharmaceutical packaging"),
    ("BP806T", "AEC2", "supply chain management"),
    ("BP806T", "AEC3", "industrial safety and waste management"),
    ("BP806T", "AEC4", "traditional healing practices"),
    ("BP806T", "AEC5", "futuristic pharma"),
    ("BP806T", "AEC6", "herbal cosmetics"),
    ("BP809P", "VAC1", "cleaning validation"),
    ("BP809P", "VAC2", "aseptic handling"),
    ("BP809P", "VAC3", "impurity profiling"),
]

SLOT_ROWS = [
    {"name": "AEC* – Elective 7 (Theory)", "name_print": "AEC* – Elective 7 (Theory)",
     "codes": ["BP806T"], "semester": 8, "subject_type": "elective-slot (AEC) — scheme print",
     "units": {}, "experiments": [],
     "flags": ["scheme-only", "detailed_syllabus_not_printed", "elective-slot-row"],
     "quirks": ["Sem-8 scheme row p.200 prints 'BP806T AEC* – Elective 7 (Theory)'; the six "
                "option syllabi print in the appendix/detail pages pp.214,274-289 as compound "
                "codes BP806T AEC1..AEC6 and are recorded as their own subject rows."]},
    {"name": "VAC* – Elective 8 (Practical)", "name_print": "VAC* – Elective 8 (Practical)",
     "codes": ["BP809P"], "semester": 8, "subject_type": "elective-slot (VAC) — scheme print",
     "units": {}, "experiments": [],
     "flags": ["scheme-only", "detailed_syllabus_not_printed", "elective-slot-row"],
     "quirks": ["Sem-8 scheme row p.200 prints 'BP809P VAC* – Elective 8 (Practical)'; the three "
                "option syllabi print in the appendix/detail pages pp.219,290-295 as compound "
                "codes BP809P VAC1..VAC3 and are recorded as their own subject rows."]},
]


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def main():
    d = json.load(open(DRAFT))
    subs = d["subjects"]
    fixed, missed = [], []
    for s in subs:
        codes = s.get("codes", [])
        if len(codes) != 1 or codes[0] not in {c for c, _, _ in COMPOUND}:
            continue
        nm = norm(s.get("name", ""))
        if not nm or "elective" in nm:      # the slot rows keep their bare codes
            continue
        cands = [(sc, tg) for sc, tg, title in COMPOUND if sc == codes[0]
                 and (nm in norm(title) or norm(title) in nm
                      or norm(title)[:18] in nm or nm[:18] in norm(title))]
        if len(cands) == 1:
            sc, tg = cands[0]
            comp = f"{sc} {tg}"
            s["codes"] = [comp]
            s.setdefault("quirks", []).append(
                f"codes recorded as printed compound '{comp}' (appendix table pp.220-221 + detail "
                f"header print); the bare slot code {sc} is owned by the scheme slot row")
            s.setdefault("flags", []).append("elective_compound_code_from_print")
            fixed.append(f"{comp}:{s.get('name','')[:36]}")
        elif len(cands) > 1:
            missed.append(f"AMBIG {s.get('name','')[:40]} -> {cands}")
        else:
            missed.append(f"NOMATCH {s.get('name','')[:40]} ({codes[0]})")

    # BP710RP / BP810RP mismatch: one subject owns both printed forms
    for s in subs:
        if "BP710RP" in [c.upper() for c in s.get("codes", [])]:
            if "BP810RP" not in [c.upper() for c in s["codes"]]:
                s["codes"].append("BP810RP")
                s.setdefault("quirks", []).append(
                    "code print mismatch inside the same document: detail header p.199 prints "
                    "'BP710RP Research Project' while the sem-8 scheme row p.200 prints "
                    "'BP810RP Research Project' — both printed forms owned by this one row")
                fixed.append("BP710RP+BP810RP")

    # add the two missing sem-8 slot rows
    have = {tuple(sorted(norm(c) for c in s.get("codes", []))) for s in subs}
    added = []
    for row in SLOT_ROWS:
        key = tuple(sorted(norm(c) for c in row["codes"]))
        if key not in have:
            row = dict(row)
            row.setdefault("name", row["codes"][0])
            subs.append(row)
            added.append(row["codes"][0])

    json.dump(d, open(DRAFT, "w"), ensure_ascii=False, indent=1)
    print(f"FIX08|compound_fixed={len(fixed)} slot_rows_added={added} issues={missed}")
    for f in fixed:
        print("  ", f)
    for m in missed:
        print("  !!", m)
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main())
