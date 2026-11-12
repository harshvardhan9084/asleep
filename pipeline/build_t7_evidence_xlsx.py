#!/usr/bin/env python3
"""build_t7_evidence_xlsx.py — owner evidence pack for T7 stage-1+2 (B85).
Sheets: 1) stage2 verdicts (all candidates, direction-tagged), 2) rule-table
transparency (family session windows + secondary letter windows + skips),
3) per-citation evidence (every cited doc's yield), 4) data-quality observation
(program_year bulk-default note).
Ledger-only companion to work/pipeline_v2/probes/t7_probe_ledger.json."""
import json
import openpyxl
from openpyxl.styles import Font, PatternFill

LED = "/home/z/my-project/work/pipeline_v2/probes/t7_probe_ledger.json"
OUT = "/home/z/my-project/work/repo_asleep/syllabus_catalog/owner_requests/quality_probe_T7_2026-11-12.xlsx"

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
ws1.title = "T7_stage2_verdicts"
rows = []
for c in cs:
    found = [e for e in c["page_evidence"] if e.get("verdict") == "found"]
    found_ctx = " || ".join(
        f"{e.get('doc','')}[s={e.get('doc_session')}] p{e.get('found_page')}: {e.get('print','')[:100]}"
        for e in found[:3])
    rows.append([c["sid"], c["course"], c["primary_code"], c["family"],
                 c["row_session"], c["family_window"], c["direction"],
                 c["subject_name"][:80], c["verdict"],
                 found_ctx[:300],
                 c["all_codes"][:80]])
sheet(ws1, ["subject_id", "course", "primary_code", "family", "row_session",
            "family_window", "direction", "subject_name", "verdict",
            "found_docs_context", "all_codes"], rows)

ws2 = wb.create_sheet("T7_rule_table_transparency")
rows = [["stage1_skip_reasons", k, v] for k, v in sorted(led["stage1_skip_reasons"].items())]
rows += [["family_window", k, v] for k, v in sorted(led["families_with_windows"].items())]
rows += [["letter_window_secondary", k, v] for k, v in sorted(led["letter_generation_windows_secondary"].items())]
sheet(ws2, ["kind", "key", "value"], rows)

ws3 = wb.create_sheet("T7_citation_evidence")
rows = []
for c in cs:
    for e in c["page_evidence"]:
        rows.append([c["sid"], c["primary_code"], c["row_session"], c["verdict"],
                     e.get("src"), e.get("sha16"), e.get("doc"),
                     e.get("doc_session"), str(e.get("cited_pages")),
                     e.get("verdict"), e.get("found_page"),
                     (e.get("print") or "")[:160]])
sheet(ws3, ["subject_id", "primary_code", "row_session", "final_verdict",
            "cite_src", "sha16", "doc", "doc_session", "cited_pages",
            "entry_verdict", "found_page", "printed_context"], rows)

ws4 = wb.create_sheet("T7_data_quality_observation")
obs = led["data_quality_observations"]
rows = [["program_year_by_course", c, json.dumps(v, ensure_ascii=False)]
        for c, v in sorted(obs["program_year_distribution_by_course"].items())]
rows += [["note", "program_year bulk-default", obs["note"][:300]]]
sheet(ws4, ["kind", "key", "value"], rows)

wb.save(OUT)
print("saved", OUT, "| candidates:", len(cs))
