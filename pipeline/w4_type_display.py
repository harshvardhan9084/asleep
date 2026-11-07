#!/usr/bin/env python3
"""w4_type_display.py — W4 (B56): subject_type normalization (129 raw variants
→ controlled vocab) + subject_name_display generation. Deterministic.
RULES §6b: raw subject_type is preserved (evidence); unmapped → needs_review,
no write. Display from subject_name_print (artifact-cleaned) or the slug."""
import csv
import json
import re
import sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

VOCAB = {"theory", "lab", "practical", "core", "departmental-elective",
         "open-elective", "elective", "value-added-mandatory",
         "project-or-capstone", "non-credit"}

EXACT = {
    "theory": "theory", "t": "theory", "the": "theory", "theory-course": "theory",
    "core": "core", "core course": "core", "bsc": "core", "basic science course": "core",
    "esc": "core", "engineering science course": "core", "pc": "core", "pcs": "core",
    "professional core": "core", "professional core course": "core", "cc": "core",
    "core course (cc)": "core", "engineering course": "core", "hsmc": "core",
    "humanities and social sciences including management courses": "core",
    "hsm course": "core", "basic science": "core", "engg course": "core",
    "departmental-elective": "departmental-elective", "department-elective": "departmental-elective",
    "dept-elective": "departmental-elective", "deptt-elective": "departmental-elective",
    "de": "departmental-elective", "dse": "departmental-elective",
    "departmental specific elective": "departmental-elective",
    "departmental elective": "departmental-elective", "deptt. elective": "departmental-elective",
    "open-elective": "open-elective", "open elective": "open-elective", "oe": "open-elective",
    "science based open elective": "open-elective", "science-based-open-elective": "open-elective",
    "elective": "elective", "elective-pool": "elective", "elective pool": "elective",
    "moocs": "elective", "mooc": "elective", "honors": "elective", "honour": "elective",
    "honours": "elective", "value-added": "value-added-mandatory",
    "value added course": "value-added-mandatory", "vac": "value-added-mandatory",
    "mandatory": "value-added-mandatory", "audit": "non-credit", "non-credit": "non-credit",
    "noncredit": "non-credit", "audit course": "non-credit", "mandatory course": "value-added-mandatory",
    "lab": "lab", "departmental-lab": "lab", "elective-lab": "lab", "core-lab": "lab",
    "lab/practical": "lab", "practical/lab": "practical", "practical": "practical",
    "p": "practical", "pc-lab": "lab", "practical-cum-lab": "practical",
    "practical/design/drawing": "practical", "sessional": "practical",
    "project": "project-or-capstone", "seminar": "project-or-capstone",
    "internship": "project-or-capstone", "mini project": "project-or-capstone",
    "mini-project": "project-or-capstone", "major project": "project-or-capstone",
    "project/seminar": "project-or-capstone", "dissertation": "project-or-capstone",
    "project & seminar": "project-or-capstone", "industrial training": "project-or-capstone",
}

def norm_type(raw, name):
    t = (raw or "").strip().lower().replace("_", "-").replace("–", "-")
    t = re.sub(r"\s+", " ", t)
    if t in EXACT:
        return EXACT[t]
    # departmental-elective-N / -v / -iv roman/numeric suffixes
    if re.fullmatch(r"department(al)?-elective[- ]?(\d+|[ivx]+)?", t):
        return "departmental-elective"
    if re.fullmatch(r"(dept|deptt|department)[- ]?elective[- ]?(\d+)?", t):
        return "departmental-elective"
    if "open elective" in t or t in ("oe", "soe"):
        return "open-elective"
    if "electiv" in t:
        return "departmental-elective" if ("dept" in t or "department" in t) else "elective"
    if t.endswith("lab") or " laboratory" in t or "lab/practical" in t or t == "labs":
        return "lab"
    if "practi" in t or t in ("p", "d", "drawing", "design", "sessional"):
        return "practical"
    if "project" in t or "seminar" in t or "intern" in t or "training" in t:
        return "project-or-capstone"
    if "value added" in t or "vac" == t or "mandatory" in t:
        return "value-added-mandatory"
    if "audit" in t or "non-credit" in t or "noncredit" in t or "nc" == t:
        return "non-credit"
    if "mooc" in t or "nptel" in t or "online" in t:
        return "elective"
    if t in ("core",) or "core" in t or t in ("bsc", "esc", "pc", "cc", "hsmc"):
        return "core"
    if t == "theory" or t.startswith("theor"):
        return "theory"
    return None  # unmapped → needs_review, no write

SMALL = {"and", "or", "of", "the", "in", "for", "with", "on", "to", "a", "an", "via", "&"}
ROMAN = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii"}

def display_from(name, name_print):
    base = (name_print or "").strip()
    if not base:
        base = (name or "").replace("-", " ").replace("_", " ")
    else:
        # name_print may hold a multi-segment history ('clean | Detailed-doc Print: ...')
        segs = [s.strip() for s in base.split(" | ")]
        cands = [s for s in segs if "Detailed-doc" not in s and "Print" not in s
                 and "Scheme" not in s and "print" not in s]
        base = (cands[0] if cands else segs[0])
        base = re.sub(r"^Detailed-doc Print:\s*", "", base, flags=re.I)
    base = re.sub(r"^[A-Z]{2,4}\d{3}[A-Z]?\s*[-–:]?\s*", "", base)  # code prefix leak
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

rows = WC.load_rows()
pre_rows_local = {r["subject_id"]: dict(r) for r in rows}  # pre-wave snapshot
n_norm = n_inf = n_unmapped = n_disp = 0
touched = set()
for r in rows:
    if r.get("row_kind") != "subject":
        continue
    sid = r["subject_id"]
    raw = (r.get("subject_type", "") or "").strip()
    name = r.get("subject_name", "") or ""
    disp = display_from(name, r.get("subject_name_print", "") or "")
    if disp and disp != r.get("subject_name_display", ""):
        r["subject_name_display"] = disp
        n_disp += 1
        touched.add(sid)
    norm = norm_type(raw, name)
    if norm is None and not raw:
        # zero-guess inference from strong name signals only
        if name.endswith("-lab") or name.endswith("-labs"):
            norm = "lab"
        elif "practical" in name:
            norm = "practical"
        elif name.endswith("-project") or "-mini-project" in name:
            norm = "project-or-capstone"
        if norm:
            n_inf += 1
    if norm:
        if r.get("subject_type_norm", "") != norm:
            r["subject_type_norm"] = norm
            n_norm += 1
            touched.add(sid)
        qf = [f for f in (r.get("quality_flags", "") or "").split(";") if f.strip() and f not in ("TYPE_RAW", "TYPE_EMPTY")]
        r["quality_flags"] = ";".join(qf + ([] if not raw or norm_type(raw, name) else []))
    else:
        if r.get("subject_type_norm", ""):
            r["subject_type_norm"] = ""
            touched.add(sid)
        n_unmapped += 1
        qf = [f for f in (r.get("quality_flags", "") or "").split(";") if f.strip()]
        tag = "TYPE_UNMAPPED" if raw else "TYPE_EMPTY"
        if tag not in qf:
            qf.append(tag)
        r["quality_flags"] = ";".join(qf)

print(f"W4|norm_set={n_norm} name_inferred={n_inf} unmapped={n_unmapped} display_set={n_disp} touched={len(touched)}")

# G6 containment-gap rows (2026-11-08 W4 run): unit1 not provable in any
# currently-resolvable cited doc (supplying doc lost to workspace resets,
# pre-G6-era citation gap; zero-guess ⇒ no edit, flag for owner).
G6_GAP_SIDS = {"process-equipment-design", "environmental-science-and-ethics"}
try:
    af = json.load(open(f"{WC.BASE}/audit_flags.json"))
except Exception:
    af = {"rows": {}}
for sid in G6_GAP_SIDS & touched:
    r = next(x for x in rows if x["subject_id"] == sid)
    # revert this wave's edits on the row (keep it byte-identical to published)
    pre = pre_rows_local.get(sid)
    if pre:
        for k in ("subject_name_display", "subject_type_norm", "quality_flags"):
            r[k] = pre.get(k, "")
    touched.discard(sid)
    fl = af["rows"].setdefault(sid, [])
    if not any(f.get("rule") == "G6_CONTAINMENT_GAP" for f in fl):
        fl.append({"rule": "G6_CONTAINMENT_GAP", "action": "needs_review",
                   "detail": "unit1 not provable in any currently-resolvable cited doc "
                             "(supplying doc lost to workspace resets / pre-G6 citation gap); "
                             "W4 display/type edits deferred pending owner decision", "field": "unit1_text"})
    print(f"W4|G6_GAP_SKIP|{sid} (edits reverted, needs_review flag recorded)")
json.dump(af, open(f"{WC.BASE}/audit_flags.json", "w"), indent=1, ensure_ascii=False)

pre_rows = {r["subject_id"]: dict(r) for r in rows}
gates = WC.run_gates(rows, touched, pre_rows)
print(f"G1|{'PASS' if not gates['g1'] else 'FAIL ' + gates['g1']}")
print(f"G2|{'PASS' if not gates['g2'] else 'FAIL ' + gates['g2']}|codes={gates['g2_codes']}")
print(f"G3|{'PASS' if not gates['g3'] else 'FAIL ' + gates['g3']}")
print(f"G6|{'PASS' if not gates['g6'] else 'FAIL ' + gates['g6']}|checks={gates['g6_checks']}|pre_edit_hits={gates['g6_pre_edit_hits']}")
if any([gates["g1"], gates["g2"], gates["g3"], gates["g6"]]):
    print("ABORT: gate failure")
    sys.exit(2)
WC.commit(rows, "W4", n_norm + n_inf + n_disp, gates,
          {"norm_set": n_norm, "name_inferred": n_inf, "unmapped": n_unmapped, "display_set": n_disp})
