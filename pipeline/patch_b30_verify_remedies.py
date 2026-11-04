#!/usr/bin/env python3
"""patch_b30_verify_remedies.py — B30 doc-07 verify remedies (RULES §6, recorded classes).

Evidence: page images of work/pipeline_v2/staging/batch30/07_btech_mfg-tech_syllabus_2010-11.pdf
- p.6 (EMT-501 Design of Machine Elements): per-unit lecture-hour digits (7/8/10/8/8)
  print as a separate RIGHT-MARGIN column value between each unit heading and its
  body — the text layer emits them as standalone digit lines that strip_furniture_deep
  removes haystack-side while the needle keeps them, so short needles (≤70 norm chars)
  hit cover_text's early-return path without the bigram fallback → false 0.00
  containment. Remedy (B28 doc-04 marker-hygiene class): move the hour digits to the
  subject quirk, unit text kept verbatim-only (heading+prose).
- pp.20-21 (EMT-032 Advanced Metrology and Measurement): the subagent's bracketed
  annotation tails leaked into every unit text (chopped "[hour marker (6) printed
  before unit body...]" fragments; U3 "[no hour marker printed]") — draft-side
  annotation leak, NOT print (page image shows unit bodies end at the prose).
  Remedy (B28 draft-side annotation hygiene class): strip the leaked tails from unit
  texts; the hour-marker/attribution evidence stays in the subject quirk.
"""
import json, re

P = '/home/z/my-project/work/pipeline_v2/drafts/07_btech_mfg-tech_syllabus_2010-11.draft.json'
d = json.load(open(P))

changed = []

for s in d['subjects']:
    name = s.get('name', '')

    # ---- EMT-032 Advanced Metrology and Measurement: strip leaked annotation tails
    if 'advanced metrology' in name.lower():
        for uk, ut in list(s.get('units', {}).items()):
            # leak = bracketed annotation anchored at the unit-text end:
            # '[hour marker (6) printed ...]', '[hour markers (6) and (10) ...]',
            # '[no hour marker printed]' (chopped-looking reprs are '[h'+'our')
            m = re.search(r"\s*\[(?:hour markers?|no hour marker) [^\]]*\]\s*$", ut)
            if m:
                new = ut[:m.start()].rstrip()
                s['units'][uk] = new
                changed.append(f'EMT-032 U{uk}: stripped annotation tail ({len(ut)-len(new)} ch)')
        # refresh the hour-marker quirk wording (evidence preserved, no longer "in unit")
        for i, q in enumerate(s.get('quirks', [])):
            if 'per-unit hour attribution ambiguous, markers noted in unit' in q:
                s['quirks'][i] = q.replace(
                    'per-unit hour attribution ambiguous, markers noted in unit',
                    'per-unit hour attribution ambiguous; the parenthesised hour markers are '
                    'NOT unit prose — recorded here, unit texts kept verbatim-only (p.20-21 '
                    'page-image attested; B28 doc-04 marker-hygiene class)')
        s['flags'] = list(dict.fromkeys((s.get('flags') or []) + ['unit_table_interleave_print']))
        s.setdefault('quirks', []).append(
            "patch-b30: bracketed draft-side annotation tails that had leaked into the unit "
            "texts (hour-marker notes) were stripped to keep unit text verbatim-only; the "
            "evidence remains in the quirks above; hour markers (6)/(8)/(6)/(10)/(10)/(10) "
            "print as right-margin column values at inconsistent positions per the p.20-21 "
            "page images (visible print authoritative, RULES §6).")

    # ---- EMT-501 Design of Machine Elements: move right-margin hour digits out of unit text
    if 'design of machine elements' in name.lower() and 'lab' not in name.lower():
        hours = {}
        for uk, ut in list(s.get('units', {}).items()):
            lines = ut.split('\n')
            keep = [l for l in lines if re.fullmatch(r"\s*\d{1,3}\s*", l) is None]
            digits = [l.strip() for l in lines if re.fullmatch(r"\s*\d{1,3}\s*", l) is not None]
            if digits:
                hours[uk] = digits
                s['units'][uk] = '\n'.join(keep).strip()
                changed.append(f'EMT-501 U{uk}: moved hour digits {digits} to quirk')
        if hours:
            s.setdefault('quirks', []).append(
                "patch-b30: the per-unit lecture-hour digits (" +
                ", ".join(f"U{uk}: {'/'.join(v)}" for uk, v in sorted(hours.items())) +
                ") print as a separate right-margin column value between each unit heading and "
                "its body on p.6 (page-image attested; visible print authoritative, RULES §6); "
                "they were transcribed into the unit texts and broke short-needle containment "
                "after haystack-side digit-line furniture stripping — moved to this quirk, unit "
                "texts kept verbatim-only (B28 doc-04 marker-hygiene class).")

json.dump(d, open(P, 'w'), ensure_ascii=False, indent=1)
print('\n'.join(changed) if changed else 'NO CHANGES')
