#!/usr/bin/env python3
"""Fix batch03 draft 03_bpharm_scheme-syllabus_2026-27 after verify_draft.py hard failures.

Investigations performed (CRON-20261027-B03):
1. HARD CONTAIN — BP103T book #7: PDF text layer dropped the first line of the printed
   entry ("7. Park, K., Park's Textbook of Preventive and Social Medicine. Banarsidas
   Bhanot" is an invisible/oddly-encoded text run; only "7." and "Publishers, Jabalpur."
   landed in the text layer). Page-15 IMAGE (150 dpi,
   work/pipeline_v2/qa_b03_p15_bp103t_books.png) shows the FULL visible entry.
   Visible print is authoritative (RULES.md §8) → restore the true printed text via
   brain_fix with page-image evidence recorded.
2. HARD GAP ×4 — CYP450, IMDR2017, ISO13485, ISO14000 are NOT subject codes: they are
   biology/standards/regulation references printed inside unit texts. Add quirks entries
   with pages (detection noise), per draft_prompt.md method step 2.
"""
import json

DRAFT = '/home/z/my-project/work/pipeline_v2/drafts/03_bpharm_scheme-syllabus_2026-27.draft.json'

d = json.load(open(DRAFT))

# --- Fix 1: BP103T book #7 (lives in reference_books, not textbooks) ---
fixed_books = 0
for s in d['subjects']:
    if s.get('primary_code') == 'BP103T':
        for tb in s.get('reference_books', []):
            if 'Publishers, Jabalpur' in tb.get('text_print', '') and 'Park' not in tb.get('text_print', ''):
                tb['text_print'] = ("Park, K., Park's Textbook of Preventive and Social Medicine. "
                                    'Banarsidas Bhanot Publishers, Jabalpur.')
                fixed_books += 1
        s.setdefault('brain_fixes', []).append({
            'field': 'textbooks[7].text_print',
            'print': '[text-layer dropped entry: "7." + blank + "Publishers, Jabalpur."]',
            'corrected': "Park, K., Park's Textbook of Preventive and Social Medicine. Banarsidas Bhanot Publishers, Jabalpur.",
            'reason': ('PDF text layer dropped the first line of printed item 7 (invisible text run); '
                       'page-15 image (qa_b03_p15_bp103t_books.png) shows the full visible entry. '
                       'Visible print is authoritative per RULES.md §8/§1.6.'),
        })
        s.setdefault('quirks', [])  # placeholder if quirks live per-subject as list of str
        s.setdefault('notes', []).append(
            'print_quirk: BP103T book item 7 first line is invisible in the PDF text layer; '
            'text restored from the page-15 image (visible print authoritative).')
print('BP103T books fixed:', fixed_books)

# --- Fix 2: noise-code quirks ---
noise_quirks = [
    'detection_noise: CYP450 is not a subject code — "CYP450 enzymes" (genetic polymorphisms) printed inside Pharmacogenomics CO/unit text, pages 272-273.',
    'detection_noise: IMDR2017 is not a subject code — "IMDR 2017" (Indian Medical Device Regulation) cited inside elective unit III/IV text (Manufacturing and Quality Systems / Regulatory Affairs), page 266.',
    'detection_noise: ISO13485 is not a subject code — "ISO 13485" medical-device quality standard cited inside CO-3/unit text and book #10, pages 265-267.',
    'detection_noise: ISO14000 is not a subject code — "ISO-14000" environmental standard printed as a unit topic (Government initiatives block, page 70) and unit topic "ISO 9000 and ISO 14000" (page 137).',
]
added = 0
for q in noise_quirks:
    if q not in d['quirks']:
        d['quirks'].append(q)
        added += 1
print('noise quirks added:', added)

json.dump(d, open(DRAFT, 'w'), indent=1, ensure_ascii=False)
print('draft rewritten:', DRAFT)
