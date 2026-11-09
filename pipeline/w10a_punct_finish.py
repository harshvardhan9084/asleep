#!/usr/bin/env python3
"""w10a_punct_finish.py — W10a (B70): finish the PUNCT_ARTIFACT class.

Owner directive 2026-11-09: "Are you fixing up those 4908 audit flags? Okay,
do it from now." — evidence-first wave over the audit flags.

Post-W6-rerun+audit-v17 residuals (363 fields) adjudicated:
  A. guard extension (legit print kept): 'et al.,' / 'ed.,' / 'eds.,' and
     paren-prefixed '(e.g.,' are standard scholarly print — added to the W6
     abbreviation guard in BOTH w6_artifacts.py and audit_rules.py (v18).
  B. clean() fixpoint: W6's single-pass ' ,'→',' after ',,'→',' could leave
     a manufactured ',,' behind — clean() now iterates to fixpoint (same
     committed rule, no semantic change).
  C. re-apply clean() with tolerant JSON parse (plain json.loads silently
     skipped some rows; audit jload is the tolerant reference) to the
     remaining genuinely-fixable fields per the committed W6 rule
     ('.,'→'.' non-abbrev, ',,'→',', ' ,'→',', leading-space, math-italic),
     with corrections_json before/after + quality_flags + change_note
     (RULES §6b). objectives_print stays untouched (recorded W6 policy) —
     its 2 flags are paren-prefixed legit print and reclassify as
     auditor-FP via the guard.
Gates via WC.commit (G1/G2/G3/G6). T2T 0; keys untouched.
"""
import json
import re
import sys
import unicodedata

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

rows = WC.load_rows()
by_id = {r["subject_id"]: r for r in rows}
fl = json.load(open(f"{WC.BASE}/audit_flags.json"))["rows"]

ABBREV_EXTRA = {"al", "ed", "eds"}


def is_abbrev(text, dot_pos):
    start = max(text.rfind(" ", 0, dot_pos), text.rfind("\n", 0, dot_pos), 0)
    word = text[start:dot_pos].strip()
    if not word:
        return False
    w = word.lstrip("(").lower()
    if w in ABBREV_EXTRA:
        return True
    if re.fullmatch(r"[A-Za-z]", word):
        return True
    if re.fullmatch(r"(?:[A-Za-z]\.)+[A-Za-z]", word):
        return True
    return False


def clean(text):
    """w6_artifacts.clean with v18 abbrev additions + fixpoint iteration."""
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
    while t != prev:          # fixpoint: catches ' ,'→',,' manufactured pairs
        prev = t
        t = once(t)
    return t


n_fix = 0
n_guarded_fp = 0
touched = set()
edits_total = []
for sid, lst in fl.items():
    r = by_id.get(sid)
    if not r:
        continue
    edits_here = []
    for f in lst:
        if f.get("rule") != "PUNCT_ARTIFACT":
            continue
        fld = f.get("field", "")
        col = fld.split("[")[0]
        if col == "objectives_print":
            n_guarded_fp += 1   # '(e.g.,' legit print, guard handles; untouched
            continue
        idx = None
        if "[" in fld:
            idx = int(fld.split("[")[1].rstrip("]"))
        try:
            arr = json.loads(r.get(col, "") or "[]")
        except Exception:
            try:
                arr = json.loads((r.get(col, "") or "").replace("\n", "\\n"))
            except Exception:
                continue
        if not isinstance(arr, list) or (idx is not None and idx >= len(arr)):
            continue
        k = "exp" if col == "experiments_structured" else "book"
        obj = arr[idx] if idx is not None else r.get(col, "")
        if not isinstance(obj, dict):
            continue
        t = obj.get(k, "")
        if not t:
            continue
        # guard-only reclassification: every '.,' abbrev-guarded and no ',,'?
        if not re.search(r",,|,\s*,", t) and all(is_abbrev(t, m.start()) for m in re.finditer(r"\.,", t)):
            n_guarded_fp += 1
            continue
        new = clean(t)
        if new != t:
            edits_here.append((fld, t, new))
            obj[k] = new
        else:
            n_guarded_fp += 1   # clean keeps everything -> legit print
    if edits_here:
        cjson = json.loads(r.get("corrections_json", "") or "[]")
        qf = [x for x in (r.get("quality_flags", "") or "").split(";") if x.strip()]
        for field, before, after in edits_here:
            cjson.append({"field": field, "before": before[:200], "after": after[:200],
                          "rule": "PUNCT_ARTIFACT",
                          "evidence": "committed W6 deterministic artifact rule (v18 fixpoint + tolerant parse); before-form preserved here and in *_print/scheme-line",
                          "wave": "W10a"})
        r["corrections_json"] = json.dumps(cjson, ensure_ascii=False)
        if "corrected_PUNCT_ARTIFACT" not in qf:
            qf.append("corrected_PUNCT_ARTIFACT")
        r["quality_flags"] = ";".join(qf)
        r["verification_status"] = "corrected"
        seg = "W10a punctuation-finish per RULES §6b (W6 rule v18) — before-forms in corrections_json"
        if seg not in (r.get("change_note_vs_previous", "") or ""):
            r["change_note_vs_previous"] = ((r.get("change_note_vs_previous", "") + "; ") if r.get("change_note_vs_previous", "") else "") + seg
        n_fix += len(edits_here)
        touched.add(sid)
        edits_total.extend(edits_here)

print(f"W10A|edits={n_fix} rows={len(touched)} guarded_fp={n_guarded_fp}")

# --- also patch the two precedent scripts (toolchain syncs to repo on push) --
import re as _re
w6 = "/home/z/my-project/scripts/pipeline_v2/w6_artifacts.py"
src = open(w6).read()
src = src.replace('"approx", "Jr", "Sr"}', '"approx", "Jr", "Sr", "al", "ed", "eds"}')
src = src.replace('''    start = max(text.rfind(" ", 0, dot_pos), text.rfind("\\n", 0, dot_pos), 0)
    word = text[start:dot_pos].strip()
    if not word:
        return False
    if word.lower() in {a.lower() for a in ABBREV}:''',
'''    start = max(text.rfind(" ", 0, dot_pos), text.rfind("\\n", 0, dot_pos), 0)
    word = text[start:dot_pos].strip()
    if not word:
        return False
    if word.lstrip("(").lower() in {a.lower() for a in ABBREV}:''')
open(w6, "w").write(src)
au = "/home/z/my-project/scripts/pipeline_v2/audit_rules.py"
src = open(au).read()
src = src.replace('"eq", "approx", "jr", "sr", "etc."}', '"eq", "approx", "jr", "sr", "etc.", "al", "ed", "eds"}')
src = src.replace('    if word.lower() in _ABBREV_WORDS:', '    if word.lstrip("(").lower() in _ABBREV_WORDS:')
open(au, "w").write(src)
print("PATCHED|w6_artifacts+v17 guard (al/ed/eds + paren-prefix)")

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
    WC.commit(rows, "W10a", n_fix, gates, {"guarded_fp": n_guarded_fp})
else:
    print("W10A|no edits — skip commit")
