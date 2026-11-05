#!/usr/bin/env python3
"""patch_b34_verify_remedies.py — B34 (CRON-20261105-B34, B30-durable-draft replay)
verify remedy for doc-04 subject 11 (Automation and Robotics).

Situation: the adopted B30 durable draft carried the printed code RME078
(2019-20 ME DE-3 scheme pool print, p.8). adjudicate_b30.py's recorded ruling
(B29 04::13 keep-published-owner class: owner 2024-25 newer; older draft never
steals a code) strips RME078 draft-side, leaving the subject codeless. The
verifier's v10 no-code remedy downgrades to WARN only with recorded evidence
flags/quirks mentioning the no-code print. Remedy (recorded B26 no-code
evidence-flag class): add the evidence flag + quirk citing the p.8 print and
the strip ruling — zero-guess: no code invented, the printed form stays in
the quirk and in the row notes narrative.
"""
import json

P = "/home/z/my-project/work/pipeline_v2/drafts/04_btech_me_y4_syllabus-cbcs_2019-20.draft.json"
d = json.load(open(P))
s = d["subjects"][11]
assert s["name"].strip().lower().startswith("automation"), s["name"]

s["flags"] = list(dict.fromkeys((s.get("flags") or []) + [
    "no-code-owned-print RME078-stripped-keep-published"]))
s.setdefault("quirks", []).append(
    "patch-b34: the 2019-20 ME DE-3 scheme pool print (p.8) shows code RME078 beside "
    "this subject — it is the ONLY code printed for this row and it was stripped "
    "draft-side per the recorded B29 04::13 keep-published-owner ruling (RME078 stays "
    "owned by robotics-and-automation, owner 2024-25 newer; an older draft never steals "
    "a code), so this row ends up with no code owned; the printed form is preserved "
    "here and in the row notes narrative; the row is appended/updated as a no-code "
    "evidence-flagged print (B26 class; zero-guess forbids inventing a substitute code).")

json.dump(d, open(P, "w"), ensure_ascii=False, indent=1)
print("patched 04::11", s["name"], "| flags:", s["flags"])
