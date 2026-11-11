#!/usr/bin/env python3
"""build_t3_evidence_xlsx.py — owner evidence pack for T3 stage-1+2 (B83).
Sheets: 1) stage2 verdicts (all candidates), 2) review set (code not printed
in own cited docs), 3) suppressed clusters + skips (transparency).
Ledger-only companion to work/pipeline_v2/probes/t3_probe_ledger.json."""
import json
import openpyxl
from openpyxl.styles import Font, PatternFill

LED = "/home/z/my-project/work/pipeline_v2/probes/t3_probe_ledger.json"
OUT = "/home/z/my-project/work/repo_asleep/syllabus_catalog/owner_requests/quality_probe_T3_2026-11-12.xlsx"

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
ws1.title = "T3_stage2_verdicts"
rows = []
for c in cs:
    ev = next((e for e in c["page_evidence"] if e["verdict"] == "found"), None)
    rows.append([c["sid"], c["course"], c["primary_code"], c["family"],
                 c["expected_domain"], c["name_domain"], c["subject_name"][:90],
                 c["verdict"], "as-drafted" if c.get("as_drafted_citation") else "cited-page",
                 (f"p{ev['found_page']}: {ev['print'][:160]}" if ev else ""),
                 c["extra"]])
sheet(ws1, ["subject_id", "course", "primary_code", "family", "family_domain",
            "name_domain", "subject_name", "verdict", "evidence_basis",
            "printed_context", "arm"], rows)

ws2 = wb.create_sheet("T3_review_set")
rows = [[c["sid"], c["course"], c["primary_code"], c["name_domain"],
         c["subject_name"][:90],
         "; ".join(f"{e['verdict']} (cited_pgs={e.get('cited_pages')},sha={e.get('sha16','')[:8]})"
                   for e in c["page_evidence"][:3])]
        for c in cs if c["verdict"] != "print_agrees_attested"]
sheet(ws2, ["subject_id", "course", "primary_code", "name_domain",
            "subject_name", "why_review"], rows)

ws3 = wb.create_sheet("T3_funnel_transparency")
rows = [["stage1_skip_reasons", k, v] for k, v in sorted(led["stage1_skip_reasons"].items())]
rows += [["secondary_domain_cluster", k, len(v)] for k, v in sorted(led["secondary_domain_clusters_recorded"].items())]
rows += [["established_family", k, v] for k, v in sorted(led["families_established"].items())]
sheet(ws3, ["kind", "key", "value"], rows)

wb.save(OUT)
print("saved", OUT, "| candidates:", len(cs), "| review:", len(rows) if rows else 0)
