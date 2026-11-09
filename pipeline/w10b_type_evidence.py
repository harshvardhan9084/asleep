#!/usr/bin/env python3
"""w10b_type_evidence.py — W10b (B71): TYPE_EMPTY 521 -> evidence-backed fill.

Owner directive 2026-11-09 "fix the 4908 audit flags from now" (continuing the
W10 flag-fix program; B70 closed PUNCT_ARTIFACT 3281->0, flags 4908->1627).

Zero-guess ladder (every write cites its own evidence class):
  L1 own-recorded print: subject_type_norm (D2 mirror) non-empty -> copy it
     (row's own recorded value, written by a prior committed wave).
  L2 name-print contact: Lab/Laboratory/Workshop -> lab (W8c owner-sanctioned
     literal mapping; 361 committed lab rows). Runs AFTER L1 so the
     slot-note row ("conduct one Lab ... two Electives", whose recorded norm
     is practical) is decided by L1, not by sentence-text word match.
  L3 name-print contact: Project/Seminar/Internship/Dissertation/Industrial
     Training -> project-or-capstone (W4 EXACT precedent, owner-reviewed).
  L4 name-print category: "Open Elective" -> open-elective;
     "Deptt./Department(al) Elective" -> departmental-elective;
     plain "Elective <n>" slot -> elective (W4 EXACT + committed elective
     rows; the 8 plain-elective rows are scheme slot prints).
  Dual contact+category prints are decided per committed precedent:
     "Software Project Management Lab" -> lab (contact print is Lab; the word
     Project is title text) and "Mini Project Lab" -> lab (committed sibling
     'Mini Project Lab' row carries lab — W9c recorded_copy class).

NO-WRITE classes stay honestly flagged (RULES §4):
  - 381 rows with no name-print category/contact evidence (defer to W10c
    corpus page reads of the cited scheme PDFs; L/T/P alone cannot decide
    because committed L-dominant rows carry theory/core/DE alike).
  - 4 "HSMC Audit Group" rows: no codes, no committed audit-group precedent,
    non-credit has zero committed rows -> no write.

Every write = §6b corrections_json {before,after,rule,evidence} +
verification_status=corrected + quality_flags corrected_W10B_TYPE_EVIDENCE
(TYPE_EMPTY tag removed) + change_note seg + subject_type_norm mirror.
DISPLAY_MISSING (2 rows) fixed via the W4 display_from policy. Gates
G1/G2/G3/G6 must PASS before commit (WC.run_gates). No rr_sid; no keys."""
import csv
import json
import re
import sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

# Pre-existing G6 containment-gap rows (documented registry class, "do NOT
# guess-fix without new print evidence"): corpus-wide probe 2026-11-09 over
# all 610 corpus PDFs (norm_al containment, junction-tolerant) = ZERO hits for
# either unit1 — no evidence-widening citation remedy is available. W10b does
# NOT touch these rows at all (not even the cosmetic display fill); they stay
# honestly flagged and are deferred to the W10c page-image/T2T evidence wave.
G6_GAP_DEFER = {"process-equipment-design", "environmental-science-and-ethics"}

rows = WC.load_rows()
pre_rows_by_id = {r["subject_id"]: dict(r) for r in rows}
fl = json.load(open(f"{WC.BASE}/audit_flags.json"))["rows"]

SMALL = {"and", "or", "of", "the", "in", "for", "with", "on", "to", "a", "an", "via", "&"}
ROMAN = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii"}

PAT = {
    "lab": re.compile(r"\b(lab|laboratory|workshop)s?\b", re.I),
    "proj": re.compile(r"\b(project|seminar|internship|dissertation|industrial training)\b", re.I),
    "open": re.compile(r"open[- ]elective", re.I),
    "dept": re.compile(r"(departm\w*|deptt|dept)[. -]*elective|departmental specific elective", re.I),
    "elec": re.compile(r"\belective\b", re.I),
    "audit": re.compile(r"\baudit\b", re.I),
}


def classify(r):
    txt = " | ".join(filter(None, [r.get("subject_name", ""), r.get("subject_name_print", "")]))
    return tuple(sorted(k for k, p in PAT.items() if p.search(txt)))


def display_from(name, name_print):
    """W4 display policy (B56), copied verbatim-semantics for self-containment."""
    base = (name_print or "").strip()
    if not base:
        base = (name or "").replace("-", " ").replace("_", " ")
    else:
        segs = [s.strip() for s in base.split(" | ")]
        cands = [s for s in segs if "Detailed-doc" not in s and "Print" not in s
                 and "Scheme" not in s and "print" not in s]
        base = (cands[0] if cands else segs[0])
        base = re.sub(r"^Detailed-doc Print:\s*", "", base, flags=re.I)
    base = re.sub(r"^[A-Z]{2,4}\d{3}[A-Z]?\s*[-–:]?\s*", "", base)
    base = re.sub(r"\s+", " ", base).strip(" -–,")
    words = base.split(" ")
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if re.fullmatch(r"[ivxIVX]+", lw) and lw in ROMAN:
            out.append(lw.upper())
        elif i > 0 and lw in SMALL and not w.endswith("."):
            out.append(lw)
        elif w.isupper() and len(w) > 3 and w[-1].isalpha():
            out.append(w.capitalize())
        elif re.match(r"^[A-Za-z]", w):
            out.append(w[0].upper() + w[1:])
        else:
            out.append(w)
    return " ".join(out)


# --- classify the TYPE_EMPTY target set --------------------------------------
te = [r for r in rows
      if r.get("row_kind") == "subject" and not (r.get("subject_type") or "").strip()]
assert len(te) == 521, f"TYPE_EMPTY drifted: {len(te)}"

from collections import Counter
combos = Counter(classify(r) for r in te)
EXPECTED = {
    (): 381, ("lab",): 99, ("proj",): 19, ("elec",): 8, ("audit",): 4,
    ("elec", "open"): 3, ("dept", "elec"): 4, ("lab", "proj"): 2,
    ("elec", "lab"): 1,
}
assert combos == Counter(EXPECTED), f"combo drift: {dict(combos)}"

# --- ladder -------------------------------------------------------------------
n_write = 0
by_class = Counter()
touched = set()
for r in te:
    sid = r["subject_id"]
    txt = " | ".join(filter(None, [r.get("subject_name", ""), r.get("subject_name_print", "")]))
    combo = classify(r)
    norm_rec = (r.get("subject_type_norm") or "").strip()
    tgt = ev = None
    if norm_rec:
        tgt = norm_rec.lower()
        ev = ("row's own recorded subject_type_norm mirror (prior committed wave write); "
              f"name print {txt[:70]!r}")
        cls = "norm_rec"
    elif combo == ("lab",) or combo == ("lab", "proj"):
        tgt = "lab"
        ev = (f"name print {txt[:70]!r} prints Lab/Laboratory contact; owner-sanctioned "
              "literal mapping laboratory/workshop->lab (W8c) + committed lab rows; "
              "dual 'Mini Project Lab' decided by committed sibling carrying lab (W9c recorded_copy)")
        cls = "lab"
    elif combo == ("proj",):
        tgt = "project-or-capstone"
        ev = (f"name print {txt[:70]!r} prints Project/Seminar/Internship/Dissertation/"
              "Industrial-Training contact; W4 EXACT precedent (owner-reviewed B56)")
        cls = "proj"
    elif combo == ("elec", "open"):
        tgt = "open-elective"
        ev = f"name print {txt[:70]!r} prints 'Open Elective'; W4 EXACT precedent"
        cls = "open"
    elif combo == ("dept", "elec"):
        tgt = "departmental-elective"
        ev = (f"name print {txt[:70]!r} prints Deptt./Departmental Elective; "
              "W4 EXACT precedent (incl. 'deptt-elective')")
        cls = "dept"
    elif combo == ("elec",):
        tgt = "elective"
        ev = (f"name print {txt[:70]!r} is a plain Elective slot print; "
              "W4 EXACT 'elective'->elective + committed elective rows")
        cls = "elec"
    # ("audit",) 4 rows and () 381 rows: NO WRITE — stay honestly flagged.
    if not tgt:
        by_class["no_write_" + ("audit" if combo == ("audit",) else "noprint")] += 1
        continue
    before = r.get("subject_type", "")
    cj = json.loads(r.get("corrections_json", "") or "[]")
    cj.append({"field": "subject_type", "before": before, "after": tgt,
               "rule": f"W10b/{cls.upper()}_PRINT_EVIDENCE", "evidence": ev,
               "wave": "W10b"})
    r["corrections_json"] = json.dumps(cj, ensure_ascii=False)
    r["subject_type"] = tgt
    r["subject_type_norm"] = tgt
    r["verification_status"] = "corrected"
    qf = [t for t in (r.get("quality_flags", "") or "").split(";") if t and t != "TYPE_EMPTY"]
    if "corrected_W10B_TYPE_EVIDENCE" not in qf:
        qf.append("corrected_W10B_TYPE_EVIDENCE")
    r["quality_flags"] = ";".join(qf)
    seg = ("W10b(§6b): subject_type filled from own name-print/recorded evidence "
           f"({cls}; before preserved in corrections_json)")
    prev = r.get("change_note_vs_previous", "") or ""
    if seg not in prev:
        r["change_note_vs_previous"] = (prev + "; " if prev else "") + seg
    touched.add(sid)
    by_class[cls] += 1
    n_write += 1

# --- DISPLAY_MISSING (2) via W4 display policy --------------------------------
n_disp = 0
for r in rows:
    if r.get("row_kind") != "subject" or r["subject_id"] in G6_GAP_DEFER:
        continue
    if (r.get("subject_name_display", "") or "").strip():
        continue
    disp = display_from(r.get("subject_name", "") or "", r.get("subject_name_print", "") or "")
    if disp:
        cj = json.loads(r.get("corrections_json", "") or "[]")
        cj.append({"field": "subject_name_display", "before": r.get("subject_name_display", ""),
                   "after": disp, "rule": "W10b/DISPLAY_W4_POLICY",
                   "evidence": "W4 display_from policy (B56): artifact-cleaned name_print, else slug",
                   "wave": "W10b"})
        r["corrections_json"] = json.dumps(cj, ensure_ascii=False)
        r["subject_name_display"] = disp
        touched.add(r["subject_id"])
        n_disp += 1

# --- gates + commit -------------------------------------------------------------
assert dict(by_class) == {"norm_rec": 1, "lab": 101, "proj": 19, "open": 3,
                          "dept": 4, "elec": 8,
                          "no_write_noprint": 381, "no_write_audit": 4}, dict(by_class)
gates = WC.run_gates(rows, touched, pre_rows_by_id)
print("GATES|" + json.dumps({k: (v if not isinstance(v, tuple) else v) for k, v in gates.items()}))
# gate_g1/g2/g3/g6 return None on PASS, a message string on FAIL.
if not (gates["g1"] is None and gates["g2"] is None and gates["g3"] is None
        and gates["g6"] in (None, True)):
    print("W10B_ABORT|gates failed"); sys.exit(2)
WC.commit(rows, "W10b", n_write, gates,
          meta_extra={"wave": "W10b", "type_writes": n_write, "display_writes": n_disp,
                      "by_class": dict(by_class), "honest_no_write": 385})
WC.refresh_flags_consumed({"TYPE_EMPTY": True, "DISPLAY_MISSING": True, "__wave__": "W10b"})
print(f"W10B_APPLY|type={n_write}|display={n_disp}|by_class={json.dumps(dict(by_class))}")
print(f"W10B_HONEST|no_print=381|audit_group=4|g6_gap_defer={sorted(G6_GAP_DEFER)} (stay flagged; W10c corpus page reads)")
return_code = 0
sys.exit(return_code)
