#!/usr/bin/env python3
"""patch_b22_alt_pair_flags.py — B22 merge-stage draft patches (B21 recorded pattern).

(1) The 13 scheme-row-only TIE subjects are ALTERNATIVE-PAIR-SLOT prints: the
    scheme row prints a paired slot (both members own published rows). merge_
    draft.py routes a TIE into the recorded SKIP_SLOT_PRINT path ONLY when the
    draft subject carries an `alternative_pair_row` flag — add it with printed
    evidence (B21 patch_b21_alt_pair_flags.py class; B02/B20 precedent).
(2) 09::73 nano-sciences: the sem-VIII OE list prints EOE-042 while the detailed
    sem-VI print 'EEE 042: POWER STATION PRACTICE' (+ EOE-042) claims the same
    slot — code-slot-collision remedy (B10/B21 recorded class): ownership stays
    with the detailed print; the collision print is retained as a narrative
    quirk and dropped from the scheme-row-only subject's codes (G2 single
    ownership).
(3) Intra-batch APPEND code-collision scan (same-commit G2 pre-check): report
    any atomic code token claimed by 2+ APPEND-planned subjects.
Idempotent.
"""
import json, os, re, sys

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"
REPORT = "/home/z/my-project/work/pipeline_v2/decisions_report.json"

# key -> (member row ids, evidence text)
ALT_PAIR = {
    "01_btech_ece_y4_syllabus-rcode_2021-22::12::hsmc-1-hsmc-2-vii-semester": (
        "rural-development-administration-and-planning, project-management-entrepreneurship",
        "VII-sem scheme row (p.2) prints 'KHU701/KHU702 HSMC-1#/HSMC-2#' — both paired members own published rows (recorded B17 slot-code transfers RDAP=KHU701/KHU801, PME=KHU702/KHU802)"),
    "01_btech_ece_y4_syllabus-rcode_2021-22::13::hsmc-1-hsmc-2-viii-semester": (
        "rural-development-administration-and-planning, project-management-entrepreneurship",
        "VIII-sem scheme row (p.3, page-image verified) prints 'KHU801/KHU802 HSMC-1#/HSMC-2#' — both paired members own published rows (recorded B17 slot-code transfers)"),
    "07_btech_ee-group_y2_syllabus-rev_2014-15::00::mathematics-iii-science-based-open-elective": (
        "engg-mathematics-iii, elementary-mathematics-iii",
        "Sem-III scheme row prints the combined cell 'NAS-301/NOE 031-039' (Mathematics-III slot + Science-Based-OE pool) — Engg. Mathematics-III (NAS-301;NAS-401) and the Science-OE pool member (NOE 031-039/041-049 ranges) both own rows (B21 recorded Maths-III/Science-OE slot class)"),
    "07_btech_ee-group_y2_syllabus-rev_2014-15::04::science-based-open-elective-mathematics-iii": (
        "engg-mathematics-iii, elementary-mathematics-iii",
        "Sem-IV scheme row prints the combined cell 'NAS-401/NOE 041-049' (Science-Based-OE pool + Mathematics-III slot) — both members own published rows (B21 recorded class)"),
    "07_btech_ee-group_y2_syllabus-rev_2014-15::01::industrial-psychology-industrial-sociology": (
        "industrial-psychology, industrial-sociology",
        "Sem-III OR-slot print 'Industrial Psychology/Industrial Sociology' — Industrial Psychology (NHU-301;NHU-402) and Industrial Sociology (NHU-302;NHU-401) both own published rows (B02 common-doc class)"),
    "07_btech_ee-group_y2_syllabus-rev_2014-15::05::industrial-psychology-industrial-sociology": (
        "industrial-psychology, industrial-sociology",
        "Sem-IV OR-slot print 'Industrial Psychology/Industrial Sociology' — both members own published rows (B02 common-doc class)"),
    "07_btech_ee-group_y2_syllabus-rev_2014-15::02::human-values-professional-ethics-cyber-security": (
        "human-values-professional-ethics, cyber-security",
        "Sem-III OR-slot print 'Human Values & Professional Ethics/Cyber Security' (AUC-001/AUC-002 audit codes) — Human Values & Professional Ethics (AUC-001;EHU111) and Cyber Security (AUC-002;BCC301;KNC301...) both own published rows (B20 (f) recorded class)"),
    "07_btech_ee-group_y2_syllabus-rev_2014-15::06::cyber-security-human-values-professional-ethics": (
        "cyber-security, human-values-professional-ethics",
        "Sem-IV OR-slot print 'Cyber Security/Human Values & Professional Ethics' (AUC-001/AUC-002) — both members own published rows (B20 (f) recorded class)"),
    "10_btech_ee_y2_model-curriculum_2019-20::12::engg-science-course-maths-iv": (
        "engineering-science-course-maths-v, mathematics-iv",
        "AICTE-model Sem-III OR-slot print 'Engg. Science Course/Maths IV' (KOE031-38 pool + KAS302) — Engineering Science Course/Maths V (KOE031-38;KAS304) and Mathematics-IV (KAS302;KAS402) both own published rows (B02/B20 recorded class)"),
    "10_btech_ee_y2_model-curriculum_2019-20::16::maths-iv-engg-science-course": (
        "mathematics-iv, maths-v-engineering-science-course",
        "AICTE-model Sem-IV OR-slot print 'Maths IV/Engg. Science Course' (KAS402 + KOE041-48 pool) — Mathematics-IV (KAS402) and Maths V/Engineering Science Course (KOE041-48;KAS404) both own published rows (B02/B20 recorded class)"),
    "10_btech_ee_y2_model-curriculum_2019-20::13::technical-communication-universal-human-values": (
        "technical-communication, universal-human-values-and-professional-ethics",
        "AICTE-model Sem-III OR-slot print 'Technical Communication/Universal Human values' (KAS301 + KVE301) — Technical Communication (KAS301;BAS301...) and Universal Human Values (KVE301;BVE301...) both own published rows (B20 (f) recorded class)"),
    "10_btech_ee_y2_model-curriculum_2019-20::15::computer-system-security-python-programming": (
        "cyber-security, python-programming",
        "AICTE-model Sem-III OR-slot print 'Computer System Security/Python Programming' (KNC301 + KNC302) — Cyber Security (KNC301...) and Python Programming (KNC302...) both own published rows (B20 (f) recorded class verbatim)"),
    "10_btech_ee_y2_model-curriculum_2019-20::18::python-programming-computer-system-security": (
        "python-programming, cyber-security",
        "AICTE-model Sem-IV OR-slot print 'Python Programming/Computer System Security' (KNC402 + KNC401) — both members own published rows (B20 (f) recorded class)"),
}

CODE_RE = re.compile(r"\b([A-Z]{2,4})\s?-?(\d{3})([A-Z]?)\b")


def atomic_codes(codes):
    out = set()
    for c in codes or []:
        for m in CODE_RE.finditer(c or ""):
            out.add(m.group(1) + m.group(2) + (m.group(3) or ""))
    return out


def main():
    # (3) needs the plans report
    plans = {}
    try:
        rep = json.load(open(REPORT))
        for p in rep["plans"]:
            plans[p["key"]] = p["op"]
    except FileNotFoundError:
        print("NOTE|no decisions_report.json — collision scan skipped")

    patched = 0
    for fn in sorted(os.listdir(DRAFTS)):
        if not fn.endswith(".draft.json"):
            continue
        stem = fn[:-len(".draft.json")]
        path = os.path.join(DRAFTS, fn)
        d = json.load(open(path))
        for i, s in enumerate(d.get("subjects", [])):
            key = f"{stem}::{i:02d}::"  # slug suffix varies by length; match on prefix
            ap = next((v for k, v in ALT_PAIR.items() if k.startswith(key)), None)
            if ap:
                members, ev = ap
                flags = [str(f) for f in (s.get("flags") or [])]
                if not any("alternative_pair" in f.lower() for f in flags):
                    s.setdefault("flags", []).append("alternative_pair_row")
                    s.setdefault("quirks", []).append(
                        f"patch-b22 alternative-pair-slot: {ev}; the slot print is program "
                        f"structure, not a subject (RULES §11) and is preserved in "
                        f"non_subject_rows; member rows: {members}")
                    patched += 1
            # (2) nano-sciences EOE-042 collision remedy
            if stem.startswith("09_btech_ee_syllabus_2009-10") and i == 73:
                cs = [str(c) for c in (s.get("codes") or [])]
                if "EOE-042" in cs:
                    s["codes"] = [c for c in cs if c != "EOE-042"]
                    s.setdefault("quirks", []).append(
                        "patch-b22 code-slot-collision remedy (B10/B21 recorded class): the "
                        "sem-VIII OE list prints EOE-042 for Nano Sciences while the detailed "
                        "print 'EEE 042: POWER STATION PRACTICE' (+EOE-042) claims the same "
                        "slot — ownership stays with the detailed print (power-station-"
                        "practice); the EOE-042 print is retained as this narrative quirk "
                        "(G2 single ownership); Nano Sciences keeps its EOE-032 list code")
                    patched += 1
        json.dump(d, open(path, "w"), indent=1, ensure_ascii=False)
    print(f"PATCHED|alt_pair+collision flags added: {patched}")

    # (3) intra-batch APPEND code-collision scan
    draft_map = {}
    for fn in sorted(os.listdir(DRAFTS)):
        if fn.endswith(".draft.json"):
            draft_map[fn[:-len('.draft.json')]] = json.load(open(os.path.join(DRAFTS, fn)))
    owner = {}
    dups = []
    for key, op in plans.items():
        if op != "APPEND":
            continue
        stem, idx = key.split("::")[0], int(key.split("::")[1])
        s = draft_map[stem]["subjects"][idx]
        for t in atomic_codes(s.get("codes")):
            if t in owner and owner[t] != key:
                dups.append(f"{t}: {owner[t]} AND {key}")
            owner[t] = key
    if dups:
        print("APPEND_CODE_DUPS|" + "; ".join(sorted(dups)))
    else:
        print("APPEND_CODE_DUPS|none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
