#!/usr/bin/env python3
"""backfill_aux_rules.py + course normalization (batch-01 follow-up, deterministic)

1) Program rules from batch-01 drafts never landed in the aux CSV (dict-spread order
   bug in cmd_decisions, now fixed for future runs). This backfills them from the
   same containment-verified drafts: for each drafts/*.draft.json rules[] entry ->
   one program_rule row (dedup by course+text), with source_history provenance.
2) course_name normalization: 'BTech' -> 'B.Tech' (registry convention since v4)
   in BOTH CSVs, splitting pipe-unioned cells per part.

Gates re-run after write: header intact, subject_id uniqueness in aux, row counts.
"""
import csv, glob, json, os, re, sys, unicodedata

BASE = "/home/z/my-project"
WORK = f"{BASE}/work/pipeline_v2"
MAIN = f"{BASE}/download/art_d_final/syllabus_extreme_rich.csv"
AUX = f"{BASE}/download/art_d_final/syllabus_aux_rows.csv"

def norm_slug(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = re.sub(r"[^a-zA-Z0-9]+", " ", s).lower().strip()
    return re.sub(r"\s+", "-", s)

def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        rdr = csv.reader(f)
        header = next(rdr)
        rows = [dict(zip(header, r)) for r in rdr]
    return header, rows

def norm_courses(cell):
    parts = [p.strip() for p in (cell or "").split("|") if p.strip()]
    out = []
    for p in parts:
        if re.sub(r"[^a-z0-9]", "", p.lower()) == "btech":
            p = "B.Tech"
        if p not in out:
            out.append(p)
    return "|".join(out)

def main():
    header, main_rows = load(MAIN)
    _h, aux_rows = load(AUX)

    # --- 1) backfill program rules
    existing = {r["subject_id"] for r in aux_rows}
    existing_texts = {norm_slug(r.get("subject_name", ""))[:50] + "|" + norm_slug(r.get("course_name", ""))
                      for r in aux_rows if r["row_kind"] == "program_rule"}
    added = 0
    for dp in sorted(glob.glob(f"{WORK}/drafts/*.draft.json")):
        d = json.load(open(dp, encoding="utf-8"))
        src = d.get("source", {})
        stem = os.path.basename(dp)[:2]
        course = src.get("course", "")
        eff = src.get("effective_session") or src.get("session_folder") or ""
        for rl in d.get("rules", []):
            txt = rl.get("rule_text_print", "") or rl.get("text", "") or ""
            if not txt:
                continue
            kind = rl.get("kind", "other")
            ident = "rule-" + norm_slug(kind)[:24] + "-" + norm_slug(txt)[:36]
            key = norm_slug(txt)[:50] + "|" + norm_slug(course)
            if ident in existing or key in existing_texts:
                continue
            row = {c: "" for c in header}
            row["subject_id"] = ident
            row["row_kind"] = "program_rule"
            row["subject_name"] = (txt[:80] + "…") if len(txt) > 80 else txt
            row["course_name"] = course
            row["university_name"] = "Dr. A.P.J. Abdul Kalam Technical University, Lucknow"
            row["status"] = "latest"
            row["notes"] = json.dumps([f"[{eff}] kind={kind} text={txt}"],
                                      ensure_ascii=False, separators=(",", ":"))
            row["source_history"] = (f"{src.get('rel_path','')}#{src.get('sha16','')}"
                                     f" p.{'/'.join(str(x) for x in (rl.get('evidence_pages') or []))}")
            aux_rows.append(row)
            existing.add(ident)
            existing_texts.add(key)
            added += 1

    # --- 2) course_name normalization both CSVs
    n_main = n_aux = 0
    for r in main_rows:
        nc = norm_courses(r.get("course_name", ""))
        if nc != r.get("course_name", ""):
            r["course_name"] = nc
            n_main += 1
    for r in aux_rows:
        nc = norm_courses(r.get("course_name", ""))
        if nc != r.get("course_name", ""):
            r["course_name"] = nc
            n_aux += 1

    # --- gates: header intact, aux subject_id unique
    ids = [r["subject_id"] for r in aux_rows]
    assert len(ids) == len(set(ids)), "duplicate subject_id in AUX after backfill"
    assert len(header) == 57

    for path, rows in ((MAIN, main_rows), (AUX, aux_rows)):
        tmp = path + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            for r in rows:
                w.writerow([r[c] for c in header])
        os.replace(tmp, path)
    print(f"backfilled program_rules: {added}; course normalized: main {n_main} cells, aux {n_aux} cells")
    print(f"main={len(main_rows)} rows, aux={len(aux_rows)} rows")

if __name__ == "__main__":
    main()
