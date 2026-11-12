#!/usr/bin/env python3
"""build_t13_evidence_xlsx.py — owner evidence pack for T13 (B90), report-only.
Sheets: 1) sampled rows + verdicts, 2) issue/note class summary,
3) rule/sample transparency. Companion to t13_probe_ledger.json."""
import json
import openpyxl
from openpyxl.styles import Font, PatternFill

LED = "/home/z/my-project/work/pipeline_v2/probes/t13_probe_ledger.json"
OUT = "/home/z/my-project/work/repo_asleep/syllabus_catalog/owner_requests/quality_probe_T13_2026-11-12.xlsx"

led = json.load(open(LED))
cs = led["sample"]

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
ws1.title = "T13_row_verdicts"
rows = [[c["sid"], c["course"], c["primary_code"], c["subject_name"],
         c["verification_status"], c["row_verdict"],
         "; ".join(c["issues"])[:170], "; ".join(c["notes"])[:170]]
        for c in cs]
sheet(ws1, ["subject_id", "course", "primary_code", "subject_name",
            "verification_status", "row_verdict", "issues", "notes"], rows)

ws2 = wb.create_sheet("T13_class_summary")
rows = [["row_verdicts", json.dumps(led["counts"]["row_verdicts"])],
        ["issue_classes", json.dumps(led["counts"]["issue_classes"])],
        ["note_classes", json.dumps(led["counts"]["note_classes"])],
        ["clean_pct", led["counts"]["clean_pct"]]]
sheet(ws2, ["summary_item", "value"], rows)

ws3 = wb.create_sheet("T13_rule_sample")
rows = [[k, v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)]
        for k, v in led["rule"].items()] + \
       [[k, v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)]
        for k, v in led["counts"].items() if k not in ("issue_classes", "note_classes", "row_verdicts")] + \
       [["policy", led["policy"]]]
sheet(ws3, ["item", "value"], rows)

wb.save(OUT)
print("saved", OUT, "| rows:", len(cs))
