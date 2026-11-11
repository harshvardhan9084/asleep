#!/usr/bin/env python3
"""build_probe_report.py — xlsx evidence pack for the 2026-11-11 quality-test
cascade run (T1 + T2 + T12 stage-1 probes, ledger-only, no CSV writes)."""
import json
import openpyxl
from openpyxl.styles import Font, PatternFill

PROBE = "/home/z/my-project/work/pipeline_v2/probes"
OUT = "/home/z/my-project/download/quality_probe_T1T2T12_2026-11-11.xlsx"

HDR = PatternFill("solid", fgColor="1F4E79")
HF = Font(color="FFFFFF", bold=True)

t1 = json.load(open(f"{PROBE}/t1_probe_ledger.json"))
t2 = json.load(open(f"{PROBE}/t2_probe_ledger.json"))
t12 = json.load(open(f"{PROBE}/t12_probe_ledger.json"))

wb = openpyxl.Workbook()

# ---- T1 summary + duplicate candidates
ws = wb.active
ws.title = "T1 duplicates"
ws.append(["T1 duplicate-subject detection (owner 3-check spec: course partition -> name mark -> unit-text mark)"])
ws.append(["Subjects scanned", t1["subjects"], "Candidate pairs (light-marked)", t1["candidate_pairs"]])
row = 4
for k, v in sorted(t1["verdicts"].items()):
    ws.cell(row=row, column=1, value=k).font = Font(bold=True)
    ws.cell(row=row, column=2, value=v)
    row += 1
row += 1
ws.cell(row=row, column=1, value="Duplicate findings (multi-column agreement: same course + name mark + unit-text mark)").font = Font(bold=True, color="C00000")
row += 1
cols = ["verdict", "course", "row A", "name A", "row B", "name B", "unit similarity u1..u5", "codes", "sessions", "next stage"]
for ci, c in enumerate(cols, 1):
    cc = ws.cell(row=row, column=ci, value=c); cc.fill = HDR; cc.font = HF
row += 1
for p in t1["pairs"]:
    if p["verdict"].startswith("duplicate_") or "same_core" in p["verdict"]:
        ur = ", ".join(f"u{k}={v:.2f}" for k, v in p["unit_ratios"].items())
        nxt = ("page-verify both prints in their cited docs, then consolidate per B28 TIER2-ALLOW accumulator class"
               if p["verdict"].startswith("duplicate_") else "recorded class (B28 OOS precedent) — no action")
        ws.append([p["verdict"], p["course"], p["a"], p["name_a"], p["b"], p["name_b"], ur,
                   p["code_rel"], p["session_rel"], nxt])
        row += 1
ws.column_dimensions["C"].width = 34; ws.column_dimensions["D"].width = 34
ws.column_dimensions["E"].width = 34; ws.column_dimensions["F"].width = 38
ws.column_dimensions["G"].width = 40; ws.column_dimensions["J"].width = 52

# ---- T1 next-stage candidate list
ws2 = wb.create_sheet("T1 next-stage 199")
ws2.append(["candidate_unresolved pairs — next cascade stage: page-evidence check of both rows' cited scheme/syllabus lines (light-marked, no data change)"])
for c, h in enumerate(["#", "course", "row A", "name A", "row B", "name B", "name ratio", "unit evidence"], 1):
    cc = ws2.cell(row=2, column=c, value=h); cc.fill = HDR; cc.font = HF
r = 3
n_next = 0
for p in t1["pairs"]:
    if p["verdict"] == "candidate_unresolved":
        n_next += 1
        ur = ", ".join(f"u{k}={v:.2f}" for k, v in p["unit_ratios"].items())
        ws2.cell(row=r, column=1, value=n_next)
        for c, v in enumerate([p["course"], p["a"], p["name_a"], p["b"], p["name_b"], p["name_ratio"], ur], 2):
            ws2.cell(row=r, column=c, value=v)
        r += 1

# ---- T2 + T12
ws3 = wb.create_sheet("T2 T12 results")
ws3.append(["T2 code double-ownership (stage 1)"])
ws3.append(["Gate G2 (same code owned by 2 rows within a course)", t2["gate_g2"], "owned codes", t2["owned_codes"]])
ws3.append([])
ws3.append(["T12 citation integrity (stage 1: every cited #sha16 must resolve to a corpus PDF)"])
ws3.append(["Distinct shas cited in CSV", t12["distinct_sha_cited"], "Corpus PDFs indexed (md5)", t12["corpus_pdfs_indexed"]])
ws3.append(["UNRESOLVED citations (bytes lost from workspace/history; content grandfathered by their batch gates — re-verify when PDFs re-supplied)"])
for c, h in enumerate(["sha16", "row (subject_id)", "known class"], 1):
    cc = ws3.cell(row=6, column=c, value=h); cc.fill = HDR; cc.font = HF
known = {"4f09e0095540f04e": "B19 remedy class (owner-upload CSE_v3, probe-verified pre-wipe)",
         "13bd875d098f99df": "B28 PRIOR_VERIFIED_LOST_SHA (Common-Subjects companion)",
         "e18a3256f09b7f6e": "B10/B19 remedy class (probe-verified pre-wipe)"}
r = 7
for sha, sid in t12["unresolved"].items():
    ws3.cell(row=r, column=1, value=sha)
    ws3.cell(row=r, column=2, value=sid)
    ws3.cell(row=r, column=3, value=known.get(sha, "NOT previously recorded — register in T12 ledger (T2T: no page evidence available; bytes absent)"))
    r += 1

wb.save(OUT)
print("saved", OUT, "| next-stage pairs:", n_next)
