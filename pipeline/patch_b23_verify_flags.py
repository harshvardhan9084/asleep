#!/usr/bin/env python3
"""patch_b23_verify_flags.py — B23 evidence-class flags (B22 recorded pattern).

First verify run: 8 FAIL / 2 PASS; every failure is the recorded print class —
the subagents recorded the evidence in per-subject QUIRKS, the verifier's
no-units downgrade reads subject FLAGS. Patch adds the class flag only where
the draft's own evidence supports it:
  - objectives_print non-empty  -> objectives_only_no_units_printed (v14/B19 class)
  - else cos non-empty          -> co_only_no_units_printed (v11/B08 class)
  - else (scheme-row-only)      -> detailed_syllabus_not_printed (B02/B18/B19 class)
  - codes empty & no no-code evidence -> no-code-printed (v10/B06 class)
Idempotent.
"""
import json, os, sys

DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"


def classify(s):
    if s.get("units"):
        return None
    if s.get("experiments"):
        return None
    if s.get("objectives_print"):
        return "objectives_only_no_units_printed"
    if s.get("cos"):
        return "co_only_no_units_printed"
    return "detailed_syllabus_not_printed"


def main():
    summary = {}
    for fn in sorted(os.listdir(DRAFTS)):
        if not fn.endswith(".draft.json"):
            continue
        stem = fn[:-len(".draft.json")]
        path = os.path.join(DRAFTS, fn)
        d = json.load(open(path))
        counts = {"obj_only": 0, "co_only": 0, "scheme_only": 0,
                  "no_code": 0, "already": 0, "untouched": 0}
        for s in d.get("subjects", []):
            flags = [str(f) for f in (s.get("flags") or [])]
            fl = [f.lower() for f in flags]
            cls = classify(s)
            if cls and not any(
                    c in fl for c in (
                        "objectives_only_no_units_printed", "co_only_no_units_printed",
                        "detailed_syllabus_not_printed", "experiments_only_no_units",
                        "unit_ocr_recovered_no_text_layer")):
                s.setdefault("flags", []).append(cls)
                counts[{"objectives_only_no_units_printed": "obj_only",
                        "co_only_no_units_printed": "co_only",
                        "detailed_syllabus_not_printed": "scheme_only"}[cls]] += 1
                if cls == "detailed_syllabus_not_printed" and not any(
                        "scheme" in q for q in (s.get("quirks") or [])):
                    s.setdefault("quirks", []).append(
                        "scheme-row-only; detailed syllabus not printed in this document")
            elif not cls and not s.get("units"):
                counts["already"] += 1
            elif s.get("units"):
                counts["untouched"] += 1
            if not s.get("codes") and not any(
                    ("no-code" in f) or ("no code" in f) or ("without code" in f)
                    for f in fl + [str(q).lower() for q in (s.get("quirks") or [])]):
                s.setdefault("flags", []).append("no-code-printed")
                s.setdefault("quirks", []).append(
                    "no atomic code printed in this document (elective slot print; "
                    "wildcard pool reference only where applicable)")
                counts["no_code"] += 1
        json.dump(d, open(path, "w"), indent=1, ensure_ascii=False)
        if any(counts.values()):
            summary[stem] = counts
            print(f"PATCHED|{stem}|{json.dumps(counts)}")
    total = {k: sum(v[k] for v in summary.values()) for k in
             ("obj_only", "co_only", "scheme_only", "no_code", "already", "untouched")} if summary else {}
    print("TOTALS|" + json.dumps(total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
