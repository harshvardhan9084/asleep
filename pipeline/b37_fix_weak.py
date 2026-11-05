#!/usr/bin/env python3
"""b37_fix_weak.py <stem> — re-extract weak draft rows (codes present but no
name and no units/cos/experiments) via one consolidated extract_scheme_batch
call anchored on their deterministic-inventory entries; replace in place.
Pure-garbage rows (no codes + template junk) are dropped."""
import json, re, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as me

stem = sys.argv[1]
D = f"/home/z/my-project/work/pipeline_v2/drafts_B37/{stem}.draft.json"
INV = f"/home/z/my-project/work/pipeline_v2/inv/{stem}.inv.json"
parsed_dir = "/home/z/my-project/work/pipeline_v2/parsed"
d = json.load(open(D))
inv = json.load(open(INV))
fulltext = open(f"{parsed_dir}/{stem}.fulltext.txt").read()

inv_by_code = {}
for x in inv:
    if x.get("class") != "detail":
        for tok in re.split(r"[/,]", x["code_print"]):
            m = re.match(r"^\s*([A-Z]{2,4})\s?-?(\d{3})([A-Z]?)\s*$", tok)
            if m:
                inv_by_code.setdefault(m.group(1) + m.group(2) + (m.group(3) or ""), x)

def row_codes(s):
    return [re.sub(r"[^A-Z0-9]", "", (c or "").upper()) for c in (s.get("codes") or []) if c]

weak_idx, garbage_idx, targets, seen = [], [], [], set()
for i, s in enumerate(d["subjects"]):
    rc = row_codes(s)
    nm = (s.get("name") or s.get("name_print") or "")
    if not rc and not nm:
        garbage_idx.append(i)
        continue
    rich = bool(s.get("units") or s.get("cos") or s.get("experiments") or s.get("textbooks"))
    if rc and not nm and not rich and not any(c in seen for c in rc):
        entry = next((inv_by_code[c] for c in rc if c in inv_by_code), None)
        if entry and entry not in targets:
            weak_idx.append(i)
            targets.append(entry)
        seen.update(rc)

print(f"garbage rows: {len(garbage_idx)} | weak rows to re-extract: {len(targets)}")
for gi in sorted(garbage_idx, reverse=True):
    del d["subjects"][gi]
    weak_idx = [i if i < gi else i - 1 for i in weak_idx]

if targets:
    try:
        rows = dict(me.extract_scheme_batch(fulltext, d.get("session", ""), d.get("course", "BTech"), targets))
        for i, entry in zip(weak_idx, targets):
            key = entry.get("code_print", "")
            obj = None
            for k, v in rows.items():
                if re.sub(r"[^A-Z0-9]", "", (k or ""))[:6] == re.sub(r"[^A-Z0-9]", "", key)[:6]:
                    obj = v
                    break
            if isinstance(obj, dict) and (obj.get("name_print") or obj.get("marks") or obj.get("ltp")):
                obj.setdefault("name", obj.get("name_print", ""))
                obj.setdefault("codes", d["subjects"][i].get("codes") or [])
                obj.setdefault("quirks", []); obj.setdefault("flags", [])
                old = d["subjects"][i]
                for k in ("codes",):
                    obj[k] = old.get(k) or obj.get(k)
                d["subjects"][i] = obj
                print("REPLACED", key, "->", (obj.get("name") or "")[:40])
        d.setdefault("flags", []).append(f"weak-rows-repaired:{len(targets)} (consolidated scheme re-extraction)")
    except Exception as e:  # noqa: BLE001
        print("REPAIR-FAIL|", repr(e)[:140])

json.dump(d, open(D, "w"), indent=1, ensure_ascii=False)
print(f"FIX_WEAK|{stem}|subjects={len(d['subjects'])}")
