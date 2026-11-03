#!/usr/bin/env python3
"""fix_08_option_codes.py — batch03 doc08 draft remedy (brain clause, evidence recorded).

The 295-page BPharm doc prints elective slots as ONE base code (e.g. BP212P) with
N printed alternatives, each appendix block header printing the compound designation
form ("BP212P SEC1" etc. — recorded verbatim in each option entry's quirks by the
segment subagents). The semester segments recorded the SLOT as its own entry carrying
[base, base+SEC1, ...]; the appendix segments recorded each OPTION with codes=[base]
only — which would collide at ladder Tier-0 (all 33 options would UPDATE the slot
row and stomp each other, and G2 would see one option owning the base code that the
slot row also claims).

Fix (faithful to print, zero invention): each OPTION entry's codes become the
COMPOUND PRINTED DESIGNATION parsed from its own recorded quirk evidence
(e.g. "BP212P SEC1"). norm_code() of the compound form is not an exact_code
token, so G2 ownership stays with the slot row and each option remains a
distinct subject row (one row per subject, RULES §11). The base code stays in
the option's quirks/notes for searchability.
"""
import json, re

P = "/home/z/my-project/work/pipeline_v2/drafts/08_bpharm_scheme-syllabus_2026-27.draft.json"
POOLS = ["BP212P", "BP312P", "BP607T", "BP610P", "BP611P", "BP708T", "BP806T", "BP809P"]

d = json.load(open(P))
pool_names, changed = set(), 0
for s in d["subjects"]:
    cs = [str(c) for c in s.get("codes", [])]
    bare = [c for c in cs if c in POOLS]
    if not bare:
        continue
    # slot entries carry the compound designators alongside the base code
    if any(" " in c for c in cs):
        pool_names.add(s.get("name", ""))
        continue
    # option entry: codes == [base]; find its printed designation in its quirks
    base = bare[0]
    desig = None
    for q in s.get("quirks", []):
        m = re.search(r"code designation '([A-Z]{2,4}\d{3}[A-Z]?\s+(?:SEC|AEC|VAC)\d+)'", str(q))
        if m and m.group(1).split()[0] == base:
            desig = m.group(1)
            break
    if desig is None:
        # BP212P slot's first option quirk uses the same phrasing; fail loudly rather than guess
        print(f"NO-DESIGNATION|{s.get('name','')[:50]}|quirks={s.get('quirks', [])[:1]}")
        continue
    s["codes"] = [desig]
    s.setdefault("quirks", []).append(
        f"CODES-FIX (merge prep, evidence recorded): codes list set to the printed compound designation "
        f"'{desig}' (appendix block-header print, quoted in the original extraction quirk); the base slot "
        f"code {base} stays owned by the slot row (G2 one-owner-per-code) and is preserved here in quirks.")
    changed += 1

json.dump(d, open(P, "w"), indent=1, ensure_ascii=False)
print(f"OPTION_CODES_FIXED|{changed}")
print(f"SLOT_ENTRIES|{sorted(pool_names)[:8]}")
