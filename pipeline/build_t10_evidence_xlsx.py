#!/usr/bin/env python3
"""build_t10_evidence_xlsx.py — owner evidence pack for T10 stage-1+2 (B86).
Sheets: 1) cluster verdicts (exact + near clusters), 2) member rows with
per-row page-evidence verdicts, 3) rule/skip transparency.
Ledger-only companion to work/pipeline_v2/probes/t10_probe_ledger.json."""
import json
import openpyxl
from openpyxl.styles import Font, PatternFill

LED = "/home/z/my-project/work/pipeline_v2/probes/t10_probe_ledger.json"
OUT = "/home/z/my-project/work/repo_asleep/syllabus_catalog/owner_requests/quality_probe_T10_2026-11-12.xlsx"

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
ws1.title = "T10_cluster_verdicts"
rows = []
for c in cs:
    found = [m for m in c["members"] if m["verdict"] == "co_print_found"]
    ev0 = next((e for m in found for e in m["page_evidence"]
                if e["verdict"] == "co_print_found"), None)
    rows.append([c["cluster"], c["cluster_verdict"], c["n_rows"],
                 ", ".join(c["courses"]), c["cross_program"],
                 "; ".join(f"{m['primary_code']}({m['course']})" for m in c["members"])[:180],
                 c["members"][0]["co1_stored"][:100],
                 (f"{ev0['doc']} p{ev0['found_page']}" if ev0 else "")])
sheet(ws1, ["cluster_kind", "cluster_verdict", "n_rows", "courses",
            "cross_program", "member codes", "shared CO1 (stored)", "print example"],
      rows)

ws2 = wb.create_sheet("T10_member_evidence")
rows = []
for c in cs:
    for m in c["members"]:
        ev = next((e for e in m["page_evidence"] if e["verdict"] == "co_print_found"), None)
        rows.append([c["cluster"], c["cluster_verdict"], m["sid"], m["course"],
                     m["primary_code"], m["subject_name"], m["effective_session_latest"],
                     m["co_count"], m["verdict"],
                     (f"{ev['doc']} p{ev['found_page']}: {ev['print_ctx'][:120]}" if ev else
                      "; ".join(f"{e['verdict']}:{e.get('doc','')[:40]}" for e in m["page_evidence"])[:160])])
sheet(ws2, ["cluster_kind", "cluster_verdict", "subject_id", "course",
            "primary_code", "subject_name", "session", "co_count",
            "member_verdict", "print evidence / cited-doc yields"], rows)

ws3 = wb.create_sheet("T10_rule_skips")
cnt = led["counts"]
rows = [["signature", led["rule"]["signature"]],
        ["exact_cluster", led["rule"]["exact_cluster"]],
        ["near_cluster", led["rule"]["near_cluster"]],
        ["stage2", led["rule"]["stage2"]],
        ["subject_rows", cnt["subject_rows"]],
        ["rows_with_co>=3", cnt["rows_with_co>=3"]],
        ["rows_skipped_lt3co", cnt["rows_skipped_lt3co"]],
        ["exact_clusters", cnt["exact_clusters"]],
        ["exact_rows", cnt["exact_rows"]],
        ["near_clusters", cnt["near_clusters"]],
        ["near_rows", cnt["near_rows"]],
        ["policy", led["policy"]]]
sheet(ws3, ["item", "value"], rows)

wb.save(OUT)
print("saved", OUT, "| clusters:", len(cs))
