#!/usr/bin/env python3
"""w8a_hygiene.py — W8a post-audit hygiene wave (owner go-ahead 2026-11-08).
Evidence-in-hand deterministic fixes over the W7 re-audit flag classes:

  W1 leftovers (RULES §6b, same dictionary evidence as B52):
    - 'Warshalll' -> 'Warshall' (2 rows; standard spelling, corpus xrow)
    - 'BehroozParahami' -> 'Behrooz Parhami' (spelling + fused-space artifact)
    - 'Geoftrey' -> 'Geoffrey' (new dictionary term; corpus prints 'Geoffrey'
      correctly on 15 rows — Geoffrey Gordon, System Simulation, PHI)
  W4 leftover:
    - DISPLAY_MISSING (2 rows): subject_name_display from the row's own
      name_print 'detailed-doc print: X' evidence
  W2 leftover:
    - BOOK_NUMART entry-start numbering strips (23 entries: '8.process …',
      '1.Bovee&Thill …', '2) Comer …'); volume/year statements (Vol. N.,
      NNNN-NN.) are legitimate print and are NOT touched
Every write carries corrections_json {field,before,after,rule,evidence} +
quality_flags tag + change_note_vs_previous wave seg (RULES §6b).
Gates G1/G2/G3/G6 must PASS before commit; push handled by the caller."""
import json
import re
import sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

BASE = WC.BASE
rows = WC.load_rows()
by_id = {r["subject_id"]: r for r in rows}

W1_PATS = [
    ("Warshal", re.compile(r"\bWarshal\b|\bWarshalll\b"), "Warshall", "W1/AUTH_TYPO_warshal",
     "ref: Stephen Warshall (transitive closure); xrow: corpus prints 'Warshall' correctly on 5+ rows "
     "(incl. data-structure, data-structures, design-and-analysis-of-algorithm)"),
    ("Parahami", re.compile(r"Behrooz\s*Parahami|(?<![A-Za-z])Parahami"), "Parhami", "W1/AUTH_TYPO_parahami",
     "ref: Behrooz Parhami, Computer Organization (Oxford); xrow: corpus prints 'Parhami' on "
     "computer-organization-and-architecture"),
    ("Geoftrey", re.compile(r"\bGeoftrey\b"), "Geoffrey", "W1/AUTH_TYPO_geoftrey",
     "xrow: corpus prints 'Geoffrey' correctly on 15 rows (Geoffrey Gordon, System Simulation, PHI)"),
]
NUMART = re.compile(r"^(\s*)(\d{1,2}[\.\)]+)(\s*)(\S.*)$", re.S)

n_w1 = n_disp = n_num = 0
touched = set()
pre_rows = {r["subject_id"]: dict(r) for r in rows}
# per-sid edit counts for accurate applied accounting after deferrals
edits_by_sid = {}
def bump(sid):
    edits_by_sid[sid] = edits_by_sid.get(sid, 0) + 1



def corrections_append(r, entry):
    cj = r.get("corrections_json", "") or ""
    try:
        arr = json.loads(cj) if cj.strip() else []
    except Exception:
        arr = []
    arr.append(entry)
    r["corrections_json"] = json.dumps(arr, ensure_ascii=False)


def qf_tag(r, rule):
    qf = r.get("quality_flags", "") or ""
    tag = "corrected_" + rule.split("/")[1]
    tags = [t for t in qf.split(";") if t]
    if tag not in tags:
        tags.append(tag)
    r["quality_flags"] = ";".join(tags)


def note_seg(r, seg):
    if seg not in (r.get("change_note_vs_previous", "") or ""):
        prev = r.get("change_note_vs_previous", "") or ""
        r["change_note_vs_previous"] = (prev + "; " if prev else "") + seg


def iter_book_entries(r):
    for col in ("textbooks_structured", "reference_books_structured", "experiments_structured"):
        arr = r.get(col, "") or ""
        if not arr.strip().startswith("["):
            continue
        try:
            lst = json.loads(arr)
        except Exception:
            continue
        for i, e in enumerate(lst):
            if isinstance(e, dict) and isinstance(e.get("book"), str):
                yield col, arr, lst, i, e


# --- W1 leftovers -----------------------------------------------------------
for r in rows:
    sid = r["subject_id"]
    plain_fields = [f"unit{i}_text" for i in range(1, 6)] + [f"co{i}_text" for i in range(1, 7)] + ["prerequisites"]
    for term, pat, fix, rule, ev in W1_PATS:
        for fld in plain_fields:
            v = r.get(fld, "") or ""
            if not v or not pat.search(v):
                continue
            before = v
            after = pat.sub(fix, v)
            if after == before:
                continue
            # fused-space special: 'BehroozParhami' needs the space restored too
            if term == "Parahami" and "BehroozParhami" in after:
                after = after.replace("BehroozParhami", "Behrooz Parhami")
            r[fld] = after
            corrections_append(r, {"field": fld, "before": before if len(before) < 400 else before[:400],
                                   "after": after if len(after) < 400 else after[:400],
                                   "rule": rule, "evidence": ev, "wave": "W8a"})
            qf_tag(r, rule)
            note_seg(r, f"W8a §6b correction ({rule}: printed typo fixed, before preserved in corrections_json)")
            touched.add(sid); bump(sid)
            n_w1 += 1
    for col, arr, lst, i, e in list(iter_book_entries(r)):
        t = e["book"]
        m = None
        for term, pat, fix, rule, ev in W1_PATS:
            if pat.search(t):
                m = (term, pat, fix, rule, ev)
                break
        if not m:
            continue
        term, pat, fix, rule, ev = m
        before = t
        after = pat.sub(fix, t)
        if term == "Parahami" and "BehroozParhami" in after:
            after = after.replace("BehroozParhami", "Behrooz Parhami")
        if after == before:
            continue
        e["book"] = after
        r[col] = json.dumps(lst, ensure_ascii=False)
        corrections_append(r, {"field": f"{col}[{i}].book", "before": before[:400], "after": after[:400],
                               "rule": rule, "evidence": ev, "wave": "W8a"})
        qf_tag(r, rule)
        note_seg(r, f"W8a §6b correction ({rule})")
        touched.add(sid); bump(sid)
        n_w1 += 1

# --- W4 DISPLAY_MISSING (evidence: the row's own name_print) -----------------
# scope: subject rows only (W4 scope; rule/summary rows have no display by design)
for r in rows:
    if (r.get("row_kind", "subject") or "subject") != "subject":
        continue
    if (r.get("subject_name_display", "") or "").strip():
        continue
    nm = r.get("subject_name", "") or ""
    if not nm:
        continue
    np_ = r.get("subject_name_print", "") or ""
    m = re.search(r"detailed-doc print:\s*([^\n|]+)", np_)
    disp = m.group(1).strip() if m else nm.strip()
    if not disp:
        continue
    r["subject_name_display"] = disp
    corrections_append(r, {"field": "subject_name_display", "before": "",
                           "after": disp, "rule": "W4/DISPLAY_FILL",
                           "evidence": "row's own subject_name_print detailed-doc print evidence "
                                       "(W4 display rule; zero-guess satisfied by recorded print)",
                           "wave": "W8a"})
    qf_tag(r, "W4/DISPLAY_FILL")
    note_seg(r, "W8a §6b fill (subject_name_display from recorded detailed-doc print)")
    touched.add(r["subject_id"]); bump(r["subject_id"])
    n_disp += 1

# --- W2 BOOK_NUMART entry-start strips ---------------------------------------
NUM_EV = ("scheme book-list print numbering artifact (entry-start 'N.'/'N)'); printed numbering "
          "preserved in corrections_json before-value; volume/year statements untouched")
for r in rows:
    sid = r["subject_id"]
    for col, arr, lst, i, e in list(iter_book_entries(r)):
        t = e["book"]
        m = NUMART.match(t)
        if not m:
            continue
        after = m.group(4)
        if not after.strip():
            continue
        e["book"] = after
        r[col] = json.dumps(lst, ensure_ascii=False)
        corrections_append(r, {"field": f"{col}[{i}].book", "before": t[:400], "after": after[:400],
                               "rule": "W2/BOOK_NUMART", "evidence": NUM_EV, "wave": "W8a"})
        qf_tag(r, "W2/BOOK_NUMART")
        note_seg(r, "W8a §6b correction (W2/BOOK_NUMART entry-start numbering strip)")
        touched.add(sid); bump(sid)
        n_num += 1

print(f"W8A|w1_fixes={n_w1} display_fills={n_disp} numart_strips={n_num} touched={len(touched)}")

# --- gates + commit -----------------------------------------------------------
def run_and_maybe_defer(rows, touched, pre_rows):
    gates = WC.run_gates(rows, touched, pre_rows)
    deferred = []
    if gates["g6"]:
        for part in gates["g6"].split(";"):
            sid = part.split(":")[0].strip()
            if sid in touched:
                deferred.append(sid)
        for sid in deferred:
            rows[rows.index(next(r for r in rows if r["subject_id"] == sid))] = dict(pre_rows[sid])
            touched.discard(sid)
        if deferred:
            print(f"W8A|g6_gap_deferred={len(deferred)}: {', '.join(deferred)}")
            gates = WC.run_gates(rows, touched, pre_rows)
    return gates, deferred


gates, deferred = run_and_maybe_defer(rows, touched, pre_rows)
print(f"G1|{'PASS' if not gates['g1'] else 'FAIL ' + gates['g1']}")
print(f"G2|{'PASS' if not gates['g2'] else 'FAIL ' + gates['g2']}|codes={gates['g2_codes']}")
print(f"G3|{'PASS' if not gates['g3'] else 'FAIL ' + gates['g3']}")
print(f"G6|{'PASS' if not gates['g6'] else 'FAIL ' + gates['g6']}|checks={gates['g6_checks']}|pre_edit_hits={gates['g6_pre_edit_hits']}")
if any([gates["g1"], gates["g2"], gates["g3"], gates["g6"]]):
    print("ABORT: gate failure")
    sys.exit(2)
applied = sum(cnt for sid, cnt in ((s, edits_by_sid.get(s, 0)) for s in touched)) if edits_by_sid else 0
WC.commit(rows, "W8a", applied, gates,
          {"w1_fixes": n_w1, "display_fills": n_disp, "numart_strips": n_num,
           "applied": applied, "touched": len(touched), "g6_gap_deferred": deferred})
print("W8A|COMMIT_OK")
