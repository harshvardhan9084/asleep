#!/usr/bin/env python3
"""b37_fix_thin.py <stem> — remove draft subjects whose codes belong to
deterministic-inventory DETAIL entries but whose row is thin (no units, no
cos, no experiments, no textbooks — i.e. a scheme-batch stub that shadowed
the real detail extraction via code-dedup), so b37_resume re-extracts them.
Also removes fully empty rows. Records a doc-level flag."""
import json, re, sys

stem = sys.argv[1]
D = f"/home/z/my-project/work/pipeline_v2/drafts_B37/{stem}.draft.json"
INV = f"/home/z/my-project/work/pipeline_v2/inv/{stem}.inv.json"
d = json.load(open(D))
inv = json.load(open(INV))

detail_code_sets = []
for x in inv:
    if x.get("class") == "detail":
        toks = [re.sub(r"[^A-Z0-9]", "", t) for t in re.split(r"[/,]", x["code_print"])]
        s = {t for t in toks if t}
        if s:
            detail_code_sets.append(s)

def row_codes(s):
    return {re.sub(r"[^A-Z0-9]", "", (c or "").upper()) for c in (s.get("codes") or []) if c}

def thin(s):
    return not (s.get("units") or s.get("cos") or s.get("experiments") or s.get("textbooks") or s.get("reference_books"))

def garbage_name(s):
    for nm in (s.get("name") or "", s.get("name_print") or ""):
        if any(b in nm for b in ("<canonical", "<verbatim", "<codes", "<int", "{name", "code_print")):
            return True
    return False

keep, removed = [], []
for s in d["subjects"]:
    for k in ("name",):
        if isinstance(s.get(k), str) and s[k].rstrip().endswith(":"):
            s[k] = s[k].rstrip().rstrip(":").strip()
    rc = row_codes(s)
    is_empty = not rc and not (s.get("name") or s.get("name_print"))
    shadow = rc and any(rc <= ds for ds in detail_code_sets) and thin(s)
    if is_empty or shadow or (garbage_name(s) and thin(s)):
        removed.append((sorted(rc), (s.get("name") or s.get("name_print") or "")[:30],
                        "empty" if is_empty else ("garbage" if garbage_name(s) else "shadowed-detail")))
        continue
    keep.append(s)

d["subjects"] = keep
if removed:
    d.setdefault("flags", []).append(f"thin-rows-repaired:{len(removed)} (scheme stubs shadowing detail extractions; re-extracted)")
json.dump(d, open(D, "w"), indent=1, ensure_ascii=False)
for r in removed:
    print("REMOVED", r)
print(f"FIX_THIN|{stem}|removed={len(removed)} kept={len(keep)}")
