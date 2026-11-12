#!/usr/bin/env python3
"""build_b91_plan_xlsx.py — B91 consolidation: the owner's question was
"what do we do with the test results? I wanted the clean and faithful
'syllabus rich' CSV". This workbook converts the completed T1-T13 cascade
evidence into the concrete path to the clean CSV.

Sheets:
  1 PATH_TO_CLEAN_CSV   - the answer: every remaining item class -> action
  2 RESTORE_CANDIDATES  - 12 BOOK_TRUNC + 1 ambiguous + 2 display fills
  3 FLAG_RETIRE_CANDIDATES - 9 stored_matches_print (flag-only change)
  4 STAY_FLAGGED        - honest markers that stay (zero-guess doctrine)
  5 OPEN_REVIEW_QUEUE   - cascade page-image queue (T3/T6/T7/T9/T10/T13)
  6 CASCADE_RESULTS     - per-test verdict totals (the proof sheet)

Style follows the repo's evidence-pack spec (hdr_fill 1F4E79, freeze A2,
width min(60, max(12, len+4))) — same as the T3-T13 packs.
"""
import json
import os
from collections import Counter

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

REPO_OR = "/home/z/my-project/work/repo_asleep/syllabus_catalog/owner_requests"
PROB = "/home/z/my-project/work/pipeline_v2/probes"
OUT_DL = "/home/z/my-project/download/art_d_final/syllabus_remediation_plan_B91.xlsx"
OUT_REPO = os.path.join(REPO_OR, "quality_probe_B91_remediation_plan_2026-11-12.xlsx")

HDR_FILL = PatternFill("solid", fgColor="1F4E79")
HDR_FONT = Font(color="FFFFFF", bold=True, size=10)
WRAP = Alignment(wrap_text=True, vertical="top")


def load(p):
    with open(p) as f:
        return json.load(f)


def sheet(wb, name, headers, rows, widths=None, title_row=None):
    ws = wb.create_sheet(name)
    r0 = 1
    if title_row:
        ws.cell(row=1, column=1, value=title_row).font = Font(bold=True, size=12)
        ws.cell(row=1, column=1).alignment = Alignment(vertical="center")
        r0 = 3
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=r0, column=c, value=h)
        cell.fill = HDR_FILL
        cell.font = HDR_FONT
        cell.alignment = WRAP
    for i, row in enumerate(rows, r0 + 1):
        for c, v in enumerate(row, 1):
            cell = ws.cell(row=i, column=c, value=v)
            cell.alignment = WRAP
            if widths:
                cell.font = Font(size=9)
    ws.freeze_panes = f"A{r0 + 1}"
    for c in range(1, len(headers) + 1):
        if widths and c <= len(widths) and widths[c - 1]:
            w = widths[c - 1]
        else:
            vals = [len(str(r[c - 1])) if len(r) >= c else 0 for r in rows]
            w = min(60, max(12, (max(vals) + 4) if vals else 12))
        ws.column_dimensions[get_column_letter(c)].width = w
    return ws


wb = Workbook()
wb.remove(wb.active)
wb.properties.creator = "Z.ai"

# ---------------- sources
b91 = load(os.path.join(PROB, "b91_booktrunc_probe_ledger.json"))
af = load("/home/z/my-project/work/pipeline_v2/audit_flags.json")
t13 = load(os.path.join(PROB, "t13_probe_ledger.json"))
t9 = load(os.path.join(REPO_OR, "t9_probe_ledger.json"))
t6 = load(os.path.join(PROB, "t6_probe_ledger.json"))
t7 = load(os.path.join(REPO_OR, "t7_probe_ledger.json"))
t10 = load(os.path.join(REPO_OR, "t10_probe_ledger.json"))
t11 = load(os.path.join(REPO_OR, "t11_probe_ledger.json"))
t3 = load(os.path.join(REPO_OR, "t3_probe_ledger.json"))
t12 = load(os.path.join(REPO_OR, "t12_probe_ledger.json"))

bt_items = b91["book_trunc"]["items"]
disp = b91["display_missing"]["items"]

# ---------------- sheet 2 RESTORE_CANDIDATES
restore, ambiguous = [], []
for it in bt_items:
    if it["verdict"] == "restorable_from_print":
        restore.append([it["primary_code"], it["subject_name"], it["course"],
                        it["field"], it["stored_entry"], it["printed_full"],
                        it["evidence"], "B92: restore value from print "
                        "(page-image verify before write)"])
    elif it["verdict"] == "ambiguous_multi_candidate":
        ambiguous.append([it["primary_code"], it["subject_name"], it["course"],
                          it["field"], it["stored_entry"], it["printed_full"],
                          it["evidence"], "B92: manual pick from candidates "
                          "(page-image)"])
for d in disp:
    if d["verdict"] == "restorable_from_print_col":
        restore.append([d["primary_code"], d["subject_name"], "", "subject_name_display",
                        "(empty)", d["proposed_display"],
                        "CSV col subject_name_print (print-attested)",
                        "B92: fill display from subject_name_print"])
sheet(wb, "RESTORE_CANDIDATES",
      ["code", "subject", "course", "field", "stored value now",
       "printed / proposed value", "evidence", "proposed action"],
      restore + ambiguous,
      widths=[10, 28, 16, 22, 40, 48, 26, 30],
      title_row=f"RESTORE CANDIDATES — {len(restore)} restorable "
                f"(+{len(ambiguous)} ambiguous). Values ONLY from print / "
                f"print-attested columns; page-image verify before write.")

# ---------------- sheet 3 FLAG_RETIRE_CANDIDATES
retire = [[it["primary_code"], it["subject_name"], it["field"], it["stored_entry"],
           it["printed_full"], it["evidence"],
           "B92: retire BOOK_TRUNC flag (stored entry already matches print)"]
          for it in bt_items if it["verdict"] == "stored_matches_print"]
sheet(wb, "FLAG_RETIRE_CANDIDATES",
      ["code", "subject", "field", "stored value", "printed span (equal)", "evidence",
       "proposed action"],
      retire, widths=[10, 28, 22, 44, 44, 26, 34],
      title_row=f"FLAG RETIRE CANDIDATES — {len(retire)} entries where the "
                f"printed block shows exactly the stored text: the BOOK_TRUNC "
                f"flag is stale. Flags-column change only, no value change.")

# ---------------- sheet 4 STAY_FLAGGED
te_field = Counter(f["field"].split("[")[0] for flags in af["rows"].values()
                   for f in flags if f["rule"] == "TYPE_EMPTY")
stay = [
    ["TYPE_EMPTY", 375, "field not stated by print",
     "; ".join(f"{k} {v}" for k, v in te_field.most_common(8)),
     "STAY — filling from anything but print = invention (zero-guess rule). "
     "These empty cells ARE the faithful state."],
    ["BOOK_TRUNC not_in_text_layer", 37,
     "stored entry absent from cited docs' text layer",
     "raster docs / book block beyond text layer",
     "STAY unless the owner orders a page-image batch; page-image "
     "verification could convert some to restorable."],
    ["BOOK_TRUNC block_pages_not_found", 4,
     "row's course block not locatable in text layer", "as above",
     "STAY / page-image queue."],
    ["BOOK_TRUNC entry_not_found_in_row", 2,
     "audit slug mismatch (subject-name variants)", "managerial-economics-mba; "
     "active-pharmaceutical-ingredients…-the",
     "B92: fix slug mapping, then re-run probe for these 2."],
    ["DISPLAY_MISSING", 2, "subject_name_display empty", "MCA-211, ECH603",
     "B92: fill from subject_name_print (listed in RESTORE_CANDIDATES)."],
    ["T12 unresolved citation shas", 6,
     "cited PDF not in corpus (sha unresolvable)",
     "; ".join(f"{k} ({v})" for k, v in t12["unresolved"].items()),
     "STAY flagged — the referenced PDFs are not ingested; per owner, do NOT "
     "ingest other-course PDFs uncommanded."],
]
sheet(wb, "STAY_FLAGGED",
      ["flag class", "count", "what it means", "detail", "disposition"],
      stay, widths=[30, 8, 30, 44, 44],
      title_row="HONEST MARKERS THAT STAY — a flag-free cell filled with a "
                "guess would make the CSV LESS faithful, not more. "
                f"Active flag set stays 442 = TYPE_EMPTY 375 / BOOK_TRUNC 65 "
                f"/ DISPLAY_MISSING 2 until B92 writes.")

# ---------------- sheet 5 OPEN_REVIEW_QUEUE
queue = []
t6c = load(os.path.join(REPO_OR, "t6_probe_ledger.json"))["candidates"]
for c in t6c:
    if c.get("row_verdict") in ("unit_text_not_found_review", "no_citation"):
        queue.append(["T6", c.get("primary_code", ""), c.get("sid", ""),
                      c.get("subject_name", ""), c.get("row_verdict"),
                      "page-image check of cited unit text"])
t7c = t7["candidates_stage2"]
for c in t7c:
    if "review" in str(c.get("verdict", "")):
        queue.append(["T7", c.get("primary_code", ""), c.get("sid", ""),
                      c.get("subject_name", ""), c.get("verdict"),
                      "page-image / provenance check of effective_session"])
t9v = Counter(c.get("row_verdict", "?") for c in t9["candidates_stage2"])
for c in t9["candidates_stage2"]:
    if c.get("row_verdict") in ("attested_in_doc_fallback_review",
                                "drafting_side_duplication_review"):
        queue.append(["T9", c.get("primary_code", ""), c.get("sid", ""),
                      c.get("subject_name", ""), c.get("row_verdict"),
                      "print-once-stored-twice: dedup candidate, page-image verify"])
for c in t10["candidates_stage2"]:
    if c.get("cluster_verdict") == "drafting_side_review":
        queue.append(["T10", c.get("cluster", ""), "", "", "drafting_side_review",
                      "KIC-052 COs beyond own print; page-image check"])
for c in t3["candidates_stage2"]:
    if c.get("verdict") in ("code_not_in_any_cited_doc", "no_citation"):
        queue.append(["T3", c.get("primary_code", c.get("code", "")),
                      c.get("sid", ""), c.get("subject_name", ""), c.get("verdict"),
                      "citation completeness check"])
for s in t13["sample"]:
    if s.get("verdict") == "issues":
        queue.append(["T13", s.get("primary_code", ""), s.get("sid", ""),
                      s.get("subject_name", ""), str(s.get("issue_classes", "")),
                      "BOP364/RTT602 effective_session_latest_empty; page-image check"])
qc = Counter(q[4] for q in queue)
sheet(wb, "OPEN_REVIEW_QUEUE",
      ["test", "code", "sid", "subject", "verdict", "what closes it"],
      queue, widths=[8, 12, 10, 30, 34, 40],
      title_row=f"OPEN REVIEW QUEUE — {len(queue)} items carried by the "
                f"cascade as honest needs_review (UNfixed, ledger-only): "
                + ", ".join(f"{k} {v}" for k, v in qc.most_common())
                + ". Each closes with a page-image batch; none is a guess-fix.")

# ---------------- sheet 6 CASCADE_RESULTS
casc = [
    ["T1", "code identity/duplication", "1,377 candidate pairs",
     "distinct_by_kind 720 / era_variant 452 / unresolved 199 / dup-likely 5",
     "accumulators = by design; 5 dup-likely stay flagged"],
    ["T2", "gate G2 code ownership", "all rows", "gate PASS (owned codes recorded)",
     "no action"],
    ["T3", "code print agreement", "86 stage-2", "attested 76 / not-in-doc 3 / no_citation 7",
     "10 in OPEN_REVIEW_QUEUE"],
    ["T6", "unit text verbatim (10% sample)", "203 of 2,026 prose rows",
     "attested_verbatim 179 (88.2%) / mixed 15 / review 6 / no_citation 3",
     "6+3 in OPEN_REVIEW_QUEUE"],
    ["T7", "effective-session windows", "24 candidates",
     "attested carryover 6 / provenance review 18",
     "18 in OPEN_REVIEW_QUEUE; program_year bulk-default observed, 0 candidates"],
    ["T8", "branch/rule table agreement", "7 candidates",
     "attested 6 / era multi-scheme service row 1 (ECE-251)", "no fix needed"],
    ["T9", "book-entry identity within row", "211 flagged rows",
     "attested print-dup 16 / fallback 41 / drafting-side 71 / unverified 83",
     "112 in OPEN_REVIEW_QUEUE"],
    ["T10", "CO duplication across rows", "93 clusters / 197 rows",
     "print-attested 89 / drafting-side 1 / inconclusive 3",
     "shared-elective composition = by design"],
    ["T11", "cross-course same-code", "5 pairs + 3 xref",
     "0 collisions; 4 attested shared prints; 1 unverified UHV sha",
     "no action"],
    ["T12", "citation sha resolution", "all citations", "6 unresolved shas",
     "STAY flagged (PDFs not in corpus)"],
    ["T13", "buyer-grade 100-row audit", "100 rows, 10 checks",
     "clean 34 / minor 64 / issues 2 (BOP364+RTT602)",
     "2 in OPEN_REVIEW_QUEUE; 64 minor = history marks, not errors"],
]
sheet(wb, "CASCADE_RESULTS",
      ["test", "question", "scope", "verdict totals", "disposition"],
      casc, widths=[7, 26, 22, 48, 36],
      title_row="T1-T13 CASCADE RESULTS (all executed, ledger-only; "
                "CSV untouched since B81) — the corpus checks its own CSV "
                "against print, not the reverse.")

# ---------------- sheet 1 PATH_TO_CLEAN_CSV
path = [
    ["Step 0 — where the CSV stands",
     "3,080 subject rows, md5 95f41cfa…, flags 442 (375/65/2). "
     "The cascade verified it against print: 88.2% unit-text verbatim, 0 code "
     "collisions, 0 CO-dup errors, 0 flag mismatches. It is already "
     "faithful-as-print; the flags are honest markers, not dirt.",
     "no action"],
    ["Step 1 — B92 restore from print",
     "12 BOOK_TRUNC entries whose full printed text was located in the row's "
     "own cited docs + 2 DISPLAY_MISSING fills from subject_name_print. "
     "Value writes, page-image verified, print-wins.",
     "READY — needs owner go (multi-stage: this ledger = stage-1 evidence)"],
    ["Step 2 — B92 retire stale flags",
     "9 BOOK_TRUNC flags where print shows the stored text is already "
     "complete (incl. all 7 EME-603 entries). Flags-column change only.",
     "READY — same batch, evidence per row"],
    ["Step 3 — B92 slug-mapping fix",
     "2 BOOK_TRUNC flags whose audit slug doesn't match the row; re-run the "
     "probe for them after remap.",
     "READY — same batch"],
    ["Step 4 — page-image queue",
     "112 T9 + 18 T7 + 6 T6 + 2 T13 + 1 T10 + 10 T3 open review items: "
     "each closes by looking at the page image; results become either "
     "attested (flag retired) or an honest confirmed-flag. No guesses.",
     "PROPOSED — one batch each or owner-prioritized subset"],
    ["Step 5 — the 'clean' end state",
     "Zero unexplained cells: every value print-attested or explicitly "
     "flagged with a reason; TYPE_EMPTY stays empty where print states "
     "nothing. Faithful ≠ flag-free: the flags are the proof of fidelity.",
     "DEFINITION — owner sign-off requested"],
]
sheet(wb, "PATH_TO_CLEAN_CSV",
      ["step", "what it means concretely", "status"],
      path, widths=[30, 76, 36],
      title_row="OWNER QUESTION 2026-11-12: \"what do we do with the test "
                "results? I wanted the clean and faithful 'syllabus rich' "
                "CSV\" — THIS is the conversion of T1-T13 evidence into the "
                "clean CSV.")

wb.save(OUT_DL)
wb.save(OUT_REPO)
print("saved:", OUT_DL)
print("saved:", OUT_REPO)
print("restore:", len(restore), "ambiguous:", len(ambiguous), "retire:", len(retire),
      "queue:", len(queue))
