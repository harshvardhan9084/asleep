#!/usr/bin/env python3
"""merge_draft.py decisions <drafts_dir>   — dry-run: ladder + flags report
   merge_draft.py commit <drafts_dir>     — live: ladder + RESOLVE_APPEND +
                                            gates G1/G2/G3/G6 + backup + write

Deterministic merge of draft subjects into the 57-col registry.
Decisions in RESOLVE_APPEND are advisory: commit re-runs the ladder live.
Unadjudicated flags ABORT the commit (exit 2).
"""
import json, os, re, sys, csv, glob, shutil, hashlib
from datetime import datetime
from difflib import SequenceMatcher

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
BASE = "/home/z/my-project/work/pipeline_v2"
QUEUE = f"{BASE}/queue.json"

REF_HEADER = ["subject_id","row_kind","subject_name","subject_name_print","primary_code",
"all_codes","code_history_all","status","university_name","course_name","branch_names",
"program_year","semester_slots","effective_session_latest","first_introduced_session",
"subject_type","subject_category_print","L","T","P","credit","sessional_ct","sessional_ta",
"sessional_total","ese_te_pe","total_marks","evaluation_note","has_detailed_syllabus",
"prerequisites","co_count","co1_text","co2_text","co3_text","co4_text","co6_text","co5_text",
"co_kls","units_count","lectures_per_unit","unit1_text","unit2_text","unit3_text","unit4_text",
"unit5_text","textbooks_structured","reference_books_structured","experiments_structured",
"choice_group_id","choice_group_policy","eligibility_print","k_era_pool_codes","source_syllabus",
"source_scheme_line","source_history","change_note_vs_previous","notes","objectives_print"]

CODE_RE = re.compile(r"\b([A-Z]{2,4})\s?-?(\d{3})([A-Z]?)\b")
STOP = set("""the of and to a in for with on by an as at or be is are from that this it its into
through their they with using use used various various study studies engineering science""".split())


def norm_code(c):
    return re.sub(r"[^A-Z0-9]", "", c.upper())


def codes_of_row(r):
    toks = set()
    for field in ("primary_code", "all_codes", "code_history_all", "k_era_pool_codes"):
        for m in CODE_RE.finditer(r.get(field, "") or ""):
            toks.add(m.group(1) + m.group(2) + (m.group(3) or ""))
    return toks


def norm_name(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()


# ---------------- course boundary (RULES §1b, owner directive 2026-10-28) ----------------
# Evidence for this block: the 2026-10-28 18:30 run ingested BCA 2024-25/2025-26
# drafts whose course metadata was mislabeled; Tier-0/Tier-1 then merged 8 BCA
# subjects INTO BTech rows (data-structure, data-structure-lab, operating-systems,
# technical-communication, universal-human-values..., web-technology,
# web-technology-lab, digital-electronics), overwriting BTech unit/CO/marks text
# with BCA text via newer-session fieldwise wins, and 6 BBC* (BCA bridge) codes
# landed inside BTech all_codes. Owner ruling: course boundaries are REAL -
# same/similar names in different courses are DIFFERENT subjects, never merged.

CANON_COURSES = ["BTech", "BPharm", "BCA", "MCA", "MBA"]


def canon_course(c):
    key = re.sub(r"[^a-z]", "", (c or "").lower())
    return {"btech": "BTech", "bpharm": "BPharm", "bca": "BCA",
            "mca": "MCA", "mba": "MBA"}.get(key, (c or "").strip())


def course_from_codes(codes):
    """Printed codes are hard evidence of the course (zero-guess §1b defense):
    if a draft's course metadata contradicts its own printed codes, the codes
    win. ONLY unambiguous prefixes may infer: AKTU re-uses generic B??/K??
    code families across courses (B2/B3 evidence: BVE301 UHV is printed in
    BOTH the BTech 2nd-yr common scheme and the BCA y2 2025-26 scheme; BVA
    value-added codes are likewise not course-unique) — so generic prefixes
    infer NOTHING. BBC### = BCA 2024-25 foundation scheme (B3 evidence: all
    BBC101-452 own rows are BCA; the only BBC tokens ever seen in BTech rows
    were the contamination this block exists to prevent)."""
    out = set()
    for c in codes or []:
        nc = norm_code(c)
        if not nc:
            continue
        if nc.startswith("BBC") or re.match(r"^BCA\d", nc) or re.match(r"^BCA\d{3}$", nc):
            out.add("BCA")
        elif nc.startswith("BOP") or nc.startswith("BPH") or re.match(r"^BP\d{3}[TPRL]$", nc):
            out.add("BPharm")
        elif re.match(r"^MCA\d", nc) or re.match(r"^MCA\d{3}$", nc):
            out.add("MCA")
        elif nc.startswith("MBA") or nc.startswith("KMB"):
            out.add("MBA")
    return out


def token_set_ratio(a, b):
    ta, tb = sorted(set(norm_name(a).split())), sorted(set(norm_name(b).split()))
    if not ta or not tb:
        return 0.0
    return SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio() * 100


def vocab_terms(texts):
    words = set()
    for t in texts:
        for w in re.findall(r"[a-z]{4,}", (t or "").lower()):
            if w not in STOP:
                words.add(w)
    return words


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", norm_name(name)).strip("-")
    return s[:60] if s else "unnamed"


def draft_vocab(s):
    return vocab_terms(list((s.get("units") or {}).values()) + [c.get("text", "") for c in s.get("cos") or []])


def row_vocab(r):
    return vocab_terms([r.get(f"unit{i}_text", "") for i in range(1, 6)] +
                       [r.get(f"co{i}_text", "") for i in range(1, 7)])


def row_owned_codes(r):
    """Ownership tokens only (primary_code + all_codes + k_era_pool exact) -
    code_history_all is narrative, not ownership (B2 recorded semantics)."""
    owned = set()
    for c in (r.get("primary_code", "") or "").split(";"):
        c = norm_code(c)
        if c:
            owned.add(c)
    for c in (r.get("all_codes", "") or "").split(";"):
        c = norm_code(c)
        if c:
            owned.add(c)
    for m in CODE_RE.finditer(r.get("k_era_pool_codes", "") or ""):
        owned.add(m.group(1) + m.group(2) + (m.group(3) or ""))
    return owned


def cross_course_hits(dsub, rows, course):
    """§1b: rows of OTHER courses whose owned codes or normalized name collide
    with this draft subject - recorded as cross-references on the appended row,
    never as update targets."""
    course = canon_course(course)
    dnc = {norm_code(c) for c in dsub.get("codes", []) if norm_code(c)}
    dname = norm_name(dsub.get("name", ""))
    hits, seen = [], set()
    for r in rows:
        if r.get("row_kind") != "subject":
            continue
        rc = canon_course(r.get("course_name"))
        if rc == course:
            continue
        if (dnc & row_owned_codes(r)) or (dname and dname == norm_name(r.get("subject_name", ""))):
            sig = (rc, r["subject_id"])
            if sig not in seen:
                seen.add(sig)
                hits.append(f"{rc}:{r['subject_id']}")
    return hits


# ---------------- ladder ----------------

# B2 remedy (brain clause, recorded): Tier-0 identity is restricted to
# OWNERSHIP tokens (primary_code + all_codes) plus exact k_era_pool_codes
# tokens. code_history_all is a NARRATIVE field by recorded v6/B01 design (it
# documents misprints, retirements and code-slot re-use: e.g. BCS403's history
# says it "replaces the retired KCS403 Microprocessor slot" — KCS403(2021-22)
# Microprocessor and BCS403(2023-24) OOP-with-Java are DIFFERENT subjects; a
# history mention must never pull one into the other's row, RULES §11).
# Evidence set: B02 draft 01 Microprocessor(KCS403)/Microprocessor
# Lab(KCS452)/Python Language Programming Lab(KCS453) vs the replacer rows'
# own history texts; E&C KEC452 duplicate-misprint narrative on the
# signal-system-lab row.
def serial_variant(na, nb):
    """True when the two names differ ONLY in their numeral/roman token
    (e.g. 'Mine Surveying - II' vs 'Mine Surveying - I', 'Mathematics-III' vs
    'Mathematics-IV'): AKTU serial subjects are distinct courses (RULES §11:
    never merge two different subjects); B2 evidence: live-commit fuzzy 97/24
    pulling Mine Surveying-II into the just-appended Mine Surveying-I row."""
    ta, tb = norm_name(na).split(), norm_name(nb).split()
    numa = re.compile(r"^[0-9ivxl]+$")
    ka = [t for t in ta if not numa.match(t)]
    kb = [t for t in tb if not numa.match(t)]
    if ka != kb:
        return False
    return [t for t in ta if numa.match(t)] != [t for t in tb if numa.match(t)]


def is_lab_name(n):
    toks = set(norm_name(n).split())
    return bool(toks & {"lab", "laboratory", "workshop"})


def ladder(dsub, rows, course, draft_session=""):
    """returns (tier, targets, score_info) — targets: list of row dicts"""
    course = canon_course(course)  # §1b: canonical comparison on both sides
    dcodes = {norm_code(c) for c in dsub.get("codes", [])}
    # Tier 0 — ownership identity only
    t0 = []
    for r in rows:
        if r.get("row_kind") != "subject":
            continue
        # §1b HARD GUARD: course boundaries are real. A draft can never update
        # a row of a different course - not by code identity, name, or content.
        if canon_course(r.get("course_name")) != course:
            continue
        owned = set()
        for c in (r.get("primary_code", "") or "").split(";"):
            c = norm_code(c)
            if c:
                owned.add(c)
        for c in (r.get("all_codes", "") or "").split(";"):
            c = norm_code(c)
            if c:
                owned.add(c)
        for m in CODE_RE.finditer(r.get("k_era_pool_codes", "") or ""):
            owned.add(m.group(1) + m.group(2) + (m.group(3) or ""))
        if dcodes & owned:
            t0.append(r)
    if len(t0) == 1:
        # CODE-REASSIGNED-ACROSS-SESSIONS retarget (B3 remedy, evidence-recorded):
        # AKTU re-uses code slots across sessions — BCA y1: BBC102 printed for
        # Mathematical Foundation in 2024-25 but for INFORMATION SYSTEMS in the
        # 2025-26 heading print (scheme table prints BBC106 there); the 18:30
        # run mislumped BBC102;BBC106;BBC205A into the math-foundation row.
        # When the unique T0 row's name CONTRADICTS the draft name and exactly
        # one same-course row name-matches, the NAME identity wins and the code
        # ownership transfers (newest print wins; older row keeps a narrative
        # history mention — the recorded B02 Microprocessor precedent). Zero
        # guessing: every transfer is flagged and recorded.
        if norm_name(dsub.get("name", "")) and norm_name(dsub.get("name", "")) != norm_name(t0[0].get("subject_name", "")):
            nm = [r for r in rows if r.get("row_kind") == "subject"
                  and canon_course(r.get("course_name")) == course
                  and norm_name(r.get("subject_name", "")) == norm_name(dsub.get("name", ""))]
            if len(nm) == 1:
                moved = sorted(dcodes & row_owned_codes(t0[0]))
                return 0, nm, (f"code-reassigned {','.join(moved)}: owned by "
                               f"{t0[0]['subject_id']}; name identity -> {nm[0]['subject_id']}")
            # B10 remedy (evidence-recorded): the unique T0 owner's name
            # contradicts the draft name and NO same-course name-identity row
            # exists. Two live classes (collapsed alnum-name similarity,
            # SequenceMatcher on norm_name minus non-alnum):
            #   (a) print variant of the SAME subject — B10 doc08/doc09 evidence:
            #       BIOINSTRUMENTATION/BIO-INSTRUMENTATION 1.000,
            #       BIOMATERIALS/BIO-MATERIALS 1.000, BIOMECHANICS/BIO-MECHANICS
            #       1.000, BIOMEDICAL SIGNAL PROCESSING/BIO-MEDICAL~ 1.000,
            #       ADVANCED/ADVANCE SEMICONDUCTOR DEVICES 0.982,
            #       MICROCONTROLLER AND BIOMEDICAL APPLICATIONS/BIO-MEDICAL
            #       APPLICATION 0.987 — UPDATE the T0 row (newest session
            #       fieldwise-wins per RULES §3).
            #   (b) genuine code-slot REASSIGNMENT to a DIFFERENT subject — B10
            #       evidence: EBM-012 printed as REHABILITATION ENGINEERING in
            #       the 2010-11 BME scheme (doc08) but as BIOELECTRICITY in the
            #       2011-12 print (doc09): collapsed similarity 0.359, zero
            #       shared unit vocabulary. The newest print APPENDS as its own
            #       row and the code transfers at commit (recorded B3 BBC102 /
            #       B02 KCS403 era model; the commit reassignment handler strips
            #       the code from the older row into code_history narrative).
            sim = SequenceMatcher(None,
                                  re.sub(r"[^a-z0-9]", "", norm_name(dsub.get("name", ""))),
                                  re.sub(r"[^a-z0-9]", "", norm_name(t0[0].get("subject_name", "")))).ratio()
            newer = bool(draft_session) and bool(t0[0].get("effective_session_latest", "")) \
                    and draft_session > t0[0].get("effective_session_latest", "")
            if sim < 0.84 and newer:
                moved = sorted(dcodes & row_owned_codes(t0[0]))
                return 3, [], (f"code-reassigned {','.join(moved)}: owned by "
                               f"{t0[0]['subject_id']} ({t0[0].get('effective_session_latest', '')}); "
                               f"collapsed-name similarity {sim:.2f} < 0.84 = different subject on a "
                               f"reassigned code slot; newest print ({draft_session}) appends its own "
                               f"row and the code transfers (B10 recorded remedy)")
            return 0, t0, ("code identity (name contradicts but collapsed-name similarity "
                           f"{sim:.2f} >= 0.84 = same-subject print variant)")
    if len(t0) > 1:
        return 0, t0, "TIE code identity across rows"
    hist_ids = set()
    for r in rows:
        if r.get("row_kind") != "subject":
            continue
        if dcodes & {m.group(1) + m.group(2) + (m.group(3) or "")
                     for m in CODE_RE.finditer(r.get("code_history_all", "") or "")}:
            hist_ids.add(r["subject_id"])
    hist_note = ("; history narrative mentions: " + ",".join(sorted(hist_ids))) if hist_ids else ""
    # Tier 1
    t1 = [r for r in rows if r.get("row_kind") == "subject"
          and canon_course(r.get("course_name")) == course
          and norm_name(r.get("subject_name", "")) == norm_name(dsub.get("name", ""))
          and norm_name(dsub.get("name", ""))]
    if len(t1) == 1:
        return 1, t1, "exact name in course"
    if len(t1) > 1:
        return 1, t1, "TIE exact name"
    # Tier 2
    dv = draft_vocab(dsub)
    cands = []
    for r in rows:
        if r.get("row_kind") != "subject" or canon_course(r.get("course_name")) != course:
            continue
        sc = token_set_ratio(dsub.get("name", ""), r.get("subject_name", ""))
        if sc < 85:
            continue
        # B2 remedy (RULES §3 labs are distinct rows): never fuzzy-merge a
        # printed lab/workshop subject into a non-lab target or vice versa.
        if is_lab_name(dsub.get("name", "")) != is_lab_name(r.get("subject_name", "")):
            continue
        # B2 remedy (RULES §11): serial-variant names (differ only by numeral)
        # are different subjects — never fuzzy-merge them.
        if serial_variant(dsub.get("name", ""), r.get("subject_name", "")):
            continue
        ov = len(dv & row_vocab(r))
        # B2 remedy (RULES §3: labs are distinct rows — a lab subject is not
        # merged into its theory pair): a draft subject with NO printed unit/CO
        # vocabulary (lab with experiments only, or scheme-only row) can never
        # Tier-2 match on name similarity alone. Evidence: commit-run live rows
        # — 'Geology For Mining Engineers Lab' scored 93/overlap-0 against its
        # own just-appended theory row; same class for the other Mining labs.
        if not dv:
            continue
        if sc >= 92 or (sc >= 85 and ov >= 3):
            cands.append((sc, ov, r))
    if len(cands) == 1:
        sc, ov, r = cands[0]
        return 2, [r], f"fuzzy {sc:.0f} overlap {ov}"
    if len(cands) > 1:
        return 2, [c[2] for c in cands], "TIE fuzzy " + "; ".join(f"{c[0]:.0f}/{c[2]['subject_id']}" for c in cands)
    return 3, [], "no match" + hist_note


# ---------------- field application ----------------

UNIT_FIELDS = {1: "unit1_text", 2: "unit2_text", 3: "unit3_text", 4: "unit4_text", 5: "unit5_text"}
CO_FIELDS = {1: "co1_text", 2: "co2_text", 3: "co3_text", 4: "co4_text", 5: "co5_text", 6: "co6_text"}


def cos_to_text(dsub):
    out = {}
    for co in dsub.get("cos") or []:
        n = int(co.get("no", 0))
        if 1 <= n <= 6 and co.get("text"):
            out[n] = co["text"]
    return out


def kls_to_text(dsub):
    parts = []
    for co in dsub.get("cos") or []:
        if co.get("kl"):
            parts.append(f"CO{co['no']}:{co['kl']}")
    return ";".join(parts)


def jsons(v):
    return json.dumps(v, ensure_ascii=False) if v else ""


def apply_update(row, dsub, dmeta, doc_short, ev):
    """newer-wins fieldwise; older drafts may only backfill empties."""
    newer = (dmeta["session"] or "") >= (row.get("effective_session_latest") or "")
    changed = []
    sem = dsub.get("semester")
    if newer:
        for n, f in UNIT_FIELDS.items():
            ut = (dsub.get("units") or {}).get(str(n)) or (dsub.get("units") or {}).get(n)
            if ut and ut != row.get(f, ""):
                row[f] = ut
                changed.append(f"unit{n}")
        ct = cos_to_text(dsub)
        for n, f in CO_FIELDS.items():
            if ct.get(n) and ct[n] != row.get(f, ""):
                row[f] = ct[n]
                changed.append(f"co{n}")
        for f, v in (("L", dsub.get("ltp", {}).get("l")), ("T", dsub.get("ltp", {}).get("t")),
                     ("P", dsub.get("ltp", {}).get("p")), ("credit", dsub.get("credit"))):
            if v not in (None, "") and str(v) != row.get(f, ""):
                row[f] = str(v)
                changed.append(f)
        m = dsub.get("marks") or {}
        for f, k in (("sessional_ct", "sessional_ct"), ("sessional_ta", "sessional_ta"),
                     ("sessional_total", "sessional_total"), ("ese_te_pe", "ese_te_pe"),
                     ("total_marks", "total")):
            if m.get(k) not in (None, "") and str(m[k]) != row.get(f, ""):
                row[f] = str(m[k])
                changed.append(f)
        if dsub.get("lectures_per_unit") and str(dsub["lectures_per_unit"]) != row.get("lectures_per_unit", ""):
            row["lectures_per_unit"] = str(dsub["lectures_per_unit"])
            changed.append("lpu")
        if dsub.get("textbooks") and jsons(dsub["textbooks"]) != row.get("textbooks_structured", ""):
            row["textbooks_structured"] = jsons(dsub["textbooks"])
            changed.append("textbooks")
        if dsub.get("reference_books") and jsons(dsub["reference_books"]) != row.get("reference_books_structured", ""):
            row["reference_books_structured"] = jsons(dsub["reference_books"])
            changed.append("refbooks")
        if dsub.get("experiments") and jsons(dsub["experiments"]) != row.get("experiments_structured", ""):
            row["experiments_structured"] = jsons(dsub["experiments"])
            changed.append("experiments")
        if dsub.get("objectives_print") and jsons(dsub["objectives_print"]) != row.get("objectives_print", ""):
            row["objectives_print"] = jsons(dsub["objectives_print"])
            changed.append("objectives")
        if dsub.get("eligibility_print") and not row.get("eligibility_print", ""):
            row["eligibility_print"] = dsub["eligibility_print"]
            changed.append("eligibility")
        if dsub.get("prerequisites") and not row.get("prerequisites", ""):
            row["prerequisites"] = dsub["prerequisites"]
            changed.append("prereq")
        if dsub.get("subject_type") and not row.get("subject_type", ""):
            row["subject_type"] = dsub["subject_type"]
            changed.append("type")
        kl = kls_to_text(dsub)
        if kl and kl != row.get("co_kls", ""):
            row["co_kls"] = kl
            changed.append("kls")
        if dsub.get("name_print") and dsub["name_print"] != row.get("subject_name_print", ""):
            row["subject_name_print"] = (row.get("subject_name_print", "") + " | detailed-doc print: " + dsub["name_print"])[:250]
            changed.append("name_print")
    else:
        for n, f in UNIT_FIELDS.items():
            ut = (dsub.get("units") or {}).get(str(n))
            if ut and not row.get(f, ""):
                row[f] = ut
                changed.append(f"backfill-unit{n}")
    # codes: add newly printed codes (H variants etc.)
    existing = {norm_code(c) for c in (row.get("all_codes", "").split(";") if row.get("all_codes") else [])}
    newc = [c for c in dsub.get("codes", []) if norm_code(c) not in existing]
    if newc:
        row["all_codes"] = ";".join([x for x in row.get("all_codes", "").split(";") if x] + newc)
        ch = row.get("code_history_all", "")
        add = " + ".join(newc)
        seg = f" -> {add} ({dmeta['session']}) - codes printed with detailed syllabus in {doc_short}"
        row["code_history_all"] = (ch + seg) if ch else seg.lstrip(" ->")
        changed.append("codes+" + ",".join(newc))
    # derived counts recomputed from the applied fields (never left stale)
    nu = sum(1 for f in UNIT_FIELDS.values() if row.get(f, ""))
    nc = sum(1 for f in CO_FIELDS.values() if row.get(f, ""))
    if nu and str(nu) != row.get("units_count", ""):
        row["units_count"] = str(nu)
        changed.append(f"units_count={nu}")
    if nc and str(nc) != row.get("co_count", ""):
        row["co_count"] = str(nc)
        changed.append(f"co_count={nc}")
    # detailed syllabus flag
    if (dsub.get("units") or dsub.get("cos")) and row.get("has_detailed_syllabus") != "TRUE":
        row["has_detailed_syllabus"] = "TRUE"
        changed.append("has_det=TRUE")
    # provenance (deduped: re-verification with the SAME copy must not stack
    # duplicate citations; a different surviving copy appends as corroboration)
    loc = ev["locator"]
    src = f"{ev['file']}#{ev['sha16']} {loc}"
    if src not in (row.get("source_syllabus", "") or ""):
        row["source_syllabus"] = (row.get("source_syllabus", "") + "; " + src).strip("; ")
    sh = row.get("source_history", "")
    seg = f"{src} (detailed syllabus ingested {dmeta['session']})"
    if seg not in sh:
        row["source_history"] = (sh + "; " if sh else "") + seg
    sch = dsub.get("scheme_line_print") or dsub.get("name_print") or ""
    if sch and not row.get("source_scheme_line", ""):
        row["source_scheme_line"] = f"{ev['file']}#{ev['sha16']} {loc} ({sch[:120]})"
    cn = row.get("change_note_vs_previous", "")
    # B2 wording fix: the six B02 docs are regular authorized scheme/syllabus
    # docs, not the two released companions; and a scheme-only corroboration
    # must not claim "detailed syllabus restored" when no field changed.
    if changed:
        note = f"{dmeta['session']}: detailed syllabus ingested/verified from {doc_short} ({', '.join(changed[:8])}{'...' if len(changed) > 8 else ''})"
    else:
        note = f"{dmeta['session']}: scheme-line corroboration from {doc_short} (no field changes; provenance/history extended)"
    if note not in cn:
        row["change_note_vs_previous"] = (cn + "; " if cn else "") + note
    if dsub.get("quirks"):
        qj = "Print quirks (" + doc_short + "): " + " | ".join(dsub["quirks"])
        if qj[:60] not in row.get("notes", ""):
            row["notes"] = (row.get("notes", "") + (" | " if row.get("notes", "") else "") + qj)[:4000]
    return changed


def build_append(dsub, dmeta, ev, scope_row, policy):
    row = {c: "" for c in REF_HEADER}
    row["subject_id"] = slug(dsub.get("name", ""))
    row["row_kind"] = "subject"
    row["subject_name"] = norm_name(dsub.get("name", "")).replace(" ", " ")
    row["subject_name"] = re.sub(r"\s+", " ", dsub.get("name", "")).strip()
    row["subject_name_print"] = dsub.get("name_print") or dsub.get("name", "")
    codes = dsub.get("codes", [])
    row["primary_code"] = codes[0] if codes else ""
    row["all_codes"] = ";".join(dict.fromkeys(codes))
    ch = ""
    sem = dsub.get("semester")
    if len(codes) > 1:
        ch = " / ".join(f"{c} ({dmeta['session']}{', sem-' + str(sem) if sem else ''})" for c in codes)
    elif codes:
        ch = f"{codes[0]} ({dmeta['session']}{', sem-' + str(sem) if sem else ''})"
    if dsub.get("code_note"):
        ch += f" - {dsub['code_note']}"
    row["code_history_all"] = ch
    row["status"] = "latest"
    row["university_name"] = "Dr. A.P.J. Abdul Kalam Technical University, Lucknow"
    row["course_name"] = canon_course(dmeta.get("course", "BTech"))  # §1b canon
    row["branch_names"] = scope_row.get("branch_names", "") if scope_row else ""
    row["program_year"] = str(dsub.get("program_year") or (scope_row.get("program_year", "") if scope_row else "") or "2")
    sems = sorted({str(dsub.get("semester"))} - {"None"}) if dsub.get("semester") else []
    row["semester_slots"] = ";".join(sems) or (scope_row.get("semester_slots", "") if scope_row else "")
    row["effective_session_latest"] = dmeta["session"]
    row["first_introduced_session"] = dmeta["session"]
    row["subject_type"] = dsub.get("subject_type", "")
    row["subject_category_print"] = dsub.get("category_print", "")
    lt = dsub.get("ltp", {})
    row["L"], row["T"], row["P"] = str(lt.get("l", "") or ""), str(lt.get("t", "") or ""), str(lt.get("p", "") or "")
    row["credit"] = str(dsub.get("credit") or "")
    m = dsub.get("marks") or {}
    row["sessional_ct"] = str(m.get("sessional_ct", "") or "")
    row["sessional_ta"] = str(m.get("sessional_ta", "") or "")
    row["sessional_total"] = str(m.get("sessional_total", "") or "")
    row["ese_te_pe"] = str(m.get("ese_te_pe", "") or "")
    row["total_marks"] = str(m.get("total", "") or "")
    row["evaluation_note"] = dsub.get("evaluation_note", "")
    row["has_detailed_syllabus"] = "TRUE" if (dsub.get("units") or dsub.get("cos")) else "FALSE"
    row["prerequisites"] = dsub.get("prerequisites", "")
    ct = cos_to_text(dsub)
    row["co_count"] = str(len(ct)) if ct else ""
    for n, f in CO_FIELDS.items():
        row[f] = ct.get(n, "")
    row["co_kls"] = kls_to_text(dsub)
    units = dsub.get("units") or {}
    row["units_count"] = str(len(units)) if units else ""
    row["lectures_per_unit"] = str(dsub.get("lectures_per_unit") or "")
    for n, f in UNIT_FIELDS.items():
        row[f] = units.get(str(n), units.get(n, "")) or ""
    row["textbooks_structured"] = jsons(dsub.get("textbooks"))
    row["reference_books_structured"] = jsons(dsub.get("reference_books"))
    row["experiments_structured"] = jsons(dsub.get("experiments"))
    if policy:
        row["choice_group_id"], row["choice_group_policy"] = policy
    row["eligibility_print"] = dsub.get("eligibility_print", "")
    row["source_syllabus"] = f"{ev['file']}#{ev['sha16']} {ev['locator']}"
    sch = dsub.get("scheme_line_print") or dsub.get("name_print") or ""
    row["source_scheme_line"] = f"{ev['file']}#{ev['sha16']} {ev['locator']} ({sch[:120]})" if sch else f"{ev['file']}#{ev['sha16']} {ev['locator']}"
    row["source_history"] = f"{row['source_syllabus']} (first ingestion {dmeta['session']})"
    row["change_note_vs_previous"] = f"First ingestion ({dmeta['session']}): verbatim from {os.path.basename(ev['file'])}"
    if dsub.get("flags"):
        row["notes"] = "flags: " + ",".join(dsub["flags"])
    if dsub.get("quirks"):
        qj = "Print quirks (" + os.path.basename(ev['file']) + "): " + " | ".join(dsub["quirks"])
        if qj[:60] not in row.get("notes", ""):
            row["notes"] = (row.get("notes", "") + (" | " if row.get("notes", "") else "") + qj)[:4000]
    row["objectives_print"] = jsons(dsub.get("objectives_print"))
    return row


# ---------------- RESOLVE_APPEND (adjudications, advisory) ----------------
# flag_key -> {"action": "...", "reason": "..."}
RESOLVE_APPEND = {
    "POOL_MEMBERS_NAMED": {
        "action": "UPDATE_POOL_NOTES",
        "reason": "The 14 BOE members are appended as real subject rows from the released Open-Elective doc; the CG-BOE-2YR pool row's notes gain the named-member list while its slot-level identity (scheme line with pool codes) stays intact. The pool row's provenance is backfilled from its recorded establishing source (B.Tech_2nd_Yr_CSE_v3.pdf#b5579aefa7a2 pp.2,3 SN-1 BOE3**/BOE4** pool lines - the same scheme lines that carry the group's slots, per registry v2/v5 records) plus the released member-list doc."},
    "BOE2YR-CHOICE-GROUP": {
        "action": "LINK_CG_BOE_2YR",
        "reason": "Every appended BOE3xx/BOE4xx subject joins the existing CG-BOE-2YR choice group (exactly-one policy), inheriting the pool row's policy print - the released doc is the member-list source for that group."},
    "SCOPE-FROM-POOL": {
        "action": "BRANCH_SCOPE_FROM_POOL",
        "reason": "Appended 2nd-year electives inherit the CG-BOE-2YR pool row's branch scope (same document scope); no per-subject branch list is printed beyond eligibility_print."},
    "SCOPE-FROM-MATHS-IV": {
        "action": "BRANCH_SCOPE_FROM_MATHS_IV",
        "reason": "Mathematics-III/V are sister common subjects printed in the same released doc as Mathematics-IV; they inherit its branch profile (doc-level scope, not per-subject)."},
    "ALTERNATIVE-PAIR-SLOT": {
        "action": "SKIP_SLOT_PRINT",
        "reason": "The draft subject is a scheme ALTERNATIVE-SLOT print (flags carry alternative_pair_row + scheme-only): it names two subjects of which BOTH already exist as registry subject rows owning the printed codes (e.g. UHV BVE301/401 + Technical Communication BAS301/401; Cyber Security BCC301/401 + Python BCC302/402; Mathematics-III BAS302 + Science-Based-OE pool). A slot print is program structure, not a subject (RULES §11: never merge two different subjects into one row); the slot print itself is preserved verbatim in the draft's non_subject_rows (semester scheme rows) and the member rows gain scheme-line corroboration via their own code-bearing draft subjects. Nothing is lost: zero-GAP holds because both member subjects own rows."},
    "HISTORY-ONLY-CODE-MENTION": {
        "action": "APPEND_NEW_ROW_WITH_HISTORY_CROSSREF",
        "reason": "The draft code matches NO row's ownership (primary_code/all_codes) but appears in another row's code_history_all NARRATIVE documenting a retired/reused code slot (e.g. BCS403's history: 'replaces the retired KCS403 Microprocessor slot'). The draft subject is the RETIRED-era subject itself (2021-22 K-era print), a DIFFERENT subject from the replacer row (RULES §11) - so it APPENDs as its own row, and the appended row's code_history records the era transition while the replacer row's narrative remains the cross-reference. G2 stays clean: the code transfers from narrative-mention to single ownership by the new row."},
    "SCOPE-FROM-DOC": {
        "action": "BRANCH_SCOPE_FROM_DOC_COVER",
        "reason": "Appended subjects inherit the branch scope printed on the ingested document's own cover (zero-guess: exactly the cover's printed branch list, no extrapolation to branches the doc does not name)."},
    "CROSS-COURSE-KEEP-SEPARATE": {
        "action": "APPEND_NEW_ROW_WITH_CROSSREF_NOTE",
        "reason": "Owner directive 2026-10-28 (RULES §1b): course boundaries are REAL - a subject printed in another course is a DIFFERENT subject even when the name or codes match. Evidence: the 2026-10-28 18:30 run let BCA 2024-25/2025-26 drafts update 8 BTech rows (data-structure, data-structure-lab, operating-systems, technical-communication, universal-human-values..., web-technology, web-technology-lab, digital-electronics), overwriting BTech unit/CO/marks text with BCA text and landing 6 BBC* codes in BTech all_codes; reverted the same day. The draft appends as its own row in its own course with a cross-reference note; the other course's row is never touched."},
    "COURSE-META-FROM-CODES": {
        "action": "USE_CODE_DERIVED_COURSE",
        "reason": "The draft's course metadata contradicts the course implied by its own printed codes (root cause of the same 18:30 corruption: BCA docs mislabeled as BTech in draft meta). Printed codes are authoritative hard evidence (RULES §1b); the ladder and all writes use the code-derived course and the correction is flagged here."},
    "CODE-REASSIGNED-ACROSS-SESSIONS": {
        "action": "UPDATE_BY_NAME_TRANSFER_CODE_OWNERSHIP",
        "reason": "AKTU re-uses code slots across sessions within a course. B3 evidence (BCA y1): BBC102 prints as Mathematical Foundation in 2024-25 but as INFORMATION SYSTEMS in the 2025-26 syllabus heading (the 2025-26 scheme table prints BBC106 there); the 18:30 run mislumped BBC102;BBC106;BBC205A into mathematical-foundation. The unique Tier-0 code match's name contradicting the draft name, with exactly one same-course row name-matching, resolves deterministically: the NAME identity row is updated (newest-session fieldwise wins) and code ownership transfers to it (newest print wins; the older row keeps a narrative history mention and follows the status=latest primary-code model). Same recorded pattern as B02's retired KCS403 slot; G2 stays clean because the transfer runs before the gates."},
    "TIER2": {
        "action": "ADJUDICATED_PER_KEY_IN_TIER2_OVERRIDES",
        "reason": "Tier-2 fuzzy matches are adjudicated per draft-subject key in TIER2_OVERRIDES with recorded evidence: name-variant classes (singular/plural, spacing, era-family) ALLOW the fuzzy target; wrong-subject hits are RETARGETed to the vocabulary-evidence row or FORCE_APPENDed as their own row. The per-key action and reason are printed on the TIER2-OVERRIDE flag line."},
    "TIER2-OVERRIDE": {
        "action": "APPLY_RECORDED_ACTION",
        "reason": "The per-key TIER2_OVERRIDES entry for this draft subject (action + recorded evidence in the flag detail); the ladder result is corrected accordingly before the plan is applied."},
}

# B2: doc-level scope from the PRINTED COVER of each ingested document
# (zero-guess: only what the cover prints; recorded reasoning per entry).
DOC_SCOPE = {
    "da3b140fa2d8ab1e": {
        "branch_names": "Computer Science and Engineering (Artificial Intelligence); Computer Science and Engineering (Artificial Intelligence & Machine Learning); Computer Science and Engineering (Data Science); Computer Science and Engineering (Internet of Things)",
        "program_year": "2",
        "reason": "cover prints exactly these four CSE-specialization branches for B.Tech 2nd Year 2021-22"},
    "7a0eeeeb1000456f": {
        "branch_names": "Electronics and Computer Engineering",
        "program_year": "2",
        "reason": "cover prints B.Tech Second Year Electronics and Computer Engineering (AICTE Model Curriculum), effective 2020-21"},
    "7d6a8a1f4b44410b": {
        "branch_names": "Computer Science and Engineering (Artificial Intelligence)",
        "program_year": "3",
        "reason": "cover prints B.Tech 3rd Year CSE (Artificial Intelligence), effective 2022-23"},
    "4c68b6c7156c50d2": {
        "branch_names": "Computer Science and Engineering (Data Science)",
        "program_year": "3",
        "reason": "cover prints B.Tech 3rd Year CSE (Data Science), effective 2022-23"},
    "51bd6d355e13d6e1": {
        "branch_names": "Mining Engineering",
        "program_year": "2",
        "reason": "cover prints B.Tech 2nd Year MINING ENGINEERING, effective session 2024-25"},
    "4f09e0095540f04e": {
        "branch_names": "Computer Science & Engineering; Computer Engineering; Computer Science; Computer Science and Engineering (Cyber Security); Computer Science and Information Technology; Information Technology; Computer Science and Engineering (Artificial Intelligence); Computer Science and Engineering (Artificial Intelligence & Machine Learning); Computer Science and Engineering (Data Science); Computer Science and Engineering (Internet of Things); Artificial Intelligence & Data Science",
        "program_year": "2",
        "reason": "cover prints exactly this CSE-family branch list for B.Tech 2nd Year, effective 2023-24"},
    # ---- B06-recovery batch (10 docs; branch = the printed cover branch; program_year
    # = the semester span the document details, deterministic Sem I-II->1 / V-VI->3 / VII-VIII->4) ----
    "b1c7a1e455c74556": {"branch_names": "Agricultural Engineering", "program_year": "1",
        "reason": "cover prints B.Tech Agricultural Engineering evaluation scheme; Sem I-II rows (2008-09 print)"},
    "9a8392667e90e4a3": {"branch_names": "Agricultural Engineering", "program_year": "3",
        "reason": "cover prints B.Tech Agricultural Engineering syllabus 2011-12; details Sem V/VI (EAG-5xx/6xx)"},
    "e7827e01a2bbd920": {"branch_names": "Agricultural Engineering", "program_year": "1",
        "reason": "cover prints B.Tech Agricultural Engineering syllabus 2013-14; details Sem I/II (NAG-1xx/2xx)"},
    "e1289ac95e742765": {"branch_names": "Agricultural Engineering", "program_year": "1",
        "reason": "cover prints B.Tech Agricultural Engineering syllabus 2016-17; details Sem I/II (RAG1xx/2xx)"},
    "6cc2ad19ea57c8f7": {"branch_names": "Agricultural Engineering", "program_year": "1",
        "reason": "cover prints B.Tech Agricultural Engineering AICTE model syllabus 2018-19; details Sem I/II (KAS/KAG 1xx/2xx)"},
    "39fa4e06a25624cd": {"branch_names": "Aeronautical Engineering", "program_year": "4",
        "reason": "cover prints B.Tech Aeronautical Engineering y4 CBCS syllabus 2019-20 (RAE7xx/8xx, Sem VII/VIII)"},
    "3e2c219acdd97acf": {"branch_names": "Agricultural Engineering", "program_year": "1",
        "reason": "cover prints B.Tech Agricultural Engineering y1 model curriculum 2020-21 (KAS/KAG 1xx/2xx)"},
    "6eec1505e6f7eab9": {"branch_names": "Aeronautical Engineering", "program_year": "4",
        "reason": "cover prints B.Tech Aeronautical Engineering y4 syllabus 2021-22; Sem VII (KAE-0xx/7xx)"},
    "f203b50ecf038f52": {"branch_names": "Aeronautical Engineering", "program_year": "4",
        "reason": "cover prints B.Tech Aeronautical Engineering y4 syllabus 2025-26; Sem VII (BAE7xx)"},
    "1a91d3db84efabbc": {"branch_names": "Agricultural Engineering", "program_year": "1",
        "reason": "cover prints B.Tech Agricultural Engineering course structure 2026-27; details y1 Sem I/II (A-generation 1xx/2xx)"},
    # ---- B07 batch (10 docs; branch = printed cover; program_year = semester span detailed) ----
    "84195404a1800d61": {"branch_names": "Agricultural Engineering", "program_year": "1",
        "reason": "cover prints B.Tech 1st Year (CSAI-family common scheme) Agricultural Engineering y1 syllabus 2022-23; details Sem I/II (BAS/BEE/BCS 1xx/2xx)"},
    "ef348f31546b304f": {"branch_names": "Agricultural Engineering", "program_year": "2",
        "reason": "cover prints B.Tech 2nd Year Agricultural Engineering model curriculum 2019-20; details Sem III/IV (KAG3xx/4xx)"},
    "9a0417ba1d09dfef": {"branch_names": "Agricultural Engineering", "program_year": "2",
        "reason": "cover prints B.Tech Second Year Agricultural Engineering Study & Evaluation Scheme with Syllabus 2017-18; details Sem III/IV (RCE/RAG 3xx/4xx)"},
    "544eb3ca93b0e4a5": {"branch_names": "Agricultural Engineering", "program_year": "2",
        "reason": "cover prints B.Tech 2nd Year Agricultural Engineering syllabus 2014-15; details Sem III/IV (NAG-3xx/4xx)"},
    "afe36bc54d1565e0": {"branch_names": "Agricultural Engineering", "program_year": "2",
        "reason": "cover prints B.Tech 2nd Year (III & IV Sem.) Agricultural Engineering syllabus 2009-10 (filename says y3-4 but print is authoritative); details Sem III/IV (EAG-3xx/4xx)"},
    "7cc09310bd72356b": {"branch_names": "Agricultural Engineering", "program_year": "3",
        "reason": "cover prints B.Tech Third Year (Agriculture Engineering) AICTE model curriculum 2020-21; details Sem V/VI (KAG-5xx/6xx)"},
    "d411cec7864d334a": {"branch_names": "Agricultural Engineering", "program_year": "3",
        "reason": "cover prints B.Tech 3rd Year Agricultural Engineering syllabus 2018-19; details Sem V/VI (RAG5xx/6xx)"},
    "02a51ac056f20f11": {"branch_names": "Agricultural Engineering", "program_year": "3",
        "reason": "cover prints B.Tech Third Year Agricultural Engineering AICTE model curriculum 2024-25; details Sem V/VI (BAG5xx/6xx)"},
    "69b6c3c47a3fbcb0": {"branch_names": "Agricultural Engineering", "program_year": "3",
        "reason": "cover prints B.Tech 3rd year (Sem V-VI) Agricultural Engineering scheme-syllabus 2015-16; details Sem V/VI (NAG-5xx/6xx)"},
    "8ca5b389f76d66d5": {"branch_names": "Agricultural Engineering", "program_year": "4",
        "reason": "cover prints B.Tech 4th Year (Sem VII-VIII) Agricultural Engineering CBCS syllabus 2019-20; details Sem VII/VIII (RAG7xx/8xx)"},
    # ---- B12 batch (10 docs, all B.Tech Biotechnology; branch = the printed cover
    # branch (cover print variants 'Bio Technology'/'Biotechnology'/'Bio-Tchnology'
    # [sic] normalize to the canonical Biotechnology); program_year = the year the
    # document details) ----
    "7f23681aed03cd34": {"branch_names": "Biotechnology", "program_year": "1",
        "reason": "cover prints B.Tech 1st Year (Bio-Tchnology [sic]) scheme 2016-17; Sem I/II rows (RAS/REE/REC/RME 1xx/2xx)"},
    "65ba77f6adefc408": {"branch_names": "Biotechnology", "program_year": "1",
        "reason": "cover prints B.Tech 1st Year Biotechnology syllabus 2022-23; details Sem I/II (BAS/BBT/BEE/BEC/BCS/BME 1xx/2xx)"},
    "cd99a5656cc12101": {"branch_names": "Biotechnology", "program_year": "2",
        "reason": "cover prints B.Tech. 2nd Year (Bio Technology) model curriculum 2019-20; details Sem III/IV (KBT3xx/4xx)"},
    "30cfa6b02bc4d971": {"branch_names": "Biotechnology", "program_year": "2",
        "reason": "cover prints B.Tech 2nd Year Biotechnology scheme-syllabus 2017-18; details Sem III/IV (RAS/RBT/RCE/RCH 3xx/4xx)"},
    "cf99d60169de6571": {"branch_names": "Biotechnology", "program_year": "2",
        "reason": "cover prints B.Tech 2nd Year Biotechnology syllabus 2014-15; details Sem III/IV (NBT-3xx/4xx)"},
    "abdc219693a0bf7f": {"branch_names": "Biotechnology", "program_year": "3",
        "reason": "cover prints B.Tech 3rd Year Biotechnology syllabus 2020-21; details Sem V/VI (KBT5xx/6xx)"},
    "421ea0b792f7ab84": {"branch_names": "Biotechnology", "program_year": "3",
        "reason": "cover prints B.Tech 3rd Year Biotechnology syllabus 2024-25; details Sem V/VI (BBT5xx/6xx)"},
    "d227ef4b67bad00f": {"branch_names": "Biotechnology", "program_year": "4",
        "reason": "cover prints B.Tech Biotechnology y4 CBCS syllabus 2019-20; details Sem VII/VIII (RBT7xx/8xx incl. NPTEL DE slots)"},
    "25a6635f987a015e": {"branch_names": "Biotechnology", "program_year": "4",
        "reason": "cover prints B.Tech 4th Year Biotechnology syllabus 2021-22; details Sem VII/VIII (KBT7xx/8xx)"},
    "310bcbf46eecc945": {"branch_names": "Biotechnology", "program_year": "4",
        "reason": "cover prints B.Tech 4th Year Biotechnology syllabus 2025-26; details Sem VII/VIII (BBT7xx/8xx)"},
}

# ---------------- TIER2_OVERRIDES (per-key adjudications, evidence-recorded) ----------------
# Tier-2 fuzzy matches are adjudicated PER KEY: ALLOW the fuzzy target (name-
# variant classes: singular/plural, spacing, era-family), RETARGET to the
# evidence-correct row, or FORCE_APPEND when the fuzzy hit is a DIFFERENT
# subject. Restored for the CRON-20261029-B06-recovery re-run from the
# published B06 manifest ("TIER2_OVERRIDES mechanism added ... per-key,
# evidence-recorded"), re-evidenced against the drafts + baseline rows.
TIER2_OVERRIDES = {
    "06_btech_ae_y4_syllabus-cbcs_2019-20::08::introduction-to-fem": {
        "action": "RETARGET", "target": "introduction-to-finite-element-methods",
        "reason": "The T2 hit on introduction-to-cfd (KAE077) is a DIFFERENT subject — draft 'Introduction to FEM' (RAE075 print) shares only 28 generic CFD/numerical terms with it, while the 2020-21 KAE074 'Introduction to Finite Element Methods' row shares 100 distinctive unit-vocabulary terms (FEM assembly, stiffness, beam/boundary approximation classes): same syllabus content reprinted under the 2019-20 RAE-era slot; the RAE075 code lands on that row as an era code addition (older draft backfills only)."},
    "06_btech_ae_y4_syllabus-cbcs_2019-20::12::aircraft-rules-and-regulation": {
        "action": "ALLOW",
        "reason": "Singular/plural print variant of the same subject: draft 'Aircraft Rules and Regulation' (RAE080, 2019-20 CBCS print) vs the 2020-21 KAE075 'Aircraft Rules and Regulations' row — same AE y4 DE subject family, draft is older so it only backfills/corroborates and adds the RAE080 era code."},
    "06_btech_ae_y4_syllabus-cbcs_2019-20::17::elements-of-aero-elasticity": {
        "action": "ALLOW",
        "reason": "Spacing print variant of the same subject: draft 'Elements of Aero Elasticity' (RAE086 print) vs the 2020-21 KAE078 'Elements of Aeroelasticity' row — identical subject across the RAE/KAE era prints; draft is older (backfill + RAE086 code addition)."},
    "09_btech_ae_y4_syllabus_2025-26::01::aircraft-maintenance": {
        "action": "ALLOW",
        "reason": "Era-family match: draft 'Aircraft Maintenance' (BAE071, 2025-26 BAE-era print, fuzzy 85/overlap 102) vs the 2020-21 KAE-era aircraft-engine-maintenance row — the same AE y4 maintenance subject carried across era schemes with high distinctive-vocabulary overlap; 2025-26 is the newest session so its content fieldwise-wins per RULES §3."},
    "10_btech_ag_course-structure_2026-27::05::fundamentals-of-electronics-engineering": {
        "action": "FORCE_APPEND",
        "reason": "Different subject (live T2 reject, B06 recorded class 'Electronics vs Electrical'): draft 'Fundamentals of Electronics Engineering' (AEC101C/AEC201C, 2026-27 A-generation) fuzzy-hit the just-appended 'Fundamentals of Electrical Engineering' row (AEE101C/AEE201C) from the SAME document — the print carries BOTH as separate subjects with separate code families (AEE=Electrical, AEC=Electronics); RULES §11 never merges two different subjects."},
    "10_btech_ag_course-structure_2026-27::11::fundamentals-of-mechanical-engineering": {
        "action": "FORCE_APPEND",
        "reason": "Different subject (live T2 reject): draft 'Fundamentals of Mechanical Engineering' (AME101D/AME201D, 2026-27 AG y1) fuzzy-hit the 2020-21 KME101 'Fundamentals of Mechanical Engineering & Mechatronics' row — the names differ by the substantive token 'Mechatronics' (a different combined subject, different era and branch print); evidence inconclusive for identity, so zero-guess keeps separate rows (RULES §4/§11)."},
    # ---- B07 (CRON-20261030-B07) per-key adjudications, evidence-recorded ----
    "03_btech_ag_y2_scheme-syllabus_2017-18::00::engineering-maths-iii": {
        "action": "FORCE_APPEND",
        "reason": "Different subject (fuzzy false positive): draft 'Engineering Maths–III' (RAS304/RAS404 dual-session print, 2017-18 AG y2) fuzzy-hit the Mathematics-I (RAG101) / Mathematics-II (RAG201; NAG-201;KAG 201T) rows — but Maths-III is the THIRD-semester Numerical-Techniques/Statistics/Complex-Variables/Integral-Transforms subject, not its I/II predecessors; the unit vocabulary (Bisection, Newton-Raphson, Runge-Kutta, Fourier/Z-transform, C-R equations) is distinctive and absent from Math-I/II rows. AKTU treats Maths-I/II/III as three separate subjects (RULES §11); APPEND as its own row."},
    "09_btech_ag_y3s5-6_scheme-syllabus_2015-16::10::irrigation-and-drainage-engineering-lab": {
        "action": "RETARGET", "target": "irrigation-drainage-engineering-lab",
        "reason": "Same era-family lab row (B7 live evidence): draft 'Irrigation and Drainage Engineering Lab' (NAG-651, 2015-16) vs the irrigation-drainage-engineering-lab row appended this commit from the 2020-21 KAG-651 print — same lab across era schemes; 'and' token variance fell below the fuzzy threshold; NAG-651 joins as the 2015-16 era code."},
    "03_btech_ag_y2_scheme-syllabus_2017-18::01::universal-human-values-professional-ethics": {
        "action": "RETARGET", "target": "universal-human-values-and-professional-ethics",
        "reason": "Same-course era-family row (B7 live evidence): draft 'Universal Human Values & Professional Ethics' (RVE301/RVE401 dual-session print, 2017-18 AG y2) fuzzy-missed the BTech universal-human-values-and-professional-ethics row (BVE301;BVE401;KVE301;KVE401;... 2023-24) only because the token 'and' drops the overlap below threshold — '&' vs 'and' print variance, same subject. The BPharm RVE401 row (cross-course hit) stays separate per RULES §1b; the BTech row gains the RVE era codes as backfill."},
    "03_btech_ag_y2_scheme-syllabus_2017-18::20::soil-water-conservation-engineering-lab": {
        "action": "RETARGET", "target": "soil-and-water-conservation-engineering-lab",
        "reason": "Same-course era-family row (B7 live evidence): draft 'Soil & Water Conservation Engineering Lab' (RAG454, 2017-18 AG y2) vs the soil-and-water-conservation-engineering-lab row (EAG-653;NAG-551, 2011-12/2015-16) — '&' vs 'and' print variance of the same lab; RAG454 joins as the 2017-18 era code."},
    "07_btech_ag_y3_syllabus_2018-19::00::irrigation-drainage-engg": {
        "action": "RETARGET", "target": "irrigation-and-drainage-engineering",
        "reason": "Abbreviated print of the same era-family subject: draft 'Irrigation & Drainage Engg.' (RAG501, 2018-19 AG y3) vs the irrigation-and-drainage-engineering row (EAG-505, 2011-12) — 'Engg.' is a printed abbreviation of 'Engineering' (fuzzy falls below threshold only because of the abbreviation); the unit vocabulary (ET, border/check-basin/furrow, drip/sprinkler, subsurface drainage) is the shared distinctive core. RETARGET keeps one row per subject (RULES G1); RAG501 joins as a 2018-19 era code; later prints (KAG-601 2020-21, BAG601 2024-25) fieldwise-win on the same row."},
    "07_btech_ag_y3_syllabus_2018-19::08::irrigation-drainage-engg-lab": {
        "action": "RETARGET", "target": "irrigation-drainage-engineering-lab",
        "reason": "Abbreviated print of the same era-family lab subject: draft 'Irrigation & Drainage Engg Lab.' (RAG551, 2018-19) vs the irrigation-and-drainage-engineering-lab row appended in this same commit from the 2020-21 KAG-651 print ('Irrigation & Drainage Engineering Lab') — same lab across era schemes; RETARGET before the append keeps one lab row; RAG551 joins as its 2018-19 era code; NAG-651 (2015-16) and BAG651 (2024-25) then converge on the same row by slug/fuzzy."},
    "01_btech_ag_y1_syllabus_2022-23::09::soft-skills": {
        "action": "ALLOW",
        "reason": "Era-family match, same subject lineage: draft 'Soft Skills' (BAS105/BAS205, 2022-23 print, fuzzy 87/overlap 52) vs the soft-skill-i row (KNC-101, 2020-21 AG y1 model-curriculum NC print). The AICTE-model Soft Skills subject carried KNC-101 (2020-21 audit) then BAS105/BAS205 (2021-22 onward); the 2022-23 doc is the newest session so it fieldwise-wins and KNC-101 stays as the era backfill code. Unit vocabulary (communication/leadership/teamwork modules) is the shared subject core."},
    "01_btech_ag_y1_syllabus_2022-23::12::basic-electrical-engineering-lab": {
        "action": "RETARGET", "target": "baisc-electrical-engineering-laboratory",
        "reason": "TIE between two lab rows resolves on code-era identity: the draft 'Basic Electrical Engineering Lab' (BEE151/BEE251, 2022-23 K-era) is the SAME subject as the 2018-19 'BAISC ELECTRICAL ENGINEERING LABORATORY' row (KEE-151P/KEE-251P, print typo retained in *_print) — the BEE code family replaced KEE-151P/251P for Basic Electrical Engineering lab. The competing 'electrical-engineering-lab' row (AEE151C/AEE251C, 2026-27 AG A-generation, name 'Electrical Engineering Lab') is a DIFFERENT subject printed in a different curriculum (live class as B06's Electronics-vs-Electrical); kept separate. 2022-23 fieldwise-wins; KEE-151P/251P backfill."},
    "01_btech_ag_y1_syllabus_2022-23::17::workshop-practice-lab": {
        "action": "ALLOW",
        "reason": "Era-family match: draft 'Workshop Practice Lab' (BWS151/BWS251, 2022-23) vs the multi-era workshop-practice row (EAG255;NEW-151;NEW-251;NEW-252;KWS101;... 2008-09 onward) — same Workshop Practice (lab) subject carried across code eras (NEW/KWS/EAG/BWS); 2022-23 is newest so it fieldwise-wins and older codes backfill."},
    "06_btech_ag_y3_scheme-syllabus_2020-21::16::irrigation-drainage-engineering": {
        "action": "ALLOW",
        "reason": "Era-family match: draft 'Irrigation & Drainage Engineering' (KAG-601, 2020-21, fuzzy 94/overlap 82) vs the irrigation-and-drainage-engineering row (EAG-505, 2011-12 AG y3) — the same AG core subject across era schemes; shared unit vocabulary (ET, border/check-basin/furrow, drip/sprinkler, subsurface drainage) is the distinctive core; 2020-21 is newer so it fieldwise-wins and EAG-505 backfills."},
    "08_btech_ag_y3_syllabus_2024-25::16::irrigation-drainage-engineering": {
        "action": "RETARGET", "target": "irrigation-and-drainage-engineering",
        "reason": "Era-family match, deterministic target: draft 'IRRIGATION & DRAINAGE ENGINEERING' (BAG601, 2024-25, fuzzy 94/overlap 82) vs the same irrigation-and-drainage-engineering row (EAG-505, 2011-12; RAG501 2018-19; KAG-601 2020-21) — the newest 2024-25 print fieldwise-wins; all older era codes backfill. Same subject, identical module structure across the era prints; RETARGET pins the single canonical row."},
    "08_btech_ag_y3_syllabus_2024-25::24::remote-sensing-and-gis-applications": {
        "action": "FORCE_APPEND",
        "reason": "Different subject (low overlap): draft 'REMOTE SENSING AND GIS APPLICATIONS' (BAG062, AG y3 2024-25, fuzzy 94 but overlap only 27) vs the remote-sensing-and-applications row (BAC-052, ACT y3 2025-26) — distinct branch curricula (AG vs ACT), distinct code families (BAG vs BAC), and the printed name differs by the substantive token 'GIS'; 27% shared vocabulary is generic RS terminology. Zero-guess (RULES §4/§11): separate rows; G3 subject_id suffix carries the distinction."},
    "09_btech_ag_y3s5-6_scheme-syllabus_2015-16::07::engineering-properties-of-biological-material": {
        "action": "ALLOW",
        "reason": "Name-variant match: draft 'Engineering Properties of Biological Material' (NAG-505, 2015-16, fuzzy 87/overlap 41) vs the engineering-properties-of-biological-materials-food-quality row (EAG-era 2011-12 print 'Engineering Properties of Biological Materials & Food Quality') — singular/plural + 'Food Quality' tail print variant of the same AG subject; 2015-16 backfills (older print)."},
    "09_btech_ag_y3s5-6_scheme-syllabus_2015-16::13::tractor-system-controls": {
        "action": "ALLOW",
        "reason": "Spacing print variant: draft 'Tractor System & Controls' (NAG-603, 2015-16, fuzzy 90/overlap 96) vs the tractor-systems-and-controls row (EAG-605, 2011-12) — singular/plural of the same AG subject with 96% distinctive-vocabulary overlap; 2015-16 backfills (older print)."},
    # ---- B08 (CRON-20261030-B08) per-key adjudications, evidence-recorded ----
    "02_btech_ag_y4_syllabus_2016-17::06::soil-and-water-conservation-structures": {
        "action": "ALLOW",
        "reason": "Same AG y4 subject across era schemes: draft 'Soil and Water Conservation Structures' (NAG-703, 2016-17 detail print) vs the water-harvesting-soil-and-water-conservation-structures row (KAG-051, 2020-21, fuzzy 87/overlap 71) — the 2020-21 print adds the 'Water Harvesting &' prefix to the same subject name; 71 shared distinctive terms; 2016-17 is older so it only backfills and adds NAG-703 as its era code."},
    "02_btech_ag_y4_syllabus_2016-17::08::testing-of-agricultural-machinery-and-tractor": {
        "action": "ALLOW",
        "reason": "Singular/plural print variant: draft 'Testing of Agricultural Machinery and Tractor' (NAG-031 detail print, 2016-17, fuzzy 99/overlap 41) vs the testing-of-agricultural-machinery-and-tractors row (RAG079A, 2019-20) — same DE-III subject; 2016-17 older so backfill + NAG-031 era-code addition."},
    "02_btech_ag_y4_syllabus_2016-17::18::renewal-energy-resources": {
        "action": "ALLOW",
        "reason": "Print-typo + name-tail variant of the same subject: draft 'Renewal Energy Resources' (NAG-081 detail print, 2016-17, fuzzy 92/overlap 19 — typo 'Renewal' kept verbatim per RULES §6) vs the renewable-energy-sources row (KAG-057, 2020-21); shared RE vocabulary (solar/biogas/wind); 2016-17 backfills and adds NAG-081."},
    "04_btech_ag_y4_syllabus_2021-22::09::precision-agriculture-and-system-management": {
        "action": "ALLOW",
        "reason": "Word-form print variant: draft 'Precision Agriculture and System Management' (KAG-era 2021-22, fuzzy 97/overlap 64) vs the precision-agricultural-and-system-management row (RAG077, 2019-20) — same subject, agricultural/agricultural print variance; 2021-22 is the newer session so its content fieldwise-wins per RULES §3."},
    "02_btech_ag_y4_syllabus_2016-17::01::precision-agriculture-and-system-management": {
        "action": "ALLOW",
        "reason": "Word-form print variant (same class as 04::09): draft 'Precision Agriculture and System Management' (NAG-012 detail print, 2016-17, fuzzy 97/overlap 47) vs the precision-agricultural-and-system-management row (RAG077, 2019-20) — same subject; 2016-17 is older so it only backfills and adds NAG-012 (the 2016-17 detail print of this OE-I subject, moved off the 2015-16 food-processing row by the B08 baseline repair)."},
    "06_btech_ai-ds_y3_syllabus_2024-25::24::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "Branch-consistent assessment row: the ladder's Tier-0 hit fires the CODE-REASSIGNED name-transfer toward mini-project-or-internship-assessment (primary BAE553; KAG354/BAG554 — AG/AE code family, EMPTY branch_names), which would move CSE-family BCS554 into the AG/AE row (cross-branch pollution, RULES §1b spirit). The CSE&E internship-assessment-mini-project row (branch Computer Science & Engineering;...; all_codes BCC351;KCS354;KEC354;KCS554;BCS554;BCE554) already OWNS BCS554 and matches the 2024-25 AI&DS print — UPDATE there; no transfer needed."},
    "07_btech_ai-ds_y4_syllabus_2024-25::10::robotics-and-automation": {
        "action": "FORCE_APPEND",
        "reason": "Different subject (live T2 reject, B06 Electronics-vs-Electrical class): draft 'Robotics and Automation' (KAD073, AI&DS Departmental Elective-IV, 2024-25, fuzzy 100/overlap 11) hit the automation-and-robotics row (BOE302/402+H — the university-wide Open Elective slot, CSE branch, 2023-24). Different elective pools (OE-II vs DE-IV), different code families (BOE vs KAD), different branches, and the draft's own print is internally mismatched (KAD073 carries KAD075's ML-Network-Security units/COs per its PRINT-CONTENT-MISMATCH flag, kept verbatim). Zero-guess keeps separate rows (RULES §11)."},
    "07_btech_ai-ds_y4_syllabus_2024-25::15::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "Branch-consistent assessment row (same class as 06::24): KCS354/KCS554 are ALREADY owned by internship-assessment-mini-project (CSE&E branch, sess 2024-25); the name-transfer toward the AG/AE-named row (empty branch) would pollute across branches. UPDATE the CSE&E row; KCS752 (sem-VII slot print) joins it as a slot code."},
    "08_btech_ai-ds_y4_syllabus_2025-26::08::mini-projects-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "TIE between internship-assessment-mini-project (fuzzy 94) and mini-project-or-internship-assessment (fuzzy 99) resolves on code-family + branch identity: the draft (BCS752, 2025-26 AI&DS) is the CSE-family assessment slot — the 99-score row is the AG/AE-named row (BAE553;KAG354;BAG554, empty branch); the 94-score row is the CSE&E branch row already carrying BCS554/KCS554/KCS354. 2025-26 is the newest session: fieldwise wins; BCS752 joins."},
    "09_btech_ai-ml-ai-ds-csd_y2_syllabus-rev_2022-23::09::operating-system-lab": {
        "action": "RETARGET", "target": "operating-systems-lab-btech",
        "reason": "Singular/plural print variant, NOT a code reassignment (B06 ALLOW class): draft 'OPERATING SYSTEM LAB' (KCS451, 2022-23 print) vs the KCS451 owner row 'Operating Systems Lab' (KCS451, 2021-22 CSAI print) — the same lab; the bare 'systems'/'system' token variance triggered the name-transfer toward the 2023-24 BCS451 row, which would strand the 2021-22 row codeless and mis-attribute the 2022-23 print. UPDATE the KCS451 owner row; 2022-23 fieldwise wins; KCS451 stays in its family row with KCS452/KCS453."},
    "02_btech_ag_y4_syllabus_2016-17::26::project": {
        "action": "RETARGET", "target": "project",
        "reason": "Same printed subject, two semester slots: the 2016-17 AG y4 document prints 'Project' in BOTH the Sem-VII (NAG-753, P=8) and Sem-VIII (NAG-852, P=12) scheme tables — one slot-subject across two semester tables (G.P. GP-101;GP201 precedent: one row, multiple slot codes). 02::23 appends the row (subject_id 'project'); this entry converges the Sem-VIII slot onto it, keeping (name,course) unique (G3) while both codes land in all_codes."},
    "07_btech_ai-ds_y4_syllabus_2024-25::16::project": {
        "action": "RETARGET", "target": "project",
        "reason": "Same program slot, newest print: draft 'Project' (KCS753/KCS851 CO-only block p.22, 2024-25 AI&DS) vs the project row appended in this commit from the 2016-17 AG slot print (NAG-753;NAG-852) — the shared final-year project slot across branches (internship-assessment-mini-project precedent: one assessment row carries multiple branch code families); 2024-25 supplies the printed CO content (2016-17 prints none) so it fieldwise-wins; KCS753/KCS851 join as slot codes; the 2025-26 prints rename the slot to Project-1/Project-II which keep their own rows."},
    "02_btech_ag_y4_syllabus_2016-17::24::gp": {
        "action": "RETARGET", "target": "g-p",
        "reason": "Same subject, print abbreviation: draft 'GP' (NGP701, Sem-VII scheme row, 2016-17) vs the g-p row ('G.P.', GP-101;GP201, 2008-09, AG branch) — GP/G.P. is the printed abbreviation of General Proficiency in the same AG program (the norm_name tokenization differs only by the abbreviation dot); NGP701/NGP801 join as the 2016-17 era codes; 2016-17 newer so it fieldwise-wins (the G.P. slot prints no units/COs in either document)."},
    "02_btech_ag_y4_syllabus_2016-17::27::gp": {
        "action": "RETARGET", "target": "g-p",
        "reason": "Same subject as 02::24: the Sem-VIII G.P. slot print (NGP801) converges on the g-p row (GP-101;GP201;NGP701;NGP801) — one General Proficiency subject across two semester tables, exactly the g-p row's own GP-101;GP201 two-slot pattern."},
    # ---- B08 cross-draft convergences (same subject printed by multiple batch
    # documents across sessions; the OLDER draft's row is appended first in
    # docs-glob order and the newer drafts RETARGET onto it so fieldwise-wins
    # (RULES §3) converges each subject into ONE row and G3 (name,course)
    # stays unique) ----
    "04_btech_ag_y4_syllabus_2021-22::01::wasteland-development": {
        "action": "RETARGET", "target": "wasteland-development",
        "reason": "Same subject reprinted across sessions: 02::17 (2016-17, NAG-043/NAG-073) appended the row earlier in this commit; the 2021-22 print (KAG-era) is newer so it fieldwise-wins on the same row; era codes accumulate."},
    "04_btech_ag_y4_syllabus_2021-22::02::waste-and-by-products-utilization": {
        "action": "RETARGET", "target": "waste-and-by-products-utilization",
        "reason": "Same subject reprinted across sessions: 02::12 (2016-17, NAG-062) appended the row earlier in this commit; the 2021-22 print (KAG-era) is newer so it fieldwise-wins on the same row."},
    "04_btech_ag_y4_syllabus_2021-22::03::crop-process-engineering": {
        "action": "RETARGET", "target": "crop-process-engg",
        "reason": "Print-abbreviation variant (B07 'Irrigation & Drainage Engg.' class): draft 'Crop Process Engineering' (2021-22) vs the crop-process-engg row appended from 02::19 (2016-17 print 'Crop Process Engg', NAG-082) — same subject; 2021-22 newer so it fieldwise-wins; the full-form print is recorded in the row's *_print/history."},
    "04_btech_ag_y4_syllabus_2021-22::04::tractor-design-principles": {
        "action": "RETARGET", "target": "tractor-design-principles",
        "reason": "Same subject reprinted across sessions: 02::20 (2016-17, NAG-083) appended the row earlier in this commit; the 2021-22 print (KAG-era) is newer so it fieldwise-wins on the same row."},
    "04_btech_ag_y4_syllabus_2021-22::07::design-of-agricultural-machinery": {
        "action": "RETARGET", "target": "design-of-agricultural-machinery",
        "reason": "Same subject reprinted across sessions: 02::03 (2016-17, NAG-021 detail print moved off the 2015-16 minor-irrigation row by the B08 baseline repair) appended the row earlier in this commit; the 2021-22 print (KAG-era) is newer so it fieldwise-wins on the same row."},
    "05_btech_ag_y4_syllabus_2025-26::02::tractor-design-principles": {
        "action": "RETARGET", "target": "tractor-design-principles",
        "reason": "Same subject, newest print: 05 (BAG-era 2025-26) fieldwise-wins on the row appended from 02::20 (2016-17) and updated by 04::04 (2021-22); BAG071-era slot codes accumulate."},
    "05_btech_ag_y4_syllabus_2025-26::03::waste-and-by-products-utilization": {
        "action": "RETARGET", "target": "waste-and-by-products-utilization",
        "reason": "Same subject, newest print: 05 (BAG-era 2025-26) fieldwise-wins on the row appended from 02::12 (2016-17) and updated by 04::02 (2021-22)."},
    "08_btech_ai-ds_y4_syllabus_2025-26::00::deep-learning": {
        "action": "RETARGET", "target": "deep-learning",
        "reason": "Same AI&DS y4 Departmental Elective across sessions: 07::07 (KDS078, 2024-25) appended the row earlier in this commit; the 2025-26 print (BAI701-era) is newer so it fieldwise-wins; era codes accumulate. Zero-GAP keeps one row per subject (RULES G1)."},

    # ---- B09 adjudications (CRON-20261031-B09; AU/AE-ECE-EI/AI-ML wave) ----
    "01_btech_ai-ml_y4_syllabus_2024-25::14::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "B08 evidence class (recorded 07::15/08::08 overrides): the ladder's Tier-0 unique code owner is internship-assessment-mini-project (CSE&E branch; all_codes BCC351;KCS354;KEC354;KCS554;BCS554;BCE554;KCS752;BCS752) but the name-identity transfer targets mini-project-or-internship-assessment (BAE553;KAG354;BAG554, EMPTY branch_names) — the AG/AE-named row — which would move CSE-family codes KCS354/KCS554/KCS752 across branches (RULES §1b spirit, B08 recorded rejection of this exact transfer). UPDATE the CSE&E code-owner row instead; the 2024-25 AI-ML print corroborates (codes already owned)."},
    "02_btech_ai-ml_y4_syllabus_2025-26::07::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "Same B08 evidence class: BCS752 was joined to internship-assessment-mini-project from the 2025-26 AI&DS print (recorded 07::xx override 'BCS752 joins'); this 2025-26 AI-ML print is the same university-wide assessment slot — the proposed name-transfer to the AG/AE-named row (BAE553;KAG354;BAG554, empty branch) would pollute cross-branch. UPDATE the code-owner row; corroboration-only (BCS752 already owned)."},
    "02_btech_ai-ml_y4_syllabus_2025-26::06::project": {
        "action": "RETARGET", "target": "project-1",
        "reason": "Joint-print corroboration on the BCS753 slot row (B08-recorded semantics 'the 2025-26 prints rename the slot to Project-1/Project-II which keep their own rows'): after patch_b09_merge_fixes.py stripped BCS851 (its sem-VIII slot row project-ii already owns it; print evidence preserved verbatim in the draft quirks), Tier-0 uniquely owns BCS753 at project-1 — but the ladder's name-transfer (draft 'Project' vs row 'Project-1') would move BCS753 to project-btech, undoing the recorded B08 Project-1/Project-II split; RETARGET pins the update to project-1. This draft's CO table is byte-identical to the 2025-26 content already on project-1, so the update is corroboration-only (source_history + change_note; zero field churn). The 'Project'-named row project-btech receives KCS753/KCS851 + 2024-25 CO content from doc01::15 (T1 name identity), completing the B08 '07::16' convergence course-correctly (the B08 override's unfiltered subject_id match had parked those codes on the BCA row — repaired this commit by repair_bca_project_b09.py)."},
    "03_btech_all-branch_y1_scheme_2016-17::09::electrical-engineering-laboratory": {
        "action": "RETARGET", "target": "baisc-electrical-engineering-laboratory",
        "reason": "TIE (fuzzy 92 baisc-electrical-engineering-laboratory vs 88 electrical-engineering-lab) resolves on era-family identity: this doc's own scheme rows print 'Basic Electrical Engg Lab' for REE151 (sem-1) and REE251 (sem-2) while the detail heading prints 'ELECTRICAL ENGINEERING LABORATORY' — the same y1 lab as the BAISC ELECTRICAL ENGINEERING LABORATORY row (KEE-151P;KEE-251P;BEE151;BEE251, print typo retained in *_print; recorded B07 override already established that the competing electrical-engineering-lab row AEE151C/AEE251C 2026-27 AG A-generation is a DIFFERENT subject). REE151/REE251 join as the 2016-17 era codes; 2016-17 older so backfill-empty only."},
    "04_btech_applied-electronics-ece-ei_syllabus_2016-17::01::control-systems-i": {
        "action": "ALLOW", "target": "",
        "reason": "Era-family same subject: draft 'Control Systems-I' (NIC-501, 2016-17 AE/ECE/EI sem-5) vs the control-system row (BEC602, 2025-26 ACT) — unit-1 texts near-identical ('Basic Components of a control system, Feedback and its effect, types of feedback control systems...'), fuzzy 90/overlap 82. 2016-17 older so backfill-empty only; NIC-501 joins as the 2016-17 era code."},
    "04_btech_applied-electronics-ece-ei_syllabus_2016-17::03::microprocessors": {
        "action": "ALLOW", "target": "",
        "reason": "Same 8085-microprocessor course across eras: draft u1 'Evolution of microprocessors, Microprocessor architecture and its operations, 8085 pins description...' vs the microprocessor row (KCS403, 2021-22) u1 'Microprocessor evolution and types, microprocessor architecture and operation...'; fuzzy 97/overlap 46. 2016-17 older so backfill-empty only; NEC-503 joins as the era code."},
    "04_btech_applied-electronics-ece-ei_syllabus_2016-17::16::computer-architecture-and-organization": {
        "action": "ALLOW", "target": "",
        "reason": "Word-order name variant of the same subject: 'Computer Architecture and Organization' vs 'Computer Organization and Architecture' (BCS302;KCS302 row) — fuzzy 100 with shared vocabulary; NEC-012 (2016-17 Elective-I) joins as the era code; older so backfill-empty only."},
    "04_btech_applied-electronics-ece-ei_syllabus_2016-17::17::microwave-engineering": {
        "action": "ALLOW", "target": "",
        "reason": "Same microwave-electronics elective lineage: draft units (rectangular waveguides TE/TM, scattering matrix, klystron/TWT tubes, solid-state, measurements) are the microwave core of the microwave-radar-engineering row (BEC073, 2026-27) whose print adds the transmission-line and RADAR units; fuzzy 88/overlap 61 shared distinctive vocabulary. 2016-17 older so backfill-empty only; NEC-601 joins as the era code."},
    "06_btech_au_syllabus_2009-10::00::mathematics-iii": {
        "action": "RETARGET", "target": "mathematics-iii-partial-differential-equations-statistical-a",
        "reason": "Wrong-subject fuzzy hit retargeted to the canonical Mathematics-III row: the ladder's Tier-2 target basic-mathematics-ii (KAG201, AG y2 basic math) is a DIFFERENT subject; the draft 'Mathematics-III' (EAS301/EAS401, 2009-10 AU: complex variable, statistics, numerical techniques) is the same university-wide Mathematics-III subject as the row 'MATHEMATICS-III (Partial Differential Equations, Statistical and Numerical Techniques)' (BAS302;BAS402, 2023-24) — the printed parenthetical names the same statistical/numerical content. 2009-10 oldest so backfill-empty only; EAS301/EAS401 join as era codes."},
    "06_btech_au_syllabus_2009-10::20::heat-mass-transfer": {
        "action": "ALLOW", "target": "",
        "reason": "Era-family row already carrying KME501;RME502A;BME501;NBT-402;EAG-404 — EME504 (2009-10 AU, the oldest print) joins as an era code; fuzzy 90/overlap 155; older so backfill-empty only."},
    "07_btech_au_syllabus_2020-21::01::strength-of-material": {
        "action": "ALLOW", "target": "",
        "reason": "Same subject, singular/plural print variant: 'Strength of Material' (KME502, 2020-21 AU) vs the strength-of-materials row (KAE403;NAG-304;EAG-405;EAG-454, 2019-20) — fuzzy 98/overlap 145; 2020-21 is the newest print so it fieldwise-wins on the row; KME502 joins as the AU-era code."},
    "08_btech_au_y2_model-curriculum_2019-20::07::engineering-mechanics": {
        "action": "FORCE_APPEND",
        "reason": "Wrong-subject fuzzy hit: the Tier-2 target 'Mechanical Engineering' (BMN302, 2024-25 Mining service course) is a DIFFERENT subject; no Engineering Mechanics row exists in BTech (the strength-of-materials-engineering-mechanics row is the AG COMBINED subject, also different). KME402 (2019-20 AU y2 model curriculum) appends as its own row."},
    "08_btech_au_y2_model-curriculum_2019-20::08::manufacturing-processes": {
        "action": "FORCE_APPEND",
        "reason": "Different course designs despite name containment (fuzzy 88): KME403 (2019-20 AU y2) units are casting/moulding, metal cutting, grinding & super-finishing, welding, unconventional machining — a y2 core course; the Tier-2 target basic-manufacturing-processes (NME-101;NME-201, 2013-14 AG y1) prints Engineering Materials + Basic Metal Forming & Casting — the y1 basic course. Zero-guess: appended as its own row; convergence can be re-evidenced later."},
    "09_btech_au_y3_syllabus_2018-19::01::heat-mass-transfer": {
        "action": "ALLOW", "target": "",
        "reason": "Era-family: RME502 (2018-19 AU y3) joins the heat-and-mass-transfer row already carrying KME501;RME502A;BME501;NBT-402;EAG-404; fuzzy 90/overlap 159; older so backfill-empty only."},
    "09_btech_au_y3_syllabus_2018-19::21::mechanical-vibration": {
        "action": "ALLOW", "target": "",
        "reason": "Singular/plural print variant of the mechanical-vibrations row (KAE056;BAE056, 2020-21): RME063 (2018-19 AU elective) joins as the era code; fuzzy 98/overlap 80; older so backfill-empty only."},
    "10_btech_au_y3_syllabus_2024-25::06::advance-manufacturing-processes": {
        "action": "FORCE_APPEND",
        "reason": "Different subject despite name adjacency (fuzzy 87/overlap 15): BME051 (2024-25 AU elective) units are Advanced Machining (EDM/ECM/USM/ AJM), Advanced Casting, Advanced Welding (EBW/LBW/USW), HERF/electro-magnetic/explosive forming, Additive Manufacturing — the ADVANCED-manufacturing subject; the Tier-2 target basic-manufacturing-processes (NME-101;NME-201) prints the y1 basic materials/forming course. Appends as its own row."},

    # ---- B10 adjudications (CRON-20261031-B10; AU y4 five-era completion +
    # Bioinformatics y2/y3 + BME 2009-10/2011-12 + AE/ECE-EI 2016-17 _2 copy +
    # BME-y2 model-curriculum corroborating KEC wave) ----
    "02_btech_au_y4_syllabus-cbcs_2019-20::00::computer-aided-design-manufacturing": {
        "action": "ALLOW", "target": "",
        "reason": "Era-family same subject: draft 'COMPUTER AIDED DESIGN & MANUFACTURING' (RME701, 2019-20 AU CBCS) vs the cad-cam-computer-aided-design-and-manufacturing row (EAU701, 2009-10) — the AU y4 CAD/CAM course across era schemes ('&'/name print variance, B07 'Irrigation & Drainage Engg.' class); 2019-20 older than row's era chain so backfill-empty only; RME701 joins as the 2019-20 era code."},
    "02_btech_au_y4_syllabus-cbcs_2019-20::04::automotive-electrical-electronics-system": {
        "action": "ALLOW", "target": "",
        "reason": "Era-family same subject: draft 'AUTOMOTIVE ELECTRICAL & ELECTRONICS SYSTEM' (RAU070, 2019-20) vs the automotive-electrical-and-electronics row (KAU 061 2020-21;BAU061 2025-26) — the same AU y4 electrical/electronics systems course carried across KAU/BAU era prints; 2019-20 older so backfill-empty only; RAU070 joins as the era code."},
    "02_btech_au_y4_syllabus-cbcs_2019-20::10::automotive-pollution-control": {
        "action": "ALLOW", "target": "",
        "reason": "Era-family same subject: draft 'AUTOMOTIVE POLLUTION & CONTROL' (RAU080, 2019-20; u1 'Pollutants – Sources – Formation – Effects...Emission Standards') vs the automotive-pollution-and-control row (EAU702 2009-10;KAU 071 2020-21, u1 same pollutant-sources/emission-standards vocabulary per B09 ingestion) — same course across EAU/KAU eras; backfill-empty only; RAU080 joins."},
    "02_btech_au_y4_syllabus-cbcs_2019-20::12::alternate-energy-sourcse-for-automobiles": {
        "action": "ALLOW", "target": "",
        "reason": "Era-family same subject with printed typo kept verbatim: draft 'ALTERNATE ENERGY SOURCSE FOR AUTOBILES' (RAU082, 2019-20; u1 alcohols-as-fuels/alternative-fuels vocabulary) vs the alternative-energy-sources-for-automobiles row (EAU052;EME052, 2009-10) — Alternate/Alternative print variance + 'SOURCSE' typo (quirk-recorded); backfill-empty only; RAU082 joins."},
    "03_btech_au_y4_syllabus_2016-17::00::computer-aided-design-and-manufacturing": {
        "action": "ALLOW", "target": "",
        "reason": "Era-family same subject: draft 'Computer Aided Design and Manufacturing' (NAU-701, 2016-17; u1 'Computers in Industrial Manufacturing: Product cycle, CAD/CAM Hardware...') vs the cad-cam-computer-aided-design-and-manufacturing row (EAU701, 2009-10) — same AU y4 CAD/CAM course across N/EAU eras; backfill-empty only; NAU-701 joins as the 2016-17 era code."},
    "03_btech_au_y4_syllabus_2016-17::04::trouble-shooting-servicing-and-maintenance-of-automobiles": {
        "action": "ALLOW", "target": "",
        "reason": "Era-family same subject: draft 'Trouble Shooting, Servicing and Maintenance of Automobiles' (NAU-801, 2016-17; u1 'Automobile Maintenance: Importance of maintenance, scheduled and unscheduled...') vs the trouble-shooting-servicing-maintenance-of-automobile row (EAU801, 2009-10) — same course, singular/plural print variance; fuzzy 95/overlap 140; backfill-empty only; NAU-801 joins."},
    "03_btech_au_y4_syllabus_2016-17::12::alternate-energy-sources-for-automobiles": {
        "action": "ALLOW", "target": "",
        "reason": "Era-family same subject: draft 'Alternate Energy Sources for Automobiles' (NAU-052, 2016-17; u1 solar/photo-voltaic/Hydrogen/Bio-mass vocabulary) vs the alternative-energy-sources-for-automobiles row (EAU052;EME052, 2009-10) — fuzzy 98/overlap 67; backfill-empty only; NAU-052 joins as the era code."},
    "03_btech_au_y4_syllabus_2016-17::14::computer-simulation-of-i-c-engines": {
        "action": "ALLOW", "target": "",
        "reason": "Era-family same subject: draft 'Computer Simulation of I.C. Engines' (NAU-061, 2016-17; u1 'Heat of reaction, Measurement of URP/HRP, Adiabatic flame temperature...') vs the computer-simulation-of-ic-engines-process row (EAU061;EME061;EME062, 2009-10) — same course, 'I.C. Engines' vs 'IC Engines Process' print variance (fuzzy 85/overlap 6 — low overlap reflects the row's scheme-only thin content, name+code-family EAU061 affinity is the identity evidence); backfill-empty only; NAU-061 joins."},
    "03_btech_au_y4_syllabus_2016-17::16::hydraulic-and-pneumatic-systems": {
        "action": "ALLOW", "target": "",
        "reason": "Era-family same subject: draft 'Hydraulic and Pneumatic Systems' (NAU-063, 2016-17; u1 fluid properties/units vocabulary) vs the hydraulic-pneumatic-systems row (EAU063;EME063, 2009-10) — fuzzy 93/overlap 148; backfill-empty only; NAU-063 joins as the era code."},
    "05_btech_au_y4_syllabus_2025-26::00::measurement-metrology": {
        "action": "ALLOW", "target": "",
        "reason": "Era-family same subject: draft 'Measurement & Metrology' (BME701, 2025-26 AU y4; u1 'Mechanical Measurements: generalized measurement system...sensitivity' vocabulary) vs the measurement-and-metrology row (EME403, 2009-10) — the same AU/ME measurement-and-metrology theory course across eras (the LAB row measurement-metrology-lab is separate, B10 docs 04 KME751 + 05 BME751 both T1 onto it); 2025-26 is the newest session so it fieldwise-wins per RULES §3; EME403 stays as the era backfill code."},
    "05_btech_au_y4_syllabus_2025-26::01::manufacturing-process-of-automotive-components": {
        "action": "ALLOW", "target": "",
        "reason": "Era-family same subject: draft 'Manufacturing Process of Automotive Components' (BAU072, 2025-26; u1 powder-metallurgy/friction-lining vocabulary) vs the manufacturing-of-automotive-components row (RAU063, 2018-19) — same course, 'Process of'/'of' print variance (fuzzy 90/overlap 43); 2025-26 newest so fieldwise-wins; RAU063 stays as the era code."},
    "02_btech_au_y4_syllabus-cbcs_2019-20::09::automation-robotics": {
        "action": "RETARGET", "target": "robotics-and-automation",
        "reason": "TIE (fuzzy 90/90) resolves on branch+era affinity: draft 'AUTOMATION & ROBOTICS' (RME078, 2019-20 AU y4 DE) — the robotics-and-automation row already carries EAU013 (2011-12 AU elective) and KAD073 (2024-25 AI-DS cross-listing), i.e. the SAME AU-branch robotics elective lineage; the competing automation-and-robotics row (BOE302;BOE402, 2023-24) is the 2nd-year university-wide OPEN-ELECTIVE member row (different program level/slot). Name-order print variance ('Automation & Robotics' vs 'Robotics and Automation', B07 abbreviation class); 2019-20 older than the row's 2024-25 so backfill-empty only — the draft's 2019-20 units fill the row's empty unit fields; RME078 joins as the era code."},
    "10_btech_bme_y2_model-curriculum_2019-20::14::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "B08/B09 recorded transfer-rejection class (B09 overrides 01::14/02::07): the ladder's Tier-0 unique code owner IS internship-assessment-mini-project (CSE&E branch; all_codes ...KEC354...) and the name-identity transfer would move the code to mini-project-or-internship-assessment (BAE553;KAG354;BAG554, EMPTY branch_names) across branches. UPDATE the CSE&E code-owner row instead; KEC354 is already owned there so this 2019-20 BME-y2 print is corroboration-only (source_history + change_note)."},
    "09_btech_bme_syllabus_2011-12::42::biomaterials": {
        "action": "FORCE_APPEND",
        "reason": "Different subject despite the identical name (live T2 fuzzy 96/overlap 32 reject): the 2011-12 BME print carries TWO different BIOMATERIALS courses — EBM-604 (Sem-VI core-elective; u1 'Introduction: Definition of biomaterials, requirements & classification...Comparison of properties...') already converged on the bio-materials row (B10 doc08 2010-11 EBM-604 append + 09::26 update), and EBM-024 (ELECTIVE-II; u1 'Definition and classification of Biomaterials, surface properties of materials, Electro kinetic theory. Crystal structure of solids...' — entirely different unit text, OCR-recovered p.44, page-image verified) — the draft subagent itself recorded 'EBM-604/EBM-024 same-name Biomaterials kept separate per printed codes'. RULES §11: never merge two different subjects; codes differ. APPEND as its own row (sid biomaterials; G3 name differs from the BIO-MATERIALS row)."},

    # ---- B11 (CRON-20261031-B11) per-key adjudications, evidence-recorded ----
    # doc01 = BME y3 2017-18 (RBM era, NEWEST BME print) converging on the
    # B10-established EBM-era BME rows (sess_latest 2010-11/2011-12): newer
    # session wins fieldwise per RULES §3; rows gain RBM era codes.
    "01_btech_bme_y3_syllabus_2017-18::01::bioinstrumentation": {
        "action": "ALLOW",
        "reason": "Era-family name-variant convergence (B10 recorded collapsed-name pair class BIOINSTRUMENTATION/BIO-INSTRUMENTATION similarity 1.0): draft 'BIOINSTRUMENTATION' (RBM502, 2017-18 BME y3 sem-V core) vs the EBM-501 'BIO-INSTRUMENTATION' row (2010-11) — same BME subject across era prints; draft u1 (transducers classification/selection, temperature/displacement/pressure transducers) is the instrument canon; 2017-18 is the newer session so it fieldwise-wins per RULES §3 and EBM-501 joins as the 2010-11 era code."},
    "01_btech_bme_y3_syllabus_2017-18::02::microprocessor-application": {
        "action": "ALLOW",
        "reason": "Era-family name-variant convergence: draft 'MICROPROCESSOR & APPLICATION' (RBM503, 2017-18) vs the EBM-502 'MICROPROCESSOR & ITS APPLICATIONS' row (2010-11) — abbreviated '& APPLICATION' print of the same BME subject; draft u1 (THE 8085 PROCESSOR: architecture, instruction set) is the same microprocessor canon; 2017-18 newer so fieldwise-wins; EBM-502 joins as era code."},
    "01_btech_bme_y3_syllabus_2017-18::08::computer-architecture-and-organization": {
        "action": "ALLOW",
        "reason": "Word-order name variant of the same subject, identical to the recorded B09 04::16 adjudication: 'Computer Architecture and Organization' vs 'Computer Organization and Architecture' (BCS302;KCS302;NEC-012 row) — fuzzy 100 with shared vocabulary; draft u1 (system design methodology, gate level, register level components, PLD) is the COA canon; REC052 (2017-18 BME Elective-II slot) joins as an era code; draft older than the row's 2023-24 session so backfill-empty only."},
    "01_btech_bme_y3_syllabus_2017-18::11::microcontroller-and-biomedical-applications": {
        "action": "ALLOW",
        "reason": "Era-family name-variant convergence: draft 'MICROCONTROLLER AND BIOMEDICAL APPLICATIONS' (RBM601/RBM-601, 2017-18) vs the EBM-602 'MICROCONTROLLER AND BIO-MEDICAL APPLICATION' row (2010-11) — 'biomedical' vs 'bio-medical' print variance of the same BME subject; draft u1 (8051 vs microprocessor, pin diagram, internal diagram) is the same microcontroller canon; 2017-18 newer so fieldwise-wins; EBM-602 joins as era code."},
    "01_btech_bme_y3_syllabus_2017-18::12::biomedical-signal-processing": {
        "action": "ALLOW",
        "reason": "Era-family name-variant convergence: draft 'BIOMEDICAL SIGNAL PROCESSING' (RBM602/RBM-602, 2017-18) vs the EBM-603 'BIO-MEDICAL SIGNAL PROCESSING' row (2010-11) — hyphen print variance; draft u1 (Z-transform introduction, convergence, inverse Z, discrete-time systems) is the same DSP canon; 2017-18 newer so fieldwise-wins; EBM-603 joins as era code."},
    "01_btech_bme_y3_syllabus_2017-18::19::biomechanics": {
        "action": "ALLOW",
        "reason": "Era-family name-variant convergence (B10 recorded collapsed-name pair class BIOMECHANICS/BIO-MECHANICS similarity 1.0): draft 'BIOMECHANICS' (RBM063/RBM-063 elective, 2017-18) vs the EBM-013 'BIO-MECHANICS' row (2010-11) — same BME elective across era prints; draft is newer so fieldwise-wins per RULES §3; EBM-013 joins as era code."},
    "01_btech_bme_y3_syllabus_2017-18::20::physiological-control-system-and-simulation-modelling": {
        "action": "ALLOW",
        "reason": "Era-family name-variant convergence: draft 'PHYSIOLOGICAL CONTROL SYSTEM AND SIMULATION MODELLING' (RBM064/RBM-064 elective, 2017-18) vs the EBM-601 'PHYSIOLOGY CONTROL SYSTEM AND SIMULATION MODELLING' row (2010-11) — 'Physiological' vs 'Physiology' print variance of the same BME subject; draft u1 (state-variable analysis of control systems) is the same control canon; 2017-18 newer so fieldwise-wins; EBM-601 joins as era code."},
    "02_btech_bme_y4_syllabus-cbcs_2019-20::13::design-and-modelling-of-biomedical-systems": {
        "action": "ALLOW",
        "reason": "Spelling print variant of the same subject: draft 'Design and Modelling of Biomedical Systems' (RBM084, 2019-20 CBCS) vs the EBM-034 'DESIGN AND MODELING OF BIOMEDICAL SYSTEMS' row (2011-12) — 'Modelling' vs 'Modeling' variance; draft u1 (SELECTION OF HARDWARE: sensor selection, power supply design, filter/amplifier design) matches the design canon; 2019-20 newer so fieldwise-wins per RULES §3; EBM-034 joins as era code."},
    "05_btech_bt_syllabus_2009-10::25::biochemistry": {
        "action": "FORCE_APPEND",
        "reason": "Different subject (substring fuzzy false positive): draft 'Biochemistry' (EBT-301, 2009-10 BT sem-III core; u1 'pH, Buffers, Biological Buffers, Water, Vitamins... animal and plant hormones') fuzzy-hit the 'Chemistry' row (KAS102;KAS202, 2018-19 AICTE-model y1 Engineering Chemistry — water/fuels/polymer canon) on token containment of 'chemistry' in 'biochemistry' — different courses' syllabi canon and different subjects (RULES §11). No exact-name BTech Biochemistry row exists (Fundamentals of Biochemistry BBI301 is a differently-named 2025-26 Bioinformatics print). APPEND as its own row (sid biochemistry)."},
    "05_btech_bt_syllabus_2009-10::39::data-structure-and-algorithms": {
        "action": "FORCE_APPEND",
        "reason": "Different program-slot print kept separate per the differently-named-variant precedent (the registry already keeps 'Data Structure' BCS301 and 'Basics Data Structure & Algorithms' BOE306 as separate rows): draft 'Data Structure and Algorithms' (ECS-508, 2009-10 BT sem-V ECS-common print) fuzzy-hit the BOE306 2nd-year open-elective row (fuzzy 89/overlap 55 — canon-identical units: Elementary Data Organization, Stacks PUSH/POP, Trees, Graphs, Searching/Sorting). Identity across eras is plausible but the print name matches NEITHER existing row and the program slots differ; zero-guess (RULES §4) keeps the 2009-10 print as its own row (sid data-structure-and-algorithms) with a crossref note recording the near-identical canon for owner review."},
    "05_btech_bt_syllabus_2009-10::68::biomedical-instrumentation": {
        "action": "FORCE_APPEND",
        "reason": "Different subject (substring fuzzy false positive): draft 'Biomedical Instrumentation' (EBT-061 elective, 2009-10 BT; u1 'Introduction to biomedical instrumentation, Basic transducer principles, Sources of bioelectric potentials, Electrodes') vs the EBM-031 'ADVANCED BIOMEDICAL INSTRUMENTATION' row (2011-12 BME; u1 'Analytical equipments: Colorimeter... UV, visible and infra-red spectrophotometry', u2 'Blood Flow meters: Electromagnetic/ultrasonic/Doppler...') — different unit canon (overlap only 4) and the row name carries the substantive modifier 'Advanced' (RULES §11: never merge two different subjects). APPEND as its own row (sid biomedical-instrumentation); the 2016-17 (NBT052) and 2018-19 (RBT053) reprints of the same BT elective RETARGET onto it."},
    "06_btech_bt_syllabus_2013-14::06::electrical-engineering": {
        "action": "RETARGET", "target": "basic-electrical-engineering",
        "reason": "TIE resolved on era-family identity (B09 recorded class: electrical-engineering-laboratory → baisc-electrical-engineering-laboratory): draft 'ELECTRICAL ENGINEERING' (NEE-101/NEE-201, 2013-14 BT y1 common) vs the basic-electrical-engineering row (RAG103;KEE101;KEE201;KEE-101T;REE101;REE201, sess 2016-17) — draft u1 'D C Circuit Analysis and Network Theorems: Circuit Concepts: Concepts of network, Active and passive elements, Voltage and current sources...' and u2 'Steady-State Analysis of Single Phase AC Circuits: series and parallel RLC, Resonance...' are near-verbatim the row's Unit-I/II (the 2013-14 print is the same y1 BEE subject under its pre-rename title); the 89-score electronics-engineering (BOE309) hit is the recorded 'Electronics vs Electrical' different-subject class (B10 10::05 precedent). NEE-101/NEE-201 join as era codes; draft older so backfill-empty only."},
    "08_btech_bt_syllabus_2016-17::11::biomedical-instrumentation": {
        "action": "RETARGET", "target": "biomedical-instrumentation",
        "reason": "Same BT elective reprinted across sessions (B09/B10 same-commit append visibility): draft 'Biomedical instrumentation' (NBT052, 2016-17 BT sem-VIII elective; u1 'History and development of biomedical instrumentation, biometrics, Basic transducer principles: active and passive transducers...') vs the EBM-031 'ADVANCED BIOMEDICAL INSTRUMENTATION' hit is the recorded different-subject class (u1 canon differs: analytical equipments/blood-flow meters, overlap 16) — the same 'Biomedical Instrumentation' elective doc05 (2009-10 EBT-061) appends earlier in this commit (identical normalized name, same course); RETARGET pins the 2016-17 print onto that row; 2016-17 newer than 2009-10 so it fieldwise-wins per RULES §3."},
    "09_btech_bt_syllabus_2018-19::07::biomedical-instrumentation": {
        "action": "RETARGET", "target": "biomedical-instrumentation",
        "reason": "Same BT elective reprinted across sessions: draft 'Biomedical instrumentation' (RBT053/RBT-013 dual-slot print, 2018-19 BT sem-V elective; u1 near-verbatim the 2016-17 print 'History and development of biomedical instrumentation, biometrics, Basic transducer principles...') vs the EBM-031 'ADVANCED BIOMEDICAL INSTRUMENTATION' hit is the recorded different-subject class (overlap 16, different canon) — RETARGET pins it onto the biomedical-instrumentation row appended from doc05 this commit; 2018-19 is the newest print of the elective so it fieldwise-wins per RULES §3."},
    "07_btech_bt_syllabus_2015-16::15::nano-biotechnology": {
        "action": "FORCE_APPEND",
        "reason": "Different subject (same-commit live fuzzy false positive): draft 'Nano Biotechnology' (NBT-011, 2015-16 BT elective; u1 'Basic biology principles and practice of micro fabrication techniques, Atomic force microscopy, biological production of...') fuzzy-hit the plant-biotechnology row appended earlier in this commit (fuzzy 86/overlap 8 — the shared 'biotechnology' token carries the score; the unit canons are unrelated: nano/micro-fabrication vs plant tissue culture). RULES §11: never merge two different subjects. APPEND as its own row (sid nano-biotechnology); the 2018-19 reprint (09::06 RBT052/RBT-012) RETARGETs onto it."},
    "09_btech_bt_syllabus_2018-19::06::nano-biotechnology": {
        "action": "RETARGET", "target": "nano-biotechnology",
        "reason": "Same BT elective reprinted across sessions: draft 'Nano Biotechnology' (RBT052/RBT-012 dual-slot print, 2018-19; u1 'Nanobiotechnology, History, Origin, Fundamental Concepts, Bottom-up versus Top-down approaches...') is the same nano-elective as the row appended from doc07 (NBT-011, 2015-16) — the ladder's plant-biotechnology T2 hit is the recorded same-commit fuzzy false positive (shared 'biotechnology' token only). RETARGET pins the 2018-19 print onto the nano-biotechnology row; 2018-19 newer so it fieldwise-wins per RULES §3."},
    "07_btech_bt_syllabus_2015-16::17::molecular-modeling-drug-design": {
        "action": "ALLOW",
        "reason": "Same subject, '&' vs 'and' print variant: draft 'Molecular Modeling & Drug Design' (NBT-013, 2015-16 BT elective) vs the molecular-modeling-and-drug-design row appended earlier this commit from doc05 (2009-10 BT print, fuzzy 94/overlap 90 — the unit canon is identical: single-molecule calculations, assemblies, molecular mechanics/dynamics). 2015-16 is newer than the 2009-10 append so it fieldwise-wins per RULES §3; NBT-013 joins as an era code."},
    "08_btech_bt_syllabus_2016-17::02::biosafety-bioethics-ipr-patents": {
        "action": "ALLOW",
        "reason": "Same elective, token-order print variant: draft 'BIOSAFETY, BIOETHICS, IPR &PATENTS' (NBT702, 2016-17 BT elective; u1 'BIOSAFETY-REGULATORY FRAMEWORK FOR GMOS IN INDIA Regulatory framework in India governing GMOs-Recombinant DNA...') vs the bioethics-biosafety-ipr row appended earlier this commit from doc05 (2009-10 print 'Bioethics, Biosafety & IPR') — the same biosafety/bioethics/IPR elective canon across era prints (token order and the '& PATENTS' suffix vary; fuzzy 85/overlap 42). 2016-17 is newer so it fieldwise-wins per RULES §3; NBT702 joins as an era code."},
    "04_btech_bt_syllabus-aicte_2018-19::07::basic-electrical-engineering-laboratory": {
        "action": "RETARGET", "target": "baisc-electrical-engineering-laboratory",
        "reason": "Same 2018-19 laboratory subject, typo print variant: draft 'Basic Electrical Engineering Laboratory' (AICTE-model BT y1 sem-1; experiment list print) vs the BAISC ELECTRICAL ENGINEERING LABORATORY row (sess 2018-19, KEE-151P;KEE-251P;BEE151;BEE251;REE151;REE251 — the 'BAISC' spelling is the establishing doc's own print, kept verbatim per RULES §6). The draft's inherited parent code KEE101 was stripped at merge (patch_b11_merge_fixes.py: folded print, theory row keeps the published ownership); the name resolves to the same-session laboratory row (B09-established). Sem-2 print 04::19 converges on the same row."},
    "04_btech_bt_syllabus-aicte_2018-19::19::basic-electrical-engineering-laboratory": {
        "action": "RETARGET", "target": "baisc-electrical-engineering-laboratory",
        "reason": "Same-session sem-2 print of the BEE Laboratory subject converging on the BAISC ELECTRICAL ENGINEERING LABORATORY row (KEE-251P already owned there); the draft's inherited parent code KEE201 was stripped at merge (patch_b11_merge_fixes.py — folded print; basic-electrical-engineering keeps KEE101;KEE201 per the published AKTU scheme); experiments update the laboratory row."},
    # ---- B12 batch (Biotechnology wave) ----
    "03_btech_bt_y2_model-curriculum_2019-20::08::genetics-molecular-biology": {
        "action": "ALLOW",
        "reason": "Name-variant class ('&' vs 'and'): draft 'Genetics & Molecular Biology' (KBT303, 2019-20) vs the genetics-and-molecular-biology row (EBT-403, 2009-10 detailed print) — the same university-wide BT elective across era prints; fuzzy 93/overlap 39 shared distinctive vocabulary (DNA/recombination/genetic-code canon); 2019-20 newer so it fieldwise-wins and EBT-403 gains a KBT303 era code."},
    "04_btech_bt_y2_scheme-syllabus_2017-18::12::heat-mass-transfer": {
        "action": "ALLOW",
        "reason": "'&' vs 'and' print variant: draft 'Heat & Mass Transfer' (RCH406, 2017-18 BT scheme) vs the heat-and-mass-transfer row (KME501;RME502A;BME501;NBT-402;... multi-era ME-family subject that BT schemes print as an elective — it already owns the BT-era NBT-402 code); fuzzy 90/overlap 45; the RCH406 print joins as an era code."},
    "04_btech_bt_y2_scheme-syllabus_2017-18::13::genetics-molecular-biology": {
        "action": "ALLOW",
        "reason": "Name-variant class ('&' vs 'and'): draft 'Genetics & Molecular Biology' (RBT401, 2017-18) vs the genetics-and-molecular-biology row (EBT-403, 2009-10) — same elective across era prints; fuzzy 93/overlap 39; RBT401 joins as an era code."},
    "05_btech_bt_y2_syllabus_2014-15::07::genetics-molecular-biology": {
        "action": "ALLOW",
        "reason": "Name-variant class ('&' vs 'and'): draft 'Genetics & Molecular Biology' (NBT-404, 2014-15) vs the genetics-and-molecular-biology row (EBT-403, 2009-10) — same elective, NBT era print; fuzzy 93/overlap 38; NBT-404 joins as an era code."},
    "06_btech_bt_y3_syllabus_2020-21::10::molecular-modeling-drug-design": {
        "action": "ALLOW",
        "reason": "Same subject, 'Modeling' vs 'Modeling and' print variant: draft 'Molecular Modeling & Drug Design' (KBT057, 2020-21) vs the molecular-modeling-and-drug-design row (EBT-041;NBT-013, 2009-10); fuzzy 94/overlap 118 — huge shared distinctive vocabulary (molecular mechanics/dynamics, QSAR, docking canon); 2020-21 newer so it fieldwise-wins; KBT057 joins as an era code."},
    "07_btech_bt_y3_syllabus_2024-25::07::biofuel-alcohol-technology": {
        "action": "ALLOW",
        "reason": "Singular/plural print variant: draft 'Biofuel & Alcohol Technology' (BBT054, 2024-25) vs the biofuels-alcohol-technology row (EBT-032;NBT-023, 2009-10 'Biofuels & Alcohol Technology'); fuzzy 98/overlap 61; BBT054 joins as the newest era code."},
    "07_btech_bt_y3_syllabus_2024-25::10::molecular-modeling-drug-design": {
        "action": "ALLOW",
        "reason": "Same subject, 'Modeling' vs 'Modeling and' print variant: draft 'Molecular Modeling & Drug Design' (BBT057, 2024-25) vs the molecular-modeling-and-drug-design row (EBT-041;NBT-013); fuzzy 94/overlap 118; BBT057 joins as the newest era code (fieldwise-wins per RULES §3)."},
    "08_btech_bt_y4_syllabus-cbcs_2019-20::01::bioseperation-down-stream-processing": {
        "action": "ALLOW",
        "reason": "Print-variant class: draft 'Bioseperation & Down Stream Processing' (RBT702, 2019-20) vs the bioseperation-down-stream-process row (NBT701, 2016-17 'Bioseperation & Down Stream Process' — trailing 'ing' print variance, the row keeps its establishing print verbatim); fuzzy 96/overlap 134; RBT702 joins as an era code."},
    "08_btech_bt_y4_syllabus-cbcs_2019-20::02::genomics-and-proteomics": {
        "action": "ALLOW",
        "reason": "'and' vs '&' print variant: draft 'Genomics and Proteomics' (RBT701, 2019-20) vs the genomics-proteomics row (EBT-062, 2009-10 'Genomics & Proteomics'); fuzzy 90/overlap 54; RBT701 joins as an era code."},
    "08_btech_bt_y4_syllabus-cbcs_2019-20::06::biosafety-bioethics-ipr-patents": {
        "action": "ALLOW",
        "reason": "Token-order/comma print variant: draft 'Biosafety, Bioethics, IPR & Patents' (RBT703, 2019-20) vs the bioethics-biosafety-ipr row (EBT-702;NBT702, 2009-10 'Bioethics, Biosafety & IPR') — the same biosafety/bioethics/IPR elective canon across era prints (B11 recorded the same class for the 2016-17 NBT702 print); fuzzy 85/overlap 169; RBT703 joins as an era code."},
    "09_btech_bt_y4_syllabus_2021-22::01::bioseparation-down-stream-processing": {
        "action": "ALLOW",
        "reason": "Spelling-variant class: draft 'Bioseparation & Downstream Processing' (KBT071, 2021-22) vs the bioseperation-down-stream-process row (NBT701, 2016-17 — the row keeps the establishing doc's printed misspelling 'Bioseperation...Down Stream' verbatim per RULES §6); fuzzy 93/overlap 133; KBT071 joins as an era code."},
    "09_btech_bt_y4_syllabus_2021-22::04::biosafety-bioethics-ipr-patents": {
        "action": "ALLOW",
        "reason": "Token-order/comma print variant: draft 'Biosafety, Bioethics, IPR & Patents' (KBT074, 2021-22) vs the bioethics-biosafety-ipr row (EBT-702;NBT702) — same elective canon (B11 recorded class); fuzzy 85/overlap 169; KBT074 joins as an era code."},
    "10_btech_bt_y4_syllabus_2025-26::02::bioseperation-down-stream-processing": {
        "action": "ALLOW",
        "reason": "Print-variant class: draft 'Bioseperation & Down Stream Processing' (BBT702, 2025-26) vs the bioseperation-down-stream-process row (NBT701, 2016-17); fuzzy 96/overlap 132; BBT702 joins as the newest era code."},
    "08_btech_bt_y4_syllabus-cbcs_2019-20::16::tissue-engineering-nptel": {
        "action": "FORCE_APPEND",
        "reason": "Different subject (B06 recorded wrong-subject fuzzy class): draft 'Tissue Engineering (NPTEL)' (RBT082) is the BT y4 CBCS Departmental Elective-V NPTEL web-course slot whose content is the NPTEL online course (raster p.18-19, transcribed); the fuzzy target 'tissue-engineering' (EBM-032;RBM082, branch Biomedical Engineering, 2011-12 detailed print) is the BME-branch university-taught elective — different printed codes, different course context, overlap only 27. RULES §11: never merge two different subjects; APPEND as its own row."},
    "08_btech_bt_y4_syllabus-cbcs_2019-20::21::industrial-biotechnology-nptel": {
        "action": "FORCE_APPEND",
        "reason": "Different subject (same recorded class): draft 'Industrial Biotechnology (NPTEL)' (RBT087) is the BT y4 CBCS Departmental Elective-VI NPTEL web-course slot (raster p.24, transcribed); the fuzzy target 'industrial-biotechnology' (NBT053, 2016-17 AKTU-taught elective with its own unit syllabus) is a different subject instance — different printed codes and course context, overlap 17. RULES §11: APPEND as its own row."},
    "09_btech_bt_y4_syllabus_2021-22::07::biostatistics-design-of-experiments": {
        "action": "FORCE_APPEND",
        "reason": "Different subject (same recorded NPTEL class as 08::16/08::21): draft 'Biostatistics & design of experiments' (KBT073, 2021-22 AKTU-taught DE with verbatim unit syllabus) fuzzy-hit the biostatistics-design-of-experiments-nptel row appended earlier in THIS commit (RBT085 NPTEL web-course slot, raster p.22; fuzzy 92 but overlap only 13 — the shared 'biostatistics/design/experiments' tokens carry the score, the unit canons are unrelated: AKTU DE units vs NPTEL course-plan weeks). RULES §11: never merge two different subjects; the dry-run ladder (no same-commit appends visible) had this draft as a plain Tier-3 APPEND — FORCE_APPEND restores that semantics."},
    "10_btech_bt_y4_syllabus_2025-26::12::open-elective-iv": {
        "action": "RETARGET", "target": "open-elective-iv",
        "reason": "Slot-print convergence across sessions (B07 recorded 'same printed slot, two semester/session prints converge on one row' class): draft 'Open Elective-IV' (BBT-era 2025-26 scheme row, code cell prints the BOEM** pool wildcard) — the ladder-time TIE (open-elective-ii;open-elective-iii) is an artifact of BOEM** being a pool wildcard printed on several OE slot rows (G2-exempt: no digits, not a specific code). 10::11 'Open Elective-III' already converged via the recorded name-transfer onto open-elective-iii (appended from doc09's sem-VIII print); the 'Open Elective-IV' name-match row open-elective-iv (appended from doc09) is the deterministic same-name target; RETARGET pins it there and the BOEM** pool print joins its all_codes."},
}

# ---------------- gates ----------------

def gate_g1(header):
    return None if header == REF_HEADER else "header mismatch"


def exact_code(tok):
    return bool(re.fullmatch(r"[A-Z]{2,4}\d{3}[A-Z]?", tok))


def gate_g2(rows):
    """Ownership = primary_code + all_codes (identity claims), scoped PER COURSE
    (RULES §1b, B3 evidence): AKTU re-uses code families across courses —
    BVE301 'Universal Human Values' is printed in BOTH the BTech 2nd-yr common
    scheme and the BCA y2 2025-26 scheme; course boundaries are real, so the
    same printed code may be owned by one row PER COURSE. Within a course the
    code is still owned by EXACTLY ONE row. code_history_all remains a
    NARRATIVE field (history mentions are not ownership claims)."""
    owner = {}
    dups = []
    for r in rows:
        toks = set()
        for c in (r.get("primary_code", "") or "").split(";"):
            c = norm_code(c)
            if exact_code(c):
                toks.add(c)
        for c in (r.get("all_codes", "") or "").split(";"):
            c = norm_code(c)
            if exact_code(c):
                toks.add(c)
        ck = canon_course(r.get("course_name", ""))
        for t in toks:
            key = (ck, t)
            if key in owner and owner[key] != r["subject_id"]:
                dups.append(f"{t} [{ck}]: {owner[key]} AND {r['subject_id']}")
            owner[key] = r["subject_id"]
    return (None, len({t for _, t in owner})) if not dups else (f"code owned by 2 rows: {'; '.join(dups[:6])}", len({t for _, t in owner}))


def gate_g3(rows):
    ids, names = set(), set()
    probs = []
    for r in rows:
        sid = r.get("subject_id", "")
        if sid in ids:
            probs.append(f"dup subject_id {sid}")
        ids.add(sid)
        if r.get("row_kind") == "subject":
            cc = r.get("course_name", "")
            if cc not in CANON_COURSES:  # §1b: canonical course names only
                probs.append(f"{sid}: non-canon course_name {cc!r}")
            key = (norm_name(r.get("subject_name", "")), cc)
            if key in names:
                probs.append(f"dup (name,course) {key}")
            names.add(key)
            pc = norm_code(r.get("primary_code", ""))
            own = {norm_code(c) for c in (r.get("all_codes", "") or "").split(";") if c}
            if pc and pc not in own:
                probs.append(f"{sid}: primary_code {pc} not in all_codes")
    return None if not probs else "; ".join(probs[:6])


def gate_g6(rows, touched_ids, parsed_dir, ocr_rows=frozenset()):
    probs = []
    checks = 0
    by_sha = {}
    for j in glob.glob(os.path.join(parsed_dir, "*.json")):
        if j.endswith(".fulltext.json") or os.path.basename(j) == "verify_report.json":
            continue
        rec = json.load(open(j))
        if not isinstance(rec, dict) or "pages" not in rec:
            continue
        by_sha[rec.get("sha16", "")] = "\n".join(p["text"] for p in rec["pages"])
    # B10 remedy (evidence-recorded): workspace resets wipe per-batch parsed
    # dirs, so a cited sha16 whose text was verified by an EARLIER run (e.g.
    # B09's ACT/AI-ML/AU docs cited by rows this batch only corroborates) may
    # have NO local parsed record. RULES §1c makes the GitHub repo the durable
    # record — the corpus PDFs live in work/repo_asleep/PDFs/. Resolve such
    # citations by hashing the repo PDFs and extracting the text layer on
    # demand, so the spot-check verifies against the ACTUAL cited document
    # instead of failing on local parsed-dir unavailability. Fabricated
    # provenance still fails (no corpus doc would contain the text).
    corpus_index = None

    def corpus_text(sha):
        nonlocal corpus_index
        if corpus_index is None:
            import hashlib as _h
            corpus_index = {}
            root = "/home/z/my-project/work/repo_asleep/PDFs"
            paths = []
            for dirpath, _dirs, files in os.walk(root):
                for fn in files:
                    if fn.lower().endswith(".pdf"):
                        paths.append(os.path.join(dirpath, fn))
            for path in paths:
                try:
                    h = _h.md5()
                    with open(path, "rb") as f:
                        for chunk in iter(lambda: f.read(1 << 20), b""):
                            h.update(chunk)
                    corpus_index.setdefault(h.hexdigest()[:16], path)
                except Exception:
                    continue
        path = corpus_index.get(sha)
        if not path:
            return None
        try:
            import fitz
            doc = fitz.open(path)
            txt = "\n".join(p.get_text() for p in doc)
            doc.close()
            return txt
        except Exception:
            return None

    needed = set()
    for r in rows:
        if r.get("subject_id") in touched_ids:
            for s in re.findall(r"#([0-9a-f]{16})", r.get("source_syllabus", "")):
                if s not in by_sha:
                    needed.add(s)
    corpus_cache = {}
    for s in sorted(needed):
        corpus_cache[s] = corpus_text(s)
        if corpus_cache[s] is not None:
            by_sha.setdefault(s, corpus_cache[s])
    for r in rows:
        if r.get("subject_id") not in touched_ids:
            continue
        if not r.get("source_syllabus", "") or not r.get("source_scheme_line", ""):
            probs.append(f"{r['subject_id']}: missing provenance")
            continue
        u1 = norm_al(r.get("unit1_text", ""))[:40]
        if u1 and len(u1) >= 20:
            # B10 remedy (evidence-recorded): rows whose unit text is
            # OCR-recovered from scanned pages with EMPTY text layer (verifier
            # v12 flag unit_ocr_recovered_no_text_layer, page-citing quirk,
            # page-image spot-checks confirm faithful transcription per RULES
            # §6) — text-layer containment is structurally impossible. The
            # spot-check is skipped with a recorded WARN; fabricated
            # provenance of NON-flagged rows still fails.
            if r["subject_id"] in ocr_rows:
                checks += 1
                print(f"G6|OCR_SKIP|{r['subject_id']} (unit text from scanned pages with empty "
                      f"text layer; unit_ocr_recovered_no_text_layer evidence on the "
                      f"contributing draft subject — page-image verified)")
                continue
            # B2 remedy: source_syllabus is a CITATION CHAIN (multiple docs
            # corroborate a row across sessions; apply_update appends per
            # contributing draft). re.search picked the FIRST resolvable 16-hex
            # citation, which can be an older doc that contributed no text
            # (evidence: discrete-structures row cited CSAI-2021-22 before the
            # CSE_v3-2023-24 doc that actually supplied unit1 — probe-verified
            # contained there). The spot check passes if unit1 is provable in
            # ANY cited, currently-resolvable doc; fabricated provenance still
            # fails (no cited doc would contain the text).
            shas = re.findall(r"#([0-9a-f]{16})", r.get("source_syllabus", ""))
            resolvable = [by_sha[s] for s in shas if s in by_sha]
            if resolvable:
                checks += 1
                ok = False
                for full_txt in resolvable:
                    ok = u1 in norm_al(full_txt)
                    if not ok:
                        # junction-tolerant fallback 1: strip standalone digit furniture lines
                        ok = u1 in norm_al(re.sub(r"(?m)^\s*\d{1,4}\s*$", "", full_txt))
                    if not ok:
                        # B2 fallback 2 (evidence: cyber-security-workshop row's
                        # legacy unit1 vs the surviving copy printing the same
                        # content as a numbered experiment list — '1. ' markers
                        # at line starts interleave the titles): strip line-start
                        # list markers, haystack-side only, needle untouched.
                        ok = u1 in norm_al(re.sub(r"(?m)^\s*\d{1,2}\.\s+", "", full_txt))
                    if ok:
                        break
                if not ok:
                    probs.append(f"{r['subject_id']}: unit1 containment FAIL vs cited source "
                                 f"(u1[:60]={norm_al(r.get('unit1_text',''))[:60]}; "
                                 f"resolvable={[s for s in shas if s in by_sha]})")
    return (None, checks) if not probs else ("; ".join(probs[:6]), checks)


def norm_al(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


# ---------------- main ----------------

def run(mode, drafts_dir):
    rows = list(csv.DictReader(open(CSV_PATH)))
    header = list(rows[0].keys()) if rows else []
    q = json.load(open(QUEUE))
    entries = {e["rel"]: e for e in q["entries"]}
    plans, flags = [], []
    crossref_by_key = {}   # key -> crossref note text (§1b)
    ocr_rows = set()       # rows whose unit text is OCR-recovered from scanned
                           # pages with EMPTY text layer (verifier v12 flag
                           # unit_ocr_recovered_no_text_layer + page-citing
                           # quirk evidence) — G6 text-layer containment is
                           # structurally impossible for them (B10 remedy)
    reassignments = []     # recorded code ownership transfers (CODE-REASSIGNED)
    touched = {}          # subject_id -> row dict (updated in place for commit)
    appends = []
    parsed_dir = f"{BASE}/parsed"

    for dp in sorted(glob.glob(os.path.join(drafts_dir, "*.draft.json"))):
        d = json.load(open(dp))
        stem = d.get("stem", os.path.basename(dp)[:-11])
        e = entries.get(d.get("pdf_rel", ""), {})
        ev = {"file": os.path.basename(e.get("file", d.get("pdf_rel", "unknown.pdf"))),
              "sha16": e.get("sha16", d.get("sha16", "")), "locator": d.get("locator", "pp.as-drafted")}
        dmeta = {"session": d.get("session", ""), "course": canon_course(d.get("course", "BTech"))}
        doc_short = ev["file"]
        pool_row = next((r for r in rows if r.get("choice_group_id") == "CG-BOE-2YR"), None)
        maths4 = next((r for r in rows if r.get("subject_id", "").startswith("mathematics-iv")), None)
        for idx, dsub in enumerate(d.get("subjects", [])):
            key = f"{stem}::{idx:02d}::{slug(dsub.get('name', ''))}"
            # §1b defense: printed codes override mislabeled draft course meta
            # (root cause of the 2026-10-28 18:30 BCA→BTech corruption).
            # course_eff is PER-SUBJECT: never mutate the shared dmeta (a leak
            # would corrupt every later subject's course and ladder).
            course_eff = dmeta["course"]
            inferred = course_from_codes(dsub.get("codes", []))
            if len(inferred) == 1 and next(iter(inferred)) != course_eff:
                flags.append((key, "COURSE-META-FROM-CODES",
                              f"draft course {course_eff} contradicts printed codes; using {next(iter(inferred))}"))
                course_eff = next(iter(inferred))
            tier, targets, info = ladder(dsub, rows, course_eff, dmeta["session"])
            # per-key Tier-2 adjudication (TIER2_OVERRIDES, evidence-recorded):
            # applied BEFORE the op decision so the plan reflects the verdict.
            # B7 remedy: RETARGET overrides also apply at tier 3 (no-match
            # appends) — evidence: 'Irrigation & Drainage Engg.' (RAG501) and
            # 'Soil & Water Conservation Engineering Lab' (RAG454) fell below
            # the token-overlap threshold only because of '&'/'Engg.' print
            # variance and splintered era-family rows; RETARGET at tier 3
            # converts the append into an UPDATE on the canonical era row.
            if TIER2_OVERRIDES.get(key) and (tier == 2 or TIER2_OVERRIDES[key]["action"] == "RETARGET"):
                ov = TIER2_OVERRIDES[key]
                if ov["action"] == "FORCE_APPEND":
                    tier, targets = 3, []
                elif ov["action"] == "RETARGET":
                    rt = next((r for r in rows if r.get("subject_id") == ov.get("target")), None)
                    if rt is not None:
                        targets = [rt]
                        tier = 2
                info = info + " | TIER2 override " + ov["action"] + ": " + ov["reason"][:160]
                flags.append((key, "TIER2-OVERRIDE", ov["action"] + ": " + ov["reason"]))
            if info.startswith("code-reassigned "):
                moved = info.split(" ")[1].split(",")
                flags.append((key, "CODE-REASSIGNED-ACROSS-SESSIONS", info))
                reassignments.append({"codes": moved,
                                      "to_row": targets[0]["subject_id"] if targets else slug(dsub.get("name", "")),
                                      "detail": info, "draft_session": dmeta["session"]})
            dflags_l = [str(f).lower() for f in (dsub.get("flags") or [])]
            alt_pair = any("alternative_pair" in f for f in dflags_l)
            if tier == 0 and len(targets) > 1 and alt_pair:
                # alternative-slot print naming subjects that exist as rows; each
                # target owns one of the printed codes - a slot is not a subject
                flags.append((key, "ALTERNATIVE-PAIR-SLOT", "scheme slot print; both members own rows: " + ";".join(r["subject_id"] for r in targets)))
                plans.append({"key": key, "name": dsub.get("name"), "codes": dsub.get("codes"),
                              "tier": tier, "info": info, "op": "SKIP", "target": None})
                if mode == "commit":
                    pass  # SKIP_SLOT_PRINT: slot stays in non_subject_rows; members already own rows
                continue
            if tier in (0, 1, 2) and len(targets) == 1:
                op = ("UPDATE", targets[0])
                if tier == 2:
                    flags.append((key, f"TIER2 {info}", "review fuzzy match"))
                if any("unit_ocr_recovered_no_text_layer" in str(f) for f in (dsub.get("flags") or [])):
                    ocr_rows.add(op[1]["subject_id"])
            elif tier in (0, 1, 2):
                flags.append((key, f"TIE {info}", "multiple candidate rows"))
                op = ("TIE", targets)
            else:
                if "history narrative mentions" in info:
                    flags.append((key, "HISTORY-ONLY-CODE-MENTION", info))
                # §1b: cross-course collision detection (owner directive 2026-10-28)
                xhits = cross_course_hits(dsub, rows, course_eff)
                if xhits:
                    flags.append((key, "CROSS-COURSE-KEEP-SEPARATE", ";".join(xhits)))
                    crossref_by_key[key] = "same name/code in other course(s): " + ", ".join(xhits)
                # Tier 3 APPEND with deterministic scope/policy rules
                codes = [norm_code(c) for c in dsub.get("codes", [])]
                if pool_row is not None and any(c.startswith("BOE3") or c.startswith("BOE4") for c in codes):
                    flags.append((key, "BOE2YR-CHOICE-GROUP", "link choice group"))
                    flags.append((key, "SCOPE-FROM-POOL", "branch scope"))
                    policy = ("CG-BOE-2YR", pool_row.get("choice_group_policy", ""))
                    scope_row = pool_row
                elif maths4 is not None and norm_name(dsub.get("name", "")).startswith("mathematics"):
                    flags.append((key, "SCOPE-FROM-MATHS-IV", "branch scope"))
                    policy = ("", "")
                    scope_row = maths4
                else:
                    policy = ("", "")
                    scope_row = None
                    if ev.get("sha16") in DOC_SCOPE:
                        flags.append((key, "SCOPE-FROM-DOC", DOC_SCOPE[ev["sha16"]]["reason"]))
                op = ("APPEND", (scope_row, policy))
            if op[0] == "UPDATE":
                tgt = op[1]["subject_id"]
            elif op[0] == "TIE":
                tgt = ";".join(r["subject_id"] for r in op[1])
            else:
                tgt = None
            plans.append({"key": key, "name": dsub.get("name"), "codes": dsub.get("codes"),
                          "tier": tier, "info": info, "op": op[0], "target": tgt})

            if mode == "commit":
                if op[0] == "UPDATE":
                    row = touched.get(op[1]["subject_id"]) or op[1]
                    touched[row["subject_id"]] = row
                    apply_update(row, dsub, dmeta, doc_short, ev)
                elif op[0] == "APPEND":
                    scope_row, policy = op[1]
                    if scope_row is None and ev.get("sha16") in DOC_SCOPE:
                        scope_row = dict(DOC_SCOPE[ev["sha16"]])
                    dmeta_eff = dict(dmeta)
                    dmeta_eff["course"] = course_eff  # per-subject §1b course
                    new = build_append(dsub, dmeta_eff, ev, scope_row, policy)
                    # §1b: subject_id is globally unique (G3) — the bare slug may
                    # belong to another course's row (BTech 'data-structure');
                    # suffix the course, then the session, deterministically.
                    taken = {r["subject_id"] for r in rows}
                    sid = new["subject_id"]
                    if sid in taken:
                        cand = f"{sid}-{course_eff.lower()}"
                        if cand in taken:
                            cand = f"{cand}-{dmeta['session']}"
                        new["subject_id"] = cand
                        new["notes"] = (new["notes"] + " | " if new.get("notes") else "") + \
                            f"subject_id '{sid}' is owned by another course's row; id suffixed to '{cand}' for global uniqueness (course boundaries are real, RULES §1b)"
                    if key in crossref_by_key:  # §1b cross-reference note
                        xr = ("Course-boundary crossref (RULES §1b, owner directive 2026-10-28): "
                              + crossref_by_key[key] + " — kept separate; course boundaries are real.")
                        new["notes"] = (new["notes"] + " | " if new["notes"] else "") + xr
                    appends.append(new)
                    rows.append(new)
                    touched[new["subject_id"]] = new
                    if any("unit_ocr_recovered_no_text_layer" in str(f) for f in (dsub.get("flags") or [])):
                        ocr_rows.add(new["subject_id"])
                elif op[0] == "SKIP":
                    pass

    # deterministic post-steps
    if mode == "commit" and appends:
        pool_row = next((r for r in rows if r.get("choice_group_id") == "CG-BOE-2YR"), None)
        if pool_row is not None and any(r["all_codes"].startswith("BOE") for r in appends):
            members = "; ".join(f"{r['subject_name']} ({r['all_codes'].replace(';', '/')})" for r in appends if r["all_codes"].startswith("BOE"))
            add = f"Members NAMED per released Open-Elective-BTech-2nd-year-2023 doc: {members}"
            if add.split(':')[0] not in (pool_row.get("notes") or ""):
                pool_row["notes"] = (pool_row.get("notes", "") + " | " + add).strip(" |")
                pool_row["change_note_vs_previous"] = (pool_row.get("change_note_vs_previous", "") + "; " if pool_row.get("change_note_vs_previous") else "") + "Members named from released companion doc (CG-BOE-2YR populated with 14 real subject rows)"
            # supersede stale quarantine wording in the group policy (brain clause:
            # determine-then-fix; the superseded print stays in change_note history)
            stale = "The individual member subjects are NOT named in any authorized document"
            if stale in (pool_row.get("choice_group_policy", "") or ""):
                old_policy = pool_row["choice_group_policy"]
                head = old_policy.split("The individual member subjects")[0].rstrip(" ")
                pool_row["choice_group_policy"] = (head + " The 14 member subjects are NAMED in the released companion doc "
                    "Open-Elective-BTech-2nd-year-2023-08092023.pdf p.1 (owner release recorded in the project charter; "
                    "the earlier companion quarantine is superseded - prior policy text preserved in change_note_vs_previous) "
                    "and are carried as 14 real subject rows sharing this group.")
                pool_row["change_note_vs_previous"] += " | policy superseded (was: " + old_policy + ")"
            # provenance backfill (per POOL_MEMBERS_NAMED decision): establishing scheme lines + released member table
            if not pool_row.get("source_syllabus", ""):
                pool_row["source_syllabus"] = ("B.Tech_2nd_Yr_CSE_v3.pdf#b5579aefa7a2 pp.2,3 SN-1 (BOE3**/BOE4** pool slots)"
                                               "; Open-Elective-BTech-2nd-year-2023-08092023.pdf#e18a3256f09b7f6e p.1 (member/eligibility table)")
            if not pool_row.get("source_scheme_line", ""):
                pool_row["source_scheme_line"] = ("B.Tech_2nd_Yr_CSE_v3.pdf#b5579aefa7a2 pp.2,3 SN-1 (Science Based Open Elective slot, "
                                                  "subject-codes cell prints the BOE3**/BOE4** pool) ; member/eligibility table: "
                                                  "Open-Elective-BTech-2nd-year-2023-08092023.pdf#e18a3256f09b7f6e p.1")
            if not pool_row.get("source_history", ""):
                pool_row["source_history"] = pool_row["source_syllabus"]
            touched.setdefault(pool_row["subject_id"], pool_row)

    flagnames = sorted({f[1].split(" ")[0] for f in flags})
    unresolved = [f for f in flags if f[1].split(" ")[0] not in RESOLVE_APPEND]

    # deterministic post-step: execute recorded code-ownership transfers BEFORE
    # gates (the transient all_codes dup is resolved here; G2 sees final state)
    if mode == "commit":
        by_id = {}
        for r in rows:
            by_id.setdefault(r["subject_id"], r)
        for ra in reassignments:
            to_row = by_id.get(ra["to_row"])
            if not to_row:
                continue
            for code in [norm_code(c) for c in ra["codes"] if norm_code(c)]:
                # strip the moved code from every OTHER same-course row that
                # still claims it in all_codes (narrative history retained)
                for r in rows:
                    if r.get("row_kind") != "subject" or r is to_row:
                        continue
                    toks = [c.strip() for c in (r.get("all_codes", "") or "").split(";") if c.strip()]
                    if code in {norm_code(c) for c in toks}:
                        keep = [c for c in toks if norm_code(c) != code]
                        r["all_codes"] = ";".join(keep)
                        if r.get("primary_code", "").strip() == code or norm_code(r.get("primary_code", "")) == code:
                            # primary follows the newest-era print (status=latest row model)
                            alt = [c for c in keep if norm_code(c)]
                            # B08 remedy: when the transferred code was the row's ONLY
                            # ownership token, the row becomes a codeless identity row
                            # (2015-16 sem-6 prints reused verbatim by the 2016-17 y4
                            # document) — G3 skips empty primary; notes carry
                            # needs_review for the owner.
                            r["primary_code"] = alt[-1] if alt else ""
                        seg = (f"; {code} re-assigned by AKTU to {to_row['subject_name']} per the "
                               f"{ra['draft_session']} scheme/syllabus print — narrative mention retained "
                               f"(code-reassigned across sessions; owner directive 2026-10-28 §1b era model)")
                        r["code_history_all"] = (r.get("code_history_all", "") or "") + seg
                        r["change_note_vs_previous"] = (r.get("change_note_vs_previous", "") + "; " if r.get("change_note_vs_previous", "") else "") + \
                            f"{code} ownership transferred to {ra['to_row']} per newest printed scheme/syllabus evidence (recorded B3 remedy)"
                        touched.setdefault(r["subject_id"], r)
                if code not in {norm_code(c) for c in (to_row.get("all_codes", "") or "").split(";")}:
                    to_row["all_codes"] = ((to_row.get("all_codes", "") + ";") if to_row.get("all_codes", "") else "") + code
                to_row["change_note_vs_previous"] = (to_row.get("change_note_vs_previous", "") + "; " if to_row.get("change_note_vs_previous", "") else "") + \
                    f"{code} ownership recorded per the {ra['draft_session']} print ({ra['detail'][:110]})"
                touched.setdefault(to_row["subject_id"], to_row)

    print(f"PLANS|{len(plans)} (UPDATE {sum(1 for p in plans if p['op']=='UPDATE')}, APPEND {sum(1 for p in plans if p['op']=='APPEND')}, TIE {sum(1 for p in plans if p['op']=='TIE')}, SKIP {sum(1 for p in plans if p['op']=='SKIP')})")
    for p in plans:
        print(f"PLAN|{p['key']}|T{p['tier']}|{p['op']}|{p['target'] or p['info']}|{(p['name'] or '')[:48]}")
    print(f"FLAGS|{len(flags)}")
    for f in flags:
        print(f"FLAG|{f[0]}|{f[1]}")
    if unresolved:
        print(f"UNRESOLVED|{len(unresolved)}: " + "; ".join(sorted({u[1].split(' ')[0] for u in unresolved})))
    with open(f"{BASE}/decisions_report.json", "w") as fh:
        json.dump({"plans": plans, "flags": flags}, fh, indent=1, ensure_ascii=False)

    if mode != "commit":
        print("DRYRUN OK (no write)")
        return 0

    if unresolved:
        print("ABORT: unadjudicated flags — add RESOLVE_APPEND entries")
        return 2

    # write rows back preserving order
    out_rows = rows
    # gates
    g1 = gate_g1(list(out_rows[0].keys()))
    g2, ncodes = gate_g2(out_rows)
    g3 = gate_g3(out_rows)
    g6, checks = gate_g6(out_rows, set(touched.keys()), parsed_dir, ocr_rows)
    print(f"G1|{'PASS' if not g1 else 'FAIL ' + g1}")
    print(f"G2|{'PASS' if not g2 else 'FAIL ' + g2}|codes={ncodes}")
    print(f"G3|{'PASS' if not g3 else 'FAIL ' + g3}")
    print(f"G6|{'PASS' if not g6 else 'FAIL ' + g6}|containment_checks={checks}")
    if g1 or g2 or g3 or g6:
        print("ABORT: gate failure")
        return 2

    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    os.makedirs(f"{BASE}/backup", exist_ok=True)
    bkp = f"{BASE}/backup/pre_commit_{ts.replace(':', '').replace('+', 'p')}.csv"
    shutil.copy(CSV_PATH, bkp)
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REF_HEADER, lineterminator="\n")
        w.writeheader()
        for r in out_rows:
            w.writerow({c: r.get(c, "") for c in REF_HEADER})
    json.dump({"ts": ts, "mode": "commit", "updates": sum(1 for p in plans if p["op"] == "UPDATE"),
               "appends": sum(1 for p in plans if p["op"] == "APPEND"),
               "flags": len(flags), "backup": bkp, "codes": ncodes,
               "rows_after": len(out_rows)},
              open(f"{BASE}/last_commit.json", "w"), indent=1)
    print(f"COMMIT OK rows={len(out_rows)} appends={sum(1 for p in plans if p['op']=='APPEND')} backup={bkp}")
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1], sys.argv[2]))
