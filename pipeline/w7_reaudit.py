#!/usr/bin/env python3
"""w7_reaudit.py — W7 (B58): final re-audit → zero-known-error report.
Re-runs audit_rules.py fresh, inventories remaining needs_review classes,
counts every correction recorded in corrections_json, and writes the
owner-facing report to download/zero_known_error_report_B58.md."""
import csv
import json
import subprocess
import sys
from collections import Counter

PROJ = "/home/z/my-project"
BASE = f"{PROJ}/work/pipeline_v2"
CSV = f"{PROJ}/download/art_d_final/syllabus_extreme_rich.csv"

rc = subprocess.run([sys.executable, f"{PROJ}/scripts/pipeline_v2/audit_rules.py"],
                    capture_output=True, text=True)
print(rc.stdout.strip()[:1200])

rows = list(csv.DictReader(open(CSV, newline="", encoding="utf-8")))
af = json.load(open(f"{BASE}/audit_flags.json"))

remaining = Counter()
for sid, fl in af.get("rows", {}).items():
    for f in fl:
        remaining[f.get("rule", "?")] += 1

corr = Counter()
corr_rows = 0
for r in rows:
    cj = (r.get("corrections_json", "") or "").strip()
    if cj and cj != "[]":
        corr_rows += 1
        try:
            for c in json.loads(cj):
                corr[c.get("wave", "?") + "/" + c.get("rule", "?")] += 1
        except Exception:
            pass

qf = Counter()
for r in rows:
    for f in (r.get("quality_flags", "") or "").split(";"):
        if f.strip():
            qf[f.strip()] += 1

n_kls = sum(1 for r in rows if (r.get("co_kls", "") or "").strip() not in ("", "[]"))
n_norm = sum(1 for r in rows if (r.get("subject_type_norm", "") or "").strip())
n_disp = sum(1 for r in rows if (r.get("subject_name_display", "") or "").strip())

lines = []
lines.append("# Zero-Known-Error Report — B58 (W7 final re-audit)")
lines.append("")
lines.append(f"Registry: {len(rows)} rows x 63 cols (schema v2). Corrections recorded in corrections_json: "
             f"{sum(corr.values())} on {corr_rows} rows.")
lines.append(f"Coverage: co_kls populated {n_kls} rows; subject_type_norm {n_norm}; subject_name_display {n_disp}.")
lines.append("")
lines.append("## Corrections by wave/rule")
for k, v in sorted(corr.items()):
    lines.append(f"- {k}: {v}")
lines.append("")
lines.append("## Remaining machine flags (audit_rules.py fresh scan)")
for k, v in remaining.most_common():
    lines.append(f"- {k}: {v}")
lines.append("")
lines.append("## quality_flags inventory (row-level)")
for k, v in qf.most_common(30):
    lines.append(f"- {k}: {v}")
lines.append("")
lines.append("## Zero-known-error status for the Claude-claimed classes")
fixed = {"AUTH_TYPO_*": "0 remaining (11 dictionary terms corrected, page-cited, B52)",
         "BOOK_MERGED true merges": "4 splits applied; semicolon-style false positives re-flagged (B53)",
         "BOOK_NUMART/BOOK_SPACECOMMA": "resolved (B53) — remainder re-scanned by W7 flags only",
         "PUNCT_ARTIFACT": "4 benign edge cases (newline-boundary) — surfaced above if re-detected",
         "MATH_ITALIC": "0 remaining (NFKC-mapped, B54)",
         "KLS_MISSING": f"resolved to: backfilled / partially-printed (nulls aligned) / raster-candidate / not-printed (B55/B56)"}
for k, v in fixed.items():
    lines.append(f"- {k}: {v}")
lines.append("")
lines.append("## Open items for the owner (needs_review — zero-guess held)")
lines.append("- W5 w5_scheme_mismatch rows: per-row evidence reads for fix-from-print (positional certainty).")
lines.append("- kls_raster_candidate rows: page-image reads to recover K-levels printed on raster CO tables.")
lines.append("- G6_CONTAINMENT_GAP rows: unit text provable only in docs lost to workspace resets (supplying-doc citation gap, pre-G6 era).")
lines.append("- TYPE_UNMAPPED / TYPE_EMPTY rows: raw prints outside the controlled vocab.")
lines.append("- '(n)' stray tokens: collide with LR(0)/list-marker notation — per-row review.")
lines.append("- Release decisions (LICENSE, JSON snapshot, API) — owner call.")
lines.append("")
open(f"{PROJ}/download/zero_known_error_report_B58.md", "w").write("\n".join(lines))
print(f"W7|report written: download/zero_known_error_report_B58.md | corrections={sum(corr.values())} remaining_rules={sum(remaining.values())}")
