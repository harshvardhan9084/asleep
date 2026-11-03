#!/usr/bin/env python3
"""concat_fragments.py <base_stem> <frags_dir> <drafts_dir> <n_frags>

Deterministically concatenates <base_stem>__frag1..N.frag.json (S05 pattern)
into <drafts_dir>/<base_stem>.draft.json:
- header from frag1 (pdf_rel/session/course/sha16); stem = base_stem;
- subjects concatenated in fragment order (boundary continuations were
  diverted to non_subject_rows by the fragment subagents — no de-dup here);
- non_subject_rows merged in order, locator suffixed " [frag<i>]" when not
  already frag-tagged;
- quirks merged in order (frag-tagged "[frag<i>]" when not already);
- flags = ordered union; a doc-level flag "concatenated_from_<n>_fragments"
  is appended for provenance.
Exits 1 if any fragment is missing or unparseable (never writes partial).
"""
import json, os, re, sys

# B03 remedy (evidence-recorded): fragment subagents divert a subject's
# cross-boundary tail into non_subject_rows(kind=boundary_continuation); the
# tail content belongs INSIDE the owning subject. This table maps each known
# BC row (by base stem + fragment no) to its owning subject and parse mode.
# Parsing is mechanical: units mode splits on printed Unit-<numeral> headings;
# experiments mode splits on printed numbered items under "List of Practical";
# a trailing "Recommended References" numbered list becomes reference_books.
BC_MERGE = {
    "08_bpharm_scheme-syllabus_2026-27": [
        {"frag": 4, "target": "Advanced Pharmacognosy (Theory)", "mode": "units"},
        {"frag": 6, "target": "Analytical Method Development and Validation (Practical)",
         "mode": "experiments"},
    ],
    "10_bpharm_y1-4_syllabus_2019-20": [
        {"frag": 2, "target": "PHARMACEUTICAL MICROBIOLOGY (Theory)", "mode": "units"},
    ],
}

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}


def parse_units_tail(print_text):
    """split printed BC tail into verbatim unit texts (+ refs list)"""
    units, refs = {}, []
    # locate unit headings
    marks = []
    for m in re.finditer(r"Unit-([IVX]+|\d+)\b", print_text):
        marks.append((m.start(), m.group(1)))
    ref_i = print_text.find("Recommended References")
    for k, (pos, num) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else (ref_i if ref_i > pos else len(print_text))
        n = ROMAN.get(num.upper()) or int(num)
        body = print_text[pos:end]
        body = body[body.find("\n") + 1:] if "\n" in body else body  # drop 'Unit-<n>' marker line-head
        units[str(n)] = body.strip()
    if ref_i >= 0:
        for m in re.finditer(r"(?m)^(\d{1,2})\.\s+(.+)$", print_text[ref_i:]):
            refs.append({"no": int(m.group(1)), "book": m.group(2).strip()})
    return units, refs


def parse_experiments_tail(print_text):
    """split printed BC tail into practical-list items (+ refs list)"""
    exps, refs = [], []
    ref_i = print_text.find("Recommended References")
    scope = print_text[:ref_i] if ref_i > 0 else print_text
    for m in re.finditer(r"(?m)^(\d{1,2})\.\s*(.*)$", scope):
        exps.append({"no": int(m.group(1)), "exp": m.group(2).strip()})
    if ref_i >= 0:
        for m in re.finditer(r"(?m)^(\d{1,2})\.\s+(.+)$", print_text[ref_i:]):
            refs.append({"no": int(m.group(1)), "book": m.group(2).strip()})
    return exps, refs


def main():
    base_stem, frags_dir, drafts_dir, n = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
    frags = []
    for i in range(1, n + 1):
        p = os.path.join(frags_dir, f"{base_stem}__frag{i}.frag.json")
        if not os.path.isfile(p):
            print(f"CONCAT|FAIL|missing {p}")
            return 1
        try:
            frags.append(json.load(open(p)))
        except Exception as ex:
            print(f"CONCAT|FAIL|unparseable {p}: {ex}")
            return 1

    h = frags[0]
    out = {
        "pdf_rel": h.get("pdf_rel", ""),
        "session": h.get("session", ""),
        "course": h.get("course", ""),
        "sha16": h.get("sha16", ""),
        "stem": base_stem,
        "subjects": [],
        "non_subject_rows": [],
        "quirks": list(h.get("quirks", [])),
        "flags": list(h.get("flags", [])),
    }
    for i, fr in enumerate(frags, 1):
        for s in fr.get("subjects", []):
            s.setdefault("quirks", [])
            if i > 1:
                s["quirks"] = [q if "[frag" in q else f"[frag{i}] {q}" for q in s["quirks"]]
            out["subjects"].append(s)
        for r in fr.get("non_subject_rows", []):
            if i > 1 and "[frag" not in r.get("locator", ""):
                r = dict(r)
                r["locator"] = (r.get("locator", "") + f" [frag{i}]").strip()
            out["non_subject_rows"].append(r)
        if i > 1:
            out["quirks"] += [q if "[frag" in q else f"[frag{i}] {q}" for q in fr.get("quirks", [])]
        for fl in fr.get("flags", []):
            if fl not in out["flags"]:
                out["flags"].append(fl)
    out["flags"].append(f"concatenated_from_{n}_fragments")

    # subject-level flags of fragments > 1 get frag tag too (traceability)
    for i, fr in enumerate(frags, 1):
        for s in fr.get("subjects", []):
            if i > 1:
                s["flags"] = [fl if "[frag" in fl or fl.startswith("spans") or fl.startswith("appendix")
                              else f"[frag{i}] {fl}" for fl in s.get("flags", [])]

    # B03 remedy: merge boundary_continuation rows back into their subjects
    for cfg in BC_MERGE.get(base_stem, []):
        fr = frags[cfg["frag"] - 1]
        bcs = [r for r in fr.get("non_subject_rows", []) if r.get("kind") == "boundary_continuation"]
        if not bcs:
            print(f"CONCAT|WARN|no boundary_continuation row in frag{cfg['frag']} of {base_stem}")
            continue
        bc = bcs[0]
        tgt = next((s for s in out["subjects"] if s.get("name") == cfg["target"]), None)
        if tgt is None:
            print(f"CONCAT|FAIL|BC target subject not found: {cfg['target']}")
            return 1
        tail = bc.get("print", "")
        if cfg["mode"] == "units":
            units, refs = parse_units_tail(tail)
            if not units:
                print(f"CONCAT|FAIL|units parse produced nothing for {cfg['target']}")
                return 1
            tgt.setdefault("units", {}).update(units)
            if refs and not tgt.get("reference_books"):
                tgt["reference_books"] = refs
            tgt.setdefault("quirks", []).append(
                f"[concat] cross-boundary tail merged from {cfg['frag']}.frag boundary_continuation "
                f"({bc.get('locator','')}): units {sorted(units)}" + (f" + {len(refs)} refs" if refs else ""))
        else:
            exps, refs = parse_experiments_tail(tail)
            if not exps:
                print(f"CONCAT|FAIL|experiments parse produced nothing for {cfg['target']}")
                return 1
            tgt["experiments"] = (tgt.get("experiments") or []) + exps
            if refs and not tgt.get("reference_books"):
                tgt["reference_books"] = refs
            tgt.setdefault("quirks", []).append(
                f"[concat] cross-boundary tail merged from {cfg['frag']}.frag boundary_continuation "
                f"({bc.get('locator','')}): {len(exps)} practical items" + (f" + {len(refs)} refs" if refs else ""))
        # drop the consumed BC row from the output non_subject_rows
        out["non_subject_rows"] = [r for r in out["non_subject_rows"]
                                   if not (r.get("kind") == "boundary_continuation" and
                                           r.get("print") == tail and cfg["frag"] > 1)]
        print(f"CONCAT|BC-MERGED|{cfg['target']}|{cfg['mode']}|units/exps from frag{cfg['frag']}")

    dst = os.path.join(drafts_dir, base_stem + ".draft.json")
    with open(dst, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    n_sub = len(out["subjects"])
    n_non = len(out["non_subject_rows"])
    print(f"CONCAT|{base_stem}|subjects={n_sub}|non_subject_rows={n_non}|quirks={len(out['quirks'])}|OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
