#!/usr/bin/env python3
"""b35_adjudicate_restem.py — CRON-20261105-B35: re-key the three B31
open-electives-science override entries from the B31-era stem
'10_btech_open-electives-science_2009-10' to this batch's staging stem
'08_btech_open-electives-science_2009-10'.

The durable B31 draft was adopted into batch35 at slot 08 (batch35 = B31 docs
01-07 + B31 doc-10 + B32 docs 01-02, filename-ASC renumbered). TIER2_OVERRIDES
keys are stem-scoped, so the recorded adjudications (verbatim, evidence
unchanged) must fire under the new stem. Content identical to the B31 entries
injected at merge_draft.py lines 3248-3259; only the key prefix differs.
"""
MD = "/home/z/my-project/scripts/pipeline_v2/merge_draft.py"
MARK = "B35 (CRON-20261105-B35) re-keyed open-electives-science overrides (batch35 stem 08_)"

src = open(MD).read()
if MARK in src:
    print("  (already injected)")
else:
    block = '''
# ---- B35 (CRON-20261105-B35) re-keyed open-electives-science overrides (batch35 stem 08_) ----
TIER2_OVERRIDES.update({
    "08_btech_open-electives-science_2009-10::00::introduction-to-soft-computing-neural-networks-fuzzy-logic-a": {
        "action": "ALLOW",
        "reason": "B35 RE-KEY of the recorded B31 STAND (identical content to '10_btech_open-electives-science_2009-10::00' — the durable B31 draft was adopted into batch35 at slot 08): STAND of the pre-adjudicated CODE-REASSIGNED-ACROSS-SESSIONS auto (RESOLVE_APPEND B3/B02 class): the unique Tier-0 code owner of EOE-031/EOE-041 is the k_era range print on the Mathematics-III/Science-Based-OE slot rows ('EOE 031-038'/'EOE 041-048' program-structure prints); the draft (2009-10 science-OE doc, the ORIGINAL establishing print) names Introduction-to-Soft-Computing, and exactly one name-identity row exists (sess 2009-10, empty units) — the slot-code-to-subject convergence (recorded B17 SLOT-CODE-TRANSFER class): the name-identity row gains the exact codes + the verbatim units; the pool slot rows keep their range prints (G2-exempt)."},
    "08_btech_open-electives-science_2009-10::01::nano-sciences": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "nano-sciences",
        "keep_published_codes": {"EOE-042": "power-station-practice"},
        "reason": "B35 RE-KEY of the recorded B31 equal-session code-slot keep (identical content to '10_btech_...::01'; recorded B19/RCS653 class): draft 'Nano Sciences' (2009-10 science-OE doc, 5 verbatim units) prints the paired slot 'EOE-032/EOE-042'; Tier-0 TIEs across nano-sciences (owns EOE-032) and power-station-practice (EEE-042;EOE-042, its own 2009-10 establishing print). Equal-session establishing prints never steal each other's codes: the update lands on the name-exact nano-sciences row (units backfill — the row prints none), EOE-042 STAYS with power-station-practice (G2 single ownership), and the science-OE pairing print is recorded as narrative on the nano-sciences row."},
    "08_btech_open-electives-science_2009-10::04::polymer-science-and-technology": {
        "action": "ALLOW",
        "reason": "B35 RE-KEY of the recorded B31 STAND (identical content to '10_btech_...::04'): STAND of the pre-adjudicated CODE-REASSIGNED-ACROSS-SESSIONS auto (B3 BBC102 class): the unique Tier-0 code owner EOE-035/EOE-045 is polymer-science-technology ('Polymer Science & Technology', 2009-10, units empty, ROE035;ROE045 also owned); the draft name 'Polymer Science and Technology' name-matches exactly one same-course row (polymer-science-and-technology, BOE311;BOE411, 2023-24, 5 units — the NEP open-elective print of the SAME science elective; '&'/'and' print variance across eras, distinctive probe: polymerization/composites/polymers). The auto transfers EOE-035/EOE-045 to the name-identity accumulator row (the &-form row keeps ROE codes + narrative; recorded variant-name-rows-pending-reconciliation owner open item); draft 2009-10 OLDER so backfill-empty only."},
})
'''
    lines = src.split("\n")
    starts = [i for i, l in enumerate(lines) if l.startswith("TIER2_OVERRIDES.update({")]
    assert starts, "no TIER2_OVERRIDES.update block found"
    s = starts[-1]
    depth = 0
    e = None
    for i in range(s, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        if depth == 0 and i > s:
            e = i
            break
    assert e is not None
    lines.insert(e + 1, block)
    open(MD, "w").write("\n".join(lines))
    print("  injected re-keyed block after TIER2_OVERRIDES ending line", e + 1)
