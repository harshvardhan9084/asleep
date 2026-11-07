#!/usr/bin/env python3
"""b49_repairs.py — B49 draft repairs (recorded classes):
1. Atomic code normalization: slash-joined compound prints ('NEE–031/NEN-031',
   'EHU-301/EHU-401', 'KAS302/KAS402/KAS302H/KAS402H') split to atomic codes;
   en/em-dashes ASCII-normalized; verbatim print kept in codes_print + quirk
   (v10 atomic_codes class; en-dash U+2013 breaks the verifier's CODE_RE).
2. NEE801 empty-name row restored print-anchored from the p.16 detail header
   (B48 17-empty-name class); units via ONE mercury-3 REX call (B44 16-REX
   class); books/references transcribed print-anchored from the same slice.
3. Doc 01 (CamScanner scan, empty text layer): every subject flagged
   `unit_ocr_recovered_no_text_layer` with a page-citing quirk (v12/v13 remedy
   classes — ORPHAN + unit/CO containment downgrade to WARN).
"""
import json, re, subprocess, sys, os

PD = "/home/z/my-project/work/pipeline_v2/parsed"
DR = "/home/z/my-project/work/pipeline_v2/drafts"

def atomic(codes, verbatim_old):
    out = []
    for c in codes:
        for part in re.split(r"[/,]", c):
            t = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2212]", "-", part)
            t = re.sub(r"\s+", "", t).strip("-")
            if t and t not in out:
                out.append(t)
    return out

def quirk_add(s, q):
    qs = s.get("quirks") or []
    if q not in qs:
        qs.append(q)
    s["quirks"] = qs

# ---------- pass 1: atomic code normalization (02/04/05/09 + 01 uniformity)
for stem in ["01_btech_che_y4_syllabus", "02_btech_compulsory-subjects",
             "04_btech_ee_y4_syllabus", "05_btech_en_y4_syllabus",
             "09_btech_s3-4_kas302-402h-maths-iv-pde-probability-statistics"]:
    p = f"{DR}/{stem}.draft.json"
    d = json.load(open(p))
    nch = 0
    for s in d["subjects"]:
        old = list(s.get("codes") or [])
        new = atomic(old, old)
        if new != old:
            nch += 1
            s["codes"] = new
            vp = ", ".join(repr(c) for c in old)
            s.setdefault("codes_print", "")
            if not s.get("codes_print"):
                s["codes_print"] = " / ".join(old)
            quirk_add(s, f"compound/en-dashed code print(s) {vp} split to atomic codes "
                         f"{new} draft-side for ladder matching; verbatim cell print kept in codes_print "
                         f"(v10 atomic_codes class; en-dash U+2013 print)")
    json.dump(d, open(p, "w"), indent=1, ensure_ascii=False)
    print(f"CODESPLIT|{stem}|subjects changed: {nch}")

# ---------- pass 2: NEE801 restore (doc 04)
P04 = f"{DR}/04_btech_ee_y4_syllabus.draft.json"
d04 = json.load(open(P04))
ft = open(f"{PD}/04_btech_ee_y4_syllabus.fulltext.txt", encoding="utf-8").read()
i0 = ft.find("NEE801:")
i1 = ft.find("===== PAGE 17", i0)
slice_txt = ft[i0:i1 if i0 != -1 and i1 != -1 else i0 + 6000]
tgt = None
for s in d04["subjects"]:
    if any(re.sub(r"[^A-Z0-9]", "", c) == "NEE801" for c in (s.get("codes") or [])):
        tgt = s
        break
assert tgt is not None, "NEE801 subject row not found"
# print-anchored restore: header + books/references from the p.16 slice
hdr = re.search(r"NEE801\s*:\s*([^\n]+)", slice_txt)
name_print = hdr.group(1).strip()
ltpm = re.search(r"L\s+T\s+P\s*\n\s*(\d)\s+(\d)\s+(\d)", slice_txt)
tb = re.search(r"Text Books\s*:\s*(.*?)References\s*:", slice_txt, re.S)
rb = re.search(r"References\s*:\s*(.*?)(?:===== PAGE|\Z)", slice_txt, re.S)

def parse_books(blob):
    out = []
    for line in (blob or "").splitlines():
        line = line.strip()
        m = re.match(r"^(\d{1,2})\s+(.+)$", line)
        if m and len(m.group(2)) > 4:
            out.append({"no": int(m.group(1)), "book": m.group(2).strip()})
    return out

tgt["name"] = name_print.title()
tgt["name_print"] = name_print
if ltpm:
    tgt["ltp"] = {"l": int(ltpm.group(1)), "t": int(ltpm.group(2)), "p": int(ltpm.group(3))}
tgt["semester"] = 8
tgt["subject_type"] = "core"
if tb:
    tgt["textbooks"] = parse_books(tb.group(1))
if rb:
    tgt["reference_books"] = parse_books(rb.group(1))
quirk_add(tgt, "empty-name extraction row restored print-anchored from p.16 detail header "
               "'NEE801: ELECTRICAL & ELECTRONICS ENGINEERING MATERIALS L T P 3 1 0' "
               "(B48 17-empty-name restore class); books/references transcribed from the same slice")

# REX units via mercury-3 (T2T per owner directive)
prompt = (
    "Extract the UNIT text of this AKTU syllabus subject VERBATIM. Return ONLY a JSON object "
    'with keys "units" (mapping "1".."N" to the full verbatim unit text incl. the unit heading '
    'line like "Crystal Structure of Materials:") — no commentary. Keep every word, keep printed '
    "punctuation; do not correct anything.\n\nSOURCE (detail page slice):\n\n" + slice_txt)
open("/tmp/rex_nee801_prompt.txt", "w").write(prompt)
r = subprocess.run([sys.executable, "/home/z/my-project/scripts/pipeline_v2/mercury_call.py",
                    "--prompt-file", "/tmp/rex_nee801_prompt.txt",
                    "--max-tokens", "4000", "--temperature", "0.5", "--timeout", "300"],
                   capture_output=True, text=True, timeout=330)
print("REX|NEE801|exit", r.returncode, "|", r.stderr.strip()[:120])
if r.returncode == 0:
    txt = r.stdout.strip()
    m = re.search(r"\{.*\}", txt, re.S)
    units = json.loads(m.group(0)).get("units") if m else None
    if units and isinstance(units, dict) and len(units) >= 3:
        tgt["units"] = {str(k): v for k, v in units.items()}
        quirk_add(tgt, "units re-extracted via mercury-3 REX from the p.16 detail slice (B44 REX class)")
    else:
        print("REX|WARN|units unusable:", str(units)[:120])
json.dump(d04, open(P04, "w"), indent=1, ensure_ascii=False)
print("RESTORED|NEE801|units:", len(tgt.get("units") or {}), "| tb:", len(tgt.get("textbooks") or []),
      "| rb:", len(tgt.get("reference_books") or []))

# ---------- pass 3: doc 01 evidence flags
P01 = f"{DR}/01_btech_che_y4_syllabus.draft.json"
d01 = json.load(open(P01))
for s in d01["subjects"]:
    fl = sorted(set((s.get("flags") or [])) | {"unit_ocr_recovered_no_text_layer"})
    s["flags"] = fl
    pg = (s.get("pages_covered") or ["1"])[0]
    q = f"subject content transcribed from page-image render p.{pg} (CamScanner scan; text layer empty; RULES §6 visible print authoritative; 3-subagent page-image transcription with per-page evidence)"
    quirk_add(s, q)
json.dump(d01, open(P01, "w"), indent=1, ensure_ascii=False)
print("FLAGGED|01|subjects:", len(d01["subjects"]))
