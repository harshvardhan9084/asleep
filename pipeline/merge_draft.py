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


def ladder(dsub, rows, course):
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
        return 0, t0, "code identity"
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


def gate_g6(rows, touched_ids, parsed_dir):
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
    for r in rows:
        if r.get("subject_id") not in touched_ids:
            continue
        if not r.get("source_syllabus", "") or not r.get("source_scheme_line", ""):
            probs.append(f"{r['subject_id']}: missing provenance")
            continue
        u1 = norm_al(r.get("unit1_text", ""))[:40]
        if u1 and len(u1) >= 20:
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
                    probs.append(f"{r['subject_id']}: unit1 containment FAIL vs cited source")
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
            tier, targets, info = ladder(dsub, rows, course_eff)
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
            if tier == 0 and info.startswith("code-reassigned "):
                moved = info.split(" ")[1].split(",")
                flags.append((key, "CODE-REASSIGNED-ACROSS-SESSIONS", info))
                reassignments.append({"codes": moved, "to_row": targets[0]["subject_id"],
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
                            if alt:
                                r["primary_code"] = alt[-1]
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
    g6, checks = gate_g6(out_rows, set(touched.keys()), parsed_dir)
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
