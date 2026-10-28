# AKTU Syllabus Draft Extraction Task

You are extracting a VERBATIM syllabus draft for the AKTU open-source catalog.
You MUST first read `/home/z/my-project/scripts/pipeline_v2/RULES.md` — it is
the constitution. Obey §6 (text-layer), §7 (draft spec), §8 (your protocol)
exactly. Zero guessing: if the PDF does not print it, leave it out.

## Inputs
- PDF_PATH: `{PDF_PATH}`
- PDF_REL: `{PDF_REL}`
- PARSED_JSON: `{PARSED_JSON}` (per-page text layer)
- FULLTEXT: `{FULLTEXT}` (full text with ===== PAGE n ===== markers)
- DRAFT_OUT: `{DRAFT_OUT}` (your output draft JSON)
- SESSION: `{SESSION}` (document's effective session, e.g. 2023-24)

## Method
1. Read PARSED_JSON and FULLTEXT completely. If the text layer is garbled for
   a region, Read the PDF page image (Read tool on PDF_PATH, use `pages`
   parameter) — the VISIBLE PRINT is authoritative (RULES §6).
2. Identify EVERY subject the document details: its printed name, ALL printed
   codes (including H variants and sessional/lab codes printed in its own
   tables), semester, printed L-T-P, credit, marks breakdown, subject type,
   full verbatim unit texts (Unit-I..V), course outcomes with K-levels,
   textbooks, reference books, experiments/practice lists, printed objectives,
   eligibility, prerequisites.
3. Verbatim discipline: transcribe print exactly, including typos. Record
   decode artifacts/garbled fragments in `quirks` (RULES §6). Blank cell =
   printed blank: omit the key rather than inventing a value.
4. Ignore university boilerplate headers/footers and page furniture.
5. Append each subject to DRAFT_OUT INCREMENTALLY: after finishing each
   subject, run a small python snippet that loads DRAFT_OUT (create it with
   pdf_rel/session/course/sha16/stem headers on first write) and appends the
   subject dict to `subjects`. Never hold everything in memory until the end.
6. Put anything that is printed but is NOT a subject (scheme summary lines,
   notes like MOOC rules, eligibility footnotes) into `non_subject_rows` with
   kind + verbatim print + page locator. Do not drop them silently.

## Output
- DRAFT_OUT per RULES §7. Every subject needs at minimum: name, name_print,
  codes, units (verbatim), cos, textbooks/reference_books if printed.
- FINAL MESSAGE: at most 6-10 lines — subject count, code list summary, quirk
  count, flags. Do NOT paste content into the final message (transport
  timeouts). A lost final message is acceptable if DRAFT_OUT is complete.
