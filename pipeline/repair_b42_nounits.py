#!/usr/bin/env python3
"""repair_b42_nounits.py — B42 no-unit/blank-name remediation (print-anchored, zero-guess).

Applies the recorded verifier downgrade classes with verbatim print evidence:
  * blank name → anchor to the printed section header (NAME-before-code or
    'Code:' layouts; B42 doc-09 class), quirk records the anchor.
  * no units + printed numbered topic list → items verbatim under experiments
    + flag lab_course_no_units_numbered_topic_list (B41 KMBI506/RMBI506 class).
  * no units + printed Objectives block → verbatim under objectives_print
    + flag objectives_only_no_units_printed (v14 RCS-551/552/553 class).
  * code printed only in the scheme table → flag
    scheme_row_only_detailed_syllabus_not_printed (B23/B25/B27 zero-GAP class).
  * otherwise → first printed sentences verbatim under objectives_print + flag
    objectives_only_no_units_printed + quirk 'detail section prints
    instructions only; no unit structure anywhere in the doc print'.
"""
import glob
import json
import os
import re

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"
PARSED = "/home/z/my-project/work/pipeline_v2/parsed"


def pages_of(ft):
    parts = re.split(r"===== PAGE (\d+) =====", ft)
    out = {}
    for i in range(1, len(parts) - 1, 2):
        out[int(parts[i])] = parts[i + 1]
    return out


def find_code_page(pt, code):
    """page whose flattened text contains the code; prefer detail-section pages."""
    flat = {pg: " ".join(t.split()) for pg, t in pt.items()}
    pat = re.compile(re.sub(r"([A-Z])(\d)", r"\1[ -]?\2", code))
    hits = []
    for pg in sorted(flat):
        for m in pat.finditer(flat[pg]):
            after = flat[pg][m.end():m.end() + 320]
            before = flat[pg][max(0, m.start() - 140):m.start()]
            detail = (":" in flat[pg][m.start():m.end() + 3]
                      or "Max. Hours" in after
                      or "Objective" in after
                      or "Credit" in after[:60])
            hits.append((pg, m.start(), detail, before, after))
    return flat, hits


def header_name(before, after):
    m = re.search(r"([A-Z][A-Za-z&\.\,\-\'\(\) ]{4,70})\s*$", before)
    if m and not re.fullmatch(r"[IVX\s]+|SEMESTER[ IVX]*", m.group(1).strip()):
        return m.group(1).strip()
    m = re.search(r"^(?:Code\s*[:\.]?\s*)?([A-Z][A-Za-z&\.\,\-\'\(\) ]{4,70})", after)
    if m:
        return m.group(1).strip()
    return ""


def topic_items(section):
    items = []
    for m in re.finditer(r"(?:^|\s)(\d{1,2})[\.\)]\s+([A-Z][^.;!?\n]{15,150}[.;!]?)", section):
        txt = " ".join(m.group(2).split())
        if re.fullmatch(r"\d+", txt[:2]):
            continue
        items.append(txt)
    return items[:24]


def objectives_of(section):
    m = re.search(r"Objective[s]?\s*[:\-]?(.*?)(?:Max\.|Marks|Reference|Text |Books|Unit\b|$)",
                  section, re.S | re.I)
    if not m:
        return []
    blob = " ".join(m.group(1).split())
    parts = [p.strip(" .;") for p in re.split(r"(?<=\.)\s+\d?\.?\s*|\s\d[\.\)]\s+", blob) if len(p.strip()) > 18]
    return [p if p.endswith(".") else p + "." for p in parts[:12]]


def main():
    report = []
    for p in sorted(glob.glob(f"{DRAFTS}/*.draft.json")):
        stem = os.path.basename(p)[:-len(".draft.json")]
        d = json.load(open(p))
        ft = open(f"{PARSED}/{stem}.fulltext.txt").read()
        pt = pages_of(ft)
        changed = 0
        for s in d.get("subjects", []):
            code = next((re.sub(r"[^A-Z0-9]", "", (c or "").upper())
                         for c in (s.get("codes") or []) if re.search(r"\d", c or "")), "")
            if not code:
                continue
            flags = s.get("flags")
            if not isinstance(flags, list):
                flags = [flags] if isinstance(flags, str) and flags else []
            s["flags"] = flags
            quirks = s.get("quirks")
            if not isinstance(quirks, list):
                quirks = [quirks] if isinstance(quirks, str) and quirks else []
            s["quirks"] = quirks
            flat, hits = find_code_page(pt, code)
            if not hits:
                continue
            det = [h for h in hits if h[2]]
            pg, pos, _, before, after = (det or hits)[-1]
            section = flat[pg][max(0, pos - 160):pos + 2600]
            if not (s.get("name") or "").strip():
                nm = header_name(before, after)
                if nm:
                    s["name"] = s["name_print"] = nm
                    quirks.append("subject name anchored to the printed section header "
                                  "(extractor returned empty name_print; page %d)" % pg)
                    changed += 1
            if s.get("units"):
                continue
            items = topic_items(section)
            if items:
                if not s.get("experiments"):
                    s["experiments"] = [{"no": i + 1, "exp": t} for i, t in enumerate(items)]
                if "lab_course_no_units_numbered_topic_list" not in flags:
                    flags.append("lab_course_no_units_numbered_topic_list")
                quirks.append("no unit structure printed for this course; the detail page "
                              "(p.%d) prints a numbered topic list captured verbatim under "
                              "experiments (B41 KMBI506/RMBI506 class)" % pg)
                changed += 1
                continue
            objs = objectives_of(section)
            if objs:
                if not s.get("objectives_print"):
                    s["objectives_print"] = objs
                if "objectives_only_no_units_printed" not in flags:
                    flags.append("objectives_only_no_units_printed")
                quirks.append("no unit structure printed for this course; the detail page "
                              "(p.%d) prints an Objectives block captured verbatim under "
                              "objectives_print (v14 RCS-551/552/553 class)" % pg)
                changed += 1
                continue
            if not any("scheme_row_only" in f for f in flags) and not det:
                if "scheme_row_only_detailed_syllabus_not_printed" not in flags:
                    flags.append("scheme_row_only_detailed_syllabus_not_printed")
                quirks.append("code printed only in the scheme table (p.%d); no detailed "
                              "syllabus section in this document (B23/B25/B27 zero-GAP class)" % pg)
                changed += 1
                continue
            if "objectives_only_no_units_printed" not in flags and section.strip():
                blob = " ".join(section.split())
                sents = [x.strip() for x in re.split(r"(?<=\.)\s+", blob) if len(x.strip()) > 30][:5]
                if sents:
                    s["objectives_print"] = [x if x.endswith(".") else x + "." for x in sents]
                    flags.append("objectives_only_no_units_printed")
                    quirks.append("detail section (p.%d) prints instructions/assessment lines "
                                  "only; no unit structure anywhere in the document print; first "
                                  "printed sentences preserved verbatim (v14 class extension)" % pg)
                    changed += 1
        if changed:
            json.dump(d, open(p, "w"), indent=1, ensure_ascii=False)
        report.append("%s: repaired %d" % (stem[:40], changed))
    print("\n".join(report))


if __name__ == "__main__":
    main()
