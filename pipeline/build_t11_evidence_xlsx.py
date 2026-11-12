#!/usr/bin/env python3
"""build_t11_evidence_xlsx.py — owner evidence pack for T11 stage-1+2 (B87).
Sheets: 1) candidate verdicts (lens A+B), 2) per-row page evidence,
3) rule/skip transparency. Ledger-only companion to t11_probe_ledger.json."""
import json
import openpyxl
from openpyxl.styles import Font, PatternFill

LED = "/home/z/my-project/work/pipeline_v2/probes/t11_probe_ledger.json"
OUT = "/home/z/my-project/work/repo_asleep/syllabus_catalog/owner_requests/quality_probe_T11_2026-11-12.xlsx"

led = json.load(open(LED))
cs = led["candidates_stage2"]

wb = openpyxl.Workbook()
hdr_fill = PatternFill("solid", fgColor="1F4E79")
hdr_font = Font(color="FFFFFF", bold=True)


def sheet(ws, cols, rows):
    ws.append(cols)
    for c in ws[1]:
        c.fill, c.font = hdr_fill, hdr_font
    for r in rows:
        ws.append(r)
    for col, w in zip(ws.columns, cols):
        ws.column_dimensions[col[0].column_letter].width = min(60, max(12, len(col) + 4))
    ws.freeze_panes = "A2"


ws1 = wb.active
ws1.title = "T11_verdicts"
rows = [[c["lens"], c["code"], c["class"], c["name_ratio"],
         " vs ".join(c["names"]), c["verdict"],
         "; ".join(f"{m['primary_code']}[{m['course']}]={m['verdict']}" for m in c["rows"])]
        for c in cs]
sheet(ws1, ["lens", "code", "stage1_class", "name_ratio", "stored names",
            "verdict", "per-row verdicts"], rows)

ws2 = wb.create_sheet("T11_page_evidence")
rows = []
for c in cs:
    for m in c["rows"]:
        ev = next((e for e in m["page_evidence"] if e.get("verdict") == "found"), None)
        rows.append([c["lens"], c["code"], c["verdict"], m["sid"], m["course"],
                     m["primary_code"], m["subject_name"], m["verdict"],
                     (f"{ev['doc']} p{ev['found_page']}: {ev['print'][:150]}" if ev else
                      "; ".join(f"{e['verdict']}:{e.get('doc','')[:40]}" for e in m["page_evidence"])[:160])])
sheet(ws2, ["lens", "code", "cluster_verdict", "subject_id", "course",
            "primary_code", "subject_name", "row_verdict", "print / cited-doc yields"], rows)

ws3 = wb.create_sheet("T11_rule_skips")
cnt = led["counts"]
rows = [[k, v] for k, v in led["rule"].items()] + [[k, v] for k, v in cnt.items()] + [["policy", led["policy"]]]
sheet(ws3, ["item", "value"], rows)

wb.save(OUT)
print("saved", OUT, "| candidates:", len(cs))
