#!/usr/bin/env python3
"""build_t8_evidence_xlsx.py — owner evidence pack for T8 stage-1+2 (B84).
Sheets: 1) stage2 verdicts (all candidates), 2) coverage + funnel transparency
(established/universal rule table, skip reasons), 3) per-candidate citation
evidence (title context for every resolvable doc).
Ledger-only companion to work/pipeline_v2/probes/t8_probe_ledger.json."""
import json
import openpyxl
from openpyxl.styles import Font, PatternFill

LED = "/home/z/my-project/work/pipeline_v2/probes/t8_probe_ledger.json"
OUT = "/home/z/my-project/work/repo_asleep/syllabus_catalog/owner_requests/quality_probe_T8_2026-11-12.xlsx"

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
ws1.title = "T8_stage2_verdicts"
rows = []
for c in cs:
    ev = next((e for e in c["page_evidence"] if e.get("verdict") == "found"), None)
    stored_titles = [e.get("doc_title", "")[:120] for e in c["page_evidence"]
                     if e.get("title_prints_stored_branch")]
    rows.append([c["sid"], c["course"], c["primary_code"], c["family"],
                 c["family_branch"], c["branch_stored"], c["subject_name"][:90],
                 c["verdict"],
                 (f"p{ev['found_page']}: {ev['print'][:160]}" if ev else ""),
                 " || ".join(stored_titles[:2])])
sheet(ws1, ["subject_id", "course", "primary_code", "family",
            "family_established_branch", "branch_stored", "subject_name",
            "verdict", "printed_context_at_code", "other_cited_doc_title_context"], rows)

ws2 = wb.create_sheet("T8_rule_table_transparency")
rows = [["coverage", "rows_without_branch_names", led["coverage"]["rows_without_branch_names"]],
        ["coverage", "branch_bearing_rows", led["coverage"]["branch_bearing_rows"]],
        ["coverage", "courses_with_branch_data", ",".join(led["coverage"]["courses_with_branch_data"])]]
rows += [["stage1_skip_reasons", k, v] for k, v in sorted(led["stage1_skip_reasons"].items())]
rows += [["established_family", k, v] for k, v in sorted(led["families_established"].items())]
rows += [["universal_family", k, "spread>=8 branches"] for k in led["families_universal"]]
sheet(ws2, ["kind", "key", "value"], rows)

ws3 = wb.create_sheet("T8_citation_evidence")
rows = []
for c in cs:
    for e in c["page_evidence"]:
        rows.append([c["sid"], c["primary_code"], c["verdict"], e.get("src"),
                     e.get("sha16"), str(e.get("cited_pages")),
                     e.get("verdict"), e.get("found_page"),
                     (e.get("print") or "")[:160],
                     (e.get("doc_title") or "")[:200],
                     e.get("title_prints_stored_branch", "")])
sheet(ws3, ["subject_id", "primary_code", "final_verdict", "cite_src", "sha16",
            "cited_pages", "entry_verdict", "found_page", "printed_context",
            "doc_title", "title_prints_stored_branch"], rows)

wb.save(OUT)
print("saved", OUT, "| candidates:", len(cs))
