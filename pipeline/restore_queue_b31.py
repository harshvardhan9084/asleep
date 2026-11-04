#!/usr/bin/env python3
"""restore_queue_b31.py — reconcile local queue to the GitHub B30 end-state.

The 19:09 cron trigger was executed by the parallel cron-loop instance (same
trace family; B30 manifest runs/20261104T125555Z_CRON-20261104-B30_*.md,
catalog commit 747874e, state commit a1e1216). This local session's workspace
was reset (38th; work/repo_asleep wiped, .env GITHUB_PAT stripped, queue left
at the B28-end state), so the recorded loser-reconciliation protocol (B28
open-item 6 / B29 open-item 9 / B30 open-item 8 class) applies: adopt the
GitHub B30 state, mark the 10 B30 rels done locally with recorded provenance,
then run the NEXT batch (B31) from the reconciled state.
"""
import json, hashlib, datetime, sys

Q = '/home/z/my-project/work/pipeline_v2/queue.json'
# B29 rels (parallel instance, 16:30 trigger; catalog ceb8938; per the repo's
# own restore_queue_b29.py) — my local queue predates BOTH parallel batches.
B30_RELS = [
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
    # B30 rels (parallel instance, 19:09 trigger; catalog 747874e; per pipeline/drafts_B30/)
    'repo_asleep/PDFs/5-course/2019-20/btech_me_y2_model-curriculum_2019-20.pdf',
    'repo_asleep/PDFs/5-course/2017-18/btech_me_y2_scheme-syllabus_2017-18.pdf',
    'repo_asleep/PDFs/5-course/2024-25/btech_me_y3_scheme_2024-25.pdf',
    'repo_asleep/PDFs/5-course/2019-20/btech_me_y4_syllabus-cbcs_2019-20.pdf',
    'repo_asleep/PDFs/5-course/2021-22/btech_me_y4_syllabus_2021-22.pdf',
    'repo_asleep/PDFs/5-course/2025-26/btech_me_y4_syllabus_2025-26.pdf',
    'repo_asleep/PDFs/5-course/2010-11/btech_mfg-tech_syllabus_2010-11.pdf',
    'repo_asleep/PDFs/5-course/2020-21/btech_mfg-tech_syllabus_2020-21.pdf',
    'repo_asleep/PDFs/5-course/2019-20/btech_mfg-tech_y2_model-curriculum_2019-20.pdf',
    'repo_asleep/PDFs/5-course/2024-25/btech_mfg-tech_y3_evaluation-scheme_2024-25.pdf',
]
B29_SET = set(B30_RELS[:10])

q = json.load(open(Q))
by_rel = {e['rel']: e for e in q['entries']}
now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S+00:00')
marked = 0
for rel in B30_RELS:
    e = by_rel.get(rel)
    if e is None:
        sys.exit(f'STOP: queue rel missing: {rel}')
    if e['status'] == 'done':
        continue
    if e['status'] != 'pending':
        sys.exit(f'STOP: unexpected status {e["status"]!r} for {rel}')
    md5 = hashlib.md5(open('/home/z/my-project/work/' + rel, 'rb').read()).hexdigest()
    if e.get('md5') and e['md5'] != md5:
        sys.exit(f'STOP: md5 mismatch for {rel}')
    e['status'] = 'done'
    e['md5'] = md5
    e['sha16'] = md5[:16]
    which = ('B29' if rel in B29_SET else 'B30')
    src = ('ceb8938 rows 2033-2088 +55/~196, manifest runs/20261104T105044Z' if rel in B29_SET
           else '747874e rows 2088-2119 +31/~146, manifest runs/20261104T125555Z')
    e['notes'] = (e.get('notes', '') + f' | done: {which} executed+pushed by the parallel cron instance '
                  f'(GitHub {src}); loser-reconciliation adoption (B28 open-item 6 class) '
                  '— not locally re-extracted').strip(' |')
    e.setdefault('meta', {}).setdefault('history', []).append(
        {'ts': now, 'event': 'done', 'note': f'{which} parallel-instance adoption'})
    marked += 1

q['meta']['batch_counter'] = 30
q['meta']['history'].append({
    'ts': now, 'event': 'restore_queue_b31',
    'note': ('loser-reconciliation to GitHub B30 end-state: 10 rels marked done with recorded '
             'provenance (parallel instance, 747874e); batch_counter 28->30; local session proceeds with B31')})

json.dump(q, open(Q, 'w'), indent=1, ensure_ascii=False)
from collections import Counter
c = Counter(e['status'] for e in q['entries'])
print(f'marked_done={marked}  batch_counter=30  status={dict(c)}')
exp = {'done': 274, 'pending': 169}
if dict(c).get('done') != exp['done'] or dict(c).get('pending') != exp['pending']:
    print(f'WARNING: expected 274 done / 169 pending per the B30 manifest')
