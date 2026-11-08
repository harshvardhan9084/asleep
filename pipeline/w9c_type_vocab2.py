#!/usr/bin/env python3
"""w9c_type_vocab2.py — W9c: W8c decision memo 71 (owner go "Do [...]
W8c memo 71] now", 2026-11-08).

The 71 TYPE_RAW rows (35 distinct undecided raw subject_type strings left in
w8c_decision_memo.json) are mapped onto the controlled vocab
{theory, lab, practical, core, departmental-elective, open-elective,
elective, value-added-mandatory} by the W8c recorded_copy method: each row
copies the subject_type of its own committed precedent class (same course +
name-token class / code-family siblings / recorded print category), with the
precedent cited in the corrections evidence. Zero-guess: no mapping without a
committed precedent or the row's own recorded print. Every write carries
corrections_json {field, before, after, rule, evidence} + quality_flags tag +
change_note (RULES §6b). subject_type_norm mirrors subject_type (W8c v2
schema D2). T2T 0; no keys; no rr_sid."""
import json
import re
import sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

rows = WC.load_rows()
by_id = {r["subject_id"]: r for r in rows}
fl = json.load(open(f"{WC.BASE}/audit_flags.json"))["rows"]

VA = "value-added-mandatory"
DE = "departmental-elective"
OE = "open-elective"

# --- raw-class mapping table (recorded_copy evidence per class) --------------
CLASS_MAP = {
    "project": None,  # per-row below
    "departmental": ("theory", "parallel committed core-theory rows of the same CBCS era "
                     "(e.g. BCS3xx-class theory rows); all 7 KCT rows are L-dominant "
                     "(L=3) with no practical print — contact-type recorded in the row"),
    "non-credit": (VA, "the row's own recorded print says non-credit; committed "
                   "non-credit precedent: sports rows value-added-mandatory "
                   "(BVA/BVA251 class, BTech/MBA/MCA x4)"),
    "scheme-only": None,  # per-row
    "activity-assessment": (VA, "committed NCMC/VA precedent (AGP151/AAC101 NCMC class); "
                            "the BC?754 activity-assessment slots are the same "
                            "mandatory non-credit assessment family"),
    "audit": (VA, "committed UHV/audit precedent: human-values rows are "
              "value-added-mandatory (BVA class); audit = mandatory non-credit"),
    "PES": (DE, "PES = Professional Elective Series (recorded subject_category_print "
            "'PES' on the rows); the vocab's professional-elective bucket is "
            "departmental-elective (committed BCT-05x/06x elective-slot family)"),
    "NCMC": (VA, "NCMC = Non-Credit Mandatory Course (print); NCMC class committed "
             "as value-added-mandatory (sports/VA precedent)"),
    "MDC": ("core", "BMBAI MBA-AI code-family siblings: core 15/16 committed "
            "(business-mathematics, business-law, financial-accounting...); the MDC "
            "label is the AICTE category print, the rows sit in the program core"),
    "IPR": ("core", "BMBAI MBA-AI siblings core 15/16; the rows are mini-project/"
            "dissertation (project class core: MBA project precedent core 3)"),
    "SEC": ("lab", "row names print 'Analytics and AI Lab 1/2' (recorded); SEC "
            "skill-lab class -> lab (committed lab-nature rows)"),
    "assessment": ("core", "internship-assessment/mini-project slot; internship/mini-"
                   "project precedent core (BTech internship core + MBA project core)"),
    "humanities": ("theory", "BAS301 Technical Communication: BAS first-year theory "
                   "family committed theory (BAS-101/301 class)"),
    "basic_science": ("theory", "BAS303 Mathematics-IV: maths precedent theory "
                      "(maths BTech theory 2 committed)"),
    "non-credit bridge course": (VA, "print says Non-Credit Bridge Course (recorded); "
                                 "non-credit -> VA (sports precedent)"),
    "activity": (VA, "startup-and-entrepreneurial-activity slot = activity-assessment "
                 "family -> VA (NCMC/VA precedent)"),
    "internship": ("practical", "BPharm training precedent practical 4/5 committed "
                   "(BP-xxx training rows); BP411I internship I-suffix"),
    "remedial": ("practical", "row name prints '(Practical)' (BP112RBP Remedial Biology "
                 "Practical); BPharm practical-family precedent"),
    "seminar": ("core", "BTech seminar precedent core 2/3 committed (seminar rows)"),
    "mini-project/internship": ("core", "mini-project/internship class core "
                                "(internship/mini-project precedent)"),
    "SDC": ("lab", "row name prints 'Innovation & Design Thinking Lab' (recorded); "
            "lab-nature committed rows"),
    "PEC": (DE, "PEC = Professional Elective Course (print); PES/PEC class -> "
            "departmental-elective (BCT-05x elective-slot family)"),
    "core-industrial-training": ("core", "name prints core-industrial-training; "
                                 "industrial-training precedent core 16 committed"),
    "scheme-row-only": (OE, "row primary_code KOE060 — KOE open-elective-slot code "
                        "family committed open-elective 34"),
    "camp": ("practical", "survey-camp precedent practical 1 committed (NCE654 class; "
             "camp rows are outdoor practical slots)"),
    "seminar-presentation": ("core", "seminar precedent core majority (technical-"
                             "presentation = seminar/presentation assessment slot)"),
    "engineering-science": (OE, "row primary_code KOE036 — KOE open-elective family "
                            "committed open-elective 34; 'engineering-science' is the "
                            "scheme's BS/ES category print, the slot is KOE"),
    "industrial-training": ("core", "industrial-training precedent core 16 committed"),
    "case-study": ("core", "RFT Food-Tech sibling rows: core 17/18 committed; "
                   "RFT-654 case-study is a sem-6 core assessment slot"),
    "Engineering": ("theory", "KEC101TH Emerging Domain in Electronics: TH-suffix "
                    "first-year theory family committed theory"),
    "Research Project Report & Viva Voce": ("core", "MBA project precedent core 3 "
                                            "committed (research project class)"),
    "Summer Training Project Report & Viva Voce": ("core", "training precedent core 3 "
                                                   "committed (BTech/MBA project class)"),
    "bridge-course": (VA, "row notes record doc stem 'mca_non-credit-bridge-elementary-"
                      "maths' — the print IS non-credit bridge -> VA (non-credit "
                      "class precedent)"),
    "as printed": (VA, "RHU001 Human Values & Professional Ethics (MCA) — UHV class "
                   "committed value-added-mandatory; raw 'as printed' was a draft "
                   "placeholder, the row's own class is the evidence"),
    "audit-course": (VA, "RCA-A01 recorded as audit course; audit class -> VA "
                     "(UHV/audit precedent)"),
}

# per-row overrides for the class-split raws
PER_ROW = {
    # project class
    "anatomy-physiology-pathophysiology-i-project": ("practical",
        "BOP-xxxP BPharm 2026-27 practical siblings: practical 16 committed"),
    "pharmaceutical-mathematics-and-biostatistics-project": ("practical",
        "BOP-125P practical sibling family (practical 16 committed)"),
    "anatomy-physiology-pathophysiology-iii-project": ("practical",
        "BOP-234P practical sibling family"),
    "pharmaceutical-jurisprudence-project-case-studies": ("practical",
        "BOP-245P practical sibling family"),
    "project": ("core", "BCA project precedent core committed (BBC rows core 17; "
                "BCA project core)"),
    "project-btech": ("core", "BTech project precedent core 9 committed"),
    "project-ii": ("core", "BTech project precedent core 9 committed (BCS851 Project-II)"),
    "project-semester-vii": ("core", "BTech project precedent core 9 committed "
                             "(EEE-753 sem-VII project)"),
    "project-semester-viii": ("core", "BTech project precedent core 9 committed "
                              "(EEE-851 sem-VIII project)"),
    "industrial-training-i-ii-evaluation-and-viva": ("core",
        "industrial-training precedent core 16 committed (EME-754 training-"
        "evaluation-viva slot)"),
    "gp": (VA, "NGP401 general-proficiency family = the NCMC/VA class (AGP151 NCMC "
           "committed value-added-mandatory)"),
    # scheme-only class
    "engineering-science-course-maths-v": (OE, "row all_codes KOE031-38 = the KOE "
                                           "open-elective pool family (open-elective 34)"),
    "maths-v-engineering-science-course": ("theory", "maths precedent theory"),
    "universal-human-values-technical-communication": (VA, "UHV slot family -> "
                                                       "value-added-mandatory (UHV/VA class)"),
    "maths-iv": ("theory", "maths precedent theory"),
    "universal-human-values": (VA, "UHV class value-added-mandatory committed"),
}


def main():
    targets = {}
    for sid, fls in fl.items():
        for f in fls:
            if f["rule"] == "TYPE_RAW":
                targets[sid] = by_id[sid]
    n_applied = 0
    per_row_counts = {}
    for sid, r in targets.items():
        raw = (r.get("subject_type") or "").strip()
        if sid in PER_ROW:
            tgt, ev = PER_ROW[sid]
        elif raw in CLASS_MAP and CLASS_MAP[raw]:
            tgt, ev = CLASS_MAP[raw]
        else:
            continue
        # name-structure guard: a row printing 'Lab' never maps below lab-nature
        before_t, before_n = r.get("subject_type", ""), r.get("subject_type_norm", "")
        r["subject_type"] = tgt
        r["subject_type_norm"] = tgt
        cj = json.loads(r.get("corrections_json", "") or "[]")
        cj.append({"field": "subject_type", "before": before_t, "after": tgt,
                   "rule": "W9c/TYPE_VOCAB_PRECEDENT",
                   "evidence": "W8c memo adjudication (owner go 2026-11-08): " + ev,
                   "wave": "W9c"})
        r["corrections_json"] = json.dumps(cj, ensure_ascii=False)
        r["verification_status"] = "corrected"
        qf = [t for t in (r.get("quality_flags", "") or "").split(";") if t]
        if "corrected_TYPE_VOCAB_PRECEDENT" not in qf:
            qf.append("corrected_TYPE_VOCAB_PRECEDENT")
        r["quality_flags"] = ";".join(qf)
        seg = "W9c(§6b): subject_type -> controlled vocab via committed precedent class (W8c memo adjudication, before preserved)"
        if seg not in (r.get("change_note_vs_previous", "") or ""):
            prev = r.get("change_note_vs_previous", "") or ""
            r["change_note_vs_previous"] = (prev + "; " if prev else "") + seg
        n_applied += 1
        per_row_counts.setdefault(raw, 0)
        per_row_counts[raw] += 1
    WC.commit(rows, "W9c", n_applied, {"note": "gates by caller"},
              meta_extra={"wave": "W9c", "rows": n_applied,
                          "by_raw": per_row_counts})
    print(f"W9C_APPLY|rows={n_applied}|by_raw={json.dumps(per_row_counts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
