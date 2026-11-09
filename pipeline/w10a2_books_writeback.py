#!/usr/bin/env python3
"""w10a2_books_writeback.py — W10a2 (B70): actual write-back of the book-field
artifact cleanup + honest ledger repair.

Discovery: since B54 the W6 book-field (textbooks/reference/experiments) edits
mutated the parsed array in memory but never re-serialized it into the CSV
(`b[k]=new` without `r[col]=json.dumps(...)`), so those corrections were
metadata-only: corrections_json recorded before/after while the field kept the
artifact. W10a inherited the same bug (213 edits, metadata-only) before its
guard-v18 patch (that part persisted). This wave:
  1. applies clean-v18 (committed W6 rule + al/ed/eds + paren-prefix guard +
     fixpoint) to every book/experiment entry of candidate rows and ACTUALLY
     writes the field back;
  2. appends its own corrections record per real change, noting supersession
     of the non-persisted W6/W10a records on the same field;
  3. where clean keeps the text but a stale W6/W10a record claims a change,
     appends an explicit no-op repair record so the ledger matches reality
     (RULES §6b honesty).
Gates via WC.run_gates + WC.commit. T2T 0.
"""
import json
import re
import sys
import unicodedata

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

JF = ["textbooks_structured", "reference_books_structured", "experiments_structured"]
ABBREV_EXTRA = {"al", "ed", "eds"}


def is_abbrev(text, dot_pos):
    start = max(text.rfind(" ", 0, dot_pos), text.rfind("\n", 0, dot_pos), 0)
    word = text[start:dot_pos].strip()
    if not word:
        return False
    if word.lstrip("(").lower() in ABBREV_EXTRA:
        return True
    if re.fullmatch(r"[A-Za-z]", word):
        return True
    if re.fullmatch(r"(?:[A-Za-z]\.)+[A-Za-z]", word):
        return True
    return False


def clean(text):
    def once(t):
        out = []
        i = 0
        while i < len(t):
            if t.startswith(".,", i) and not is_abbrev(t, i):
                out.append(".")
                i += 2
                continue
            out.append(t[i])
            i += 1
        t = "".join(out)
        t = re.sub(r",,", ",", t)
        t = re.sub(r" ,", ",", t)
        t = re.sub(r"^\s+([a-z])", r"\1", t, flags=re.M)
        if any(0x1D400 <= ord(ch) <= 0x1D7FF for ch in t):
            t = "".join(unicodedata.normalize("NFKC", ch) if 0x1D400 <= ord(ch) <= 0x1D7FF else ch for ch in t)
        return t

    prev = text
    t = once(prev)
    while t != prev:
        prev = t
        t = once(t)
    return t


rows = WC.load_rows()
by_id = {r["subject_id"]: r for r in rows}

# candidates: current PUNCT flags + any row carrying W6/W10a book-field records
fl = json.load(open(f"{WC.BASE}/audit_flags.json"))["rows"]
cand = set()
for sid, lst in fl.items():
    if any(f.get("rule") == "PUNCT_ARTIFACT" for f in lst):
        cand.add(sid)
stale_repair = {}
for r in rows:
    try:
        cj = json.loads(r.get("corrections_json", "") or "[]")
    except Exception:
        continue
    for e in cj:
        fld = str(e.get("field", ""))
        col = fld.split("[")[0]
        if col in JF and e.get("rule") == "PUNCT_ARTIFACT" and e.get("wave") in ("W6", "W10a"):
            cand.add(r["subject_id"])
            stale_repair.setdefault(r["subject_id"], set()).add(fld)

n_fix = 0
n_stale = 0
n_arr_unparseable = 0
touched = set()
for sid in sorted(cand):
    r = by_id[sid]
    try:
        cjson = json.loads(r.get("corrections_json", "") or "[]")
    except Exception:
        cjson = []
    qf = [x for x in (r.get("quality_flags", "") or "").split(";") if x.strip()]
    row_changed = False
    for col in JF:
        raw = r.get(col, "") or "[]"
        try:
            arr = json.loads(raw)
        except Exception:
            n_arr_unparseable += 1
            continue
        if not isinstance(arr, list):
            continue
        k = "exp" if col == "experiments_structured" else "book"
        arr_changed = False
        for i, b in enumerate(arr):
            if not isinstance(b, dict):
                continue
            t = b.get(k, "")
            if not t:
                continue
            fld = f"{col}[{i}]"
            new = clean(t)
            if new != t:
                b[k] = new
                arr_changed = True
                row_changed = True
                n_fix += 1
                cjson.append({"field": fld, "before": t[:200], "after": new[:200],
                              "rule": "PUNCT_ARTIFACT", "wave": "W10a2",
                              "evidence": "committed W6 deterministic artifact rule (v18 fixpoint); actual field write-back — supersedes the non-persisted W6/W10a record on this field (JSON re-serialization was missing since B54); before-form preserved here"})
            elif fld in stale_repair.get(sid, set()):
                has_stale = any(e.get("field") == fld and e.get("wave") in ("W6", "W10a")
                                and str(e.get("after", ""))[:200] != t[:200] for e in cjson)
                if has_stale:
                    cjson.append({"field": fld, "before": t[:200], "after": t[:200],
                                  "rule": "PUNCT_ARTIFACT", "wave": "W10a2",
                                  "evidence": "no-op ledger repair: prior W6/W10a book-field record did not persist (write-back missing); v18 abbrev guard keeps this legit print (et al./ed./eds./paren-prefixed); field verified unchanged"})
                    n_stale += 1
                    row_changed = True
        if arr_changed:
            r[col] = json.dumps(arr, ensure_ascii=False)
    if row_changed:
        if "corrected_PUNCT_ARTIFACT" not in qf:
            qf.append("corrected_PUNCT_ARTIFACT")
        r["quality_flags"] = ";".join(qf)
        r["verification_status"] = "corrected"
        seg = "W10a2 book-field write-back repair per RULES §6b — non-persisted W6/W10a JF edits actually applied; before-forms in corrections_json"
        if seg not in (r.get("change_note_vs_previous", "") or ""):
            r["change_note_vs_previous"] = ((r.get("change_note_vs_previous", "") + "; ") if r.get("change_note_vs_previous", "") else "") + seg
        touched.add(sid)

print(f"W10A2|field_fixes={n_fix} rows={len(touched)} noop_ledger_repairs={n_stale} unparseable_arrays={n_arr_unparseable}")

if touched:
    pre_rows = {r["subject_id"]: dict(r) for r in rows}
    gates = WC.run_gates(rows, touched, pre_rows)
    print(f"G1|{'PASS' if not gates['g1'] else 'FAIL ' + gates['g1']}")
    print(f"G2|{'PASS' if not gates['g2'] else 'FAIL ' + gates['g2']}|codes={gates['g2_codes']}")
    print(f"G3|{'PASS' if not gates['g3'] else 'FAIL ' + gates['g3']}")
    print(f"G6|{'PASS' if not gates['g6'] else 'FAIL ' + gates['g6']}|checks={gates['g6_checks']}|pre_edit_hits={gates['g6_pre_edit_hits']}")
    if any([gates["g1"], gates["g2"], gates["g3"], gates["g6"]]):
        print("ABORT: gate failure")
        sys.exit(2)
    WC.commit(rows, "W10a2", n_fix, gates, {"noop_ledger_repairs": n_stale, "unparseable_arrays": n_arr_unparseable})
else:
    print("W10A2|no edits — skip commit")
