#!/usr/bin/env python3
"""Restructure batch03 draft 10 (generic B.Tech first-year course-structure) — CRON-20261027-B03 adjudication.

EVIDENCE (doc 10's own prints, sha16 6149e0397e06f2f2):
- Semester tables (p2, p7) print umbrella lines with UNSUFFIXED family codes:
  'AAS101/ AAS102 | Applied Physics/ Applied Chemistry (Both are Stream Specific)';
  'AAS203 | Applied Mathematics-II (Stream Specific)'.
- Stream tables (p3-5, p9-10) print stream-variant subjects with DISTINCT names per code:
  AAS101A 'Physics for Sustainable Structural Systems (CE stream)' ...
  AAS101I 'Physics of Fibres and Textile Materials (Textile Engineering stream)';
  AAS102A-H distinct chemistry titles; AAS103A-H / AAS203A-H distinct maths titles;
  AEE101A-C / AEC101A-C / AME101A-D / ACE151A-I all share ONE identical name per family.

ADJUDICATION (recorded reasoning, zero-guess):
1. Same-name families (AEE/AEC/AME/ACE + all '(Common to all)' subjects) = ONE subject,
   many codes (RULES.md §3) — draft already correct, no change.
2. Distinct-name stream variants = DISTINCT subjects (ladder §4 Tier 1 requires name
   identity). Doc 10's umbrella entry conflated 8-9 distinct subjects -> split:
   umbrella rows keep ONLY the unsuffixed family codes (their own semester-table print);
   each stream variant not already claimed by a branch doc of this batch (05 AG/07 BT/
   08 CE/09 CH print their stream's variant rows directly) becomes its own row.
3. Variant codes claimed by branch docs (AAS101A, AAS102A/H, AAS201A, AAS202A/H,
   AAS203A/H, AAS103A/H) are declared in quirks as covered cross-doc (keeps V-GAP green,
   catalog-level zero-GAP holds via the branch rows).
4. Variant rows carry the family's printed LTP/credits/marks (doc 10 prints evaluation
   data only on the family line; structural inference noted, not invented).
5. Identical-title 1xx/2xx pairs merged as one subject with semesters [1,2] per the docs'
   identical prints (consistent with all four branch drafters); owner can split later
   without loss — needs_review stays on the umbrella rows' notes.
"""
import json

DRAFT = '/home/z/my-project/work/pipeline_v2/drafts/10_btech_course-structure_2026-27.draft.json'

d = json.load(open(DRAFT))
subjects = d['subjects']

FAMILY_PHYS = dict(subject_type='core', category_print='BSC', program_year=1,
                   ltp_print='3-0-0', L=3, T=0, P=0, credit_print='03', credit=3,
                   marks={'CT': None, 'TA': None, 'sessional_total': 30, 'ESE': 70, 'total': 100},
                   co_count=None, co_texts=[], co_kls=[], objectives_print=[], prerequisites=None,
                   lectures_per_unit=None, units=[], textbooks=[], reference_books=[],
                   experiments=[], eligibility_print='', brain_fixes=[])
FAMILY_MATH = dict(FAMILY_PHYS, ltp_print='3-1-0', L=3, T=1, P=0, credit_print='04', credit=4)

def mk(codes, primary, name_print, slug, sems, family_slug, fields, ev_pages, stream_print, sem_note):
    s = {
        'codes_print': codes, 'primary_code': primary, 'name_print': name_print,
        'name_slug': slug, 'branch_names_print': [stream_print], 'semesters': sems,
        'scheme_line_print': ('Stream-variant subject; evaluation data printed only on the family line: '
                              + sem_note),
        'choice_group_hint': ("One stream-variant course per student's stream (Sem-I table p2 "
                              "'Both are Stream Specific'; stream tables p3/p9 map stream->variant)"),
        'flags': [], 'evidence_pages': ev_pages,
        'notes': [
            'stream_variant_row: doc 10 prints this stream variant with its own distinct title in the '
            'stream table; evaluation (L-T-P/credits/marks) is printed only on the family line, carried '
            'here as the family print (structural inference, recorded).',
            'The 1xx (Sem-I) and 2xx (Sem-II) prints carry identical titles; merged as one subject with '
            'semester_slots [1,2] per the identical-title print (consistent with the branch course-structure '
            'drafts of this batch); owner may split later without loss.',
            'Part of the umbrella family row "' + family_slug + '" (unsuffixed codes) — see that row for the '
            'family/slot semantics and the full printed variant mapping.',
        ],
    }
    s.update(dict(fields))
    return s

new_rows = [
    # Applied Physics stream variants (titles exactly as printed p3; Sem-II p9 identical)
    mk(['AAS101B', 'AAS201B'], 'AAS101B', 'Physics of Materials (ME stream)',
       'physics-of-materials', [1, 2], 'applied-physics', FAMILY_PHYS, [3, 9], 'ME Stream',
       "Sem-I: BSC AAS101/AAS102 'Applied Physics/Applied Chemistry (Both are Stream Specific)' L3 T0 P0, NCrF Hrs. 45, IA 30, EA 70, Total 100, Credits 03 (p2) || Sem-II: AAS201/AAS202 same (p7)"),
    mk(['AAS101C', 'AAS201C'], 'AAS101C', 'Quantum Physics and Electronic Sensors (ECE stream)',
       'quantum-physics-and-electronic-sensors', [1, 2], 'applied-physics', FAMILY_PHYS, [3, 9], 'ECE Stream',
       "Sem-I family line p2 / Sem-II p7 (L3 T0 P0, IA 30, EA 70, Total 100, Credits 03)"),
    mk(['AAS101D', 'AAS201D'], 'AAS101D', 'Physics of Electrical Engineering Materials (EE stream)',
       'physics-of-electrical-engineering-materials', [1, 2], 'applied-physics', FAMILY_PHYS, [3, 9], 'EE Stream',
       "Sem-I family line p2 / Sem-II p7 (L3 T0 P0, IA 30, EA 70, Total 100, Credits 03)"),
    mk(['AAS101E', 'AAS201E'], 'AAS101E', 'Quantum Physics and Applications (CSE stream)',
       'quantum-physics-and-applications', [1, 2], 'applied-physics', FAMILY_PHYS, [3, 9], 'CSE Stream',
       "Sem-I family line p2 / Sem-II p7 (L3 T0 P0, IA 30, EA 70, Total 100, Credits 03)"),
    mk(['AAS101I', 'AAS201I'], 'AAS101I', 'Physics of Fibres and Textile Materials (Textile Engineering stream)',
       'physics-of-fibres-and-textile-materials', [1, 2], 'applied-physics', FAMILY_PHYS, [3, 9], 'TX Stream',
       "Sem-I family line p2 / Sem-II p7 (L3 T0 P0, IA 30, EA 70, Total 100, Credits 03)"),
    # Applied Chemistry stream variants (titles exactly as printed p4; Sem-II p9-10 identical)
    mk(['AAS102B', 'AAS202B'], 'AAS102B',
       'Applied Chemistry for Advanced Metal Protection and Sustainable Energy Systems (ME Stream)',
       'applied-chemistry-for-advanced-metal-protection-and-sustainable-energy-systems', [1, 2],
       'applied-chemistry', FAMILY_PHYS, [4, 9, 10], 'ME Stream',
       "Sem-I family line p2 / Sem-II p7 (L3 T0 P0, IA 30, EA 70, Total 100, Credits 03)"),
    mk(['AAS102C', 'AAS202C'], 'AAS102C',
       'Applied Chemistry for Emerging Electronics and Futuristic Devices (EE & ECE Stream)',
       'applied-chemistry-for-emerging-electronics-and-futuristic-devices', [1, 2],
       'applied-chemistry', FAMILY_PHYS, [4, 9, 10], 'EE & ECE Stream',
       "Sem-I family line p2 / Sem-II p7 (L3 T0 P0, IA 30, EA 70, Total 100, Credits 03)"),
    mk(['AAS102D', 'AAS202D'], 'AAS102D', 'Applied Chemistry for Smart Systems (CSE Stream)',
       'applied-chemistry-for-smart-systems', [1, 2], 'applied-chemistry', FAMILY_PHYS, [4, 9, 10], 'CSE Stream',
       "Sem-I family line p2 / Sem-II p7 (L3 T0 P0, IA 30, EA 70, Total 100, Credits 03)"),
    mk(['AAS102E', 'AAS202E'], 'AAS102E',
       'Applied Chemistry for Fibres, Polymers and Sustainable Textiles (TX Stream)',
       'applied-chemistry-for-fibres-polymers-and-sustainable-textiles', [1, 2],
       'applied-chemistry', FAMILY_PHYS, [4, 9, 10], 'TX Stream',
       "Sem-I family line p2 / Sem-II p7 (L3 T0 P0, IA 30, EA 70, Total 100, Credits 03)"),
    # Applied Mathematics-I stream variants (titles exactly as printed p3-4)
    mk(['AAS103A', 'AAS103B', 'AAS103C', 'AAS103G'], 'AAS103A',
       'Differential Calculus and Linear Algebra (CE Stream)',
       'differential-calculus-and-linear-algebra', [1], 'applied-mathematics-i', FAMILY_MATH, [3, 4], 'CE / ME / EE & ECE / CH Streams',
       "Sem-I: BSC AAS103 'Applied Mathematics-I (Stream Specific)' L3 T1 P0, NCrF Hrs. 60, IA 30, EA 70, Total 100, Credits 04 (p2 Sr.No.2)"),
    mk(['AAS103D', 'AAS103E', 'AAS103F'], 'AAS103D', 'Calculus and Linear Algebra (CSE Stream)',
       'calculus-and-linear-algebra', [1], 'applied-mathematics-i', FAMILY_MATH, [3, 4], 'CSE / TX / BT Streams',
       "Sem-I: BSC AAS103 'Applied Mathematics-I (Stream Specific)' L3 T1 P0, Credits 04 (p2 Sr.No.2)"),
    # Applied Mathematics-II stream variants (titles exactly as printed p9)
    mk(['AAS203B', 'AAS203G'], 'AAS203B', 'Multivariable Calculus and Numerical Methods (ME Stream)',
       'multivariable-calculus-and-numerical-methods', [2], 'applied-mathematics-ii', FAMILY_MATH, [9], 'ME / CH Streams',
       "Sem-II: BSC AAS203 'Applied Mathematics-II (Stream Specific)' L3 T1 P0, NCrF Hrs. 60, IA 30, EA 70, Total 100, Credits 04 (p7 Sr.No.2)"),
    mk(['AAS203C'], 'AAS203C', 'Calculus, Laplace Transform and Numerical Techniques (EE & ECE Stream)',
       'calculus-laplace-transform-and-numerical-techniques', [2], 'applied-mathematics-ii', FAMILY_MATH, [9], 'EE & ECE Stream',
       "Sem-II family line p7 (L3 T1 P0, Credits 04)"),
    mk(['AAS203D'], 'AAS203D', 'Numerical Methods (CSE Stream)',
       'numerical-methods', [2], 'applied-mathematics-ii', FAMILY_MATH, [9], 'CSE Stream',
       "Sem-II family line p7 (L3 T1 P0, Credits 04)"),
    mk(['AAS203E'], 'AAS203E', 'Calculus and Numerical Method (TX Stream)',
       'calculus-and-numerical-method', [2], 'applied-mathematics-ii', FAMILY_MATH, [9], 'TX Stream',
       "Sem-II family line p7 (L3 T1 P0, Credits 04); title printed with singular 'Method' for TX stream"),
    mk(['AAS203F'], 'AAS203F', 'Calculus and Numerical Methods (Biotechnology Stream)',
       'calculus-and-numerical-methods', [2], 'applied-mathematics-ii', FAMILY_MATH, [9], 'BT Stream',
       "Sem-II family line p7 (L3 T1 P0, Credits 04)"),
]

# --- shrink umbrella entries to their own semester-table (unsuffixed) codes ---
shrink = {
    'applied-physics': ['AAS101', 'AAS201'],
    'applied-chemistry': ['AAS102', 'AAS202'],
    'applied-mathematics-i': ['AAS103'],
    'applied-mathematics-ii': ['AAS203'],
}
restructured = 0
for s in subjects:
    slug = s.get('name_slug')
    if slug in shrink:
        old_codes = s['codes_print']
        s['codes_print'] = shrink[slug]
        s['primary_code'] = shrink[slug][0]
        s.setdefault('notes', []).append(
            'RESTRUCTURED (CRON-20261027-B03 adjudication): this row is the family/slot line as printed in the '
            'semester tables (unsuffixed codes ' + ', '.join(shrink[slug]) + '); the stream variants printed in the '
            'stream tables (p3-5, p9-10) are distinct subjects with distinct titles and are represented as their own '
            'rows in this draft or in the branch course-structure drafts (05 AG / 07 BT / 08 CE / 09 CH) of this batch.')
        restructured += 1
print('umbrella rows shrunk:', restructured)

# --- add variant rows (skip if a slug already exists) ---
existing_slugs = {s.get('name_slug') for s in subjects}
added = 0
for nr in new_rows:
    if nr['name_slug'] in existing_slugs:
        print('skip (slug exists):', nr['name_slug'])
        continue
    subjects.append(nr)
    existing_slugs.add(nr['name_slug'])
    added += 1
print('variant rows added:', added)

# --- quirks: declare branch-covered variant codes (keeps V-GAP green; catalog zero-GAP holds via branch rows) ---
cov_quirk = (
    'cross_doc_coverage: stream-variant codes AAS101A, AAS102A, AAS102H, AAS201A, AAS202A, AAS202H, '
    'AAS203A, AAS203H, AAS103A, AAS103H are printed in doc 10 stream tables (p3-5, p9-10) AND as live table '
    'rows in the branch course-structure docs of this same batch (08 CE: AAS101A/AAS102A/AAS201A/AAS202A/'
    'AAS203A/AAS103A; 05 AG: AAS102H/AAS202H/AAS203H/AAS103H; 07 BT and 09 CH likewise); their subject rows '
    'are drafted from those branch docs, so doc 10 keeps only the unsuffixed family codes on its umbrella rows.')
if cov_quirk not in d['quirks']:
    d['quirks'].append(cov_quirk)
    print('coverage quirk added')

# --- open_items: record the adjudication outcome ---
oi = ('CRON-20261027-B03 adjudication applied: umbrella rows keep unsuffixed family codes; 16 stream-variant '
      'rows added from doc 10 stream tables p3-5/p9-10; branch-covered variants (AAS101A/AAS102A/AAS102H/AAS201A/'
      'AAS202A/AAS202H/AAS203A/AAS203H/AAS103A/AAS103H) left to the branch drafts (08/05/07/09); identical-title '
      '1xx+2xx pairs merged with semesters [1,2] — owner split/keep call still open on the umbrella + variant rows.')
if oi not in d['open_items']:
    d['open_items'].append(oi)

json.dump(d, open(DRAFT, 'w'), indent=1, ensure_ascii=False)
print('draft rewritten:', DRAFT, '| subjects now:', len(subjects))
