#!/usr/bin/env python3
"""Enqueue the authorized corpus work/repo_asleep/PDFs/5-course/<session>/*.pdf
as pending entries, per the queue meta rebuild recipe recorded 2026-10-27:
"When the owner restores repo access, re-clone to work/repo_asleep and APPEND
the 5-course rels (BTech/BPharm/BCA/MCA/MBA, session-dir structure) as pending."

Zero-guess: session = the session dir name; 'no_session_found' -> session=null.
Course is NOT guessed from filenames (advisory field; the draft/cover proves it).
PDFs/other_courses/ is out of charter scope (5-course charter) - not enqueued.
Idempotent: rels already present in the queue are skipped.
"""
import json, os, datetime

Q = '/home/z/my-project/work/pipeline_v2/queue.json'
CORPUS = '/home/z/my-project/work/repo_asleep/PDFs/5-course'

q = json.load(open(Q))
known = {e['rel'] for e in q['entries']}

added, sessions = 0, {}
for sess in sorted(os.listdir(CORPUS)):
    sdir = os.path.join(CORPUS, sess)
    if not os.path.isdir(sdir):
        continue
    session = None if sess == 'no_session_found' else sess
    for fn in sorted(os.listdir(sdir)):
        if not fn.lower().endswith('.pdf'):
            continue
        rel = f"repo_asleep/PDFs/5-course/{sess}/{fn}"
        if rel in known:
            continue
        q['entries'].append({
            "rel": rel,
            "file": os.path.join(sdir, fn),
            "session": session,
            "course": None,          # proven from PDF cover at draft time, not filename
            "status": "pending",
            "notes": "authorized corpus (owner: harshvardhan9084, github.com/harshvardhan9084/asleep); enqueued per queue-meta rebuild recipe after re-clone 2026-10-28",
        })
        added += 1
        sessions[sess] = sessions.get(sess, 0) + 1

now = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
q['meta'].setdefault('history', []).extend([
    {"ts": now,
     "event": "corpus audit (owner correction honored): queue held only artd_v3/sources + upload rels - no aktu-pyq rel ever entered the queue post-reset; registry sources are the 2 charter-released companions + 6 recorded upload re-ingestions (all decisions in meta.history)"},
    {"ts": now,
     "event": "corpus restored: re-cloned PUBLIC repo github.com/harshvardhan9084/asleep (owner-designated corpus) to work/repo_asleep (614 files); PDFs/5-course = 19 session dirs, 485 PDFs; PDFs/other_courses out of 5-course charter scope - not enqueued"},
    {"ts": now,
     "event": f"enqueued {added} corpus PDFs as pending (session-dir structure; no_session_found -> session=null; course=null until cover-proven)"},
])
json.dump(q, open(Q, 'w'), indent=1, ensure_ascii=False)
print(f"enqueued={added}; entries now={len(q['entries'])}")
for s in sorted(sessions):
    print(f"  {s}: +{sessions[s]}")
