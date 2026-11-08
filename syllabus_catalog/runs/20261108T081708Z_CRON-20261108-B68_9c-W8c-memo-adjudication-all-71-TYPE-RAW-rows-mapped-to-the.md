# CRON-20261108-B68 — W9c W8c decision memo 71 (owner go: "Do [BOOK_TRUNC 574, scheme adjudications 401, W8c memo 71] now")

## Scope
The 71 TYPE_RAW rows (35 distinct raw subject_type strings left undecided in
w8c_decision_memo.json since B64). Owner's "Do ... now" = the go decision the
memo was waiting for; adjudication stays evidence-based (W8c recorded_copy method).

## Method
Each row copies the committed subject_type of its own precedent class — same-course
name-token siblings (project/seminar/training/sports/maths/camp families), code-family
siblings (BMBAI core 15/16, BOP-xxxP practical 16, KOE open-elective 34, BBC BCA core 17,
RFT core 17), or the row's own recorded print (PES/PEC/NCMC category prints, 'Non-Credit
Bridge Course', '(Practical)', '...Lab' names, KMBI MBA-AI core sequence). Guards:
contact-type from the row's recorded L/T/P (all 7 KCT 'departmental' rows are L=3 ->
theory); print-faithfulness (print says non-credit/audit -> value-added-mandatory,
the vocab's mandatory-non-credit bucket).

## Mapping (35 raws -> 71 rows, all applied)
project->practical x4 (BOP-xxxP) / core x7 (BTech/BCA/EEE sem projects, EME-754);
departmental->theory x7; non-credit/NCMC/audit/audit-course/activity/activity-assessment/
non-credit bridge/bridge-course/as printed (UHV)->value-added-mandatory x21;
PES x3 + PEC x1 ->departmental-elective; MDC x2 + IPR x2 ->core (BMBAI core family);
SEC x2 + SDC x1 ->lab; scheme-only/scheme-row-only/engineering-science ->open-elective x3
+ maths theory x2 + UHV VA x1; internship->practical; remedial->practical;
seminar/seminar-presentation/assessment/mini-project-internship/case-study/core-industrial-
training/industrial-training/Research+Summer Project->core x9; humanities/basic_science/
Engineering(KEC101TH)->theory x3; camp->practical.

## Gates / push
G1 PASS, G2 PASS (6,412 owned codes), G3 PASS, G6 PASS (34 containment checks incl.
the recorded OCR_PRIOR_SKIP class). subject_type + subject_type_norm set together
(schema D2); corrections_json before/after per row; TYPE_RAW 71 -> 0 in re-audit.
T2T calls: 0 (deterministic; keys 5/5 untouched).
