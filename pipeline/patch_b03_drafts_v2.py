#!/usr/bin/env python3
"""B03 draft patches v2 (evidence-recorded, deterministic):

1. Draft 10 REMEDIAL alternative-pair codes: the sem-I scheme prints
   'BP106RBT/BP106RMT Remedial Biology/Remedial Mathematics' as an
   alternative-slot pair, and the extractor had put BOTH codes on BOTH
   entries. Each card's own printed header carries exactly one code
   (name_print: 'BP106RBT. REMEDIAL BIOLOGY (Theory)' /
   'BP106RMT. REMEDIAL MATHEMATICS (Theory)') -> each entry owns exactly its
   own printed code (G2: one owner per code; RULES §11: never merge two
   different subjects).
2. Drafts 08 + 10 name convention: subject_name gains the printed card-header
   qualifier '(Theory)'/'(Practical)' — the print itself distinguishes the
   same-name theory/practical pairs this way (e.g. 'General Pharmacy (Theory)'
   vs 'General Pharmacy (Practical)'). Zero-guess: the qualifier is verbatim
   print from name_print; subject_name_print keeps the full printed header.
   Without this, same-(name,course) theory/practical pairs collide in G3 or
   fuzzy-merge into one row (RULES §3: labs are distinct rows).
"""
import json, re

P = "/home/z/my-project/work/pipeline_v2"


def load(stem):
    return json.load(open(f"{P}/drafts/{stem}.draft.json"))


def save(stem, d):
    json.dump(d, open(f"{P}/drafts/{stem}.draft.json", "w"), ensure_ascii=False, indent=1)


# 1) draft 10 remedial codes
d10 = load("10_bpharm_y1-4_syllabus_2019-20")
rb = [s for s in d10["subjects"] if s.get("name") == "REMEDIAL BIOLOGY" and "BP106RBT" in s["codes"]]
rm = [s for s in d10["subjects"] if s.get("name") == "REMEDIAL MATHEMATICS"]
assert len(rb) == 1 and len(rm) == 1, (len(rb), len(rm))
rb[0]["codes"] = ["BP106RBT"]
rb[0]["quirks"] = rb[0].get("quirks", []) + [
    "Sem-I scheme prints BP106RBT/BP106RMT as an alternative slot pair (Remedial Biology / Remedial "
    "Mathematics); this entry owns only BP106RBT per its own printed card header 'BP106RBT. REMEDIAL "
    "BIOLOGY (Theory)'."]
rm[0]["codes"] = ["BP106RMT"]
rm[0]["quirks"] = rm[0].get("quirks", []) + [
    "Sem-I scheme prints BP106RBT/BP106RMT as an alternative slot pair; this entry owns only BP106RMT "
    "per its own printed card header 'BP106RMT. REMEDIAL MATHEMATICS (Theory)'."]
save("10_bpharm_y1-4_syllabus_2019-20", d10)

# 2) name qualifiers from printed headers (drafts 08 + 10)
QUAL = re.compile(r"\s*\((Theory|Practical|Lab|Laboratory)\)\s*$", re.I)


def fix_names(d, stem):
    n = 0
    for s in d["subjects"]:
        np_ = (s.get("name_print") or "").strip()
        m = QUAL.search(np_)
        if not m:
            continue
        base = np_[: m.start()].strip()
        # strip a leading printed code prefix 'BP102T. ' if present
        base = re.sub(r"^[A-Z]{2,4}[0-9A-Z]{2,5}[A-Z]?\s*\.\s*", "", base).strip()
        qual = m.group(1).title()
        new_name = f"{base} ({qual})"
        if re.sub(r"\W+", "", new_name.lower()) != re.sub(r"\W+", "", (s.get("name") or "").lower()):
            s["name"] = new_name
            n += 1
    save(stem, d)
    return n


n8 = fix_names(load("08_bpharm_scheme-syllabus_2026-27"), "08_bpharm_scheme-syllabus_2026-27")
n10 = fix_names(load("10_bpharm_y1-4_syllabus_2019-20"), "10_bpharm_y1-4_syllabus_2019-20")
print(f"PATCH2-OK: draft10 remedial codes split (RBT/RMT); names qualified: 08={n8}, 10={n10}")
