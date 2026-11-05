#!/usr/bin/env python3
"""b36_repair_kpi072.py — CRON-20261105-B35/B36 recorded-class repair.

The B35 replay adopted B32 doc-02 (pe-ipe_syllabus_2020-21) at renumbered slot
10, so the stem-keyed B32 override ('02_btech_pe-ipe_syllabus_2020-21::26::
project-management', RETARGET_KEEP_PUBLISHED_CODE_OWNER keeping KPI072 with
facility-planning-design) did not fire; the CODE-REASSIGNED auto moved KPI072
onto project-management. This repairs the two rows to the RECORDED B32 ruling
(adjudicate_b32.py evidence: KPI072's published owner is facility-planning-
design — the 2021-22 PE/I-PE y4 print and the 2024-25 ME-Ind scheme both
corroborate KPI072=Facility Planning; the 2020-21 detail p.53 'KPI 072' print
is an intra-doc clash against the doc's own contents/pool KPI 073 print; the
2020-21 print is OLDER than both corroborating prints; B19/B20
older-draft-never-steals-a-code class). KPI073 (the contents/pool print)
STAYS with project-management per the same ruling.

Repairs: facility-planning-design all_codes += KPI072; project-management
all_codes -= KPI072; change_note_vs_previous + source_history/notes entries on
both rows record the repair and its evidence (update-first: repairing the
published-code-owner is precisely the owner's 'update first > append second'
directive — no new rows).
"""
import csv, sys

CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
NOTE = ("B36 repair (CRON-20261105-B35 replay re-key miss): the B32-recorded ruling "
        "RETARGET_KEEP_PUBLISHED_CODE_OWNER (adjudicate_b32.py '02_btech_pe-ipe_syllabus_2020-21::26::"
        "project-management') keeps KPI072 with facility-planning-design — KPI072's published owner "
        "(2021-22 PE/I-PE y4 print + 2024-25 ME-Ind scheme corroborate KPI072=Facility Planning; the "
        "2020-21 detail p.53 'KPI 072' print is an intra-doc clash against the doc's own contents/pool "
        "KPI 073 print, and 2020-21 is OLDER than both corroborating prints; B19/B20 "
        "older-draft-never-steals-a-code class). The B35 renumbered-stem replay let the CODE-REASSIGNED "
        "auto move KPI072 onto project-management; this restores the recorded ownership. KPI073 stays "
        "with project-management per the same ruling; the 2020-21 'KPI 072' print remains a narrative "
        "dual-use slot mention (recorded owner-reconciliation open item).")

rows = list(csv.DictReader(open(CSV)))
hdr = list(rows[0].keys())
hit_fp = hit_pm = False
for r in rows:
    if r["subject_id"] == "facility-planning-design":
        toks = [t for t in r["all_codes"].split(";") if t]
        if "KPI072" not in toks:
            toks.append("KPI072")
            r["all_codes"] = ";".join(toks)
        r["change_note_vs_previous"] = (r.get("change_note_vs_previous", "") + " | " + NOTE).strip(" |")
        r["source_history"] = (r.get("source_history", "") + " | B36 repair: KPI072 restored to its published owner per the recorded B32 RETARGET_KEEP_PUBLISHED_CODE_OWNER ruling (2021-22 PE/I-PE y4 print KPI072=Facility Planning and Design; 2024-25 ME-Ind scheme same print)").strip(" |")
        hit_fp = True
    elif r["subject_id"] == "project-management":
        toks = [t for t in r["all_codes"].split(";") if t and t != "KPI072"]
        r["all_codes"] = ";".join(toks)
        if r["primary_code"] == "KPI072":  # cannot happen per the B35 state (primary RAU072) — guard anyway
            r["primary_code"] = "RAU072"
        r["change_note_vs_previous"] = (r.get("change_note_vs_previous", "") + " | " + NOTE).strip(" |")
        r["notes"] = (r.get("notes", "") + " | B36 repair: KPI072 does NOT belong to this row — it stays with facility-planning-design per the recorded B32 keep ruling; the 2020-21 PE/I-PE p.53 'KPI 072' print is recorded as a narrative dual-use slot mention (KPI 073 = the contents/pool print this row keeps).").strip(" |")
        hit_pm = True

assert hit_fp and hit_pm, (hit_fp, hit_pm)
with open(CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=hdr)
    w.writeheader()
    w.writerows(rows)
print("repaired: facility-planning-design += KPI072; project-management -= KPI072")
