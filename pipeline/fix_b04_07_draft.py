#!/usr/bin/env python3
"""CRON-20261027-B04 pre-commit fix: TX draft's chem-lab entry carries stray ME-suffix codes.

Evidence: the TX doc's SCHEME tables print AAS152E/AAS252E ( Fibres/Polymers/Textiles family)
while its detail-header prints AAS152B/AAS252B. Cross-document corroboration (batch-03 doc 10
stream tables: AAS102E = 'Applied Chemistry for Fibres, Polymers and Sustainable Textiles
(TX Stream)', AAS102B = '...(ME Stream)'; the ME branch doc 05 of this batch prints AAS152B for
its own 'Advanced Metal Protection...' lab) makes the E suffix certain for TX. Brain clause:
fix with certainty, keep printed form in notes, record brain_fix.
"""
import json

DRAFT = '/home/z/my-project/work/pipeline_v2/drafts/07_btech_textile-tech_course-structure_2026-27.draft.json'
d = json.load(open(DRAFT))

fixed = 0
for s in d['subjects']:
    if s.get('primary_code') == 'AAS152E':
        cs = [c for c in s.get('codes_print', []) if str(c) not in ('AAS152B', 'AAS252B')]
        removed = len(s.get('codes_print', [])) - len(cs)
        s['codes_print'] = cs
        s.setdefault('brain_fixes', []).append({
            'field': 'codes_print',
            'print': 'AAS152B/AAS252B (detail header)',
            'corrected': 'AAS152E/AAS252E (scheme tables)',
            'reason': ('TX chemistry family is the E suffix per the doc scheme tables AND doc-10 stream '
                       'table corroboration (AAS102E = Fibres/Polymers/Textiles TX stream; B suffix is the '
                       'ME stream, owned by the ME doc 05 of this batch). Detail-header B print kept here '
                       'as note; active codes = scheme print (RULES.md §5 scheme line wins).'),
        })
        s.setdefault('notes', []).append(
            'print_quirk: detail header prints AAS152B/AAS252B (ME-suffix remnant); scheme tables print '
            'AAS152E/AAS252E which govern (brain_fix recorded). Header print preserved verbatim here.')
        fixed += 1
        print('AAS152E entry fixed, removed codes:', removed)
        break

json.dump(d, open(DRAFT, 'w'), indent=1, ensure_ascii=False)
print('draft rewritten')
