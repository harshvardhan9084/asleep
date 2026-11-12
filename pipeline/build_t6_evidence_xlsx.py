#!/usr/bin/env python3
"""build_t6_evidence_xlsx.py — owner evidence pack for T6 stage-1 (B89).
Sheets: 1) sampled rows + verdicts, 2) per-unit coverage detail,
3) rule/skip transparency. Ledger-only companion to t6_probe_ledger.json."""
import json
import openpyxl
from openpyxl.styles import Font, PatternFill

LED = "/home/z/my-project/work/pipeline_v2/probes/t6_probe_ledger.json"
OUT = "/home/z/my-project/work/repo_asleep/syllabus_catalog/owner_requests/quality_probe_T6_2026-11-12.xlsx"

led = json.load(open(LED))
cs = led["candidates"]

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
        ws.column_dimensions[col[0].column_letter].width = min(55, max(12, len(col) + 4))
    ws.freeze_panes = "A2"


ws1 = wb.active
ws1.title = "T6_row_verdicts"
rows = [[c["sid"], c["course"], c["primary_code"], c["subject_name"],
         len(c["units"]), c["row_verdict"],
         ", ".join(u["verdict"] for u in c["units"])]
        for c in cs]
sheet(ws1, ["subject_id", "course", "primary_code", "subject_name",
            "n_prose_units", "row_verdict", "per-unit verdicts"], rows)

ws2 = wb.create_sheet("T6_unit_coverage")
rows = [[c["sid"], c["primary_code"], u["unit"], u["chars"], u["verdict"],
         u["coverage"], u["best_doc_sha"], u["doc_session"]]
        for c in cs for u in c["units"]]
sheet(ws2, ["subject_id", "primary_code", "unit_field", "chars",
            "unit_verdict", "best_coverage", "best_doc_sha16", "doc_session"], rows)

ws3 = wb.create_sheet("T6_rule_skips")
rows = [[k, v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)]
        for k, v in led["rule"].items()] + \
       [[k, v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)]
        for k, v in led["counts"].items()] + \
       [["policy", led["policy"]]]
sheet(ws3, ["item", "value"], rows)

wb.save(OUT)
print("saved", OUT, "| rows:", len(cs))
