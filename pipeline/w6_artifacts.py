#!/usr/bin/env python3
"""w6_artifacts.py — W6 (B54): unicode/punctuation artifact cleanup (deterministic).
1. ',,' → ','  and ' ,' → ','  (spacing artifacts)
2. '.,' → '.'  GUARDED: kept when the period ends an abbreviation or
   initialism (e.g., / i.e., / viz., / etc., / No., / Inc., / Co., / single
   initials 'J.,' / dotted initialisms 'U.S.A.,' 'G.P.,') — those are legit
   print; all other '.,' (e.g. 'Direct Memory Access., I/O') → '.'
3. math-italic Unicode (U+1D400-1D7FF decode artifacts) → NFKC plain ASCII.
4. '(n) lowercase' tokens: NO auto-fix (LR(0)/list-marker notation collides);
   stays needs_review by design (recorded decision).
RULES §6b: before-forms in corrections_json; objectives_print untouched."""
import csv
import json
import re
import sys
import unicodedata

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

BASE = WC.BASE
TF = [f"unit{i}_text" for i in range(1, 6)] + [f"co{i}_text" for i in range(1, 7)]
JF = ["textbooks_structured", "reference_books_structured", "experiments_structured"]

ABBREV = {"e.g", "i.e", "viz", "etc", "No", "Inc", "Ltd", "Co", "Corp", "Pvt", "Sons",
          "Bros", "Dr", "Mr", "Mrs", "St", "vs", "Vol", "pp", "Fig", "Eq", "approx", "Jr", "Sr"}


def is_abbrev(text, dot_pos):
    """True if the '.' at dot_pos ends an abbreviation/initialism (keep ',')."""
    start = max(text.rfind(" ", 0, dot_pos), text.rfind("\n", 0, dot_pos), 0)
    word = text[start:dot_pos].strip()
    if not word:
        return False
    if word.lower() in {a.lower() for a in ABBREV}:
        return True
    if re.fullmatch(r"[A-Za-z]", word):          # single initial: 'J.,'
        return True
    if re.fullmatch(r"(?:[A-Za-z]\.)+[A-Za-z]", word):  # dotted initialism: G.P., U.S.A.
        return True
    return False


def clean(text):
    out = []
    i = 0
    changed = []
    while i < len(text):
        if text.startswith(".,", i) and not is_abbrev(text, i):
            out.append(".")
            i += 2
            changed.append(".,")
            continue
        out.append(text[i])
        i += 1
    t = "".join(out)
    t2 = re.sub(r",,", ",", t)
    if t2 != t:
        changed.append(",,")
    t3 = re.sub(r" ,", ",", t2)
    if t3 != t2:
        changed.append(" ,")
    t4 = re.sub(r"^\s+([a-z])", r"\1", t3, flags=re.M)  # leading stray space before lowercase
    if t4 != t3:
        changed.append("lead-space")
    # math-italic → plain
    if any(0x1D400 <= ord(ch) <= 0x1D7FF for ch in t4):
        t4 = "".join(unicodedata.normalize("NFKC", ch) if 0x1D400 <= ord(ch) <= 0x1D7FF else ch for ch in t4)
        changed.append("math-italic")
    return t4, changed


rows = WC.load_rows()
by_id = {r["subject_id"]: r for r in rows}
flags_doc = WC.load_flags()
math_sids = {sid for sid, fl in flags_doc.get("rows", {}).items()
             if any(f.get("rule") == "MATH_ITALIC" for f in fl)}

n_fix = 0
touched = set()
rule_stats = {}
for r in rows:
    sid = r["subject_id"]
    edits_here = []
    for c in TF:
        t = r.get(c, "") or ""
        if not t:
            continue
        if not (".," in t or ",," in t or " ," in t or any(0x1D400 <= ord(ch) <= 0x1D7FF for ch in t)):
            continue
        new, changed = clean(t)
        if new != t:
            rule = "PUNCT_ARTIFACT" if any(ch in (".,", ",,", " ,", "lead-space") for ch in changed) else "MATH_ITALIC"
            if sid in math_sids and "math-italic" in changed:
                rule = "MATH_ITALIC"
            edits_here.append((c, t, new, rule, "+".join(sorted(set(changed)))))
            r[c] = new
    for col in JF:
        try:
            arr = json.loads(r.get(col, "") or "[]")
        except Exception:
            continue
        k = "exp" if col == "experiments_structured" else "book"
        for i, b in enumerate(arr):
            if not isinstance(b, dict):
                continue
            t = b.get(k, "")
            if not t or not (".," in t or ",," in t or " ," in t):
                continue
            new, changed = clean(t)
            if new != t:
                edits_here.append((f"{col}[{i}]", t, new, "PUNCT_ARTIFACT", "+".join(sorted(set(changed)))))
                b[k] = new
    if edits_here:
        cjson = json.loads(r.get("corrections_json", "") or "[]")
        qf = [f for f in (r.get("quality_flags", "") or "").split(";") if f.strip()]
        rules_here = set()
        for field, before, after, rule, kind in edits_here:
            cjson.append({"field": field, "before": before[:200], "after": after[:200],
                          "rule": rule, "evidence": f"decode/punctuation artifact class ({kind}); print form preserved in corrections_json before-value and *_print/scheme-line", "wave": "W6"})
            rules_here.add(rule)
        r["corrections_json"] = json.dumps(cjson, ensure_ascii=False)
        for rule in rules_here:
            if rule not in qf:
                qf.append(f"corrected_{rule}")
        r["quality_flags"] = ";".join(qf)
        r["verification_status"] = "corrected"
        seg = f"W6 artifact cleanup per RULES §6b ({', '.join(sorted(rules_here))}) — before-forms in corrections_json"
        if seg not in (r.get("change_note_vs_previous", "") or ""):
            r["change_note_vs_previous"] = ((r.get("change_note_vs_previous", "") + "; ") if r.get("change_note_vs_previous", "") else "") + seg
        touched.add(sid)
        n_fix += len(edits_here)
        for rule in rules_here:
            rule_stats[rule] = rule_stats.get(rule, 0) + 1

print(f"W6|edits={n_fix} rows_touched={len(touched)} by_rule={rule_stats}")

pre_rows = {r["subject_id"]: dict(r) for r in rows}
gates = WC.run_gates(rows, touched, pre_rows)
print(f"G1|{'PASS' if not gates['g1'] else 'FAIL ' + gates['g1']}")
print(f"G2|{'PASS' if not gates['g2'] else 'FAIL ' + gates['g2']}|codes={gates['g2_codes']}")
print(f"G3|{'PASS' if not gates['g3'] else 'FAIL ' + gates['g3']}")
print(f"G6|{'PASS' if not gates['g6'] else 'FAIL ' + gates['g6']}|checks={gates['g6_checks']}|pre_edit_hits={gates['g6_pre_edit_hits']}")
if any([gates["g1"], gates["g2"], gates["g3"], gates["g6"]]):
    print("ABORT: gate failure")
    sys.exit(2)
WC.commit(rows, "W6", n_fix, gates, {"by_rule": rule_stats})
