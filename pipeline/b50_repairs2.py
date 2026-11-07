#!/usr/bin/env python3
"""b50_repairs2.py — doc 05 (MBA) second-pass repairs:
1. Row 27 (empty-name, MBA214, zero content): restored print-anchored from the
   'MBA 214: FINANCIAL MANAGEMENT' detail header; units via ONE mercury-3 REX
   call from the detail slice (B48 17-empty-name + B44 REX classes).
2. Row 38 (RESEARCH PROJECT REPORT AND VIVA, MBA413): the print carries a
   guidelines NOTE (marks 150, two external examiners) instead of units ->
   notes_print transcribed verbatim + practical_turns_notes_only_no_units_printed
   flag (B47/B48 notes-only class) with the fulltext evidence.
"""
import json, re, subprocess, sys

PD = "/home/z/my-project/work/pipeline_v2/parsed"
DR = "/home/z/my-project/work/pipeline_v2/drafts"

P05 = f"{DR}/05_mba_syllabus.draft.json"
d = json.load(open(P05))
ft = open(f"{PD}/05_mba_syllabus.fulltext.txt", encoding="utf-8").read()

# ---- row 27 restore
tgt = next(s for s in d["subjects"] if not (s.get("name") or "").strip())
i0 = ft.find("MBA 214:")

def quirk_add(s, q):
    qs = s.get("quirks") or []
    if q not in qs:
        qs.append(q)
    s["quirks"] = qs
i1 = ft.find("MBA 215:", i0)
slice_txt = ft[i0:i1 if i0 != -1 and i1 != -1 else i0 + 5000]
hdr = re.search(r"MBA 214\s*:\s*([^\n]+)", slice_txt)
tgt["name"] = hdr.group(1).strip().title()
tgt["name_print"] = hdr.group(1).strip()
tgt["codes"] = ["MBA-214"]
tgt.setdefault("codes_print", "MBA 214")
tgt["subject_type"] = "core"
quirk_add(tgt, "empty-name extraction row restored print-anchored from the 'MBA 214: FINANCIAL "
               "MANAGEMENT' detail header (B48 17-empty-name restore class); units re-extracted "
               "via mercury-3 REX from the same slice (B44 REX class)")
prompt = ("Extract the UNIT text of this AKTU syllabus subject VERBATIM. Return ONLY a JSON object "
          'with keys "units" (mapping "1".."N" to the full verbatim unit text incl. any unit heading '
          'like "Unit I") — no commentary. Keep every word and printed punctuation; do not correct '
          "anything.\n\nSOURCE (detail slice):\n\n" + slice_txt)
open("/tmp/rex_mba214_prompt.txt", "w").write(prompt)
r = subprocess.run([sys.executable, "/home/z/my-project/scripts/pipeline_v2/mercury_call.py",
                    "--prompt-file", "/tmp/rex_mba214_prompt.txt",
                    "--max-tokens", "4000", "--temperature", "0.5", "--timeout", "300"],
                   capture_output=True, text=True, timeout=330)
print("REX|MBA214|exit", r.returncode, "|", r.stderr.strip()[:100])
if r.returncode == 0:
    m = re.search(r"\{.*\}", r.stdout.strip(), re.S)
    units = json.loads(m.group(0)).get("units") if m else None
    if units and isinstance(units, dict) and len(units) >= 3:
        tgt["units"] = {str(k): v for k, v in units.items()}

# ---- row 38 notes-only
p38 = next(s for s in d["subjects"] if (s.get("name") or "").upper().startswith("RESEARCH PROJECT REPORT"))
j0 = ft.find("RESEARCH PROJECT REPORT:")
k0 = ft.find("===== PAGE 2", j0)
j1 = ft.find("COMPREHENSIVE VIVA", j0)
end = min(x for x in (k0 if k0 != -1 else len(ft), j1 if j1 != -1 else len(ft)))
note = ft[j0:end].strip()
p38["notes_print"] = note
p38["flags"] = sorted(set(p38.get("flags") or []) | {"practical_turns_notes_only_no_units_printed"})
quirk_add(p38, "no units printed; the scheme prints a RESEARCH PROJECT REPORT guidelines note "
               "(150 marks, two external examiners) transcribed verbatim in notes_print "
               "(B47/B48 notes-only class; fulltext evidence)")
json.dump(d, open(P05, "w"), indent=1, ensure_ascii=False)
print("RESTORED|MBA214|units:", len(tgt.get("units") or {}), "| NOTES|MBA413|", len(note), "chars")
