#!/usr/bin/env python3
"""build_t9_evidence_xlsx.py — owner evidence pack for T9 stage-1+2 (B88).
Sheets: 1) flagged rows + verdicts, 2) duplicate groups + print counts,
3) rule/skip transparency. Ledger-only companion to t9_probe_ledger.json."""
import json
import openpyxl
from openpyxl.styles import Font, PatternFill

LED = "/home/z/my-project/work/pipeline_v2/probes/t9_probe_ledger.json"
OUT = "/home/z/my-project/work/repo_asleep/syllabus_catalog/owner_requests/quality_probe_T9_2026-11-12.xlsx"

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
ws1.title = "T9_row_verdicts"
rows = [[c["sid"], c["course"], c["primary_code"], c["subject_name"],
         c["effective_session_latest"], c["n_groups"], c["row_verdict"],
         "; ".join(f"{g['kind']}:{g['verdict']}" for g in c["groups"])[:180]]
        for c in cs]
sheet(ws1, ["subject_id", "course", "primary_code", "subject_name", "session",
            "n_dup_groups", "row_verdict", "group verdicts"], rows)

ws2 = wb.create_sheet("T9_group_evidence")
rows = []
for c in cs:
    for g in c["groups"]:
        ev = max(g["page_evidence"], key=lambda e: e.get("count_scoped", 0)
                 + e.get("count_whole", 0)) if g["page_evidence"] else None
        rows.append([c["sid"], c["primary_code"], g["kind"], g["verdict"],
                     " | ".join(g["fragments"]), g["best_scoped"], g["best_whole"],
                     (f"{ev['doc']} blocks p{ev.get('block_pages')}" if ev else "")])
sheet(ws2, ["subject_id", "primary_code", "group_kind", "verdict",
            "title fragments", "count_in_course_block", "count_whole_doc",
            "best doc / block pages"], rows)

ws3 = wb.create_sheet("T9_rule_skips")
rows = [[k, v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)]
        for k, v in led["rule"].items()] + \
       [[k, v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)]
        for k, v in led["counts"].items()] + \
       [["policy", led["policy"]]]
sheet(ws3, ["item", "value"], rows)

wb.save(OUT)
print("saved", OUT, "| rows:", len(cs))
