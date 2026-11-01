#!/usr/bin/env python3
"""patch_b23_alt_pair_flags.py — B23 ALTERNATIVE-PAIR-SLOT draft flags
(B21/B22 recorded pattern; the merge_draft.py SKIP_SLOT_PRINT path requires
alternative_pair_row flags on the draft subjects).

The 6 T0-TIE subjects are scheme OR-slot prints whose printed codes are owned
by TWO published rows each (both members own rows):
  01::15/19 Maths-III/Science-OE combined cells (RAS301/ROE-030-039 +
            RAS401/ROE-040-049 — R-era print of the B02 slot family)
  01::16/20 UHV/Environment-&-Ecology (RVE301+RAS302 / RAS402+RVE401)
  06::01/03 Sociology/Cyber-Security (RAS502+RUC501 / RAS602+RUC601)
Idempotent.
"""
import json, os, sys

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"

ALT_PAIR = {
    "01_btech_ee_y2_scheme-syllabus_2017-18::15::science-based-open-elective-mathematics-iii": (
        "science-based-open-elective, science-based-open-elective-mathematics-iii",
        "Sem-III scheme row prints the combined cell 'ROE030 to 039' + 'RAS301' (Science-Based-OE pool + Mathematics-III slot) — Science Based Open Elective (ROE-030..039, 2017-18 print) and Mathematics-III/Science-OE slot row (RAS301) both own the printed codes (B21/B22 recorded Maths-III/Science-OE slot class)"),
    "01_btech_ee_y2_scheme-syllabus_2017-18::19::mathematics-iii-science-based-open-elective": (
        "science-based-open-elective, mathematics-iii-science-based-open-elective",
        "Sem-IV scheme row prints the combined cell 'RAS401' + 'ROE040 to 049' (Mathematics-III slot + Science-Based-OE pool) — both members own published rows (B21/B22 recorded class)"),
    "01_btech_ee_y2_scheme-syllabus_2017-18::16::universal-human-values-professional-ethics-environment-ecolo": (
        "universal-human-values-and-professional-ethics, environment-ecology",
        "Sem-III OR-slot print 'Universal Human Values & Professional Ethics/Environment & Ecology' (RVE301 + RAS302) — UHV (RVE301;RVE401) and Environment & Ecology (RAS302;RAS402) both own published rows (B02 common-doc class)"),
    "01_btech_ee_y2_scheme-syllabus_2017-18::20::environment-ecology-universal-human-values-professional-ethi": (
        "environment-ecology, universal-human-values-and-professional-ethics",
        "Sem-IV OR-slot print 'Environment & Ecology/Universal Human Values & Professional Ethics' (RAS402 + RVE401) — both members own published rows (B02 common-doc class)"),
    "06_btech_eee-ece-ee_y3_syllabus_2018-19::01::sociology-cyber-security": (
        "cyber-security, sociology-cyber-security",
        "Sem-V OR-slot print 'Sociology / Cyber Security' (RAS502 + RUC501) — Cyber Security (RUC501;RUC601) and the published Sociology/Cyber-Security slot row (RAS502;RAS602, established from the same 2018-19 print family) own the printed codes; the member subjects (industrial-sociology, cyber-security) own rows (B02/B20 recorded class)"),
    "06_btech_eee-ece-ee_y3_syllabus_2018-19::03::sociology-cyber-security": (
        "cyber-security, sociology-cyber-security",
        "Sem-VI OR-slot print 'Sociology / Cyber Security' (RAS602 + RUC601) — both members own published rows (B02/B20 recorded class)"),
}


def main():
    patched = 0
    for fn in sorted(os.listdir(DRAFTS)):
        if not fn.endswith(".draft.json"):
            continue
        stem = fn[:-len(".draft.json")]
        path = os.path.join(DRAFTS, fn)
        d = json.load(open(path))
        for i, s in enumerate(d.get("subjects", [])):
            key = f"{stem}::{i:02d}::"
            ap = next((v for k, v in ALT_PAIR.items() if k.startswith(key)), None)
            if ap:
                members, ev = ap
                flags = [str(f).lower() for f in (s.get("flags") or [])]
                if not any("alternative_pair" in f for f in flags):
                    s.setdefault("flags", []).append("alternative_pair_row")
                    s.setdefault("quirks", []).append(
                        f"patch-b23 alternative-pair-slot: {ev}; the slot print is program "
                        f"structure, not a subject (RULES §11) and is preserved in "
                        f"non_subject_rows; member rows: {members}")
                    patched += 1
        json.dump(d, open(path, "w"), indent=1, ensure_ascii=False)
    print(f"PATCHED|alt_pair flags added: {patched}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
