#!/usr/bin/env python3
"""Owner-commissioned quality-test plan + PDF-DNA report. All numbers freshly measured
2026-11-11 from the B80 CSV (md5 b1da9c97) and the repo corpus tree @ c2909b4."""
import sys, os
XLSX_SKILL_DIR = "/home/z/my-project/skills/xlsx"
for sub in [XLSX_SKILL_DIR, os.path.join(XLSX_SKILL_DIR, "templates")]:
    if sub not in sys.path:
        sys.path.insert(0, sub)
from openpyxl import Workbook
from openpyxl.styles import Alignment
import base as B

OUT = "/home/z/my-project/download/quality_test_plan_2026-11-11.xlsx"
wb = Workbook(); wb.properties.creator = "Z.ai"

def put(ws, r, c, v, style="body", wrap=False):
    cell = ws.cell(row=r, column=c, value=v)
    if style == "title": cell.font = B.font_title(); cell.alignment = B.align_title()
    elif style == "header": cell.font = B.font_header(); cell.fill = B.fill_header(); cell.alignment = B.align_header()
    elif style == "sub": cell.font = B.font_subheader()
    elif style == "cap": cell.font = B.font_caption()
    else: cell.font = B.font_body()
    if wrap: cell.alignment = Alignment(wrap_text=True, vertical="top", horizontal="left")
    return cell

def zebra(ws, r, i, c0, c1):
    f = B.fill_data_row(i)
    for c in range(c0, c1 + 1): ws.cell(row=r, column=c).fill = f

# ---------------- Sheet 1: test catalog
ws = wb.active; ws.title = "Test catalog"
widths = {"A":2.5,"B":7,"C":26,"D":20,"E":52,"F":40,"G":9,"H":16}
for col,w in widths.items(): ws.column_dimensions[col].width = w
put(ws, 2, 2, "Quality-test catalog - iterative cascade design (light marking at every stage; no CSV write until multi-stage confirmation)", "title")
hdr = ["ID","Test","Columns used","Cascade stages (collect -> check -> confirm)","Action if confirmed","Priority","Expected yield"]
r=4
for c,h in enumerate(hdr,2): put(ws,r,c,h,"header",wrap=True)
ws.row_dimensions[r].height=28; r+=1
tests = [
 ("T1","Duplicate-subject detection (owner spec)","subject_name, subject_name_print, course_name, program_year, unit1..unit5_text, primary_code, all_codes, semester_slots",
  "Stage 0: partition by course_name (+program_year) - same-name across BTech/BCA/MCA is NOT duplication (owner's data-structure example). Stage 1: name-similarity grouping within course (exact normalized match + token-Jaccard>=0.6) -> candidates to probe ledger ONLY. Stage 2: read unit3_text (owner's pick) then all units for candidates - squash-containment / Jaccard. Stage 3: code-family overlap (all_codes).",
  "All three agree -> recorded adjudication class (merge candidate, never auto-merge; print-proven same subject only). Disagree -> row stands, ledger note 'distinct-evidence'.","P0","~20-60 candidate pairs by name; true dups expected rare (define-once model + G3 subject idempotency already ran)"),
 ("T2","Code double-ownership re-audit","primary_code, all_codes, code_history_all, course_name, effective_session_latest",
  "Stage 1: same normalized code claimed by 2 rows within one course+session. Stage 2: cited scheme pages of both rows. Stage 3: latest-print-wins per B67/B75 precedent.",
  "Only if print-proven: retarget or alternative-pair-slot flag.","P3","~0 (G2 gate live, 0 dups) - standing regression guard"),
 ("T3","Code-name mismatch","primary_code, subject_name, subject_name_print, notes, source_scheme_line",
  "Stage 1: code family (e.g. NCS/NME/KCS) vs subject_name domain - rule table per AKTU code grammar. Stage 2: for hits, page-check the row's own cited scheme line.",
  "Print-proven mismatch -> fix or retarget per B20/B76 classes; else ledger note.","P2","low single digits, high buyer value"),
 ("T4","Marks arithmetic re-test (accepted-print precedence)","credit, sessional_ct, sessional_ta, sessional_total, ese_te_pe, total_marks, source_scheme_line",
  "Stage 1: recompute sums from printed components; collect mismatches (335 such flags exist). Stage 2: page-image check of the row's own scheme line - AKTU's own tables are known to break arithmetic (B67: 12 accepted-print). Stage 3: latest-print-wins.",
  "AKTU-print-confirmed -> accepted-print flag (drop as honest). Extraction error -> fix per 6b(4) with scheme-line proof.","P2","~335 flags re-adjudicated, several more honest drops expected"),
 ("T5","Derivation fill (owner-authorized: calculate, never invent)","sessional_total, ese_te_pe, total_marks, corrections_json",
  "Stage 1: rows with total_marks empty but BOTH components printed = 5 rows (measured; 629 of 641 empties have zero components printed - truly not-printed, left blank by design). Stage 2: re-verify component cells carry citations.",
  "Write total_marks = component sum, rule=derived_sum_components, evidence=cited component cells, flag derived_not_printed (transparent, not silent).","P0","5 rows - small but exactly the owner's invent-vs-calculate boundary"),
 ("T6","Unit-text cross-contamination (sampled)","unit1..unit5_text, source_syllabus, notes",
  "Stage 1: random 10% of unit-bearing rows. Stage 2: squash-containment of each unit in its row's OWN cited doc text layer (parsed cache). Stage 3: failures page-imaged.",
  "Contaminated unit -> re-extract from cited page per 6b; containment-gap -> documented G6 class.","P1","expected ~0-2% (G6 covers touched rows only - this extends coverage)"),
 ("T7","Semester/year coherence","semester_slots, program_year, effective_session_latest, primary_code, code_history_all",
  "Stage 1: code-era grammar (E/N/R/K/A generations) vs printed session/year sanity. Stage 2: hits page-checked against cited scheme.",
  "Fix per print or flag needs_review.","P2","low"),
 ("T8","Branch coherence","branch_names, primary_code, all_codes, subject_name",
  "Stage 1: code family vs branch (NME->ME, KCS->CSE...) rule table. Stage 2: hits checked against cited scheme page.",
  "Fix or flag.","P2","low"),
 ("T9","Book-entry identity within row","textbooks_structured, reference_books_structured",
  "Stage 1: fuzzy title+author duplicates within one row's structured lists (squash-normalized). Stage 2: cited book pages.",
  "Deduplicate with corrections_json before/after.","P2","modest (W2/W6 already cleaned 902+978 entries)"),
 ("T10","CO duplication across rows","co1..co6_text, subject_name",
  "Stage 1: identical CO spans across different subjects (squash-normalized). Stage 2: verify each row's own cited doc prints them.",
  "Copy-paste contamination -> re-extract; genuinely same printed COs -> keep + note.","P2","unknown, worth measuring"),
 ("T11","Cross-course same-code consistency","all_codes, subject_name, unit1..unit5_text, course_name",
  "By design the same printed code may be owned once PER COURSE (G2 rule). Stage 1: same code in 2 courses with same name. Stage 2: unit-content divergence check (OOS-split precedent).",
  "Divergent content -> recorded split note (same-core-different-tail class); identical -> no-op.","P3","BCA/MCA share several BTech codes"),
 ("T12","Citation integrity","source_history, source_syllabus, source_scheme_line, notes, corrections_json",
  "Stage 1: every cited sha16 must exist in the repo corpus (437 cited today; 3 sha_unresolved known from B78). Stage 2: corpus md5 re-verification.",
  "Unresolvable shas stay documented (corpus-loss class).","P3","3 known, stable"),
 ("T13","Independent buyer-grade spot audit (sells to Microsoft)","all key fields",
  "Random 100 rows; human/VLM page-image verification of subject_name, units, scheme numbers vs the cited PDF pages; scored pass rate.",
  "Independent quality certificate for the dataset (all current audits are instrumented self-audits).","P1","the single biggest trust-raiser for a buyer"),
]
for i,t in enumerate(tests):
    for c,v in enumerate(t,2): put(ws,r,c,v,wrap=True)
    zebra(ws,r,i,2,8)
    ws.row_dimensions[r].height = 64
    r+=1
put(ws,r+1,2,"Standing mechanics: every stage writes ONLY to work/pipeline_v2/probes/<test_id>.json (ledger keyed sid::field, like the existing w9a/w10c checkpoints). quality_flags change only after multi-stage confirmation via recorded adjudication. CSV writes only through gates G1/G2/G3/G6 + push_catalog.sh. No stage ever invents values.", "cap", wrap=True)
ws.merge_cells(start_row=r+1,start_column=2,end_row=r+3,end_column=8)
ws.freeze_panes="B5"

# ---------------- Sheet 2: derivation vs invention (measured)
ws2 = wb.create_sheet("Derivation vs invention")
ws2.column_dimensions["A"].width=2.5; ws2.column_dimensions["B"].width=58; ws2.column_dimensions["C"].width=46
put(ws2,2,2,"'Calculate is not invent' - measured on the current file (B80, 3,085 rows)", "title")
r=4
put(ws2,r,2,"Question", "header"); put(ws2,r,3,"Measured answer", "header"); r+=1
facts=[
 ("total_marks empty rows","641"),
 ("  ...with BOTH sessional_total and ese_te_pe printed (pure arithmetic, derivable NOW)","5  -> T5 will fill with derived_not_printed flag"),
 ("  ...with exactly one component printed (sum not computable, nothing to invent)","7"),
 ("  ...with ZERO components printed anywhere in sources (AKTU never printed it)","629 -> stays blank: blank means not-printed, never unknown"),
 ("credit empty rows","407; 0 have LTP printed - no attested derivation rule exists in corpus, so nothing calculable"),
 ("subject_type empty rows (375 flags)","0 of 375 have any category print - genuinely not-printed, both auditor arms exhausted (B79)"),
 ("Owner's principle applied","Inventing = writing a value no print supports (forbidden, RULES 6b). Calculating = arithmetic on printed components (authorized, evidence = the component cells; transparently flagged as derived, never silent)."),
]
for i,(k,v) in enumerate(facts):
    put(ws2,r,2,k,wrap=True); put(ws2,r,3,v,wrap=True); zebra(ws2,r,i,2,3); r+=1

# ---------------- Sheet 3: PDF DNA & corpus
ws3 = wb.create_sheet("PDF DNA & corpus")
ws3.column_dimensions["A"].width=2.5; ws3.column_dimensions["B"].width=58; ws3.column_dimensions["C"].width=52
put(ws3,2,2,"How much PDF DNA is in the CSV, and where the PDFs live", "title")
r=4
put(ws3,r,2,"Item", "header"); put(ws3,r,3,"Verified value", "header"); r+=1
dna=[
 ("Distinct source PDFs cited somewhere in the CSV (the data's DNA)","437 (scan of #sha16 fingerprints across ALL columns)"),
 ("Rows carrying >=1 citation","3,085 of 3,085 = 100% provenance"),
 ("Total citation tokens in the CSV","24,140"),
 ("Corpus actually processed by the pipeline","448 charter PDFs = 434 done + 14 failed (queue baseline)"),
 ("Corpus physical location","Inside the repo itself: asleep/PDFs/5-course/<session>/<file>.pdf (survives every workspace wipe; each doc has md5+sha16 identity)"),
 ("Where the PDFs come from","AKTU's own published syllabus / evaluation-scheme documents, collected per session into the repo (registry README charter)"),
 ("Session span","2004-05 through 2026-27 (23 sessions + 21 undated)"),
 ("Cited-doc spread by course (rows' course)","BTech 345 / MBA 48 / MCA 27 / BPharm 14 / BCA 6 - BTech-heavy by document count; MBTech has many branches x years x sessions"),
 ("EXPANSION: unprocessed other-course PDFs already in the repo","165 (PDFs/other_courses/: B.Voc, M.Tech, M.Pharm, AICTE model docs, unknowns) - zero of them ingested; the 5-course scope was the written charter (README)"),
 ("Complete-AKTU expansion cost","~165 docs at the historical pace of ~10 docs/batch = ~17 batches; plus charter update (README + RULES 1b course guard) + queue rebuild. Needs owner charter decision; no ingestion started in this run."),
]
for i,(k,v) in enumerate(dna):
    put(ws3,r,2,k,wrap=True); put(ws3,r,3,v,wrap=True); zebra(ws3,r,i,2,3); r+=1

wb.save(OUT); print("saved:", OUT)
