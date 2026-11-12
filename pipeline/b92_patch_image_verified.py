#!/usr/bin/env python3
"""b92_patch_image_verified.py — page-image verification gate for B92 restores.

4 restored values were eyeballed against the cited pages (owner-plan gate):
  ECE053  -> print entry verified on btech_ce_y4_syllabus_2016-17.pdf p.17;
             glued span replaced by the exact printed citation.
  KBT751D -> print cell verified on btech_bt_y4_syllabus_2021-22.pdf p.23;
             the print itself merges Glazer + Eisenthal into ONE S.N-1 cell
             (print-wins) - value extended to the full printed cell.
  EME-603 -> EME-603's own p.34 list prints all 7 stored entries verbatim;
             the Bevan 'restore' reverted to stored-verbatim, flag retired.
  EMT-601 -> print item C verified on btech_mfg-tech_syllabus_2010-11.pdf
             p.10; stored entry is print-verbatim minus the list letter -
             reverted to stored-verbatim, flag retired.
Also syncs w9a_ckpt verified_complete evidence + b92 ledger review section.
"""
import csv
import hashlib
import io
import json
import re

CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
LEDGER = "/home/z/my-project/work/pipeline_v2/probes/b92_apply_ledger.json"
CKPT = "/home/z/my-project/work/pipeline_v2/w9a_ckpt.json"

FIX = {
    "ECE053": {"after": "Jain, S. K. and Singh, V. P. – Water Resources Systems Planning & Management, Elesvier, Amsterdam",
               "evidence": "btech_ce_y4_syllabus_2016-17.pdf p.17 (page-image verified B92)"},
    "KBT751D": {"after": "Glazer AN, Nikaido H : Microbial Biotechnology: Fundamentals of Applied Microbiology Eisenthal, R. & Danson N.J. (Eds) Enzyme Assays: \u201cAPractical Approach\u201d, IRI Press, Oxford, UK",
                "evidence": "btech_bt_y4_syllabus_2021-22.pdf p.23 (page-image verified B92; print merges Glazer+Eisenthal in one cell)"},
}
REVERT = ["EME-603", "EMT-601"]

led = json.load(open(LEDGER))
act = {a["code"] + "::" + a["field"]: a for a in led["actions"] if a.get("verdict") == "restored"}

orig = open(CSV, "rb").read()
rows = list(csv.DictReader(open(CSV)))
touched = set()

def set_book(r, col, old_sq, new):
    arr = json.loads(r[col])
    hit = False
    for e in arr:
        if squash(e.get("book", "")) == old_sq:
            e["book"] = new
            hit = True
    if hit:
        r[col] = json.dumps(arr, ensure_ascii=False)
    return hit

def squash(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def retoken(qf, drop, add):
    toks = [t.strip() for t in re.split(r"[;,]", qf or "") if t.strip()]
    toks = [t for t in toks if t != drop and t != add]
    toks.append(add)
    return ";".join(toks)

for r in rows:
    code = r["primary_code"]
    if code not in FIX and code not in REVERT:
        continue
    key = next((k for k in act if k.startswith(code + "::")), None)
    if key is None:
        continue
    a = act[key]
    col = "textbooks_structured" if a["field"].startswith("textbooks") else "reference_books_structured"
    cur_sq = squash(a["after"])
    touched.add(r["subject_id"])
    if code in FIX:
        assert set_book(r, col, cur_sq, FIX[code]["after"]), f"{code}: current value not found"
        cj = json.loads(r["corrections_json"]) if (r["corrections_json"] or "").strip() else []
        for e in reversed(cj):
            if e.get("rule") == "BOOK_TRUNC_restored_print_B92" and e.get("field") == a["field"]:
                e["after"] = FIX[code]["after"]
                e["evidence"] = FIX[code]["evidence"]
                break
        r["corrections_json"] = json.dumps(cj, ensure_ascii=False)
    else:
        assert set_book(r, col, cur_sq, a["before"]), f"{code}: current value not found"
        r["quality_flags"] = retoken(r["quality_flags"], "corrected_BOOK_TRUNC_restored_print",
                                     "reviewed_BOOK_TRUNC_print_complete")
        cj = json.loads(r["corrections_json"]) if (r["corrections_json"] or "").strip() else []
        cj = [e for e in cj if not (e.get("rule") == "BOOK_TRUNC_restored_print_B92"
                                    and e.get("field") == a["field"])]
        r["corrections_json"] = json.dumps(cj, ensure_ascii=False) if cj else ""

buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
w.writeheader()
w.writerows(rows)
new = buf.getvalue().encode("utf-8")

o_rows = list(csv.reader(io.StringIO(orig.decode("utf-8"))))
n_rows = list(csv.reader(io.StringIO(new.decode("utf-8"))))
assert len(o_rows) == len(n_rows)
changed = []
hdr = o_rows[0]
for i, (a, b) in enumerate(zip(o_rows, n_rows)):
    if a != b:
        cols = [hdr[j] for j, (x, y) in enumerate(zip(a, b)) if x != y]
        changed.append((n_rows[i][0], cols))
print("changed rows:", changed)
assert all(set(c) <= {"textbooks_structured", "reference_books_structured",
                      "quality_flags", "corrections_json"} for _, c in changed)

with open(CSV, "wb") as fh:
    fh.write(new)

# sync w9a ckpt evidence for the two reverted entries
ck = json.load(open(CKPT))
for code in REVERT:
    key = next(k for k in act if k.startswith(code + "::"))
    ck["results"][key] = {"status": "verified_complete",
                          "evidence": f"B92 page-image verified: stored entry is print-verbatim ({code})"}
json.dump(ck, open(CKPT, "w"), indent=1)

# record the review in the ledger
led["page_image_review"] = {
    "ece053": FIX["ECE053"]["evidence"], "kbt751d": FIX["KBT751D"]["evidence"],
    "eme603": "btech_me-pe_syllabus_2009-10.pdf p.34 (page-image verified B92; all 7 stored entries print-verbatim -> retired)",
    "emt601": "btech_mfg-tech_syllabus_2010-11.pdf p.10 (page-image verified B92; stored entry print-verbatim minus list letter -> retired)",
    "csv_md5": hashlib.md5(new).hexdigest(),
}
json.dump(led, open(LEDGER, "w"), indent=1, ensure_ascii=False)
print("md5:", hashlib.md5(orig).hexdigest(), "->", hashlib.md5(new).hexdigest())
