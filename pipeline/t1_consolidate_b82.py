#!/usr/bin/env python3
"""t1_consolidate_b82.py — CRON-20261111-B82 (T1 duplicate consolidation).

Resolves the 5 T1 duplicate_likely_code_gap findings from the owner
quality-test cascade (§6b page-evidence pass recorded in
work/pipeline_v2/probes/t1_evidence_ledger.json):

  ALLOW — consolidate into the define-once accumulator row (codes + code
  history + provenance unioned; secondary row deleted; NO content fields
  (units/COs/books/marks) transferred; sessions never invented):
    1. control-system              <- control-system-i            (EIC-501/RBM501/RIC603)
    2. i-c-engine-fuels-lubrication<- i-c-engine-fuel-lubrication (BME052/BME054)
    3. computer-aided-design       <- computer-aided-design-cad   (NME-701/EME-701)
    4. pharmaceutical-chemistry-vi-medicinal-chemistry-ii
                                  <- pharmaceutical-chemistry-vii-medicinal-chemistry-ii (RPH-627)
    5. net-framework-and-c         <- dot-net-framework-c         (RCAI-702/MCA-512)

  DEMOTE (keep separate — recorded reason, no CSV change):
    microcontroller-embedded-systems-design vs microcontroller-for-embedded-systems
    (units 1-2 shared >=0.999 but units 3-5 diverge <0.13 — the recorded B28
    same-core-different-tail split class, OOS ECS-305 precedent).

Every merge cites both rows' printed subject names from their OWN cited docs
(fitz text layer, page-cited). Classes exercised: TIER2-ALLOW era/branch
accumulator (B28 ITC/FEM precedents). Usage: --dry-run (default) | --apply
"""
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import merge_draft as MD  # gate_g1/g2/g3/g6, REF_HEADER (stdlib-only import)

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
FLAGS_PATH = "/home/z/my-project/work/pipeline_v2/audit_flags.json"
PARSED_DIR = "/home/z/my-project/work/pipeline_v2/parsed"
BACKUP_DIR = "/home/z/my-project/work/pipeline_v2/backup"
RESULT_PATH = "/home/z/my-project/work/pipeline_v2/t1_b82_result.json"
ADJ_PATH = "/home/z/my-project/work/pipeline_v2/probes/t1_adjudication_b82.json"
AUDIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_rules.py")

DEMOTION = {
    "pair": ["microcontroller-embedded-systems-design",
             "microcontroller-for-embedded-systems"],
    "decision": "DEMOTE (keep separate)",
    "class": "same_core_diff_tail(B28class)",
    "reason": ("units 1-2 shared (0.999/1.0) but units 3-5 diverge (0.094/0.121/0.016) "
               "— the recorded B28 same-core-different-tail split class (OOS ECS-305 "
               "Java-vs-C++ precedent): 'MICROCONTROLLER & EMBEDDED SYSTEMS DESIGN' "
               "(KEC-061, 2020-21 ECE doc) and 'MICROCONTROLLER FOR EMBEDDED SYSTEMS' "
               "(REC062 2018-19 -> KECZ-061/BECZ061 2021-22 EC docs) are different "
               "subjects sharing an intro core. KEC-061/KECZ-061 slot-print proximity "
               "recorded as an observation; no CSV change."),
}

MERGES = [
    {
        "primary": "control-system",
        "secondary": "control-system-i",
        "class": "TIER2-ALLOW era/branch accumulator (B28 ITC precedent)",
        "codes_added": ["EIC-501", "RBM501", "RIC603"],
        "evidence": (
            "primary prints: 'CONTROL SYSTEM' btech_act_y3_syllabus-rev_2025-26.pdf"
            "#328fc29743da6525 p.22 (scheme p.3 'BEC602 Control System'); "
            "'NIC-501 CONTROLSYSTEM-I' btech_applied-electronics-ece-ei_syllabus_2016-17.pdf"
            "#3fb28b3b8722cb6d p.5 — the accumulator's OWN 2016-17 era already prints "
            "Control-System-I. secondary prints: 'EIC 501 CONTROL SYSTEM I' "
            "btech_bme_syllabus_2009-10.pdf#5cc5a89a9c439987 p.6 (scheme p.4 'EIC-501 "
            "Control System-I'); 'CONTROL SYSTEM- I' btech_bme_y3_syllabus_2017-18.pdf"
            "#9b9305a2b763d1e5 p.4 (RBM501); 'RIC603 CONTROL SYSTEM-I' "
            "btech_ei_y3_scheme-syllabus_2018-19.pdf#0a0c4a294e3e51f1 p.19."),
        "units": "T1 stage-2 unit ratios {2:0.948, 3:0.557, 4:1.0, 5:0.874} shared; "
                 "unit1 0.076 = BME-era rewording (DC-motors emphasis), not a different subject",
    },
    {
        "primary": "i-c-engine-fuels-lubrication",
        "secondary": "i-c-engine-fuel-lubrication",
        "class": "TIER2-ALLOW era/print-variant accumulator (B28 TAFL typo-variant precedent)",
        "codes_added": ["BME052"],
        "evidence": (
            "primary prints: 'Subject Code: KME 054' btech_au_syllabus_2020-21.pdf"
            "#d6b5abb82266b6a5 p.15 (TOC p.4 'KME 054 I C Engine, fuels & lubrication'); "
            "'BME 054- I C Engine, Fuels & Lubrication' btech_au_y3_syllabus_2024-25.pdf"
            "#791e1e692a29bd76 p.20. secondary prints: 'BME 052 - I C Engine Fuel & "
            "Lubrication' btech_me-ind_y3_evaluation-scheme_2024-25.pdf#9c81bf6940829c7d "
            "p.16 AND btech_me_y3_scheme_2024-25.pdf#6c00370d9f7d0ba5 p.17. AKTU "
            "cross-doc slot inconsistency recorded: the AU 2024-25 doc prints 'BME 052- "
            "Mechatronics Systems' p.22 while ME-Ind/ME 2024-25 docs print BME 052 as "
            "this subject; BME052 ownership taken per the ME-Ind/ME prints + unit agreement. "
            "BME054 NOT unioned into all_codes: already owned by mechatronic-systems per "
            "its establishing print (G2 code-owner rule, B20 class); the AU 2024-25 print "
            "'BME 054- I C Engine, Fuels & Lubrication' p.20 stays recorded in this row's "
            "code_history_all as the same cross-doc slot inconsistency."),
        "units": "T1 stage-2 unit ratios all five 0.988-0.995 (same syllabus, "
                 "singular/plural + comma print variant)",
    },
    {
        "primary": "computer-aided-design",
        "secondary": "computer-aided-design-cad",
        "class": "TIER2-ALLOW multi-branch accumulator (B28 FEM precedent)",
        "codes_added": ["NME-701", "EME-701"],
        "evidence": (
            "primary prints: 'ECE 051 - Computer Aided Design' btech_ce_syllabus_2010-11.pdf"
            "#441c7c04a2569344 p.6 (detailed p.27 'ECE – 051 COMPUTER AIDED DESIGN'); "
            "'NCE 051 - Computer Aided Design' btech_ce_y4_syllabus_2016-17.pdf"
            "#52245ed4397dccfc p.3 (detailed p.16). secondary prints: 'NME-701: "
            "COMPUTER AIDED DESIGN (CAD)' btech_me-ind-pe-ipe_y4_syllabus_2016-17.pdf"
            "#567c7444bd3db972 p.4; 'EME-701 : COMPUTER AIDED DESIGN (CAD)' "
            "btech_me-pe_syllabus_2009-10.pdf#c46b141f3ee05115 p.39. Identical unit "
            "text printed across the CE/ME/ME-PE branch schemes (T1 units all 1.0) — "
            "one AKTU-wide subject, branch-specific codes."),
        "units": "T1 stage-2 unit ratios all five 1.0",
    },
    {
        "primary": "pharmaceutical-chemistry-vi-medicinal-chemistry-ii",
        "secondary": "pharmaceutical-chemistry-vii-medicinal-chemistry-ii",
        "class": "TIER2-ALLOW scheme-renumbering accumulator (B28 era-family precedent)",
        "codes_added": ["RPH-627"],
        "evidence": (
            "primary prints: 'PHARMACEUTICAL CHEMISTRY-VI' + '(MEDICINAL CHEMISTRY-II)' "
            "+ 'BOP-361' bpharm_syllabus.pdf#e427b15176573f9d p.16 (scheme p.2 'BOP-361 "
            "(Medicinal Chemistry-II)'; practical BOP-361P p.17). secondary prints: "
            "'PHARMACEUTICAL CHEMISTRY-VII (MEDICINAL CHEMISTRY-II)' "
            "bpharm_y3_scheme-syllabus-cbcs-rev.pdf#b2d1ea61547479fd p.16 (scheme p.2 "
            "'RPH-627 (Medicinal Chemistry-II)'; practical RPH-627P p.17). The CBCS-rev "
            "scheme renumbers the SAME sem-6 course VI->VII (its PC-VI = Medicinal "
            "Chemistry-I sem-5 p.3/p.5); the parenthetical subject identity "
            "'(MEDICINAL CHEMISTRY-II)' is stable and units 1-4 are verbatim identical."),
        "units": "T1 stage-2 unit ratios {1:1.0, 2:1.0, 3:1.0, 4:1.0, 5:0.09} — "
                 "unit5 revised between scheme prints",
    },
    {
        "primary": "net-framework-and-c",
        "secondary": "dot-net-framework-c",
        "class": "TIER2-ALLOW era/print-variant accumulator (B28 era-family precedent)",
        "codes_added": ["RCAI-702", "MCA-512"],
        "evidence": (
            "primary prints: 'NET FRAMEWORK AND C#' + 'MCA 503' mba_electives_2004-05_2.pdf"
            "#ab5c068f2ca37915 p.24; '.NET FRAMEWORK & C#' + 'NBC-701' "
            "mca-dd_y4-5_syllabus_2016-17.pdf#4c4757568f431526 p.1/p.3 ('NBC-701 : .Net "
            "Framework and C#'). secondary prints: 'RCAI-702 Dot Net Framework & C#' "
            "mca-integrated_y4_syllabus_2020-21.pdf#b3c5743eb5e159b5 p.2/p.4; 'MCA 512: "
            "Dot Net Framework and C#' mca_y3_syllabus_2010-11.pdf#a4f273baab09cdb9 p.4 "
            "(scheme p.2 'Dot Net Framework & C#' wrapped across two lines). One subject "
            "across five code eras (MCA503 -> MCA-512 -> NBC-701/NMCA513 -> RCAI-702)."),
        "units": "T1 stage-2 unit ratios all five 1.0",
    },
]

SHA_RE = re.compile(r"#([0-9a-f]{16})")


def snapshot(r):
    return {
        "subject_name": r.get("subject_name"),
        "name_print": (r.get("subject_name_print") or "")[:120],
        "primary_code": r.get("primary_code"),
        "all_codes": r.get("all_codes"),
        "first_introduced_session": r.get("first_introduced_session"),
        "effective_session_latest": r.get("effective_session_latest"),
        "units_filled": sum(1 for i in range(1, 6) if (r.get(f"unit{i}_text") or "").strip()),
        "quality_flags": r.get("quality_flags"),
    }


def append_codes(primary, codes):
    have = [c.strip() for c in (primary.get("all_codes") or "").split(";") if c.strip()]
    added = []
    for c in codes:
        if c not in have:
            have.append(c)
            added.append(c)
    primary["all_codes"] = ";".join(have)
    return added


def append_history(primary, secondary, sid):
    ch = (primary.get("code_history_all") or "").rstrip()
    add = (secondary.get("code_history_all") or "").strip()
    if add:
        piece = f" | T1-B82 merge from {sid} (chain verbatim): {add}"
        primary["code_history_all"] = ch + piece if ch else piece


def append_sources(primary, secondary):
    have = set(SHA_RE.findall(primary.get("source_history") or ""))
    have |= set(SHA_RE.findall(primary.get("source_syllabus") or ""))
    entries = [e.strip() for e in (secondary.get("source_history") or "").split(";") if e.strip()]
    add = [e for e in entries if not (set(SHA_RE.findall(e)) & have)]
    if add:
        primary["source_history"] = (primary.get("source_history") or "").rstrip() + "; " + "; ".join(add)
    sl = (secondary.get("source_scheme_line") or "").strip()
    if sl:
        primary["source_scheme_line"] = ((primary.get("source_scheme_line") or "").rstrip()
                                         + " | merged-row scheme line: " + sl)


def main():
    apply = "--apply" in sys.argv
    rows = list(csv.DictReader(open(CSV_PATH)))
    fields = list(rows[0].keys())
    assert fields == MD.REF_HEADER, "header drift vs REF_HEADER"
    by_id = {r["subject_id"]: r for r in rows}
    n0 = len(rows)

    adjudication = {
        "batch": "CRON-20261111-B82",
        "test": "T1 duplicate consolidation (§6b page-evidence pass)",
        "evidence_ledger": "work/pipeline_v2/probes/t1_evidence_ledger.json",
        "merges": [], "demotions": [DEMOTION],
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "applied": bool(apply),
    }
    deletes, touched = [], set()
    total_added = []

    for m in MERGES:
        p, s = by_id.get(m["primary"]), by_id.get(m["secondary"])
        if not p or not s:
            print(f"MISSING {'primary' if not p else 'secondary'} {m['primary']}/{m['secondary']}")
            sys.exit(2)
        rec = {"pair": [m["primary"], m["secondary"]], "decision": "ALLOW (consolidate)",
               "class": m["class"], "evidence": m["evidence"], "unit_agreement": m["units"],
               "secondary_snapshot": snapshot(s), "applied_fields": {}}
        if apply:
            added = append_codes(p, m["codes_added"])
            append_history(p, s, m["secondary"])
            append_sources(p, s)
            note = (f"T1 B82 consolidation: merged {m['secondary']} "
                    f"({s.get('subject_name')}) into this define-once row — same subject "
                    f"per §6b page evidence, both prints cited in corrections_json; "
                    f"codes {','.join(m['codes_added'])} unioned; code-history chain and "
                    f"source provenance carried verbatim; no content fields transferred.")
            for col, piece in (("notes", note),):
                r_old = (p.get(col) or "").rstrip()
                p[col] = (r_old + (" " if r_old else "") + piece)
            try:
                cj = json.loads(p.get("corrections_json", "") or "[]")
            except Exception:
                cj = []
            cj.append({
                "field": "row_merge",
                "before": f"two rows: {m['primary']} ({p.get('subject_name')}) + "
                          f"{m['secondary']} ({s.get('subject_name')})",
                "after": f"one define-once row {m['primary']} owning codes "
                         f"{(p.get('all_codes') or '')}",
                "rule": "T1_TIER2_ALLOW_CONSOLIDATION",
                "evidence": m["evidence"] + " Unit agreement: " + m["units"],
                "wave": "T1-B82",
            })
            p["corrections_json"] = json.dumps(cj, ensure_ascii=False)
            cn = (p.get("change_note_vs_previous") or "").rstrip()
            p["change_note_vs_previous"] = (
                cn + (" | " if cn else "")
                + f"T1 B82 TIER2-ALLOW consolidation: absorbed {m['secondary']} "
                  f"({s.get('subject_name')}) — duplicate_likely_code_gap resolved ALLOW "
                  f"per §6b page evidence (class: {m['class']}); row deleted.")
            deletes.append(m["secondary"])
            touched.add(m["primary"])
            rec["applied_fields"] = {
                "codes_added": added,
                "code_history_appended": bool((s.get("code_history_all") or "").strip()),
                "source_entries_added": len(set(SHA_RE.findall(p.get("source_history") or ""))
                                            - set(SHA_RE.findall(snapshot(s)["all_codes"] or ""))),
                "corrections_entries": len(cj),
            }
            total_added += added
        adjudication["merges"].append(rec)

    print(f"B82|plan|rows {n0} -> {n0 - len(deletes)}|merges={len(MERGES)}"
          f"|codes_added={total_added}|demote=1 (recorded only)")

    if not apply:
        for m in MERGES:
            print(f"  DRY {m['secondary']} -> {m['primary']} codes {m['codes_added']}")
        json.dump(adjudication, open(ADJ_PATH, "w"), indent=1, ensure_ascii=False)
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    bkp = os.path.join(BACKUP_DIR, f"pre_commit_B82_{stamp}.csv")
    shutil.copy2(CSV_PATH, bkp)

    rows = [r for r in rows if r["subject_id"] not in set(deletes)]
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MD.REF_HEADER, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    g1 = MD.gate_g1(MD.REF_HEADER)
    g2, ncodes = MD.gate_g2(rows)
    g3 = MD.gate_g3(rows)
    g6, checks = MD.gate_g6(rows, touched, PARSED_DIR)
    gates = {"G1": g1 or "PASS", "G2": (g2 or f"PASS codes={ncodes}"),
             "G3": g3 or "PASS", "G6": (g6 or f"PASS containment_checks={checks}")}
    print("GATES|" + " | ".join(f"{k} {v}" for k, v in gates.items()))
    adjudication["gates"] = gates
    adjudication["rows"] = {"before": n0, "after": len(rows)}
    adjudication["codes_added"] = total_added

    if g1 or g2 or g3 or g6:
        json.dump(adjudication, open(ADJ_PATH, "w"), indent=1, ensure_ascii=False)
        print("GATE_FAIL|CSV rolled back from backup")
        shutil.copy2(bkp, CSV_PATH)
        sys.exit(2)

    pre = os.path.join(BACKUP_DIR, "audit_flags_preB82.json")
    if os.path.exists(FLAGS_PATH):
        shutil.copy2(FLAGS_PATH, pre)
    rc = subprocess.run([sys.executable, AUDIT, "--csv", CSV_PATH,
                         "--out", FLAGS_PATH, "--quiet"], capture_output=True, text=True, timeout=600)
    if rc.returncode != 0:
        print("AUDIT|FAIL", rc.stderr[-400:])
        sys.exit(2)
    new = json.load(open(FLAGS_PATH))
    adjudication["flags_after"] = new.get("total_flags")
    adjudication["summary_after"] = new.get("summary")
    adjudication["backup"] = bkp
    json.dump(adjudication, open(ADJ_PATH, "w"), indent=1, ensure_ascii=False)
    print(f"B82|done|rows {n0} -> {len(rows)}|flags -> {new.get('total_flags')}")
    print("SUMMARY|" + json.dumps(new.get("summary")))


if __name__ == "__main__":
    main()
