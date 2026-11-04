#!/usr/bin/env python3
"""restore_queue_b29.py — reconcile local queue to the GitHub B29 end-state.

The 16:30 cron trigger was executed by a PARALLEL cron-loop instance (same
trace family; B29 manifest runs/20261104T105044Z_CRON-20261104-B29_*.md,
catalog commit ceb8938, state commit b21b3ac). This local session's run was
delayed to the 19:09 trigger with the queue still at the B28-end state, so the
recorded loser-reconciliation protocol (B28 open-item 6, B29 open-item 9)
applies: adopt the GitHub state and mark the 10 B29 rels done locally with
recorded provenance, then run the NEXT batch (B30) from the reconciled state.
"""
import json, hashlib, datetime, sys

Q = '/home/z/my-project/work/pipeline_v2/queue.json'
B29_RELS = [
    'repo_asleep/PDFs/5-course/2019-20/btech_me-ind_y2_model-curriculum_2019-20.pdf',
    'repo_asleep/PDFs/5-course/2024-25/btech_me-ind_y3_evaluation-scheme_2024-25.pdf',
    'repo_asleep/PDFs/5-course/2018-19/btech_me-ind_y3_syllabus_2018-19.pdf',
    'repo_asleep/PDFs/5-course/2019-20/btech_me-ind_y4_syllabus-cbcs_2019-20.pdf',
    'repo_asleep/PDFs/5-course/2021-22/btech_me-ind_y4_syllabus_2021-22.pdf',
    'repo_asleep/PDFs/5-course/2025-26/btech_me-ind_y4_syllabus_2025-26.pdf',
    'repo_asleep/PDFs/5-course/2009-10/btech_me-pe_syllabus_2009-10.pdf',
    'repo_asleep/PDFs/5-course/2026-27/btech_me_course-structure_2026-27.pdf',
    'repo_asleep/PDFs/5-course/2018-19/btech_me_syllabus_2018-19.pdf',
    'repo_asleep/PDFs/5-course/2020-21/btech_me_syllabus_2020-21.pdf',
]

q = json.load(open(Q))
by_rel = {e['rel']: e for e in q['entries']}
now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S+00:00')
marked = 0
for rel in B29_RELS:
    e = by_rel.get(rel)
    if e is None:
        sys.exit(f'STOP: queue rel missing: {rel}')
    if e['status'] == 'done':
        continue
    if e['status'] != 'pending':
        sys.exit(f'STOP: unexpected status {e["status"]!r} for {rel}')
    md5 = hashlib.md5(open('/home/z/my-project/work/' + rel, 'rb').read()).hexdigest()
    e['status'] = 'done'
    e['md5'] = md5
    e['sha16'] = md5[:16]
    e['notes'] = (e.get('notes', '') + ' | done: B29 executed+pushed by the parallel cron instance '
                  '(GitHub ceb8938 rows 2033-2088 +55/~196, manifest runs/20261104T105044Z); '
                  'loser-reconciliation adoption (B28 open-item 6 class) — not locally re-extracted').strip(' |')
    e.setdefault('meta', {})['history'] = e.get('meta', {}).get('history', [])
    e['meta']['history'].append({'ts': now, 'event': 'done', 'note': 'B29 parallel-instance adoption'})
    marked += 1

q['meta']['batch_counter'] = 29
q['meta']['history'].append({
    'ts': now, 'event': 'restore_queue_b29',
    'note': ('loser-reconciliation to GitHub B29 end-state: 10 rels marked done with recorded '
             'provenance (parallel instance, ceb8938); batch_counter 28->29; local session proceeds with B30')})

json.dump(q, open(Q, 'w'), indent=1, ensure_ascii=False)
from collections import Counter
c = Counter(e['status'] for e in q['entries'])
print(f'marked_done={marked}  batch_counter=29  status={dict(c)}')
