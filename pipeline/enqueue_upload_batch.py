#!/usr/bin/env python3
"""Enqueue the 6 in-scope never-ingested/unverified PDFs as pending-pinned;
record corroborating-copy and out-of-scope classifications in queue meta.history
(append-only audit). Zero-guess: sessions only from printed covers."""
import json, datetime

Q = '/home/z/my-project/work/pipeline_v2/queue.json'
U = '/home/z/my-project/upload/'
q = json.load(open(Q))

def E(rel, session, notes):
    return {"rel": "upload/" + rel, "file": U + rel, "session": session,
            "course": "BTech", "status": "pending-pinned",
            "notes": notes}

new = [
    E("B.Tech 2nd Year CSAI_CSML_CSDS_CSIOT_2021-22 0709.pdf", "2021-22",
      "14pp AKTU Evaluation Scheme & Syllabus B.Tech 2nd Year for CSAI/CSML/CSDS/CSIOT (+per cover). Never ingested (not among the 6 cited sources). Cover prints 2021-22."),
    E("B.Tech. 2nd Year E&C AICTE Model Curriculum 2019-20 23 March 2021.pdf", "2020-21",
      "16pp AKTU Evaluation Scheme & Syllabus B.Tech 2nd Year Electronics and Computer Engineering AS PER AICTE MODEL CURRICULUM, printed [Effective from the Session: 2020-21]. Never ingested: all 34 existing E&C rows cite only B.Tech_2nd_Yr_CSE_v3.pdf. Filename says 2019-20, printed cover says effective 2020-21 (cover print authoritative)."),
    E("B.Tech._3rd_Yr_CSE(AI)_2022_23_revised_.pdf", "2022-23",
      "35pp AKTU Evaluation Scheme & Syllabus B.Tech 3rd Year CSE (Artificial Intelligence), revised 2022-23. Cited doc 09291fd4fad1262e original bytes lost in workspace reset; this copy 7d6a8a1f4b44410b unverified — full re-ingestion for verification + gap closure."),
    E("B.Tech._3rd_Yr_CSE(DS)_2022_23_revised_.pdf", "2022-23",
      "37pp AKTU Evaluation Scheme & Syllabus B.Tech 3rd Year CSE (Data Science), revised 2022-23. NEVER ingested (no citation in registry). Existing CSE-DS rows only cover 2nd-year common subjects from CSE_v3."),
    E("B.Tech_2nd_Year_Mining_Engg_Evaluation_scheme_2024-25.pdf", "2024-25",
      "12pp AKTU Evaluation Scheme & Syllabus B.Tech 2nd Year MINING ENGINEERING, printed (Effective from session 2024-25). Mining Engineering absent from the registry's 16 branches — new branch."),
    E("B.Tech_2nd_Yr_CSE_v3.pdf", None,
      "18pp AKTU Evaluation Scheme & Syllabus B.Tech 2nd Year CSE-family (11+ branches per cover). Cited doc b5579aefa7a2 original bytes lost in reset; this copy 4f09e0095540f04e unverified. No session print on cover (zero-guess: session=null). Full re-ingestion for verification + gap closure (e.g. KOE03x slots)."),
]
known = {e['rel'] for e in q['entries']}
added = 0
for e in new:
    if e['rel'] not in known:
        q['entries'].append(e)
        added += 1

now = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
q['meta'].setdefault('history', []).extend([
    {"ts": now, "event": "corroborating-copy: upload/B.Tech. 3rd Year Civil Engineering.pdf (03d279e76a24f6ff) proven CONTENT-IDENTICAL to ingested doc B.Tech. 3rd Year Civil Engineering.pdf (79a6daf1f0cd9310) — normalized-alnum fulltext vs work/registry_v6/civil_fulltext.txt matches after stripping dump page-markers (295-char delta = 38 pages x ~7.8 marker chars; head+tail equal); byte-different re-save, NOT enqueued"},
    {"ts": now, "event": "corroborating-copy: upload/B.Tech. Arttificial Intelligence & Machine Learning Syllabus 3rd year 2024-25.pdf (d7e92cd90471acb6) proven CONTENT-IDENTICAL to ingested doc (65731720e3822273) — same method, 303-char delta = 39 pages x ~7.8; NOT enqueued"},
    {"ts": now, "event": "out-of-scope (charter 5-course BTech/BPharm/BCA/MCA/MBA), NOT enqueued: M.Tech Integrated CSE 3rd Year 2021-22; M.Tech. Integrated Ist Year AICTE Model Curriculum 2020-21; M.Tech_AI_and_DS_2021_22; MTech Microelectronics 2018-19; Master of Integrated Technology 2nd Year CSE 2020-21; PharmD Ordinance 2021-22 + Syllabus PharmD 2021-22 (PharmD != BPharm); AKTU_in_numbers_2026-10-03 (project stats poster, non-syllabus); DOC-20251220-WA0031 (120pp Hindi official ordinance/letter print, non-syllabus)"},
    {"ts": now, "event": f"enqueued {added} in-scope pending-pinned PDFs from upload/ (6 intended; never-ingested or unverified-copy re-ingestion)"},
])
json.dump(q, open(Q, 'w'), indent=1, ensure_ascii=False)
print(f"enqueued={added}; entries now={len(q['entries'])}")
for e in q['entries']:
    if e['status'] == 'pending-pinned':
        print("  PINNED:", e['rel'])
