#!/usr/bin/env python3
"""b37_cleanup.py — final draft hygiene across the 10 B37 drafts:
  1. drop template-garbage rows (name 'verbatim'/'<canonical'/etc., or no codes
     + no name);
  2. drop no-code rows whose normalized name duplicates a CODED row in the same
     draft (the coded row owns the subject);
  3. move note-like no-code rows (MOOCs rules etc.) to non_subject_rows;
  4. refill empty-name coded rows from deterministic-inventory scheme entries
     (one consolidated extract_scheme_batch call per doc, names/anchors only)."""
import json, re, sys, glob
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as me

GARBAGE = {"verbatim", "<verbatim>", "title of the course", "name"}

def norm_name(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

for D in sorted(glob.glob("/home/z/my-project/work/pipeline_v2/drafts_B37/*.draft.json")):
    stem = D.split("/")[-1][:-11]
    d = json.load(open(D))
    subs = d.get("subjects", [])
    coded_names = {}
    for s in subs:
        cs = [re.sub(r"[^A-Z0-9]", "", c) for c in (s.get("codes") or []) if c]
        if cs and (s.get("name") or s.get("name_print")):
            for c in cs:
                coded_names.setdefault(norm_name(s.get("name") or s.get("name_print")), c)
    keep, removed, nonsub = [], [], []
    for s in subs:
        cs = [re.sub(r"[^A-Z0-9]", "", c) for c in (s.get("codes") or []) if c]
        nm = (s.get("name") or s.get("name_print") or "").strip()
        rich = bool(s.get("units") or s.get("experiments") or s.get("cos") or s.get("textbooks"))
        if not cs and (nm.lower() in GARBAGE or not nm):
            removed.append((cs, nm[:28], "garbage"))
            continue
        if not cs and rich and re.search(r"MOOC|honours|degree|note|rule", nm, re.I) and not s.get("marks"):
            nonsub.append({"kind": "moocs-note", "print": nm, "locator": f"draft subject row (no code)"})
            removed.append((cs, nm[:28], "moved-to-non-subject"))
            continue
        if not cs and norm_name(nm) in coded_names and not rich:
            removed.append((cs, nm[:28], "no-code dup of coded row"))
            continue
        keep.append(s)
    # refill empty-name coded rows from inv
    need = []
    for s in keep:
        cs = [re.sub(r"[^A-Z0-9]", "", c) for c in (s.get("codes") or []) if c]
        if cs and not (s.get("name") or s.get("name_print")):
            need.append(s)
    if need:
        import os
        INVP = f"/home/z/my-project/work/pipeline_v2/inv/{stem}.inv.json"
        inv = json.load(open(INVP)) if os.path.exists(INVP) else []
        by_code = {}
        for x in inv:
            for tok in re.split(r"[/,]", x.get("code_print", "")):
                m = re.match(r"^\s*([A-Z]{2,4})\s?-?(\d{3})([A-Z]?)\s*$", tok)
                if m:
                    by_code.setdefault(m.group(1) + m.group(2) + (m.group(3) or ""), x)
        filled = 0
        for s in need:
            cs = [c for c in (re.sub(r"[^A-Z0-9]", "", c) for c in s.get("codes") or []) if c]
            entry = next((by_code[c] for c in cs if c in by_code and by_code[c].get("name_print")), None)
            if entry:
                s["name"] = entry["name_print"]; s["name_print"] = entry["name_print"]
                s.setdefault("quirks", []).append("name filled from printed scheme cell (deterministic pairing)")
                filled += 1
        still = [s for s in need if not (s.get("name") or s.get("name_print"))]
        if still:
            fulltext = open(f"/home/z/my-project/work/pipeline_v2/parsed/{stem}.fulltext.txt").read()
            targets = []
            for s in still:
                cs = [c for c in (re.sub(r"[^A-Z0-9]", "", c) for c in s.get("codes") or []) if c]
                entry = next((by_code[c] for c in cs if c in by_code), None)
                if entry and entry not in targets:
                    targets.append(entry)
            if targets:
                try:
                    rows = dict(me.extract_scheme_batch(fulltext, d.get("session", ""), d.get("course", "BTech"), targets))
                    for s in still:
                        cs = [c for c in (re.sub(r"[^A-Z0-9]", "", c) for c in s.get("codes") or []) if c]
                        for k, v in rows.items():
                            nk = re.sub(r"[^A-Z0-9]", "", (k or ""))
                            if nk and any(c.startswith(nk[:4]) and nk[:6] in c for c in cs) and v.get("name_print"):
                                s["name"] = v["name_print"]; s["name_print"] = v["name_print"]
                                s.setdefault("quirks", []).append("name extracted from printed scheme row (consolidated re-extraction)")
                                filled += 1
                                break
                except Exception as e:  # noqa: BLE001
                    print("  refill-fail:", repr(e)[:90])
        print(f"  {stem[:44]}: refilled {filled}/{len(need)} empty-name rows")
    d["subjects"] = keep
    if nonsub:
        d.setdefault("non_subject_rows", []).extend(nonsub)
    if removed:
        d.setdefault("flags", []).append(f"cleanup-removed:{len(removed)} rows ({', '.join(sorted({r[2] for r in removed}))})")
    json.dump(d, open(D, "w"), indent=1, ensure_ascii=False)
    print(f"CLEAN|{stem[:52]}|kept={len(keep)} removed={len(removed)} nonsub+={len(nonsub)}")
