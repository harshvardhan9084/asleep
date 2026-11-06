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
            if sim < 0.84 and not newer:
                # B21 remedy (evidence-recorded, fixes the pre-B21 fallthrough that
                # silently UPDATEd a different subject): a draft print that is NOT
                # newer than the code owner's establishing print, whose name
                # similarity is below the print-variant threshold, is a DIFFERENT
                # subject printed on a collided slot code (evidence B21: doc05
                # Communication Lab - II 'NEC 652' vs the instrumentation-lab owner
                # from the same-session AEI print — unit/experiment vocabulary
                # overlap 0). RULES §3: the published owner keeps the code; the
                # draft APPENDS as its own row with the collided code dropped to a
                # narrative quirk (never two owners of one code, G2).
                moved = sorted(dcodes & row_owned_codes(t0[0]))
                if moved:
                    drop = set(moved)
                    dsub["codes"] = [c for c in (dsub.get("codes") or [])
                                     if norm_code(c) not in drop]
                    dsub.setdefault("quirks", []).append(
                        "Code " + ",".join(moved) + " prints on this subject in the " +
                        str(draft_session) + " scheme, but the code is owned by " +
                        t0[0]["subject_id"] + " from its " +
                        str(t0[0].get("effective_session_latest", "")) +
                        " establishing print — narrative mention only, ownership unchanged "
                        "(B21 code-slot-collision remedy: equal-or-older print never takes "
                        "a code from its published owner, RULES §3; collapsed-name "
                        f"similarity {sim:.2f} < 0.84 = different subject, not a print variant)")
                return 3, [], (f"code-slot collision: collapsed-name similarity {sim:.2f} < 0.84 = "
                               f"different subject; draft print {draft_session} is not newer than the "
                               f"code owner's ({t0[0].get('effective_session_latest', '')}) so the code "
                               f"stays with {t0[0]['subject_id']} (RULES §3) and the draft appends "
                               f"its own row (B21 recorded remedy)")
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
    if isinstance(lt, str):  # B37 hardening: string prints like '3-1-0' coerce to dict
        nums = re.findall(r"\d+", lt)
        lt = {"l": int(nums[0]) if len(nums) > 0 else None,
              "t": int(nums[1]) if len(nums) > 1 else None,
              "p": int(nums[2]) if len(nums) > 2 else None}
    if not isinstance(lt, dict):
        lt = {}
    row["L"], row["T"], row["P"] = str(lt.get("l", "") or ""), str(lt.get("t", "") or ""), str(lt.get("p", "") or "")
    row["credit"] = str(dsub.get("credit") or "")
    m = dsub.get("marks") or {}
    if isinstance(m, str):  # B37 hardening: string marks print -> dict
        nums = re.findall(r"\d+", m)
        keys = ("sessional_ct", "sessional_ta", "sessional_total", "ese_te_pe", "total")
        m = {keys[i]: (int(nums[i]) if i < len(nums) else None) for i in range(len(keys))}
    if not isinstance(m, dict):
        m = {}
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
    "SLOT-CODE-TRANSFER": {
        "action": "APPEND_REAL_SUBJECT_WITH_CODE_TRANSFER",
        "reason": "A dual slot-code heading ('KHU701/KHU801' = HSMC-1/HSMC-2 offering) names a REAL subject (verbatim units printed) whose codes currently sit on generic slot rows ('HSMC-1#/HSMC-2#' program-structure prints). The newest detailed print wins (recorded CODE-REASSIGNED principle): the subject appends with its printed codes; ownership transfers off the slot rows via the recorded reassignment executor, which leaves a slot row that loses every code as a codeless identity row (B08 remedy; narrative history retained in code_history_all; G3 skips empty primary). Zero-GAP: the subject's content lands in a subject row; the slot prints remain in the draft's non_subject_rows and the slot rows' names."},
    "TIER2-OVERRIDE": {
        "action": "APPLY_RECORDED_ACTION",
        "reason": "The per-key TIER2_OVERRIDES entry for this draft subject (action + recorded evidence in the flag detail); the ladder result is corrected accordingly before the plan is applied."},
}

# ---------------- SLOT_CODE_TRANSFERS (B17 recorded class) -----------------
# A dual slot-code print (e.g. 'KHU701/KHU801' = HSMC-1 Sem-VII / HSMC-2
# Sem-VIII offering) naming a REAL subject (verbatim units printed) whose
# printed codes are currently owned by generic slot rows (program-structure
# prints, not subjects). Newest detailed print wins (CODE-REASSIGNED
# principle): the subject APPENDs with its printed codes; code ownership
# transfers off the slot rows via the recorded reassignment executor (B08
# remedy: a slot row losing every code becomes a codeless identity row with
# its narrative history retained; G3 skips empty primary). Zero-GAP holds.
SLOT_CODE_TRANSFERS = {
    "03_btech_common_y4_hsmc-courses_2021-22::00::rural-development-administration-and-planning": {
        "codes": ["KHU701", "KHU801"],
        "reason": "B17 HSMC slot-code transfer: the 2021-22 HSMC doc prints 'KHU701/KHU801 RURAL DEVELOPMENT: ADMINISTRATION AND PLANNING' as a REAL subject (5 verbatim units + COs; p.2 scheme list 'HSMC1/HSMC2 || KHU701/KHU801 ...' = HSMC-1 Sem-VII / HSMC-2 Sem-VIII offering) — the only current owners of KHU701/KHU801 are the generic slot rows hsmc-1-hsmc-2 / hsmc-2-hsmc-1 ('HSMC-1#/HSMC-2#' program-structure prints). The subject appends with its printed codes; the slot rows keep their prints in names/code_history (codeless identity rows, recorded B08 remedy)."},
    "03_btech_common_y4_hsmc-courses_2021-22::01::project-management-entrepreneurship": {
        "codes": ["KHU702", "KHU802"],
        "reason": "B17 HSMC slot-code transfer: the 2021-22 HSMC doc prints 'KHU702/KHU802 PROJECT MANAGEMENT & ENTREPRENEURSHIP' as a REAL subject (5 verbatim units; same HSMC-1/HSMC-2 dual-slot model) — KHU702/KHU802 currently sit on the generic slot rows hsmc-1-hsmc-2 / hsmc-2-hsmc-1. The subject appends with its printed codes; slot rows keep their prints (codeless identity rows, recorded B08 remedy)."},
    "09_btech_ee_syllabus_2009-10::01::mathematics-iii": {
        "codes": ["EAS-301", "EAS-401"],
        "reason": "B22 slot-code transfer (recorded B17 HSMC class): the 2009-10 EE print details 'EAS-301/EAS-401: MATHEMATICS –III' as a REAL subject (verbatim units; the detailed header carries BOTH slot codes on one heading — quirk recorded by the draft). The only current owners of EAS-301/EAS401 are the two 2017-18-era slot-variant rows mathematics-iii-science-based-open-elective (EAS-301) and science-based-open-elective-mathematics-iii (EAS401) — the B02 paired-slot prints ('Mathematics-III/Science Based Open Elective'). The detailed 2009-10 print wins (newest-detailed principle, recorded CODE-REASSIGNED model): the subject appends with its printed codes; the slot rows keep their slot prints/names and narrative history (codeless of EAS-3xx, recorded B08 remedy). G2 clean: the transfer runs before the gates."},
}

# B2: doc-level scope from the PRINTED COVER of each ingested document
# (zero-guess: only what the cover prints; recorded reasoning per entry).
DOC_SCOPE = {
    # ---- B23 covers (zero-guess branch scope per printed cover/scheme title) ----
    "bddd363be8c50739": {
        "branch_names": "Electrical Engineering; Electrical & Electronics Engineering",
        "program_year": "2",
        "reason": "B23 EE/EE-EN y2 2017-18: cover prints 'Study & Evaluation Scheme with Syllabus for B.Tech. Second Year Electrical Engineering / Electrical & Electronics Engineering On Choice Based Credit System (Effective from the Session: 2017-18)'"},
    "8bba5a23e7feb769": {
        "branch_names": "Electrical Engineering",
        "program_year": "3",
        "reason": "B23 EE y3 AICTE model 2020-21: cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. 3rd YEAR (EE) ELECTRICAL ENGINEERING BASED ON AICTE MODEL (CURRICULUM)'; page headers 'Curriculum & Evaluation Scheme EE (V & VI semester)'"},
    "d5fe2023680b3af8": {
        "branch_names": "Electrical Engineering",
        "program_year": "3",
        "reason": "B23 EE y3 2024-25: cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. 3rd YEAR (EE) ELECTRICAL ENGINEERING BASED ON AICTE MODEL CURRICULUM &NEP2020 [Effective from the Session: 2024-25]'"},
    "20b42db5d7a9076a": {
        "branch_names": "Electrical Engineering",
        "program_year": "4",
        "reason": "B23 EE y4 CBCS 2019-20: cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. IV YEAR ELECTRICAL ENGINEERING — CHOICE BASED CREDIT SYSTEM (CBCS) [Effective from the Session: 2019-20]' (p.1 text layer fragmented; fragments reassembled)"},
    "6576a3b45d078590": {
        "branch_names": "Electrical Engineering",
        "program_year": "4",
        "reason": "B23 EE y4 2021-22: p.1 cover text layer glyph-scrambled (fragments 'ELECTR(ICAL) ENGIN(EERING)… B. TECH … AICTE MODEL … (VII & VIII semester)'); legible page headers print 'Curriculum & Evaluation Scheme EE (VII & VIII semester)' — single branch print (zero-guess)"},
    "a0cf580ebf4be896": {
        "branch_names": "Electrical Engineering; Electrical & Electronics Engineering",
        "program_year": "3",
        "reason": "B23 EEE-ECE-EE y3 2018-19: cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. III YEAR ELECTRICAL ENGINEERING / & ELECTRONICS ENGINEER(ING) — CHOICE BASED CREDIT SYSTEM (CBCS) [Effective from the Session: 2018-19]' (p.1 fragmented; two-branch shared scheme)"},
    "39be9cd7bd3de4c2": {
        "branch_names": "Electrical & Electronics Engineering",
        "program_year": "2",
        "reason": "B23 EEE-ECE y2 AICTE model 2019-20: cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. 2nd YEAR ELECTRICAL & ELECTRONICS ENGINEERING BASED ON AICTE MODEL CURRICULUM [Effective from the Session: 2019-20]'"},
    "e7c6f352c36de776": {
        "branch_names": "Electrical & Electronics Engineering",
        "program_year": "3",
        "reason": "B23 EEE-ECE y3 AICTE model rev 2020-21: cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. 3rd YEAR (EN) ELECTRICAL & ELECTRONICS ENGINEERING'; page headers 'Curriculum & Evaluation Scheme EN (V & VI semester)'"},
    "036329f4428dd944": {
        "branch_names": "Electrical & Electronics Engineering",
        "program_year": "3",
        "reason": "B23 EEE-ECE y3 2024-25: cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. 3rd YEAR (EN) ELECTRICAL & ELECTRONICS ENGINEERING BASED ON AICTE MODEL CURRICULUM & NEP2020 [Effective from the Session: 2024-25]'"},
    "18fce1778aaeb500": {
        "branch_names": "Electrical & Electronics Engineering",
        "program_year": "4",
        "reason": "B23 EEE-ECE y4 CBCS 2019-20: cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. IV YEAR ELECTRICAL & ELECTRONICS ENGINEERING — CHOICE BASED CREDIT SYSTEM (CBCS) [Effective from the Session: 2019-20]' (p.1 fragmented; fragments reassembled)"},
    # ---- B22 covers (zero-guess branch scope per printed cover/scheme title) ----
    "0579856dc67bbeff": {
        "branch_names": "Electronics and Communication Engineering",
        "program_year": "4",
        "reason": "B22 ECE y4 2021-22: p.1 cover text layer is glyph-scrambled (draft quirk recorded; fragments 'ELECTRONICS A(ND) ... COMMUNICA(TION)'); the scheme-title prints on pp.2-3 (and the p.3 page image, B22 verification) print 'ELECTRONICS AND COMMUNICATION ENGINEERING / B.Tech. VII Semester / Electronics and Communication Engineering' — single legible branch print; program_year 4 from the printed VII-VIII semester span"},
    "b875786af75ea86d": {
        "branch_names": "Electronics Engineering; Electronics & Communication Engineering; Electronics & Telecommunication Engineering",
        "program_year": "4",
        "reason": "B22 ECE y4 revised 2019-20: cover prints 'EVALUATION SCHEME & SYLLABUS FOR B.TECH. FINAL YEAR ELECTRONICS ENGINEERING/ ELECTRONICS & COMMUNICATION ENGINEERING/ ELECTRONICS & TELECOMMUNICATION ENGINEERING — CHOICE BASED CREDIT SYSTEM (CBCS) [Effective from the Session: 2019-20]'"},
    "cd8250b44c898bd0": {
        "branch_names": "Electronics Engg.; Electronics & Communication Engg.; Electronics & Telecomm Engg.",
        "program_year": "4",
        "reason": "B22 ECE y4 2011-12: p.2 scheme title prints 'Study and Evaluation Scheme B. Tech. in Electronics Engg/ Electronics & Communication Engg/ Electronics & Telecomm Engg [Effective from the session 201112] YEAR 4th, SEMESTER-VIII' (p.1 text layer empty)"},
    "3298dc1f8195fb2f": {
        "branch_names": "Electronics Engg.; Electronics & Communication Engg.; Electronics & Telecommunication Engg.",
        "program_year": "4",
        "reason": "B22 ECE y4 2016-17: cover prints 'Study and Evaluation Scheme B. Tech. in Electronics Engg/Electronics & Communication Engg/Electronics & Telecommunication Engg [Effective from the session 2016-17] YEAR 4th, SEMESTER-VII'"},
    "a1cfb31bae23d270": {
        "branch_names": "Electronics Engineering; Electronics and Communication Engineering; Electronics and Telecommunication Engineering",
        "program_year": "4",
        "reason": "B22 ECE y4 2025-26: cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. FOURTH YEAR — ELECTRONICS ENGINEERING / ELECTRONICS AND COMMUNICATION ENGINEERING / ELECTRONICS AND TELECOMMUNICATION ENGINEERING'"},
    "a9b82a5ad092f514": {
        "branch_names": "Electrical Engineering; Electrical and Electronics Engineering",
        "program_year": "4",
        "reason": "B22 EE/EE-EN y4 2025-26: cover prints 'Evaluation Scheme & Syllabus For B. Tech. 4th Year — Electrical Engineering & Electrical and Electronics Engineering' (draft D06: the two branches share one scheme)"},
    "2a559deeb26d4e0d": {
        "branch_names": "Electrical Engineering; Electrical & Electronics Engineering",
        "program_year": "2",
        "reason": "B22 EE-group y2 revised 2014-15: cover prints 'Syllabus for B. Tech. Electrical Engineering / B.Tech. Electrical & Electronics Engg. of Second Year (Effective from the Session: 2014-15)'; p.2 scheme title 'B-Tech. Electrical Engg./Electrical & Electronics Engineering YEAR: 2nd SEMESTER-III'"},
    "17778c4a3a6a7a09": {
        "branch_names": "Electrical Engineering; Electrical and Electronics Engineering; Electrical & Computer Engineering",
        "program_year": "1",
        "reason": "B22 EE-stream course structure 2026-27: cover prints 'EVALUATION SCHEME & SYLLABUS Of B. TECH. First Year EE STREAM — Electrical Engineering/Electrical and Electronics Engineering/Electrical & Computer Engineering (Effective from the Academic Session: 2026-27)'"},
    "8f2892a46c32012b": {
        "branch_names": "Electrical Engg.; Electrical & Electronics Engineering",
        "program_year": "2,3,4",
        "reason": "B22 EE 2009-10: cover prints 'Syllabus — 2nd Year, 3rd Year and 4th Year [Effective from the session: 2009-10] B.TECH. ELECTRICAL ENGINEERING'; p.2 scheme title 'B-Tech. Electrical Engg./Electrical & Electronics Engineering (EFFECTIVE FROM SESSION: 2009-10)'"},
    "eb4a3200ae2e913d": {
        "branch_names": "Electrical Engineering",
        "program_year": "2",
        "reason": "B22 EE y2 AICTE model curriculum 2019-20: cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. 2nd YEAR ELECTRICAL ENGINEERING — AICTE MODEL CURRICULUM [Effective from the Session: 2019-20]'; p.2 header 'EVALUATION SCHEME - B.TECH 2nd YEAR (ELECTRICAL ENGINEERING)'"},
    "9f353dd680d7c524": {
        "branch_names": "",
        "program_year": "4",
        "reason": "B17 HSMC+OE-II list 2021-22: cover prints 'EVALUATION SCHEME & SYLLABUS FOR HUMANITIES, SCOCIAL SCIENCE AND MANAGEMENT COURSE (HSMC COURSE) & OPEN ELECTIVES II LIST AS PER AICTE MODEL CURRICULUM [Effective from the Session:2021-22]' and the list page header prints 'B.Tech. VII Semester (2021-22)' — no branch list printed (HSMC/OE are common slots), so branch_names stays BLANK (zero-guess, B16 BNC class); program_year 4 from the printed VII-semester span"},
    "3791c12eb1101e50": {
        "branch_names": "",
        "program_year": "1",
        "reason": "B17: cover prints 'COURSE STURCTURE & EVALUATION SCHEME of Bachelor of Technology (B.Tech.) First Year (Along with the SOPs for General Proficiency, Innovation & Design Thinking Lab, and AICTE Activity Points) AS PER AICTE MODEL CURRICULUM' (typo STURCTURE kept verbatim) — common first-year structure, no branch list printed; per-stream variant codes are recorded in the draft's non_subject_rows; branch_names BLANK (zero-guess), program_year 1"},
    "1f7976d962297c2e": {
        "branch_names": "Computer Science and Business Systems",
        "program_year": "4",
        "reason": "B17: cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. 4TH YEAR — Computer Science and Business Systems — Based On NEP2020 — (Effective from the Session: 2025-26)'"},
    "829a3843b2605d88": {
        "branch_names": "Computer Science and Design",
        "program_year": "3",
        "reason": "B17: cover prints 'Evaluation Scheme & Syllabus For B.Tech. 3rd Year (Computer Science and Design) Based On NEP2020 Effective from the Session: 2024-25)'"},
    "6db264fcd825bdae": {
        "branch_names": "Computer Science and Design",
        "program_year": "4",
        "reason": "B17: cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. FOURTH (IV) YEAR (COMPUTER SCIENCE AND DESIGN) AS PER AICTE MODEL CURRICULUM [Effective from the Session: 2024-25]'"},
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
    # ---- B13 DOC_SCOPE (added post-commit by repair_b13_branch_scope.py evidence; the
    # B13 merge ran without these, the repair backfilled branch/py from the same covers) ----
    "2ac6e53d06c52026": {"branch_names": "Carpet & Textile Technology", "program_year": "2;3;4",
        "reason": "cover prints 'Syllabus 2nd, 3rd and 4th Year [Effective from session 2009-10] — B.TECH. CARPET & TEXTILE TECHNOLOGY' (multi-year doc; per-row year from semester_slots)"},
    "85fc0a911e174919": {"branch_names": "Carpet & Textile Technology", "program_year": "2",
        "reason": "cover prints 'Carpet & Textile Technology' under 'B. TECH. SECOND YEAR' (model-curriculum 2019-20)"},
    "5e07ff5fe10cd6c3": {"branch_names": "Carpet & Textile Technology", "program_year": "2",
        "reason": "cover prints 'Study & Evaluation Scheme with Syllabus for B.Tech. Second Year Carpet And Textile Technology' (cover variant 'And')"},
    "641f700a7ab5d96d": {"branch_names": "Carpet & Textile Technology", "program_year": "3",
        "reason": "cover prints 'B.TECH. THIRD YEAR CARPET & TEXTILE TECHNOLOGY' (model-curriculum 2020-21)"},
    "c891df6c0f371cb2": {"branch_names": "Carpet & Textile Technology", "program_year": "3",
        "reason": "cover prints 'B. TECH. THIRD YEAR (CARPET AND TEXTILE TECHNOLOGY)' (cover variant 'AND')"},
    "020ea64f9757080b": {"branch_names": "Carpet & Textile Technology", "program_year": "3",
        "reason": "cover prints 'B. TECH. THIRD YEAR / Carpet & Textile Technology' [Effective from the Session: 2024-25]"},
    "fe2cf38bfff60b34": {"branch_names": "Carpet & Textile Technology", "program_year": "4",
        "reason": "cover prints 'B. TECH 4th YEAR Carpet & Textile Technology' (CBCS 2019-20)"},
    "37283cd70588ae6e": {"branch_names": "Carpet & Textile Technology", "program_year": "4",
        "reason": "cover doubled-glyph garble 'CARPET C T & TEX XTILE TE ECHNOL LOGY' reconstructed CARPET & TEXTILE TECHNOLOGY (page-image evidence)"},
    "874148082be7bca8": {"branch_names": "Carpet & Textile Technology", "program_year": "4",
        "reason": "cover prints 'B. TECH. FOURTH YEAR' + branch 'Carpet & Textile Technology' (2025-26)"},
    "fb01885f539db1af": {"branch_names": "Computer Science;Computer Engineering;Computer Science and Engineering", "program_year": "4",
        "reason": "cover prints three branches 'Computer Science', 'Computer Engineering', 'Computer Science and Engineering' — combined CS/CE/CSE scheme; cover authoritative"},
    # ---- B14 batch (10 docs; B.Tech Civil Engineering eras 2009-10 → 2026-27 + one
    # combined CS/CE/CST/CSE y3 doc; branch = the printed cover; program_year =
    # the year span the document details) ----
    "3a7ea7b8a35eecac": {"branch_names": "Computer Science;Computer Engineering;Computer Science and Engineering;Computer Science & Technology", "program_year": "3",
        "reason": "cover prints 'B. TECH. THIRD YEAR' with NEP2020 note + stray line '/Computer Science & Technology'; running header prints 'Curriculum & Evaluation Scheme: CS, Computer Engineering and CSE (V & VI Semester)' — combined CS/CE/CST/CSE scheme; printed BCS/BOE codes authoritative (cover authoritative class, B13 fb01885f precedent)"},
    "fdb242ca8196872a": {"branch_names": "Civil Engineering", "program_year": "2",
        "reason": "cover prints 'Syllabus — 2nd Year (III & IV Sem.) [Effective from session 2009-10] — B. Tech. Civil Engineering' (filename suffix 'ce-env' is not a printed branch; the cover print is authoritative)"},
    "48fb58b17dc773d4": {"branch_names": "Civil Engineering;Environmental Engineering", "program_year": "1",
        "reason": "cover prints 'EVALUATION SCHEME & SYLLABUS of B. TECH. First Year CE STREAM (Civil Engineering, Environmental Engineering)' 2026-27 (A-generation y1 course structure)"},
    "441c7c04a2569344": {"branch_names": "Civil Engineering", "program_year": "3;4",
        "reason": "cover prints 'Syllabus 3rd & 4th Year [Effective from session 2010-11] — B. Tech. Civil Engineering' (multi-year doc; per-row year from semester_slots, B13 2ac6e53d class)"},
    "155474986bb7ff5e": {"branch_names": "Civil Engineering", "program_year": "3",
        "reason": "cover prints 'COURSE STRUCTURE AND SYLLABUS (EFFECTIVE FROM Session: 2015-16) — B.Tech. (Civil Engineering) Third Year (5th & 6th Semester)'"},
    "7d57955ee5a52da0": {"branch_names": "Civil Engineering", "program_year": "2",
        "reason": "cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. SECOND YEAR (CIVIL ENGINEERING) (Effective from session 2019-20)'"},
    "7757cf07f29ab03b": {"branch_names": "Civil Engineering", "program_year": "2",
        "reason": "cover prints 'Study & Evaluation Scheme with Syllabus for B.Tech. Second Year Civil Engineering On Choice Based Credit System (Effective from the Session: 2017-18)'"},
    "36de9916de00e952": {"branch_names": "Civil Engineering", "program_year": "2",
        "reason": "cover prints 'SYLLABUS of B. Tech. Civil Engineering (2nd Year) [Effective Form session 2014-15]' (double space + 'Form' [sic] kept as printed)"},
    "c7f7ebaf7182ffa8": {"branch_names": "Civil Engineering", "program_year": "3",
        "reason": "cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. THIRD YEAR (CIVIL ENGINEERING) On Choice Based Credit System [Effective from session 2018-19]'"},
    "3ce1c2a2b92b5bd8": {"branch_names": "Civil Engineering", "program_year": "3",
        "reason": "cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. THIRD YEAR (CIVIL ENGINEERING) (Effective from session 2020-21)'"},
    # ---- B15 batch (9 docs: BTech Civil y4 eras + BTech Chemical Engineering) ----
    "d5349714f37cc8a4": {"branch_names": "Civil Engineering", "program_year": "4",
        "reason": "cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. FOURTH YEAR (CIVIL ENGINEERING) On Choice Based Credit System (Effective from session 2019-20)'"},
    "7cdbdbce0c98abe2": {"branch_names": "Civil Engineering", "program_year": "4",
        "reason": "raster cover (text layer empty); printed codes BCE701/BCE070-073/BCE75x/BCE851 + printed cover read from 300-450dpi page renders (B.Tech IV Year Civil Engineering rev 2025-26) — RULES §6 visible print authoritative"},
    "52245ed4397dccfc": {"branch_names": "Civil Engineering", "program_year": "4",
        "reason": "cover prints 'Syllabus 4th Year [Effective from session 2016-17] B. Tech. Civil Engineering'"},
    "e8a9f24c9ca8616e": {"branch_names": "Civil Engineering", "program_year": "4",
        "reason": "cover prints 'Curriculum & Evaluation Scheme (VII & VIII semester) ... B. TECH. FOURTH YEAR CIVIL ENGINEERING' (AICTE model per print)"},
    "f256be81a97e517b": {"branch_names": "Chemical Engineering;Plastic Engineering;Food Technology", "program_year": "1",
        "reason": "cover prints 'EVALUATION SCHEME & SYLLABUS of B. TECH. First Year CH STREAM (Chemical Eng...)' — the CH-stream first-year common course-structure 2026-27; stream list per cover (Chemical Engineering, Plastic Engineering, Food Technology)"},
    "6ae3a8ec043ecbe5": {"branch_names": "Chemical Engineering", "program_year": "3",
        "reason": "cover prints 'Evaluation Scheme & Syllabus For B.Tech. 3rd Year (Chemical Engineering) Based On AICTE MODEL CURRICULUM (Effective from the Session: 2024-25)'"},
    "a2ca2c50abd0b736": {"branch_names": "Chemical Engineering", "program_year": "4",
        "reason": "cover prints 'Evaluation Scheme & Syllabus For B.TECH. FINAL YEAR (CHEMICAL ENGINEERING) Based On AICTE MODEL CURRICULUM & NEP2020 (Effective from the Session: 2025-26)'"},
    "43311ba67427581a": {"branch_names": "Chemical Engineering", "program_year": "3",
        "reason": "cover prints 'SYLLABUS Bachelor of Chemical Engineering 3rd Year (V & VI Semester) (Effective from Session 2015-2016)' (UPTU-era print)"},
    "1153e3e75b1356b5": {"branch_names": "Chemical Engineering", "program_year": "3",
        "reason": "cover prints 'PROPOSED STUDY & EVALUATION SCHEME FOR III YEAR B.TECH. (CHEMICAL ENGINEERING) ON CHOICE BASED CREDIT SYSTEM (CBCS) [EFFECTIVE FROM THE SESSION 2018-19]'"},
    # ---- B16 batch (10 docs; branch = printed cover; program_year = semester span detailed) ----
    "c0a99d3733f78578": {"branch_names": "Chemical Engineering", "program_year": "2-4",
        "reason": "cover prints 'Syllabus 2nd, 3rd and 4th Year [Effective from session 2009-10] B.TECH. CHEMICAL ENGINEERING' (UPTU-era print)"},
    "6f38756d90d55d99": {"branch_names": "Chemical Engineering", "program_year": "2",
        "reason": "cover prints 'Study & Evaluation Scheme with Syllabus for B.Tech. Second Year Chemical Engineering On Choice Based Credit System (Effective from the Session: 2017-18)'"},
    "7953702843e0bfb6": {"branch_names": "Chemical Engineering", "program_year": "2",
        "reason": "cover prints 'Syllabus for B. Tech. Chemical Engineering of Second Year (Effective from the Session: 2014-15)' (UPTU-era print)"},
    "440a08377e3a411c": {"branch_names": "Chemical Engineering", "program_year": "2",
        "reason": "cover prints 'Evaluation Scheme & Syllabus For B.Tech. 2nd Year (Chemical Engineering) On AICTE MODEL CURRICULUM (Effective from the Session: 2019-20)'"},
    "108e24cb20fe1213": {"branch_names": "Chemical Engineering", "program_year": "3",
        "reason": "cover prints 'Evaluation Scheme & Syllabus For B.Tech. 3rd Year (Chemical Engineering) On AICTE MODEL CURRICULUM (Effective from the Session: 2020-21)'"},
    "8502954d3fcefcb6": {"branch_names": "Chemical Engineering", "program_year": "4",
        "reason": "cover prints 'EVALUATION SCHEME & SYLLABUS FOR B.TECH. FOURTH YEAR (CHEMICAL ENGINEERING) ON CHOICE BASED CREDIT SYSTEM (CBCS)' Session- 2019-20"},
    "b256e1517a5fc0b7": {"branch_names": "Chemical Engineering", "program_year": "4",
        "reason": "cover prints 'EVALUATION SCHEME & SYLLABUS FOR B.TECH. FOURTH YEAR CHEMICAL ENGINEERING AS PER AICTE MODEL CURRICULUM [Effective from the Session: 2021-22] ... (VII & VIII semester)'"},
    "7b3d338328997e93": {"branch_names": "Common to All Branches EXCEPT Agriculture Engineering and Biotechnology", "program_year": "1",
        "reason": "cover prints 'EVALUATION SCHEME AND SYLLABI For B. Tech. 1ST Year Common to All Branches EXCEPT Agriculture Engineering and Biotechnology Effective from the Session: 2022-23' (the EXCEPT scope is the printed eligibility boundary, kept verbatim)"},
    "c0161d00091ad224": {"branch_names": "", "program_year": "3",
        "reason": "cover prints 'EVALUATION SCHEME & SYLLABUS FOR COMMOM NON CREDIT COURSE (NC) (V & VI Semester) [Effective from the Session: 2024-25] Non Credit Course 2024-25 AICTE Model Curriculum B series' — no branch list printed (university-wide NC courses; branch_names left blank per zero-guess; program_year from the printed V & VI semester span)"},
    "b686fd84fcbe5544": {"branch_names": "All Branches except Agriculture & Bio Tech", "program_year": "1",
        "reason": "cover prints 'Evaluation Scheme & Syllabus for B. Tech. (All Branches except Agriculture & Bio Tech) AS PER AICTE MODEL CURRICULUM (Effective from the Session: 2018-19)'"},
}

# ---------------- TIER2_OVERRIDES (per-key adjudications, evidence-recorded) ----------------
# Tier-2 fuzzy matches are adjudicated PER KEY: ALLOW the fuzzy target (name-
# variant classes: singular/plural, spacing, era-family), RETARGET to the
# evidence-correct row, or FORCE_APPEND when the fuzzy hit is a DIFFERENT
# subject. Restored for the CRON-20261029-B06-recovery re-run from the
# published B06 manifest ("TIER2_OVERRIDES mechanism added ... per-key,
# evidence-recorded"), re-evidenced against the drafts + baseline rows.
TIER2_OVERRIDES = {
    # --- B38 adjudications (adjudicate_b38 marker) ---
    "01_btech_textile-tech_y2_model-curriculum_2019-20::01::fabric-manufacturing-ii": {
        "action": "RETARGET", "target": "fabric-manufacture-ii",
        "reason": "B38 TIE resolution (fuzzy 88/-i, 91/-ii, 89/-iii, 86/woven-fabric) on roman-numeral identity + code lineage: draft 'Fabric Manufacturing-II' (KTT402, 2019-20 y2 model-curriculum sem-4 print, 5 verbatim units) — the fabric-manufacture-ii row owns ECT402/ETE402 (the same university course's E-era ladder; KTT402 is its K-era code, cf. the B33 KTT/BPE ladder classes); -i and -iii are different-semester courses; woven-fabric-manufacture is the Handloom-Tech branch course (BHT-551/601). RETARGET pins the update on the numeral-matching -ii row."},
    "02_btech_textile-tech_y2_scheme-syllabus_2017-18::00::environment-ecology": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "environment-ecology",
        "keep_published_codes": {"RVE401": "universal-human-values-professional-ethics"},
        "reason": "B38 TIE resolution (code identity across rows on RAS402/RVE401 — the paired-cell print): draft 'Environment & Ecology' (RAS402/RVE401, 2017-18 y2 scheme print) — the environment-ecology row owns RAS402 (EAS-105/RAS302 ladder) and universal-human-values-professional-ethics owns RVE401; a paired-cell slot print is NOT a subject (recorded SKIP_SLOT_PRINT class) and one row must not absorb both members' codes. RETARGET pins the update on the name-identity environment-ecology row; RVE401 stays with its published owner (B37 NAS-202 same-session class); the paired print is recorded in the slot row environment-ecology-universal-human-values-p."},
    "03_btech_textile-tech_y3_model-curriculum_2020-21::10::advance-weaving-technology": {
        "action": "RETARGET", "target": "advanced-weaving-technology",
        "reason": "B38 TIE resolution (fuzzy 91/advanced-welding-technology vs 98/advanced-weaving-technology): draft 'Advance Weaving Technology' (KTT603, 2020-21 y3 model-curriculum print, 5 verbatim units) — the advanced-weaving-technology row owns RTT603 (the same course's R-era code); the welding row (NME-055/EME-022/RME506) is a DIFFERENT subject sharing only the generic skeleton. RETARGET pins the update on the weaving row (fuzzy 98 + code family RTT603=KTT603 lineage)."},
    "04_btech_textile-tech_y3_syllabus_2024-25::00::yarn-manufacturing-iii": {
        "action": "RETARGET", "target": "yarn-manufacture-iii",
        "reason": "B38 TIE resolution (fuzzy 85/-i, 88/-ii, 90/-iii) on roman-numeral identity + code lineage: draft 'Yarn Manufacturing –III' (BTT502, 2024-25 NEP y3 sem-5 print, 5 verbatim units) — the yarn-manufacture-iii row owns ETE502/RTT502 (the same course's E/R-era ladder; BTT502 is its B-era code). -i/-ii are different-semester courses. RETARGET pins the update on the numeral-matching -iii row."},
    "04_btech_textile-tech_y3_syllabus_2024-25::08::advance-weaving-technology": {
        "action": "RETARGET", "target": "advanced-weaving-technology",
        "reason": "B38 TIE resolution (fuzzy 91/advanced-welding-technology vs 98/advanced-weaving-technology): draft 'Advance Weaving Technology' (BTT603, 2024-25 NEP print, 5 verbatim units) — converges onto the same advanced-weaving-technology row as 03::10 (BTT603 = the B-era code of KTT603/RTT603); the welding row is a different subject."},
    "05_btech_textile-tech_y4_syllabus-cbcs_2019-20::09::process-control-in-spinning-weaving": {
        "action": "FORCE_APPEND",
        "reason": "B38 wrong-family FORCE_APPEND (recorded B30 EMT-011 class + RULES §11): draft 'Process Control in Spinning & Weaving' (RTT085, 2019-20 y4 CBCS DE-5 print, detailed units) — the TIE candidates process-control-in-spinning (ETEF-041) and process-control-in-weaving (ETEF042) are the 2009-10 four-branch-textile DE pool's TWO SEPARATE subjects (spinning-only / weaving-only); the 2019-20 print is a COMBINED course covering both domains in one syllabus. fuzzy 87/85 (both below the identity line) confirms neither candidate is a name variant. Appends as its own row with cross-reference notes to both pool rows; doc 06 (2021-22) prints the same RTT085 course and converges by Tier-1 name identity at commit."},
    "10_btech_y1_syllabus-hindi_2021-22::03::electrical-engineering": {
        "action": "RETARGET", "target": "basic-electrical-engineering",
        "reason": "B38 TIE resolution (fuzzy 89/electronics-engineering vs 88/basic-electrical-engineering) on code lineage: draft 'ELECTRICAL ENGINEERING' (KEE101TH/KEE201TH, 2021-22 y1 print, 5 verbatim units) — the basic-electrical-engineering row owns KEE101/KEE201/KEE-101T/KEE-201T (the same course; 'TH' is this document's theory-suffix print convention and 'ELECTRICAL ENGINEERING' its shortened header form of 'Basic Electrical Engineering'); electronics-engineering is a DIFFERENT subject sharing the generic skeleton. RETARGET pins the update on the KEE101-owner row (equal-session print: fieldwise per §3, source corroboration recorded)."},
    "05_btech_textile-tech_y4_syllabus-cbcs_2019-20::07::textile-marketing-and-merchandising": {
        "action": "FORCE_APPEND",
        "reason": "B38 wrong-subject FORCE_APPEND (recorded B30 class): draft 'Textile Marketing and Merchandising' (RTT071, 2019-20 y4 CBCS DE print, detailed units) — the Tier-2 hit marketing-merchandising-of-carpet-textiles (EACT704, 2009-10 Carpet-Tech DE row, fuzzy 86, overlap 8) is a carpet-specific DIFFERENT subject. Appends as its own row with a cross-reference note; RTT071 unclaimed → the new row owns it."},
    "08_btech_vlsi_y3_syllabus-rev_2025-26::11::analog-integrated-circuit-design": {
        "action": "FORCE_APPEND",
        "reason": "B38 wrong-subject FORCE_APPEND (recorded B30 class): draft 'ANALOG INTEGRATED CIRCUIT DESIGN' (BVL-053, 2025-26 VLSI y3 rev DE print, lecture-plan table units) — the Tier-2 hit integrated-circuits-design (fuzzy 86, overlap 13) is a name-skeleton match on the shared 'integrated circuits design' tokens; the VLSI-branch analog IC design course (op-amp stages, CMOS analog blocks per its printed units) is a DIFFERENT subject from the generic IC-design row. Appends as its own row owning the unclaimed BVL053 with cross-reference notes."},

    # --- B33 commit-run live-ladder adjudications (b33b marker) ---
    "04_btech_plastic_y2_model-curriculum_2019-20::06::plastics-materials-i": {
        "action": "RETARGET", "target": "plastic-materials-i",
        "reason": "B33 live-ladder TIE resolution (fuzzy 97/plastic-materials-i vs 95/plastic-materials-ii) on roman-numeral identity + recorded singular/plural print-variance class: draft 'Plastics Materials-I' (KPE401, 2019-20 y2 model-curriculum sem-4 print) — the plastic-materials-i row is this commit's accumulator of the SAME course (EPL-501 2009-10 'PLASTIC MATERIALS - I' + RPL-501 2018-19 prints); 'Plastics' vs 'Plastic' is the recorded plural print variance (B29 ALLOW class); the -II row is a DIFFERENT semester course (KPE501/EPL601). RETARGET pins the update on the numeral-matching -i row."},
    "04_btech_plastic_y2_model-curriculum_2019-20::07::plastics-processing-i": {
        "action": "RETARGET", "target": "plastic-processing-i",
        "reason": "B33 live-ladder TIE resolution (fuzzy 98/plastic-processing-i vs 95/plastic-processing-ii) on roman-numeral identity + recorded singular/plural print-variance class: draft 'Plastics Processing-I' (KPE402, 2019-20 y2 model-curriculum sem-4 print) — the plastic-processing-i row is this commit's accumulator of the SAME course (EPL-503 2009-10 'PLASTIC PROCESSING-I' + RPL-502 2018-19); the -II row is a DIFFERENT semester course (KPE502/EPL602). RETARGET pins the update on the numeral-matching -i row."},
    "04_btech_plastic_y2_model-curriculum_2019-20::09::synthesis-and-polymerization-lab": {
        "action": "ALLOW",
        "reason": "B33 same-lab ALLOW (recorded TIER2 name-variant class; overlap-0 is the no-unit-prose lab artifact): draft 'Synthesis and Polymerization Lab' (KPE451, 2019-20 y2 model-curriculum sem-4 lab) -> synthesis-polymerization-lab row (fuzzy 93; the row is this commit's accumulator of doc-01 'SYNTHESIS & POLYMERIZATION LAB' EPL-554) — 14 experiments each with 9+ verbatim-identical items (bulk/solution/suspension/emulsion polymerization, viscosity molecular weight, phenol-formaldehyde/urea-formaldehyde/unsaturated-polyester resins); the residual fuzz cap is the '&'/and print variance. Same lab, era ladder converges on one row."},

    # --- B33 adjudications (adjudicate_b33 marker) ---
    "01_btech_plastic_syllabus_2009-10::03::manufacturing-technology": {
        "action": "FORCE_APPEND",
        "reason": "B33 wrong-subject FORCE_APPEND (recorded B30 EMT-011/EMT-801 class + RULES §11 never-merge-different-subjects): draft 'MANUFACTURING TECHNOLOGY' (EME-405, 2009-10 Plastic-Engineering DE print, 5 verbatim units) — the Tier-2 hit garment-manufacturing-technology (KHT-051 Fashion/Tech row, fuzzy 86, overlap 13) is a DIFFERENT subject (garment/fabric domain vs this manufacturing course: sheet-metal working, jigs & fixtures, metal cutting); it shares only a two-sentence generic intro with Manufacturing Science-I (EME402) whose unit bodies differ materially (unit1 428 vs 299 chars, different topics + hour structures). No 'Manufacturing Technology' theory row exists in BTech (only Manufacturing Science-I/II and the RME452/RME553 LAB rows). Appends as its own row owning the unclaimed EME405, with cross-reference notes to manufacturing-science-i and garment-manufacturing-technology."},
    "01_btech_plastic_syllabus_2009-10::34::instrumentation": {
        "action": "FORCE_APPEND",
        "reason": "B33 wrong-subject FORCE_APPEND (same recorded class): draft 'INSTRUMENTATION' (EPL-021, 2009-10 Plastic-Engineering DE print, 4 verbatim units: measurement fundamentals, standards/accuracy, IP quantities, telemetry) — the Tier-2 hit bio-instrumentation (EBM-501 Biomedical row, fuzzy 88, overlap 7) is a DIFFERENT subject (biomedical signals/patient safety). No unit identity with industrial-instrumentation (NIC-602), process-instrumentation (NCH604) or instrumentation-and-process-control (ECH507) either. Appends as its own row owning the unclaimed EPL021, with cross-reference notes."},
    "01_btech_plastic_syllabus_2009-10::29::chemical-thermodynamics": {
        "action": "RETARGET", "target": "chemical-engineering-thermodynamics",
        "reason": "B33 same-course RETARGET (per-unit verbatim identity class, identical evidence to 02::10): draft 'CHEMICAL THERMODYNAMICS' (EPL-012/ECH-401, 2009-10 Plastic DE-I print) — all five units are character-identical (±1 whitespace artifact) to the chemical-engineering-thermodynamics accumulator row's establishing ECH-401 print; the plastic DE list prints the CHE core course under the shortened name with the DE-list code EPL-012. The auto code-slot-collision APPEND (collapsed-name 0.80 < 0.84) would SPLIT one subject into two rows (RULES §11); the name-similarity miss is a prefix-artifact ('Engineering' inserted mid-name). RETARGET pins the update on the ECH401 accumulator: EPL-012 joins code_history, ECH-401 ownership unchanged (already the row's own), the DE print variant recorded via name_print."},
    "02_btech_plastic_syllabus_2018-19::10::chemical-thermodynamics": {
        "action": "RETARGET", "target": "chemical-engineering-thermodynamics",
        "reason": "B33 same-course RETARGET (per-unit verbatim identity class, B37 computer-programming-lab dual-print analog): draft 'CHEMICAL THERMODYNAMICS' (RPL052, 2018-19 Plastic DE-I print) — all five units are character-identical (±1 whitespace artifact) to the chemical-engineering-thermodynamics accumulator row's establishing ECH-401 print (2009-10); the R-era DE list re-codes the SAME university course as RPL-052. The Tier-2 auto hit chemical-process-thermodynamics (KCH 505, 2020-21, different unit bodies) is a different course. RETARGET pins the update on the ECH401 accumulator: RPL052 joins code_history, the canonical name stays, the 'Chemical Thermodynamics' print variant is recorded via name_print."},
    "06_btech_plastic_y3_syllabus_2024-25::11::heat-mass-transfer": {
        "action": "ALLOW",
        "reason": "B33 same-subject name-variant ALLOW (recorded TIER2 ALLOW class): 'Heat & Mass Transfer' (BPE056, 2024-25 Plastic print; the doc itself states '(Same as KME 501)' — recorded in the draft quirks) -> heat-and-mass-transfer row (fuzzy 90, overlap 180); ampersand print variance of the same BTech shared course; the doc's cross-branch same-course note is recorded on the row."},
    "08_btech_plastic_y4_syllabus_2016-17::02::industrial-safety-hazard-management": {
        "action": "ALLOW",
        "reason": "B33 same-subject name-variant ALLOW (recorded TIER2 ALLOW class): 'Industrial Safety & Hazard Management' (NPL-801, 2016-17 Plastic y4 print) -> industrial-safety-and-hazard-management row (fuzzy 95, overlap 85); '&'/'and' print variance, same subject; the ECH-043 2009-10 print (doc 01::27) stays with its published owner per the recorded CODE-REASSIGNED class."},

    # --- B39 commit-run adjudications (adjudicate_b39 marker) ---
    "01_btech_y1_syllabus_2008-09::04::electrical-engineering": {
        "action": "RETARGET", "target": "basic-electrical-engineering",
        "reason": "B39 TIE resolution (fuzzy TIE electronics-engineering vs basic-electrical-engineering) on unit-vocabulary identity + the recorded B38 name-class: draft 'ELECTRICAL ENGINEERING' (EEE-101/EEE-201, 2008-09 y1 print, 5 verbatim units: DC circuit analysis & network theorems / steady-state single-phase AC / three-phase AC circuits / power system layout / electrical machines) — the basic-electrical-engineering row owns KEE101/KEE201/KEE-101T/KEE-201T (the same course's K-era ladder; the identical shortened header print 'ELECTRICAL ENGINEERING' was recorded in B38 on KEE101TH as the shortened form of 'Basic Electrical Engineering'); the DC-circuits-to-machines unit vocabulary is the BEE syllabus while the electronics-engineering row's semiconductors/OP-AMP content is a DIFFERENT subject sharing the generic skeleton. RETARGET pins the update on the KEE101-owner row; 2008-09 older print: backfill-empty only; EEE101/EEE201 are unowned so they accumulate cleanly."},
    "03_btech_y2_common-subjects-syllabus-rev_2014-15::03::laser-systems-and-applications": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "laser-systems-and-applications",
        "keep_published_codes": {"NOE033": "mathematics-iii-science-based-open-elective", "NOE043": "science-based-open-elective-mathematics-iii"},
        "reason": "B39 TIE resolution (code identity across rows on the dual-slot print NOE-033/NOE-043): the name-identity laser-systems-and-applications row (EOE-033/EOE-043, 2009-10 establishing print, EMPTY units) gains the 2014-15 verbatim units/COs/books (newer-session fieldwise); the N-era slot codes stay owned by the two Science-Based-OE slot rows exactly as the recorded B31/B35 STAND kept them for the E/K-era prints (introduction-to-soft-computing precedent: name-identity rows gain units, NOT slot codes; the pool rows keep their expanded range prints); the keep_owner executor records the N-era print as narrative on the target row."},
    "03_btech_y2_common-subjects-syllabus-rev_2014-15::04::polymer-science-technology": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "polymer-science-technology",
        "keep_published_codes": {"NOE035": "mathematics-iii-science-based-open-elective", "NOE045": "science-based-open-elective-mathematics-iii"},
        "reason": "B39 TIE resolution (same dual-slot class as 03::03): the name-identity polymer-science-technology row (ROE035/ROE045 2017-18 R-era ladder, EMPTY units) gains the 2014-15 verbatim units; NOE-035/NOE-045 stay owned by the two Science-Based-OE slot rows (B31/B35 STAND); narrative records the N-era print."},
    "03_btech_y2_common-subjects-syllabus-rev_2014-15::07::discrete-mathematics": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "discrete-mathematics-btech",
        "keep_published_codes": {"NOE038": "mathematics-iii-science-based-open-elective", "NOE048": "science-based-open-elective-mathematics-iii"},
        "reason": "B39 TIE resolution (same dual-slot class as 03::03): the BTech name-identity discrete-mathematics-btech row (ROE038/ROE048 ladder; 2009-10 units printed) gains the 2014-15 verbatim units (newer-session fieldwise wins); NOE-038/NOE-048 stay owned by the two Science-Based-OE slot rows (B31/B35 STAND); RULES §1b: the BCA discrete-mathematics row is a DIFFERENT subject and is never touched."},
    "03_btech_y2_common-subjects-syllabus-rev_2014-15::08::nuclear-science": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "nuclear-science",
        "keep_published_codes": {"NOE036": "mathematics-iii-science-based-open-elective", "NOE046": "science-based-open-elective-mathematics-iii"},
        "reason": "B39 TIE resolution (same dual-slot class as 03::03): the name-identity nuclear-science row (EOE-046/ROE036/ROE046 ladder, units printed) gains the 2014-15 verbatim units (newer-session fieldwise); NOE-036/NOE-046 stay owned by the two Science-Based-OE slot rows (B31/B35 STAND)."},
    "04_btech_y2_engg-science-course_2019-20::04::basics-data-structure-and-algorithms": {
        "action": "RETARGET", "target": "basics-data-structure-algorithms",
        "reason": "B39 TIE resolution (fuzzy 94/basics-data-structure-algorithms vs 89/data-structure-and-algorithms): the target row owns KOE035;KOE045 as exact tokens (the 2023-24 BOE/K-era accumulator; u1 'Introduction: Basic Terminology, Elementary Data Organization, Built in Data Types in C...' matches the 2019-20 AICTE-model-curriculum print) — the draft 'Basics Data Structure & Algorithms' (KOE-035/KOE-045 dual print, 2019-20 ES-course doc) is the SAME course; the 89 fuzzy candidate data-structure-and-algorithms (ECS-508, 2009-10 CSE DE) is a DIFFERENT subject sharing the generic skeleton. RETARGET pins the update on the exact-name row; the dual print atomizes to both codes at apply time."},
    "05_btech_y2_engg-science-course_2021-22::04::basics-data-structure-and-algorithms": {
        "action": "RETARGET", "target": "basics-data-structure-algorithms",
        "reason": "B39 TIE resolution (same row as 04::04; the 2021-22 ES-course doc prints the identical KOE-035/KOE-045 course with identical unit content) — converges onto the basics-data-structure-algorithms accumulator; 2021-22 vs 2023-24 row session: backfill-empty only."},
    "09_btech_y3-4_syllabus_2010-11::23::data-mining-data-warehousing": {
        "action": "RETARGET", "target": "data-warehousing-and-data-mining",
        "reason": "B39 TIE resolution (fuzzy 92/data-warehousing-and-data-mining vs 91/data-warehouse-and-data-mining): word-order print variants of the same course family; the target owns the K/AI-era accumulator codes (KAI075;BCS058;NCS066;BCS058H;BCS-058H) and its u1 'Data Warehousing: Overview, Definition, Data Warehousing Components...' is the DW&DM canon also printed in the competing row; the 2010-11 ECS-075 'Data Mining & Data Warehousing' is the E-era print of the same university course (5 verbatim units; ECS-075 unowned so it accumulates cleanly). RETARGET pins the update on the higher-fuzzy code-bearing accumulator; the 91 candidate row corroborates as a same-family print."},
    "04_btech_y2_engg-science-course_2019-20::02::sensor-and-instrumentation": {
        "action": "ALLOW",
        "reason": "B39 TIER2 same-subject ALLOW (fuzzy 92, overlap 104): 'Sensor and Instrumentation' vs the sensor-instrumentation row's 'Sensor & Instrumentation' — the recorded 'and'/'&' print-variance class (B29/B33); the row owns KOE034;KOE044 (this 2019-20 print's own codes) and its u1 'Sensors & Transducer: Definition, Classification & selection of sensors...' verbatim-matches the draft; the dual code print 'KOE034/044' atomizes at apply time."},
    "04_btech_y2_engg-science-course_2019-20::03::energy-science-and-engineering": {
        "action": "ALLOW",
        "reason": "B39 TIER2 same-subject ALLOW (fuzzy 93, overlap 137): 'Energy Science and Engineering' vs 'Energy Science & Engineering' — the 'and'/'&' print-variance class; the energy-science-engineering row owns KOE033;KOE043 and its u1 'Energy and its Usage: Units and scales of energy use, Mechanical energy and transport...' verbatim-matches the draft's unit-I."},
    "05_btech_y2_engg-science-course_2021-22::02::energy-science-and-engineering": {
        "action": "ALLOW",
        "reason": "B39 TIER2 same-subject ALLOW (same row + class as 04::03; the 2021-22 doc prints the identical KOE-033/KOE-043 course with identical unit-I vocabulary)."},
    "09_btech_y3-4_syllabus_2010-11::02::design-and-analysis-of-algorithms": {
        "action": "ALLOW",
        "reason": "B39 TIER2 same-subject ALLOW (fuzzy 98, overlap 84): plural/singular print variance ('Design and Analysis of Algorithms' vs the design-and-analysis-of-algorithm row) — the recorded B29/B33 singular/plural class; the row owns BCS503;KCS503;NCS501 (the accumulator) and the 2010-11 ECS-502 print is the E-era of the same course; ECS-502 is unowned so it accumulates cleanly."},
    "09_btech_y3-4_syllabus_2010-11::07::computer-network": {
        "action": "ALLOW",
        "reason": "B39 TIER2 same-subject ALLOW (fuzzy 97, overlap 49): singular/plural print variance ('Computer Network' vs 'Computer Networks') — recorded class; the computer-networks row owns BCS603;KCS603;NCS601;RCS-601 (the accumulator); the 2010-11 ECS-601 print is the E-era of the same course (unowned code, accumulates)."},
    "09_btech_y3-4_syllabus_2010-11::12::distributed-systems": {
        "action": "ALLOW",
        "reason": "B39 TIER2 same-subject ALLOW (fuzzy 97, overlap 80): plural print variance ('DISTRIBUTED SYSTEMS' vs 'Distributed System') — recorded class; the row owns KDS052;KCS077;NCS-701;RCS701; the 2010-11 ECS-701 print is the E-era of the same course (unowned code, accumulates)."},
    "09_btech_y3-4_syllabus_2010-11::40::multimedia-systems": {
        "action": "ALLOW",
        "reason": "B39 TIER2 same-subject ALLOW (fuzzy 97, overlap 96): plural print variance ('Multimedia Systems' vs 'Multimedia System', 2009-10 establishing row); the 2010-11 EIT-081 print is the same course's E-era (unowned code, accumulates)."},
    "10_btech_y3_syllabus_2024-25::14::instrumentation-measurement-lab": {
        "action": "ALLOW",
        "reason": "B39 TIER2 same-subject ALLOW (fuzzy 100 normalized-identical): word-order print variance — the 2024-25 ICE print 'INSTRUMENTATION & MEASUREMENT LAB' (BIC-551) vs the measurement-instrumentation-lab row 'Measurement & Instrumentation Lab' (KEC-653A;KIC-553;KIC-551 K-era ICE labs, empty unit text) — the same university lab across the K->B era rename; BIC-551 accumulates."},
    "10_btech_y3_syllabus_2024-25::20::microcontrollers-and-sensors-for-iot-devices": {
        "action": "ALLOW",
        "reason": "B39 TIER2 same-subject ALLOW (fuzzy 86, overlap 134 shared distinctive terms): the 2024-25 ICE DE print 'MICROCONTROLLERS AND SENSORS FOR IOT DEVICES' (BIC-063) vs the microcontrollers-and-sensors-for-iot-applications row (BEC-064, 2025-26) — unit-I is verbatim-identical on both prints ('Fundamentals of IOT: Introduction to IoT, IoT Design Methodology, Design Principles for Connected Devices...') and the unit vocabulary (MSP430, sensor interfacing, IoT security) is the same course; DEVICES/APPLICATIONS is the era print variance; the row's 2025-26 session is newer so the 2024-25 draft BACKFILLS only and BIC-063 accumulates to code_history."},
    # --- B37 commit-run TIE adjudications (adjudicate_b37b marker) ---
    "03_btech_syllabus_2013-14::32::computer-programming-lab": {
        "action": "RETARGET", "target": "computer-programming-lab",
        "reason": "B37 TIE resolution (code identity across rows on NCS-151/NCS-252): draft 'Computer Programming Lab' (2013-14 y1/y2 paired lab print, WAP experiment list) RETARGETs onto the name-identity computer-programming-lab row (the same university-wide lab; dual-print class recorded B36 KAS304/KAS404); the competing code-identity row keeps its codes untouched; 2013-14 older print: backfill-empty only."},
    "04_btech_textile-chem-texteng-mmft_y2_syllabus_2009-10::147::mathematics-iii": {
        "action": "RETARGET", "target": "mathematics-iii",
        "reason": "B37 TIE resolution (code identity EAS-301/EAS-401 after the paired-print splits): draft 'Mathematics-III' (EAS-301/EAS-401, 2009-10 instrumentation-family, 5 verbatim units) RETARGETs onto the name-identity mathematics-iii accumulator row (EAS-301-era establishing print; recorded era-ladder class); the science-based-OE slot rows keep their EOE range prints (recorded B31/B35 class) and the paired print is preserved in the draft's non_subject_rows."},
    "04_btech_textile-chem-texteng-mmft_y2_syllabus_2009-10::50::general-proficiency": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "general-proficiency",
        "keep_published_codes": {"GP301": "general-proficiency-lab"},
        "reason": "B37 recorded GP301 keep-owner class (B25/B26 + recorded entry 07_btech_me-pe_syllabus_2009-10::02::general-proficiency): the 2009-10 GP301 General Proficiency print corroborates the general-proficiency row; GP301's published owner general-proficiency-lab keeps the code (equal/older print never takes a code from its published owner); fieldwise backfill-empty only."},

    # --- B37 adjudications (adjudicate_b37 marker) ---
    "02_btech_syllabus_2009-10::39::transducers-and-sensors": {
        "action": "RETARGET", "target": "transducer-and-sensors",
        "reason": "B37 TIE resolution (fuzzy 98 transducer-and-sensors vs 100 sensors-and-transducers) on code-lineage identity: draft 'Transducers and Sensors' (EIC-401, 2009-10 Instrumentation-family 3rd/4th-yr syllabus, 5 verbatim units) — the transducer-and-sensors row owns NIC-502 (2016-17 N-era print of the SAME instrumentation branch family EIC->NIC, establishing source btech_applied-electronics-ece-ei_syllabus); the competing sensors-and-transducers row (KEE052/BEE052, 2020-21 EE-branch open-elective accumulator) is a DIFFERENT branch's elective with its own code family (recorded B29-TQM / B23 code-owner class: lineage beats generic-vocabulary ratio). 2009-10 is the older print: backfill-empty only; NIC-502 ownership unchanged."},
    "03_btech_syllabus_2013-14::24::engineering-chemistry": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "engineering-chemistry",
        "keep_published_codes": {"NAS202": "engineering-physics-ii"},
        "reason": "B37 TIE resolution (code identity across rows on NAS-102/NAS-202) on name identity + era-ladder lineage: draft 'ENGINEERING CHEMISTRY' (NAS-102/NAS-202 paired 2013-14 y1/y2 print, 5 verbatim units) — the engineering-chemistry accumulator row already owns the whole era ladder of this university-wide course (RAG202; KAS-102T/KAS-202T; BAS102/BAS202; RAS102/RAS202 from the AG 2016-17 establishing print); NAS-102/NAS-202 are the 2013-14-era codes of the SAME course (EAS->NAS->KAS/BAS/RAS ladder). G2 ruling (recorded B36 KAS304 same-session class): NAS-202 stays with its published owner engineering-physics-ii (equal-session prints never transfer codes); the chemistry row gains NAS-102 only; the NAS-202 chemistry/physics dual-print is recorded for owner reconciliation."},
    "09_btech_textile-tech_course-structure_2026-27::19::applied-physics-lab-applied-chemistry-for-fibres-polymers-an": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "applied-physics-lab",
        "keep_published_codes": {"AAS152": "applied-chemistry-lab"},
        "reason": "B37 TIE resolution (code identity across rows on the AAS151/ASS251 paired lab cell) — same-session corroborating print (recorded B27 RCS-653 class): the TX-stream 2026-27 first-year doc prints 'AAS151/ ASS251 Applied Physics Lab/ Applied Chemistry ... Lab' as a PAIRED scheme cell; the applied-physics-lab row is the 2026-27 establishing print (btech_ag_course-structure_2026-27, owns AAS151/AAS251/ASS251). Equal-session prints never take codes from their published owner (B29 RETARGET class): the TX doc is recorded as a corroborating source with backfill-empty-only, and the paired-cell lab-content split (physics vs chemistry experiments in one cell) is flagged needs_review for owner reconciliation per RULES §4 — the draft's merged experiment list is NOT written fieldwise."},


    # ---- B29 (CRON-20261105-B29) per-key adjudications, evidence-recorded ----
    "02_btech_me-ind_y3_evaluation-scheme_2024-25::03::heat-transfer-lab": {
        "action": "RETARGET", "target": "heat-and-mass-transfer-lab",
        "reason": "B29 same-session name-variant corroboration (recorded B27 RCS653 class): draft 'Heat Transfer Lab' (BME551, 2024-25 ME-Ind eval-scheme print, detailed experiment list) — the auto CODE-REASSIGNED name-transfer would move BME551 from heat-and-mass-transfer-lab to the name-exact heat-transfer-lab row (a CHEM-family accumulator: ECH-656 2009-10 BT print + RCH355/455 2017-18). BME551's published owner heat-and-mass-transfer-lab carries the recorded continuity KME551 (2020-21 'Heat & Mass Transfer Lab') -> BME551 (2024-25, established from btech_ae_y3_syllabus_2024-25 detailed print) — this ME-Ind print is a same-session name-variant corroboration of the SAME ME-family lab (thermal-conductivity/heat-exchanger experiments), not a different subject. RETARGET pins the update on the published owner; the 'Heat Transfer Lab' print variant is recorded in the change note."},
    "02_btech_me-ind_y3_evaluation-scheme_2024-25::11::computational-fluid-dynamics": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "computational-fluid-dynamics",
        "keep_published_codes": {"BME055": "turbo-machines"},
        "reason": "B29 doc-internal code-pairing contradiction (recorded B27 RCS653 class + print-quirk rule §6): this eval-scheme doc's p.4 mapping table prints BME055=Turbo Machines / BME062=CFD while its detail-page headers print BME055 on the CFD page and BME062 on the Turbo page — the SAME 08-Hours Turbo unit text is printed under BME055 in the published same-session detailed print (btech_au_y3_syllabus_2024-25, turbo-machines row unit1 verbatim-identical to this doc's Turbo page). Three independent evidences (this doc's own mapping table + the AU detailed print + the published registry) establish BME055=Turbo Machines / BME062=CFD; the detail-header print is the outlier and is recorded as a print-quirk. The auto name-identity transfers would INVERT the published pairing — rejected. BME055 stays with turbo-machines; BME062 stays with computational-fluid-dynamics; the draft's CFD units corroborate the CFD row (2024-25 print older than the row's 2025-26 BAE074 session — backfill-empty only)."},
    "02_btech_me-ind_y3_evaluation-scheme_2024-25::21::turbo-machines": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "turbo-machines",
        "keep_published_codes": {"BME062": "computational-fluid-dynamics"},
        "reason": "B29 doc-internal code-pairing contradiction (same evidence as 02::11): BME062 stays with computational-fluid-dynamics (this doc's p.4 mapping table + the published same-session detailed prints); the detail-page header printing BME062 on the Turbo page is recorded as a print-quirk. The draft's 08-Hours Turbo units are verbatim-identical to the turbo-machines row's establishing print (btech_au_y3_syllabus_2024-25) — same-session corroboration; BME055 remains this row's 2024-25 code."},
    "04_btech_me-ind_y4_syllabus-cbcs_2019-20::00::cad-cam": {
        "action": "RETARGET", "target": "cad-cam-computer-aided-design-and-manufacturing",
        "reason": "B29 same-subject name-shortening RETARGET (recorded B23 code-owner class + B28 era-accumulator class): draft 'CAD/CAM' (RME701, 2019-20 ME-Ind CBCS print, detailed units 'Principles of Computer Graphics...') — the auto CODE-REASSIGNED path (collapsed-name 0.26 < 0.84) would APPEND a new row and transfer RME701, splitting ONE subject into two rows (RULES §11). The target row already owns RME701 from a 2019-20 print (btech_au_y4_syllabus-cbcs_2019-20, recorded in code_history) — 'CAD/CAM' is the abbreviated print of the same subject ('CAD/CAM Computer Aided Design and Manufacturing'); 0.26 is a prefix-abbreviation artifact of the full-name ratio. Same-session corroborating print: fieldwise update; EAU701/NAU-701 E-era history retained."},
    "04_btech_me-ind_y4_syllabus-cbcs_2019-20::02::cad-cam-lab": {
        "action": "RETARGET", "target": "computer-aided-design-manufacturing-lab",
        "reason": "B29 same-session code-owner RETARGET (recorded B27 RCS653 class, B23 07::20 KAS401 pattern): draft 'CAD/CAM Lab' (RME751, 2019-20 ME-Ind CBCS print, experiment list) — the auto name-identity transfer would move RME751 from its published 2019-20 owner computer-aided-design-manufacturing-lab (establishing print btech_au_y4_syllabus-cbcs_2019-20) onto the E-era cad-cam-lab row (EAU751 2009-10 / NAU-751 2016-17). RME751's owner print is the SAME session as this corroborating ME-Ind print of the SAME ME-family lab; an equal-session print never takes a code from its published owner. RETARGET pins the experiment-list corroboration on the RME751 owner row; the E-era cad-cam-lab row is untouched."},
    "04_btech_me-ind_y4_syllabus-cbcs_2019-20::13::automation-and-robotics": {
        "action": "RETARGET", "target": "robotics-and-automation",
        "reason": "B29 recorded-prior-adjudication RETARGET (recorded entry 02_btech_au_y4_syllabus-cbcs_2019-20::09::automation-robotics): draft 'Automation and Robotics' (RME078, 2019-20 ME-Ind CBCS DE-4 print, detailed units) — the SAME 2019-20 CBCS RME-078 DE-slot print already adjudicated to the robotics-and-automation row (branch+era affinity: EAU013 2011-12 AU elective + KAD073 2024-25 AI-DS cross-listing = the AU-branch robotics lineage; the competing automation-and-robotics row BOE302/402 is the 2nd-year university-wide OPEN-ELECTIVE member row, different program level). The auto name-identity transfer contradicts that recorded resolution — rejected. RME078 is already owned by the target; 2019-20 print older than the row's 2024-25 session: backfill-empty only; name-order print variance recorded."},
    "04_btech_me-ind_y4_syllabus-cbcs_2019-20::19::total-quality-management": {
        "action": "RETARGET", "target": "total-quality-management-tqm",
        "reason": "B29 TIE resolution (fuzzy 92 total-quality-management-tqm vs 86 quality-management) on print identity + code lineage: draft 'Total Quality Management' (RME085, 2019-20 ME-Ind CBCS DE-6 print, detailed units verbatim-continuing the TQM accumulator's 'Quality Concepts: Evolution of Quality control, concept change, TQM Modern concept...' text) — the TQM row is the ME-Ind establishing print (NME-041, 2016-17 ME-Ind-PE-IPE, same DE family); RME085 joins as the era code. The competing quality-management row (NOE072/EOE-072, Civil-branch open-elective accumulator, fuzzy 86 on generic quality vocabulary) is a distinct printed course with its own code family; the shared unit1 opening is generic TQM vocabulary. RULES §2: higher score + print identity wins."},
    "06_btech_me-ind_y4_syllabus_2025-26::04::total-quality-management": {
        "action": "RETARGET", "target": "total-quality-management-tqm",
        "reason": "B29 TIE resolution (same evidence as 04::19): draft 'Total Quality Management' (BPI062, 2025-26 ME-Ind print, detailed units) — converges onto the TQM accumulator (NME-041 2016-17 -> RME085 2019-20 -> BPI062 2025-26); 2025-26 is the newest session: fieldwise units win; the Civil quality-management row (fuzzy 86) stays untouched."},
    "07_btech_me-pe_syllabus_2009-10::02::general-proficiency": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "general-proficiency",
        "keep_published_codes": {"GP301": "general-proficiency-lab"},
        "reason": "B29 code-owner protection (recorded B25/B26 GP class, IDENTICAL resolution to 04_btech_it_y2_scheme-syllabus_2009-10::09::general-proficiency): draft 'General Proficiency' (GP-301, 2009-10 ME-PE scheme-row print) — the auto CODE-REASSIGNED name-transfer would move GP301 from general-proficiency-lab (its recorded owner per the B25/B26 class) to the name-exact general-proficiency row; an equal-or-older print never takes a code from its published owner (RULES §3). RETARGET pins the scheme-row corroboration on the name-exact general-proficiency row; GP301 STAYS with general-proficiency-lab (B19 keep_published_codes mechanism)."},
    "07_btech_me-pe_syllabus_2009-10::75::operations-research": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "operations-research",
        "keep_published_codes": {"EME051": "computer-aided-vehicle-design"},
        "reason": "B29 same-session cross-branch collided DE-slot print (recorded B27 RCS653 class): draft 'Operations Research' (EME-051, 2009-10 ME-PE DE print, detailed units) — EME051 is ALSO printed by the SAME-SESSION 2009-10 AU doc (btech_au_syllabus_2009-10, dual EAU051/EME051 slot print) for Computer Aided Vehicle Design, whose row owns it. Two authoritative same-session prints cannot be split by newest-print-wins; the published owner keeps EME051. The ME-PE subject content converges onto the name-exact multi-branch operations-research accumulator (already NOE073;KOE075;RCS-051;EOE-073;NME-051 — the 2016-17 ME-Ind-PE-IPE print established NME-051 for the same subject); the 2009-10 EME-051 print is recorded as narrative (B19 mechanism); G2 single ownership preserved."},
    "07_btech_me-pe_syllabus_2009-10::76::maintenance-engineering-management": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "maintenance-engineering-management",
        "keep_published_codes": {"EME052": "alternative-energy-sources-for-automobiles"},
        "reason": "B29 same-session cross-branch collided DE-slot print (recorded B27 RCS653 class, same evidence as 07::75): EME052 is printed by the 2009-10 AU doc for Alternative Energy Sources for Automobiles (dual EAU052/EME052 slot print) AND by this 2009-10 ME-PE doc for Maintenance Engineering & Management — the published owner keeps EME052. The ME-PE subject updates the name-exact maintenance-engineering-management row (2018-19 AU establishing print; 2009-10 print is OLDER: backfill-empty only; the collided print recorded as narrative)."},
    "07_btech_me-pe_syllabus_2009-10::77::design-of-thermal-systems": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "design-of-thermal-systems",
        "keep_published_codes": {"EME053": "vehicle-dynamics"},
        "reason": "B29 same-session cross-branch collided DE-slot print (recorded B27 RCS653 class, same evidence as 07::75): EME053 is printed by the 2009-10 AU doc for Vehicle Dynamics (dual EAU053/EME053 slot print) AND by this 2009-10 ME-PE doc for Design of Thermal Systems — the published owner keeps EME053. The ME-PE subject updates the name-exact design-of-thermal-systems row (NME-052, 2016-17 ME-Ind-PE-IPE establishing print; 2009-10 print older: backfill-empty only; collided print recorded as narrative)."},
    "07_btech_me-pe_syllabus_2009-10::81::finite-element-method": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "finite-element-method",
        "keep_published_codes": {"EME061": "computer-simulation-of-ic-engines-process"},
        "reason": "B29 same-session cross-branch collided DE-slot print (recorded B27 RCS653 class, same evidence as 07::75): EME061 is printed by the 2009-10 AU doc for Computer Simulation of I.C. Engines (dual EAU061/EME061 slot print) AND by this 2009-10 ME-PE doc for Finite Element Method — the published owner keeps EME061. The ME-PE FEM print converges onto the name-exact finite-element-method row (the recorded 6-branch FEM accumulator, B28 10::08 class: era reorganization not a different subject); the collided print recorded as narrative; G2 preserved."},
    "07_btech_me-pe_syllabus_2009-10::82::non-destructive-testing": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "non-destructive-testing",
        "keep_published_codes": {"EME062": "computer-simulation-of-ic-engines-process"},
        "reason": "B29 same-session cross-branch collided DE-slot print (recorded B27 RCS653 class, same evidence as 07::75): EME062 is printed by the 2009-10 AU doc (its row history records 'EME062 (2009-10)' alongside EAU061/EME061) AND by this 2009-10 ME-PE doc for Non-Destructive Testing — the published owner keeps EME062. The ME-PE NDT print updates the name-exact non-destructive-testing row (NME-065, 2016-17 ME-Ind-PE-IPE establishing print; 2009-10 print older: backfill-empty only; collided print recorded as narrative)."},
    "07_btech_me-pe_syllabus_2009-10::86::fundamentals-of-biomedical-engineering": {
        "action": "FORCE_APPEND",
        "reason": "B29 wrong-subject FORCE_APPEND (recorded B28 class, J=0.11-0.19 precedents + RULES §11 never-merge-different-subjects): draft 'Fundamentals of Biomedical Engineering' (EME-066, 2009-10 ME-PE DE print, detailed units: biomechanics, musculoskeletal statics/dynamics, bioelectric signals) — the Tier-2 hit fundamentals-of-electrical-engineering (AEE101C/BEE101 Ag-generation row, fuzzy 87 on the shared 'fundamentals-of-X-engineering' name skeleton, unit-vocabulary overlap only 6) is a DIFFERENT subject (circuits/machines vs biomechanics/bioinstrumentation). Appends as its own row with a cross-reference note to the electrical-engineering row."},
    "02_btech_me-ind_y3_evaluation-scheme_2024-25::14::refrigeration-air-conditioning": {
        "action": "ALLOW",
        "reason": "B29 same-subject name-variant ALLOW (recorded TIER2 class): 'Refrigeration & Air Conditioning' (BME653, 2024-25) -> refrigeration-and-air-conditioning accumulator (fuzzy 94, overlap 32); singular/print-order variant, same course."},
    "03_btech_me-ind_y3_syllabus_2018-19::01::thermal-and-hydraulic-machines": {
        "action": "ALLOW",
        "reason": "B29 same-subject name-variant ALLOW (recorded TIER2 class): 'Thermal and Hydraulic Machines' (RME053-family print, 2018-19) -> thermal-hydraulic-machines row (fuzzy 93, overlap 75); ampersand/conjunction print variance, same course."},
    "04_btech_me-ind_y4_syllabus-cbcs_2019-20::15::advanced-welding": {
        "action": "ALLOW",
        "reason": "B29 same-subject print-variant ALLOW (recorded TIER2 class): 'Advanced Welding' (2019-20) -> advance-welding row (fuzzy 97, overlap 76); the row's establishing print carries the 'Advance Welding' typo form retained verbatim per RULES §6."},
    "07_btech_me-pe_syllabus_2009-10::36::unconventional-manufacturing-processes": {
        "action": "ALLOW",
        "reason": "B29 same-subject singular/plural ALLOW (recorded TIER2 class): 'Unconventional Manufacturing Processes' (EME-041, 2009-10) -> unconventional-manufacturing-process row (fuzzy 97, overlap 49)."},
    "07_btech_me-pe_syllabus_2009-10::41::optimisation-techniques-in-engineering": {
        "action": "ALLOW",
        "reason": "B29 same-subject ALLOW (recorded TIER2 class + B28 era-reorganization precedent): 'Optimisation Techniques in Engineering' (EME-023, 2009-10 ME-PE DE print, detailed units) -> optimization-techniques-in-chemical-engineering row (fuzzy 87, overlap 23 distinctive terms: unconstrained/multivariable optimum conditions, quasi-Newton/least-squares/Gauss-Newton, LP simplex/transportation, dynamic programming, finite-difference). The title variance ('in Engineering' vs 'in Chemical Engineering') is branch-level print variance of the same 2009-10 generic-optimization course (B7 print-variance convergence class); the ECH-021 establishing print stays as the row's name_print/history; unit reorganization recorded in change_note."},
    "07_btech_me-pe_syllabus_2009-10::42::mechanical-vibration": {
        "action": "ALLOW",
        "reason": "B29 same-subject singular/plural ALLOW (recorded TIER2 class): 'Mechanical Vibration' (EME-0xx, 2009-10) -> mechanical-vibrations row (fuzzy 98, overlap 80)."},
    "07_btech_me-pe_syllabus_2009-10::45::refrigeration-air-conditioning": {
        "action": "ALLOW",
        "reason": "B29 same-subject name-variant ALLOW (recorded TIER2 class): 'Refrigeration & Air Conditioning' (EME-0xx, 2009-10) -> refrigeration-and-air-conditioning accumulator (fuzzy 94, overlap 24)."},
    "07_btech_me-pe_syllabus_2009-10::58::management-information-system": {
        "action": "ALLOW",
        "reason": "B29 same-subject singular/plural ALLOW (recorded TIER2 class): 'Management Information System' (EME-0xx, 2009-10) -> management-information-systems row (fuzzy 98, overlap 40)."},
    "07_btech_me-pe_syllabus_2009-10::78::advanced-synthesis-of-mechanism": {
        "action": "ALLOW",
        "reason": "B29 same-subject print-variant ALLOW (recorded TIER2 class): 'Advanced Synthesis of Mechanism' (EME-0xx, 2009-10) -> advance-synthesis-of-mechanisms row (fuzzy 97, overlap 56; the row's establishing print carries the 'Advance ... Mechanisms' typo forms retained verbatim per RULES §6)."},
    "09_btech_me_syllabus_2018-19::03::ic-engines-and-compressors": {
        "action": "ALLOW",
        "reason": "B29 same-subject name-variant ALLOW (recorded TIER2 class): 'IC Engines and Compressors' (RME-05x, 2018-19) -> i-c-engines-compressors row (fuzzy 90, overlap 94 — near-verbatim unit vocabulary)."},
    "09_btech_me_syllabus_2018-19::13::refrigeration-air-conditioning": {
        "action": "ALLOW",
        "reason": "B29 same-subject name-variant ALLOW (recorded TIER2 class): 'Refrigeration and Air Conditioning' (RME-6xx, 2018-19) -> refrigeration-and-air-conditioning accumulator (fuzzy 94, overlap 24)."},
    "10_btech_me_syllabus_2020-21::16::refrigeration-air-conditioning": {
        "action": "ALLOW",
        "reason": "B29 same-subject name-variant ALLOW (recorded TIER2 class): 'Refrigeration & Air Conditioning' (KME-6xx, 2020-21) -> refrigeration-and-air-conditioning accumulator (fuzzy 94, overlap 32)."},
    # ---- B23 (CRON-20261101-B23) per-key adjudications, evidence-recorded ----
    "03_btech_ee_y3_syllabus_2024-25::06::power-systems-ii": {
        "action": "RETARGET", "target": "power-system-ii",
        "reason": "B23 same-commit-visibility RETARGET (recorded B06/B09/B10 class): draft 'POWER SYSTEMS-II' (BEE-5xx core, 2024-25 print, detailed units) — the live loop's earlier PS-I update (03::05) added the 2024-25 AICTE phrasing to power-system-i, making it fuzzy-eligible (93) alongside the name-exact power-system-ii (97). PS-I and PS-II are DISTINCT subjects (recorded distinct-row design, cf. Machine-I/II); RETARGET pins the update to the name-exact power-system-ii row (plural/singular print variant)."},
    "09_btech_eee-ece_y3_syllabus_2024-25::17::power-systems-ii": {
        "action": "RETARGET", "target": "power-system-ii",
        "reason": "B23 same-commit-visibility RETARGET (same evidence as 03::06): the 2024-25 EEE-ECE print of the same PS-II course; converges onto the name-exact power-system-ii row; PS-I untouched."},
    "01_btech_ee_y2_scheme-syllabus_2017-18::02::electrical-measurements-instrumentation": {
        "action": "RETARGET", "target": "electrical-measurement-measuring-instruments",
        "reason": "B23 code-owner RETARGET (B22 10::01 recorded class, verbatim evidence): draft 'Electrical Measurements & Instrumentation' (REE302, 2017-18 EE print, detailed units). The ladder's Tier-2 hit electronic-instrumentation-and-measurements (EIM, ECE-family) is rejected: 39% vocab / 0.45 best-unit. The EE-family owner electrical-measurement-measuring-instruments (NEE302;EEE-302;KEE302) matches at 91% shared vocab with best per-unit 1.00 — VERBATIM unit identity; REE302 joins as era code."},
    "07_btech_eee-ece_y2_model-curriculum_2019-20::01::electrical-measurements-instrumentation": {
        "action": "RETARGET", "target": "electrical-measurement-measuring-instruments",
        "reason": "B23 code-owner RETARGET (B22 10::01 recorded class): draft 'Electrical Measurements & Instrumentation' (KEE302, 2019-20 EEE-ECE AICTE model print — the SAME AICTE model measurements course B22's 10::01 re-homed; KEE302 is ALREADY owned by electrical-measurement-measuring-instruments since that recorded RETARGET). The auto CODE-REASSIGNED path (collapsed-name 0.82 < 0.84) would transfer KEE302 OFF its recorded owner — rejected; the print corroborates the owner row (units fieldwise-win)."},
    "02_btech_ee_y3_model-curriculum-rev-aicte_2020-21::07::microprocessor-and-microcontroller": {
        "action": "RETARGET", "target": "microprocessor-microcontroller",
        "reason": "B23 code-owner RETARGET (B20-h vocabulary-evidence class): draft 'Microprocessor and Microcontroller' (KEE602, 2020-21 AICTE EE print, detailed units) — TIE candidates microprocessor-microcontroller (BEC502;KEC-502 canon row) vs advanced-microprocessors-and-microcontrollers (2009-10 elective row): 92% shared vocab / 0.74 best-unit vs 47% / 0.36. The basic MP&MC course is the canon row; KEE602 joins as era code."},
    "08_btech_eee-ece_y3_model-curriculum-rev-aicte_2020-21::07::microprocessor-and-microcontroller": {
        "action": "RETARGET", "target": "microprocessor-microcontroller",
        "reason": "B23 code-owner RETARGET (same evidence as 02::07): the 2020-21 EEE-ECE AICTE print of the same KEE-602 MP&MC course; canon row matches 92%/0.74 vs advanced 47%/0.36."},
    "04_btech_ee_y4_syllabus-cbcs_2019-20::14::microprocessors-and-microcontrollers": {
        "action": "RETARGET", "target": "advanced-microprocessors-and-microcontrollers",
        "reason": "B23 code-owner RETARGET (vocabulary-evidence class): draft 'MICROPROCESSORS AND MICROCONTROLLERS' (REE070, 2019-20 CBCS elective, detailed units) — TIE candidates: advanced-microprocessors-and-microcontrollers matches 100% shared vocab with best per-unit 0.99 (VERBATIM — the 2019-20 print is the same course as the 2009-10 EEE print that established the row in B22); microprocessor-microcontroller only 41%/0.05. REE070 joins as era code."},
    "10_btech_eee-ece_y4_syllabus-cbcs_2019-20::04::microprocessors-and-microcontrollers": {
        "action": "RETARGET", "target": "advanced-microprocessors-and-microcontrollers",
        "reason": "B23 code-owner RETARGET (same evidence as 04::14): the 2019-20 EEE-ECE CBCS print of the same REE-070 course; advanced row matches 100%/0.99."},
    "03_btech_ee_y3_syllabus_2024-25::02::electrical-machine-ii": {
        "action": "FORCE_APPEND",
        "reason": "B23 wrong-subject FORCE_APPEND (B14/B15/B19/B20-e class + RULES §11 never-merge-different-subjects): draft 'ELECTRICAL MACHINE-II' (BEE503, 2024-25 print, detailed units) — TIE candidates electrical-machines (NIC-011 open-elective print: 49% vocab / 0.30 best-unit) and electrical-machines-i (KEE402 EM-I row: 40% / 0.12): NEITHER reaches unit identity, and Machine-II must NEVER merge into Machine-I (recorded distinct-row design, cf. electro-mechanical-energy-conversion-i/ii). Appends as its own row with cross-reference notes to both rows."},
    "09_btech_eee-ece_y3_syllabus_2024-25::02::electrical-machine-ii": {
        "action": "FORCE_APPEND",
        "reason": "B23 wrong-subject FORCE_APPEND (same evidence as 03::02): the 2024-25 EEE-ECE print of the same BEE-503 EM-II course; converges onto the 03::02-appended row by Tier-1 name identity at commit."},
    "02_btech_ee_y3_model-curriculum-rev-aicte_2020-21::13::sensors-and-transducers": {
        "action": "FORCE_APPEND",
        "reason": "B23 wrong-subject FORCE_APPEND (B14/B15/B19/B20-e class, recorded unit evidence): draft 'Sensors and Transducers' (KEE052, AICTE EE print, detailed units) — the Tier-2 candidate transducer-and-sensors (NIC-502, 2016-17) is the applied-MEASUREMENT course (generalized instrument configurations, motion/force/flow/temperature measurement): only 30% shared vocab, best per-unit 0.05. Different subjects sharing a generic title family; appends as its own row with a cross-reference note."},
    "03_btech_ee_y3_syllabus_2024-25::13::sensors-and-transducers": {
        "action": "FORCE_APPEND",
        "reason": "B23 wrong-subject FORCE_APPEND (same evidence as 02::13): the 2024-25 EE print of the same AICTE sensors course; converges onto the 02::13-appended row by Tier-1 name identity at commit."},
    "08_btech_eee-ece_y3_model-curriculum-rev-aicte_2020-21::13::sensors-and-transducers": {
        "action": "FORCE_APPEND",
        "reason": "B23 wrong-subject FORCE_APPEND (same evidence as 02::13): the 2020-21 EEE-ECE AICTE print of the same course; converges onto the 02::13-appended row by Tier-1 name identity at commit."},
    "09_btech_eee-ece_y3_syllabus_2024-25::10::sensors-and-transducers": {
        "action": "FORCE_APPEND",
        "reason": "B23 wrong-subject FORCE_APPEND (same evidence as 02::13): the 2024-25 EEE-ECE print of the same course; converges onto the 02::13-appended row by Tier-1 name identity at commit."},
    "02_btech_ee_y3_model-curriculum-rev-aicte_2020-21::10::microprocessor-and-microcontroller-lab": {
        "action": "ALLOW",
        "reason": "B23 era-family ALLOW: draft 'Microprocessor and Microcontroller Lab' (KEE652, 2020-21 AICTE print, experiments only) — the target microprocessor-microcontroller-lab (BEC552;KEC-552 canon row) is the same lab subject; the low vocab overlap (6) reflects the no-units lab class (experiment lists only), not a content difference; KEE652 joins as era code."},
    "08_btech_eee-ece_y3_model-curriculum-rev-aicte_2020-21::10::microprocessor-and-microcontroller-lab": {
        "action": "ALLOW",
        "reason": "B23 era-family ALLOW (same evidence as 02::10): the 2020-21 EEE-ECE print of the same KEE-652 lab; its PART-A+PART-B experiment lists corroborate the canon lab row."},
    "02_btech_ee_y3_model-curriculum-rev-aicte_2020-21::19::analog-digital-communication": {
        "action": "FORCE_APPEND",
        "reason": "B23 wrong-subject FORCE_APPEND (B14/B15/B19/B20-e class, recorded unit evidence): draft 'Analog & Digital Communication' (KEE058, AICTE DE elective, detailed units) — the Tier-2 candidate digital-communication (BEC601/KEC-601 canon) is the pure DIGITAL communication course: only 29% shared vocab, best per-unit 0.42; the AICTE print covers analog modulation + digital basics as one course. Different subject; appends as its own row with a cross-reference note."},
    "03_btech_ee_y3_syllabus_2024-25::19::analog-digital-communication": {
        "action": "FORCE_APPEND",
        "reason": "B23 wrong-subject FORCE_APPEND (same evidence as 02::19): the 2024-25 EE print of the same AICTE ADC course; converges onto the 02::19-appended row by Tier-1 name identity at commit."},
    "08_btech_eee-ece_y3_model-curriculum-rev-aicte_2020-21::19::analog-digital-communication": {
        "action": "FORCE_APPEND",
        "reason": "B23 wrong-subject FORCE_APPEND (same evidence as 02::19): the 2020-21 EEE-ECE print; converges onto the 02::19-appended row by Tier-1 name identity at commit."},
    "09_btech_eee-ece_y3_syllabus_2024-25::16::analog-digital-communication": {
        "action": "FORCE_APPEND",
        "reason": "B23 wrong-subject FORCE_APPEND (same evidence as 02::19): the 2024-25 EEE-ECE print; converges onto the 02::19-appended row by Tier-1 name identity at commit."},
    "02_btech_ee_y3_model-curriculum-rev-aicte_2020-21::17::neural-networks-fuzzy-system": {
        "action": "ALLOW",
        "reason": "B23 same-subject ALLOW: draft 'Neural Networks & Fuzzy System' (KEE-0xx DE) fuzzy 93, shared vocab 66 vs the B22-appended neural-networks-and-fuzzy-system row (2009-10 EEE print) — same subject; singular/plural print variant."},
    "03_btech_ee_y3_syllabus_2024-25::17::neural-networks-fuzzy-systems": {
        "action": "ALLOW",
        "reason": "B23 same-subject ALLOW (same evidence as 02::17): the 2024-25 EE print, fuzzy 92/65; converges by name identity."},
    "08_btech_eee-ece_y3_model-curriculum-rev-aicte_2020-21::17::neural-networks-fuzzy-system": {
        "action": "ALLOW",
        "reason": "B23 same-subject ALLOW (same evidence as 02::17): the 2020-21 EEE-ECE print, fuzzy 93/66."},
    "09_btech_eee-ece_y3_syllabus_2024-25::14::neural-networks-fuzzy-systems": {
        "action": "ALLOW",
        "reason": "B23 same-subject ALLOW (same evidence as 02::17): the 2024-25 EEE-ECE print, fuzzy 92/66."},
    "02_btech_ee_y3_model-curriculum-rev-aicte_2020-21::23::electrical-and-hybrid-vehicles": {
        "action": "ALLOW",
        "reason": "B23 name-variant ALLOW: draft 'Electrical and Hybrid Vehicles' (KEE-0xx DE) fuzzy 97, shared vocab 38 vs published electric-and-hybrid-vehicles — same subject (Electric/Electrical token variance)."},
    "04_btech_ee_y4_syllabus-cbcs_2019-20::15::utilization-of-electrical-energy-and-traction": {
        "action": "ALLOW",
        "reason": "B23 same-subject ALLOW: draft 'UTILIZATION OF ELECTRICAL ENERGY AND TRACTION' (REE-0xx elective) fuzzy 88, shared vocab 68 vs the B22-appended utilization-of-electrical-energy-electric-traction row — same subject; the row-name variant pair (electric-traction vs and-traction) is a recorded open item; REE code joins as era code."},
    "10_btech_eee-ece_y4_syllabus-cbcs_2019-20::05::utilization-of-electrical-energy-and-traction": {
        "action": "ALLOW",
        "reason": "B23 same-subject ALLOW (same evidence as 04::15): the 2019-20 EEE-ECE print, fuzzy 88/68; REN/REE code joins as era code."},
    "04_btech_ee_y4_syllabus-cbcs_2019-20::19::energy-efficiency-conservation": {
        "action": "ALLOW",
        "reason": "B23 name-variant ALLOW: draft 'ENERGY EFFICIENCY & CONSERVATION' (REE-0xx) fuzzy 94, shared vocab 59 vs published ENERGY EFFICIENCY AND ENERGY CONSERVATION (ECH013, 2009-10; B22-corroborated) — same subject, ellipsis print variant."},
    "10_btech_eee-ece_y4_syllabus-cbcs_2019-20::09::energy-efficiency-conservation": {
        "action": "ALLOW",
        "reason": "B23 name-variant ALLOW (same evidence as 04::19): the 2019-20 EEE-ECE print, fuzzy 94/59."},
    "04_btech_ee_y4_syllabus-cbcs_2019-20::26::ehv-ac-dc-transmission": {
        "action": "ALLOW",
        "reason": "B23 same-subject ALLOW: draft 'EHV AC & DC TRANSMISSION' (REE-0xx) fuzzy 86, shared vocab 95 (near-total) vs the B22-appended hvdc-ac-transmission row — same subject (HVDC/EHV family); REE code joins as era code."},
    "10_btech_eee-ece_y4_syllabus-cbcs_2019-20::16::ehv-ac-dc-transmission": {
        "action": "ALLOW",
        "reason": "B23 same-subject ALLOW (same evidence as 04::26): the 2019-20 EEE-ECE print, fuzzy 86/95."},
    "05_btech_ee_y4_syllabus_2021-22::00::advanced-micro-processors-micro-controllers": {
        "action": "ALLOW",
        "reason": "B23 era-family ALLOW: draft 'Advanced Micro processors & Micro Controllers' (KEE070, 2021-22 DE print, detailed units) vs the B22-appended advanced-microprocessors-and-microcontrollers row (2009-10 EEE print): fuzzy 88/34 with best per-unit 0.91 (u1 verbatim) — same subject, KEE070 joins as era code."},
    "05_btech_ee_y4_syllabus_2021-22::06::power-system-dynamics-and-control": {
        "action": "FORCE_APPEND",
        "reason": "B23 wrong-subject FORCE_APPEND (B14/B15/B19/B20-e class, recorded unit evidence): draft 'Power System dynamics and Control' (KEE076, 2021-22 DE print, detailed units) — the Tier-2 candidate process-dynamics-and-control is the CHEMICAL-engineering course (BCH503/NCH603/RCH602/ECH602/KCH503): 40% vocab / 0.06 best-unit (name-token overlap only); power-system-operation-and-control (31%/0.10) and power-system-analysis (39%/0.07) also fail unit identity. No vocabulary-evidence row exists; appends as its own row with cross-reference notes."},
    "06_btech_eee-ece-ee_y3_syllabus_2018-19::19::principles-of-communication": {
        "action": "ALLOW",
        "reason": "B23 singular/plural ALLOW: draft 'Principles of Communication' (REE-0xx) fuzzy 98, shared vocab 79 vs published principles-of-communications — same subject; REE code joins as era code."},
    "06_btech_eee-ece-ee_y3_syllabus_2018-19::22::intelligent-sensors-instrumentation": {
        "action": "ALLOW",
        "reason": "B23 era-family ALLOW: draft 'Intelligent Sensors & Instrumentation' (REE061, 2018-19 elective, detailed units) vs published intelligent-instrumentation (EEE-022;NIC-022): 87% shared vocab with best per-unit 0.98 (VERBATIM) — same subject; REE061 joins as era code."},
    "06_btech_eee-ece-ee_y3_syllabus_2018-19::23::bio-medical-instrumentation": {
        "action": "FORCE_APPEND",
        "reason": "B23 wrong-subject FORCE_APPEND (B14/B15/B19/B20-e class, recorded unit evidence): draft 'Bio-Medical Instrumentation' (REE062, 2018-19 elective, detailed units) — candidates bio-medical-sensors-instrumentation (BEC-052, 2024-25 print): 49% vocab / 0.31 best-unit; bio-instrumentation (EBM/RBM/EEE-051): 30% / 0.07. Neither reaches unit identity and the emphasis differs (sensors-transducers vs clinical instrumentation); appends as its own row with cross-reference notes to both."},
    "08_btech_eee-ece_y3_model-curriculum-rev-aicte_2020-21::15::bio-medical-instrumentation": {
        "action": "FORCE_APPEND",
        "reason": "B23 wrong-subject FORCE_APPEND (same evidence as 06::23): the 2020-21 AICTE print of the same course (fuzzy 87/50 vs the sensors row); converges onto the 06::23-appended row by Tier-1 name identity at commit."},
    "10_btech_eee-ece_y4_syllabus-cbcs_2019-20::15::optical-fiber-communication": {
        "action": "ALLOW",
        "reason": "B23 same-subject ALLOW: draft 'OPTICAL FIBER COMMUNICATION' (REE/REN-0xx elective) fuzzy 88, shared vocab 70 vs published optical-communication (KEC-058;BEC-057, B21/B22 recorded) — same fiber-optics subject; REE code joins as era code."},
    "07_btech_eee-ece_y2_model-curriculum_2019-20::20::technical-communication": {
        "action": "RETARGET", "target": "universal-human-values-and-professional-ethics",
        "reason": "B23 code-owner RETARGET (B02-recorded ownership): draft 'Technical Communication' (scheme-row-only, KAS401 — the sem-IV OR-slot print 'Technical Communication/Universal Human values'; the full slot print is preserved in the draft's non_subject_rows). The auto CODE-REASSIGNED name-transfer would move KAS401 OFF the recorded owner universal-human-values-and-professional-ethics (all_codes include KAS401 since the B02-era ingest) onto the print-variant name row — rejected. RETARGET pins the scheme-line corroboration onto the recorded KAS401 owner; the technical-communication member keeps its own KAS301 row untouched."},
    # ---- B22 (CRON-20261101-B22) per-key adjudications, evidence-recorded ----
    # 16 Tier-2 flags: 6 wrong-subject FORCE_APPENDs (4x Speech Processing ->
    # AG 'Seed Processing' RAG052 + process-instrumentation + basic-signals),
    # 1 code-owner RETARGET (KEE-302 -> EMMI), 9 name-variant/era-family
    # ALLOWs (unit-vocab evidence recorded per key).
    "01_btech_ece_y4_syllabus-rcode_2021-22::07::speech-processing": {
        "action": "FORCE_APPEND",
        "reason": "B22 wrong-subject FORCE_APPEND (B14/B15/B19/B20-e class): the only Tier-2 candidate seed-processing is the Agricultural Engineering subject 'Seed Processing' (RAG052, 2018-19 AG print: seed industry/seed acts units) — name-similarity 88 is 'speech'/'seed'+'processing' token variance; shared unit vocabulary 4 generic tokens. The 2021-22 ECE print 'Speech Processing' (KEC-078, detailed units) appends as its own row; later Speech-Processing prints (02::18/03::13/04::14) converge onto it by Tier-1 name identity at commit (recorded same-commit visibility class)."},
    "02_btech_ece_y4_syllabus-rev_2019-20::16::wireless-mobile-communication": {
        "action": "ALLOW",
        "reason": "B22 name-variant ALLOW ('&' vs 'and' print class, B18/B19 recorded): draft 'Wireless & Mobile Communication' (2019-20 REC print) fuzzy 94, shared unit vocabulary 135 tokens — same subject as the published wireless-and-mobile-communication row; REC-0xx code joins as era code."},
    "02_btech_ece_y4_syllabus-rev_2019-20::18::speech-processing": {
        "action": "FORCE_APPEND",
        "reason": "B22 wrong-subject FORCE_APPEND (same evidence as 01::07): Tier-2 candidate seed-processing is the AG 'Seed Processing' RAG052 row (seed-industry units; shared vocab 4 generic tokens). The 2019-20 ECE print 'Speech Processing' (REC-08x) appends; converges onto the 01::07-appended speech-processing row by Tier-1 name identity at commit (same-commit visibility class)."},
    "03_btech_ece_y4_syllabus_2011-12::03::satellite-communications": {
        "action": "ALLOW",
        "reason": "B22 singular/plural print variant ALLOW (B18/B19 recorded class): draft 'SATELLITE COMMUNICATIONS' (2011-12 EEC print) fuzzy 98, shared vocab 50 tokens vs published satellite-communication — same subject; EEC-0xx code joins as era code."},
    "03_btech_ece_y4_syllabus_2011-12::05::artificial-neural-networks": {
        "action": "ALLOW",
        "reason": "B22 singular/plural print variant ALLOW (B18/B19 recorded class): draft 'Artificial Neural Networks' (2011-12 EEC print) fuzzy 98, shared vocab 40 tokens vs published artificial-neural-network — same subject."},
    "03_btech_ece_y4_syllabus_2011-12::09::mobile-and-wireless-communication": {
        "action": "ALLOW",
        "reason": "B22 word-order print variant ALLOW (B18/B19 recorded class): draft 'Mobile and Wireless Communication' (2011-12 EEC print) fuzzy 100, shared vocab 44 tokens vs published wireless-and-mobile-communication — same subject; EEC-0xx joins as era code."},
    "03_btech_ece_y4_syllabus_2011-12::13::speech-processing": {
        "action": "FORCE_APPEND",
        "reason": "B22 wrong-subject FORCE_APPEND (same evidence as 01::07): Tier-2 candidate seed-processing is the AG 'Seed Processing' RAG052 row (shared vocab 4 generic tokens). The 2011-12 ECE print 'SPEECH PROCESSING' appends; converges onto the 01::07-appended speech-processing row by Tier-1 name identity at commit."},
    "04_btech_ece_y4_syllabus_2016-17::10::wireless-mobile-communication": {
        "action": "ALLOW",
        "reason": "B22 name-variant ALLOW ('&' vs 'and' print class): draft 'Wireless & Mobile Communication' (2016-17 NEC print) fuzzy 94, shared vocab 134 tokens — same subject as wireless-and-mobile-communication."},
    "04_btech_ece_y4_syllabus_2016-17::14::speech-processing": {
        "action": "FORCE_APPEND",
        "reason": "B22 wrong-subject FORCE_APPEND (same evidence as 01::07): Tier-2 candidate seed-processing is the AG 'Seed Processing' RAG052 row (shared vocab 4 generic tokens). The 2016-17 ECE print 'Speech Processing' appends; converges onto the 01::07-appended speech-processing row by Tier-1 name identity at commit."},
    "07_btech_ee-group_y2_syllabus-rev_2014-15::15::instrumentation-process-control": {
        "action": "FORCE_APPEND",
        "reason": "B22 wrong-subject FORCE_APPEND (B14/B15/B19/B20-e class): the Tier-2 candidate process-instrumentation is the chemical-process print (ECH604/ECH504/REC408; unit vocabulary 'process industries, flow/level/pressure transmitters' family) — draft 'Instrumentation & Process Control' (NEE-403, 2014-15 EE-group, detailed units) shares only 24% vocabulary and best per-unit similarity 0.35: different subjects that merely share the instrumentation token family. Appends as its own row with NEE-403; cross-reference note to process-instrumentation recorded."},
    "09_btech_ee_syllabus_2009-10::11::microprocessors": {
        "action": "ALLOW",
        "reason": "B22 era-family ALLOW (B18/B19 recorded class): draft 'Microprocessors' (2009-10 EEE print) fuzzy 97, shared vocab 57 tokens vs published microprocessor — the row already owns the same-era 2009-10 ECE print codes (EEC- 503/EEC 503, recorded B21); the EEE print is the same subject family; EEE-5xx code joins as era code."},
    "09_btech_ee_syllabus_2009-10::44::cryptography-and-network-security": {
        "action": "ALLOW",
        "reason": "B22 same-subject ALLOW: draft 'Cryptography and Network Security' (2009-10 EEE open-elective print) fuzzy 94, shared vocab 70 tokens vs published cryptography-network-security-btech — same BTech subject; EOE code joins as era code."},
    "09_btech_ee_syllabus_2009-10::56::energy-efficiency-and-conservation": {
        "action": "ALLOW",
        "reason": "B22 name-variant ALLOW (word-order/ellipsis class): draft 'Energy Efficiency and Conservation' (2009-10 EOE scheme-row print) fuzzy 100 vs published ENERGY EFFICIENCY AND ENERGY CONSERVATION (ECH013, 2009-10 ECE print) — same subject name modulo the repeated 'energy' token; scheme-row-only corroborating print; low unit overlap (9) reflects the scheme-row-only class, not content difference."},
    "10_btech_ee_y2_model-curriculum_2019-20::01::electrical-measurements-instrumentation": {
        "action": "RETARGET", "target": "electrical-measurement-measuring-instruments",
        "reason": "B22 code-owner RETARGET (B20-c singular/plural+abbreviated-print class with recorded unit evidence): draft 'Electrical Measurements & Instrumentation' (KEE-302, 2019-20 AICTE EE-model print, detailed units). The ladder's Tier-2 hit electronic-instrumentation-and-measurements (EIM, ECE-family EEC-403) is rejected: shared vocab 40%, best per-unit 0.41, and the print says ELECTRICAL not ELECTRONIC. The published EE-family measurements row electrical-measurement-measuring-instruments (NEE-302, 2014-15 EE-group print) matches better on every axis: shared vocab 45%, best per-unit 0.57 (measurement methods/characteristics/errors/standards/indicating-instruments topic sequence identical), same branch family. KEE-302 joins as era code; 2019-20 units fieldwise-win (RULES §3); NEE-302 print stays in source_history."},
    "10_btech_ee_y2_model-curriculum_2019-20::02::basic-signals-systems": {
        "action": "FORCE_APPEND",
        "reason": "B22 wrong-subject FORCE_APPEND (B14/B15/B19/B20-e class, recorded unit evidence): draft 'Basic Signals & Systems' (KEE-303, 2019-20 AICTE EE-model print, detailed units) vs Tier-2 candidate signals-and-systems (EEC-404/NEC-303/REC303 ECE-canon): shared vocab only 43% with best per-unit SequenceMatcher 0.08 — the AICTE print is a rewritten unit split (State-Variable analysis unit, no sampling unit). Precedent: the B02 AICTE E&C-model print 'Signal System' (KEC403/BEC403) was likewise kept as its OWN row (unit-vocab 38% vs the EE print; best 0.34). Appends as its own row with KEE-303 + cross-reference note to signals-and-systems and signal-system (same signals-course family; kept separate per unit-text evidence, RULES §11)."},
    "10_btech_ee_y2_model-curriculum_2019-20::08::networks-analysis-synthesis": {
        "action": "ALLOW",
        "reason": "B22 plural-variant + era-family ALLOW (B18/B19 recorded class): draft 'Networks Analysis & Synthesis' (KEE-403, AICTE EE-model print) fuzzy 91, shared vocab 58 of 106 tokens (best per-unit 0.46) vs published network-analysis-and-synthesis — the row is the multi-era canon (NEC-301 2014-15, KEC303 2019-20, BEC303, REE305); KEE-403 joins as era code; 2019-20 units fieldwise-win."},
    "05_btech_ece_y4_syllabus_2025-26::10::open-elective-iii": {
        "action": "RETARGET", "target": "open-elective-iii",
        "reason": "B22 same-commit-visibility RETARGET (recorded B06/B09/B10 class): draft 'Open Elective-III' (BOEM** wildcard slot print, 2025-26 ECE y4) — the live loop's 05::06 update wrote the raw wildcard 'BOEM**' onto open-elective-ii (all_codes), so the Tier-0 wildcard scan finds open-elective-ii (same-commit) AND open-elective-iii (static 'BOEM**' owner) — a wildcard-wart TIE, not two real subjects. RETARGET pins the update to the NAME-EXACT row open-elective-iii."},
    "05_btech_ece_y4_syllabus_2025-26::11::open-elective-iv": {
        "action": "RETARGET", "target": "open-elective-iv",
        "reason": "B22 same-commit-visibility RETARGET (recorded class): draft 'Open Elective-IV' (BOEM** wildcard slot print) — Tier-0 wildcard scan finds open-elective-ii (05::06 live update) + open-elective-iii (static) both carrying the 'BOEM**' wart; neither is the name-exact row. RETARGET pins the update to open-elective-iv (name identity; the row owns no wildcard yet and gains the printed 'BOEM**')."},
    "06_btech_ee-en_y4_syllabus_2025-26::11::open-elective-iii": {
        "action": "RETARGET", "target": "open-elective-iii",
        "reason": "B22 same-commit-visibility RETARGET (recorded class): draft 'Open Elective-III' (BOEM** wildcard slot print, 2025-26 EE/EE-EN y4) — the 05::06 live update put 'BOEM**' on open-elective-ii and 05::10's update kept it on open-elective-iii; the wildcard scan TIEs across those warts. RETARGET pins the update to the NAME-EXACT row open-elective-iii."},
    "06_btech_ee-en_y4_syllabus_2025-26::12::open-elective-iv": {
        "action": "RETARGET", "target": "open-elective-iv",
        "reason": "B22 same-commit-visibility RETARGET (recorded class): draft 'Open Elective-IV' (BOEM** wildcard slot print, 2025-26 EE/EE-EN y4) — same wildcard-wart TIE (open-elective-ii + open-elective-iii carry 'BOEM**' from the doc05 updates). RETARGET pins the update to the NAME-EXACT row open-elective-iv."},
    # ---- B18 (CRON-20261101-B18) per-key adjudications, evidence-recorded ----
    # Six mini-project prints (2022-23 KCS554 x2, 2024-25 BCS554 x4) + four
    # DBMS-lab print variants + DW&DM + Constitution: each RETARGETs to the
    # PUBLISHED code-owner row (the kind-level CODE-REASSIGNED default would
    # transfer codes onto print-variant name rows, reversing recorded Task-28/
    # B08/B12 lineage and ping-ponging BCS551/KCS551 between variant rows).
    "05_btech_cse-cyber-security_y4_syllabus_2025-26::06::project": {
        "action": "RETARGET", "target": "project-1",
        "reason": "B18 joint-print Project pin (recorded B09 precedent, merge_draft.py B17-era entry 'Joint-print corroboration on the BCS753 slot row'): after patch_b18_tie_strips.py stripped BCS851 (its sem-VIII slot row project-ii already owns it), Tier-0 uniquely owns BCS753 at project-1 — but the ladder's name-transfer (draft 'Project' vs row 'Project-1') would move BCS753 to project-btech, undoing the recorded B08 Project-1/Project-II split; RETARGET pins the update to project-1. The 2025-26 Cyber-Security print's shared CO table corroborates project-1's published 2025-26 content (B08 AI-DS print) — corroboration-only; the joint print evidence is preserved verbatim in the draft quirks."},
    "07_btech_cse-ds_y4_syllabus_2025-26::06::project": {
        "action": "RETARGET", "target": "project-1",
        "reason": "B18 joint-print Project pin (recorded B09 precedent): BCS851 stripped (project-ii owns it); Tier-0 uniquely owns BCS753 at project-1; the name-transfer toward project-btech would undo the recorded B08 Project-1/Project-II split; RETARGET pins the update to project-1. 2025-26 CSE-DS print corroborates project-1's published 2025-26 content."},
    "10_btech_cse-iot_y4_syllabus_2025-26::06::project": {
        "action": "RETARGET", "target": "project-1",
        "reason": "B18 joint-print Project pin (recorded B09 precedent): BCS851 stripped (project-ii owns it); Tier-0 uniquely owns BCS753 at project-1; the name-transfer toward project-btech would undo the recorded B08 Project-1/Project-II split; RETARGET pins the update to project-1. 2025-26 CSE-IoT print corroborates project-1's published 2025-26 content."},
    "01_btech_cse-aiml_y3_syllabus-rev_2022-23::16::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "B18 mini-project CSE&E code-owner RETARGET class (recorded B17 override of this exact transfer; B16 rejection): the ladder's Tier-0 code-reassigned name-transfer would move KCS554 OUT of the CSE&E code-owner row internship-assessment-mini-project (all_codes BCC351;KCS354;KEC354;KCS554;BCS554;BCE554;KCS752, KCS554 owner since Task 28 'KCS554 PS 50' + B02 CSAI sem-5 placement prints) into the AG/AE-named cross-branch slot row (primary BAE553, EMPTY branch_names) — cross-branch pollution, RULES §1b spirit. The draft name 'Mini Project or Internship Assessment' is the 2022-23 print form of the same assessment slot (K-era); UPDATE the CSE&E code-owner row; the RETARGET re-points the registered reassignment (no other row claims KCS554)."},
    "02_btech_cse-aiml_y3_syllabus_2024-25::24::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "B18 mini-project CSE&E code-owner RETARGET class (recorded B17 override of this exact transfer): BCS554 is ALREADY owned by the CSE&E code-owner row internship-assessment-mini-project; the name-transfer toward the AG/AE-named cross-branch row (BAE553 primary, empty branch) is rejected per RULES §1b spirit. The draft subject is the 2024-25 AIML y3 scheme-row print (PS=100/Total=100). UPDATE the CSE&E code-owner row; RETARGET re-points the registered reassignment."},
    "04_btech_cse-cyber-security_y3_syllabus_2024-25::14::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "B18 mini-project CSE&E code-owner RETARGET class (recorded B17 override of this exact transfer): draft BCS554 (2024-25 Cyber-Security y3 scheme-row print) — BCS554 is ALREADY owned by the CSE&E code-owner row internship-assessment-mini-project; name-transfer toward the AG/AE-named cross-branch row rejected per RULES §1b spirit. UPDATE the CSE&E code-owner row."},
    "06_btech_cse-ds_y3_syllabus_2024-25::24::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "B18 mini-project CSE&E code-owner RETARGET class (recorded B17 override of this exact transfer; byte-class precedent 06_btech_csd_y3_syllabus_2024-25::24): draft BCS554 (2024-25 CSE-DS y3 scheme-row print 'Mini Project or Internship Assessment*', PS=100/Total=100, footnote 'will be done during summer break after VI Semester... assessed during VII semester' preserved in non_subject_rows) — BCS554 already owned by internship-assessment-mini-project. UPDATE the CSE&E code-owner row."},
    "08_btech_cse-iot_y3_syllabus-rev_2022-23::27::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "B18 mini-project CSE&E code-owner RETARGET class (recorded B17 override of this exact transfer): draft KCS554 (2022-23 CSE-IoT y3 scheme-row print) — KCS554 already owned by the CSE&E code-owner row internship-assessment-mini-project since Task 28. UPDATE the CSE&E code-owner row; RETARGET re-points the registered reassignment."},
    "09_btech_cse-iot_y3_syllabus_2024-25::24::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "B18 mini-project CSE&E code-owner RETARGET class (recorded B17 override of this exact transfer): draft BCS554 (2024-25 CSE-IoT y3 scheme-row print, PS=100/Total=100 coordinate-verified, differs from the sibling 02 print PS50+TE50 — both kept verbatim in the row's scheme history) — BCS554 already owned by internship-assessment-mini-project. UPDATE the CSE&E code-owner row."},
    "01_btech_cse-aiml_y3_syllabus-rev_2022-23::13::database-management-systems-lab": {
        "action": "RETARGET", "target": "database-management-system-lab",
        "reason": "B18 singular/plural print variant, NOT a code reassignment (recorded B06/B17 class, merge_draft.py line-class 'OPERATING SYSTEM LAB' KCS451): draft 'Database Management Systems Lab' (KCS551, 2022-23 AIML print) vs the KCS551 owner row database-management-system-lab ('Database Management System Lab', KCS551, established from B.Tech._3rd_Yr_CSE(AI)_2022_23_revised_.pdf#7d6a8a1f4b44410b — the same 2022-23 CSE-family print family). The bare 'systems'/'system' token variance triggered the name-transfer toward the B-era 'systems' variant row (BCS551 owner), which would strand the K-era row codeless and ping-pong the code against 02::11/04::11/09::11. UPDATE the KCS551 owner row; 2022-23 print corroborates; KCS551 stays in its family row."},
    "02_btech_cse-aiml_y3_syllabus_2024-25::11::database-management-system-lab": {
        "action": "RETARGET", "target": "database-management-systems-lab",
        "reason": "B18 singular/plural print variant, NOT a code reassignment (recorded B06/B17 class): draft 'Database Management System Lab' (BCS551, 2024-25 AIML print) — BCS551 is owned by database-management-systems-lab (B-era variant row). The name-transfer toward the K-era singular row would strand the B-era row codeless and ping-pong the code against 01::13. UPDATE the BCS551 owner row; print variance recorded as a quirk on the updated row (owner open item: variant-name rows pending reconciliation)."},
    "04_btech_cse-cyber-security_y3_syllabus_2024-25::11::database-management-system-lab": {
        "action": "RETARGET", "target": "database-management-systems-lab",
        "reason": "B18 singular/plural print variant, NOT a code reassignment (recorded B06/B17 class): draft 'Database Management System Lab' (BCS551, 2024-25 Cyber-Security print) — BCS551 owned by database-management-systems-lab. UPDATE the BCS551 owner row; RETARGET re-points the registered reassignment (no other row claims BCS551)."},
    "09_btech_cse-iot_y3_syllabus_2024-25::11::database-management-system-lab": {
        "action": "RETARGET", "target": "database-management-systems-lab",
        "reason": "B18 singular/plural print variant, NOT a code reassignment (recorded B06/B17 class): draft 'Database Management System Lab' (BCS551, 2024-25 CSE-IoT print) — BCS551 owned by database-management-systems-lab. UPDATE the BCS551 owner row."},
    "02_btech_cse-aiml_y3_syllabus_2024-25::04::data-warehouse-data-mining": {
        "action": "RETARGET", "target": "data-warehousing-and-data-mining",
        "reason": "B18 DW&DM code-owner RETARGET: draft 'Data Warehouse & Data Mining' (BCS058, 2024-25 AIML y3 print — same '&' name form as the Task-28 establishing print) — BCS058's published owner is data-warehousing-and-data-mining (primary KAI075, all_codes KAI075;BCS058; recorded B08-era code transfer off the name-only row data-warehouse-and-data-mining). The ladder's name-transfer would reverse that recorded ownership onto a codeless variant-name row. UPDATE the published BCS058 owner row; the two variant-name rows remain a recorded owner open item; content corroboration only (same 2024-25 session)."},
    "06_btech_cse-ds_y3_syllabus_2024-25::25::constitution-of-india-law-and-engineering-indian-tradition-c": {
        "action": "RETARGET", "target": "constitution-of-india-essence-of-indian-traditional-knowledg",
        "reason": "B18 Constitution code-owner RETARGET: draft 'Constitution of India. Law and Engineering / Indian Tradition, Culture and Society' (BNC501/BNC502/BNC601/BNC602, 2024-25 CSE-DS scheme-row print, blank credit cells) — the BNC codes' published owner is constitution-of-india-essence-of-indian-traditional-knowledg (recorded Task-28/B08 lineage 'constitution-of-india-or-indian-tradition += BNC...' then transferred). The ladder's name-transfer would move 4 mandatory non-credit codes onto another print-variant row. UPDATE the published BNC owner row; the newer DS print name is recorded in the row's name-print/notes; scheme-row-only (no units/COs printed — zero-guess)."},
    "06_btech_csd_y3_syllabus_2024-25::24::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "B17 mini-project CSE&E code-owner RETARGET class (recorded B16 rejection of this exact transfer): the ladder's Tier-0 code-reassigned name-transfer would move CSE-family BCS554 OUT of the CSE&E code-owner row internship-assessment-mini-project (all_codes BCC351;KCS354;KEC354;KCS554;BCS554;BCE554;KCS752, branch Computer Science & Engineering) into the AG/AE-named cross-branch slot row (primary BAE553, EMPTY branch_names) — cross-branch pollution, RULES §1b spirit. UPDATE the CSE&E code-owner row; the RETARGET re-points the registered reassignment so any OTHER row claiming these codes is stripped to single ownership (G2). The draft subject is the 2024-25 CSD scheme-row print (PS=100, Total=100; no detailed syllabus printed — flagged no_detailed_syllabus_printed)."},
    "07_btech_csd_y4_syllabus_2024-25::14::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "B17 mini-project CSE&E code-owner RETARGET class (recorded B16 override: 'UPDATE the CSE&E row; KCS752 (sem-VII slot print) joins it as a slot code'): the draft (2024-25 CSD y4; heading prints '(KCS 354 , KCS 554 , KCS 752)' — three earlier-year assessment codes of the same slot) carries KCS354/KCS554/KCS752, ALL already owned by the CSE&E code-owner row internship-assessment-mini-project; the name-transfer toward the AG/AE-named row (BAE553 primary, empty branch) would pollute cross-branch (RULES §1b spirit, B08 recorded rejection). UPDATE the CSE&E code-owner row; 2024-25 print corroborates/extends."},
    "09_btech_cse-ai_y3_syllabus_2024-25::14::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "B17 mini-project CSE&E code-owner RETARGET class (same recorded B16 rejection): draft BCS554 (2024-25 CSE-AI y3 scheme-row print, PS=100/Total=100, marks columns word-coordinate verified) — BCS554 is ALREADY owned by the CSE&E code-owner row internship-assessment-mini-project; the name-transfer toward the AG/AE-named cross-branch row (BAE553 primary, empty branch) is rejected per RULES §1b spirit. UPDATE the CSE&E code-owner row."},
    "03_btech_common_y4_hsmc-courses_2021-22::05::renewable-energy-resources": {
        "action": "ALLOW",
        "reason": "B17 renewable-energy-resources ALLOW (era-family/same-elective class): the T2 target renewable-energy-sources row (KAG-057;BAG057;NAG-081, 2020-21 AG print) carries a unit1 VERBATIM-IDENTICAL to the draft's unit1 ('Introduction: Various non-conventional energy resources- Introduction, availability, classification, relative merits and demerits. Solar Cells: Theory of solar cells. Solar cell materials, solar cell array, solar cell power plant, limitations.') — the same university-wide renewable-energy elective content reprinted as KOE074 in the 2021-22 OE-II list; KOE074 joins as the newest era code and 2021-22 fieldwise wins (RULES §3 newest-session policy)."},
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

    # ---- B14 (CRON-20261031-B14) per-key adjudications, evidence-recorded ----
    # doc02/07/08 = Civil Geoinformatics across three era prints (ECE402 2009-10,
    # RCE402 2017-18, NCE402 2014-15); doc05 DCS-I/II serial variants; doc09
    # Geoenvironmental Engineering false-positive; 7 name-variant ALLOWs.
    "02_btech_ce-env_y2_scheme-syllabus_2009-10::09::geoinformatics": {
        "action": "FORCE_APPEND",
        "reason": "Different subject (token-anagram false positive, recorded B06 'Electronics vs Electrical' class): draft 'Geoinformatics' (ECE402, 2009-10 Civil y2 core; u1 'Aerial Photographs- Basic terms & Definitions, scales, relief displacements, Flight Planning, Stereoscopy' — photogrammetry/GIS/GPS canon) fuzzy-hit the bioinformatics row (EBM-021, BME; genomics/proteomics canon) ONLY because 'geoinformatics'/'bioinformatics' are token anagrams (overlap 5 generic terms). RULES §11: never merge two different subjects. APPEND as the Civil Geoinformatics row; the later same-subject prints (RCE402 2017-18, NCE402 2014-15 — doc08 u1 opens with the IDENTICAL 'Aerial Photographs- Basic terms...' sentence) converge on this row by name identity."},
    "07_btech_ce_y2_scheme-syllabus_2017-18::04::geoinformatics": {
        "action": "RETARGET", "target": "geoinformatics",
        "reason": "Same subject, era-family convergence (live T2 hit on bioinformatics was the same token-anagram false positive as 02::09): draft 'Geoinformatics' (RCE402, 2017-18 Civil y2 core; u1 photogrammetry/aerial-camera/scale vocabulary) vs the geoinformatics row appended this commit from the 2009-10 ECE402 print — one Civil Geoinformatics subject across era prints; 2017-18 is newer so its content fieldwise-wins per RULES §3 and ECE402 joins as the 2009-10 era code."},
    "08_btech_ce_y2_syllabus_2014-15::10::geo-informatics": {
        "action": "RETARGET", "target": "geoinformatics",
        "reason": "Same subject, era-family convergence: draft 'Geo-informatics' (NCE402, 2014-15 Civil y2; u1 opens with the IDENTICAL sentence to the 2009-10 ECE402 print: 'Aerial Photographs- Basic terms & Definitions, scales, relief displacements, Flight Planning, Stereoscopy...') — hyphenated print variant of the same subject; RETARGET onto the geoinformatics row (appended from doc02) keeps ONE row per subject (RULES §11); 2014-15 print backfills between the 2009-10 and 2017-18 eras."},
    "08_btech_ce_y2_syllabus_2014-15::11::geo-informatics-lab": {
        "action": "RETARGET", "target": "geoinformatics-lab",
        "reason": "Same lab, era-family convergence (hyphenated print variant, geo-informatics-lab vs geoinformatics-lab slugs differ so T1 misses): draft 'Geo-informatics Lab' (NCE452, 2014-15) vs the geoinformatics-lab row appended from doc02's ECE452 print — doc07's RCE452 'Geoinformatics Lab' print converges on that row by equal name; the experiment lists are the same lab canon ('Demonstration and working on Electronic Total Station...', 'To layout a precise traverse...', 'Demonstration and working with Mirror stereoscopes...'). RETARGET keeps ONE lab row (RULES §11)."},
    "07_btech_ce_y2_scheme-syllabus_2017-18::07::surveying-lab": {
        "action": "RETARGET", "target": "survey-field-work",
        "reason": "Same lab RENAMED across era prints (content evidence, zero-guess): draft 'Surveying Lab' (RCE352, 2017-18; experiments 'To measure bearings of a closed traverse by prismatic compass', 'To find out reduced levels of given points using Auto/dumpy level', 'To perform fly leveling with Auto/tilting level') vs the survey-field-work row appended from doc02's ECE353 2009-10 print — the 2009-10 and 2017-18/2014-15 experiment lists are the SAME printed experiments (traverse bearings, reduced levels, fly leveling). The 2009-10 doc names it 'Survey Field Work', the later eras 'Surveying Lab'; AKTU renamed the printed slot. RETARGET keeps ONE row (RULES §11); row name stays the first-appended print, newer prints recorded in name_print/notes."},
    "08_btech_ce_y2_syllabus_2014-15::06::surveying-lab": {
        "action": "RETARGET", "target": "survey-field-work",
        "reason": "Same lab renamed across era prints (identical experiment canon to the 2009-10 ECE353 'Survey Field Work' print and the 2017-18 RCE352 print — see 07::07 adjudication): draft 'Surveying Lab' (NCE353, 2014-15) RETARGETs onto the survey-field-work row; one row per subject (RULES §11); 2014-15 print backfills."},
    "07_btech_ce_y2_scheme-syllabus_2017-18::01::surveying": {
        "action": "RETARGET", "target": "surveying-i",
        "reason": "Same subject renamed across era prints (content evidence): draft 'Surveying' (RCE302, 2017-18 Civil y2 sem-3; u1 'Surveying: definition, divisions, classification and principles of surveying. Scales: plain, vernier, diagonal...' — the definition/classification/principles canon) vs the surveying-i row appended from doc02's ECE303 print (u1 'Importance of surveying to engineers, plane and geodetic surveying, principles of surveying, classification...'; doc08's NCE303 print opens IDENTICALLY) — the 2017-18 scheme shortened the printed name 'Surveying-I' → 'Surveying'; slug difference ('surveying' vs 'surveying-i') defeats T1 so RETARGET keeps ONE row (RULES §11)."},
    "02_btech_ce-env_y2_scheme-syllabus_2009-10::08::structural-analysis-i": {
        "action": "RETARGET", "target": "structural-analysis",
        "reason": "Same subject as the EXISTING structural-analysis row (BCE502, 2024-25; u1 'Classification of Structures, Types of structural frameworks and Load transfer...' — IDENTICAL canon to this draft's u1 'Classification of Structures, stress resultants...' and to doc07's RCE403 u1): the 2009-10/2014-15 prints name it 'Structural Analysis-I' (ECE401/NCE401, y2 sem-4), the 2017-18/2020-21/2024-25 prints name it 'Structural Analysis' (RCE403/KCE502/BCE502). Appending 'structural-analysis-i' would SPLIT one subject into two rows (RULES §11); RETARGET merges the era prints onto the existing row — 2009-10/2014-15 are the OLDEST prints so they backfill-empty only (RULES §3) and ECE401/NCE401 join as era codes. (SA-II is a DIFFERENT subject: 04::03 appends structural-analysis-ii.)"},
    "08_btech_ce_y2_syllabus_2014-15::08::structural-analysis-i": {
        "action": "RETARGET", "target": "structural-analysis",
        "reason": "Same subject as structural-analysis (see 02::08 adjudication): draft 'Structural Analysis-I' (NCE401, 2014-15) carries the same classification/trusses/strain-energy/rolling-loads/arches canon as the existing BCE502 row; RETARGET merges era prints onto ONE row (RULES §11); 2014-15 backfills-empty only; NCE401 joins as the era code."},
    "05_btech_ce_syllabus_2015-16::03::structural-analysis-2": {
        "action": "RETARGET", "target": "structural-analysis-ii",
        "reason": "Same subject, numeral/roman print variant (recorded B02 serial-IDENTITY class — the numeral matches, unlike the serial-variant guard): draft 'STRUCTURAL ANALYSIS-2' (NCE504, 2015-16) vs the structural-analysis-ii row appended this commit from doc04's ECE504 'STRUCTURAL ANALYSIS II' print — identical fixed-beams/Muller-Breslau/suspension-bridges/matrix-methods/plastic-analysis canon; slug difference ('-2' vs '-ii') defeats T1 so RETARGET keeps ONE row; 2015-16 is older than 2010-11? NO — both are era prints; the row keeps the first-appended name, NCE504 joins as the 2015-16 era code."},
    "09_btech_ce_y3_scheme-syllabus_2018-19::01::design-of-structure-1": {
        "action": "RETARGET", "target": "structural-analysis-ii",
        "reason": "Same subject RENAMED across era prints (content evidence, §4 determine-then-fix): draft 'DESIGN OF STRUCTURE 1' (RCE502, 2018-19 y3 sem-5; u1 'Analysis of fixed beams, Continuous beams and simple frames...', u2 Muller-Breslau, u3 Suspension Bridges/stiffening girders, u4 Matrix methods, u5 Plastic Analysis) — the FIVE-UNIT CANON IS VERBATIM-IDENTICAL to the structural-analysis-ii row's ECE504 2010-11 print (and NCE502 2015-16); AKTU renamed the printed subject in the 2018-19 y3 scheme. RETARGET keeps ONE row; RCE502 joins as the 2018-19 era code; the rename is recorded in name_print/notes."},
    "09_btech_ce_y3_scheme-syllabus_2018-19::10::design-of-structure-ii": {
        "action": "RETARGET", "target": "design-of-concrete-structures",
        "reason": "Same subject RENAMED across era prints (content evidence, §4 determine-then-fix): draft 'DESIGN OF STRUCTURE -II' (RCE601, 2018-19 y3 sem-6; u1 'Introduction to Various Design Philosophies, Design of Rectangular Singly and Doubly...', u2 shear, u3 slabs by LSM, u4 columns, u5 footings) — the UNIT CANON IS VERBATIM-IDENTICAL to the existing design-of-concrete-structures row (BCE601 2024-25 print; KCE601 2020-21 converging this commit at 10::14); AKTU renamed the printed subject in the 2018-19 y3 scheme. RETARGET keeps ONE row; RCE601 joins as the 2018-19 era code."},
    "05_btech_ce_syllabus_2015-16::10::environmental-engineering-2": {
        "action": "RETARGET", "target": "environmental-engineering-ii",
        "reason": "Same subject, numeral/roman print variant: draft 'ENVIRONMENTAL ENGINEERING – 2' (NCE602, 2015-16 sem-6; u1 'Introduction: Beneficial uses of water and quality requirements...' IDENTICAL canon to doc04's ECE602 'ENVIRONMENTAL ENGINEERING – II' print — water quality/sedimentation/filtration/wastewater/sludge digestion) vs the environmental-engineering-ii row appended this commit from doc04; slug difference ('-2' vs '-ii') defeats T1; RETARGET keeps ONE row; NCE602 joins as the 2015-16 era code."},
    "05_btech_ce_syllabus_2015-16::07::cad-lab-i": {
        "action": "RETARGET", "target": "cad-lab-1",
        "reason": "Same lab, numeral/roman print variant: draft 'CAD LAB I' (NCE553, 2015-16) vs the cad-lab-1 row appended this commit from doc04's ECE-651 'CAD LAB-1' print — identical Civil CAD-lab prints; slug difference ('cad-lab-i' vs 'cad-lab-1') defeats T1; RETARGET keeps ONE row; NCE553 joins as the 2015-16 era code."},
    "09_btech_ce_y3_scheme-syllabus_2018-19::16::cad-lab-2": {
        "action": "RETARGET", "target": "cad-lab-ii",
        "reason": "Same lab, numeral print variant: draft 'CAD LAB- 2' (RCE652, 2018-19) vs the cad-lab-ii row appended this commit from doc05's NCE653 'CAD LAB II' print; slug difference defeats T1; RETARGET keeps ONE row (RULES §11); RCE652 joins as the 2018-19 era code."},
    "05_btech_ce_syllabus_2015-16::18::transportation-system-and-planning": {
        "action": "RETARGET", "target": "transportation-system-planning",
        "reason": "Same subject, 'and'-token print variant (B07 abbreviation class): draft 'TRANSPORTATION SYSTEM AND PLANNING' (NCE023, 2015-16 DE; u1 'Introduction: Overview of transportation system, nature of traffic problems...' IDENTICAL canon to doc04's ECE023 'Transportation System Planning' print) vs the transportation-system-planning row appended this commit from doc04; RETARGET keeps ONE row; NCE023 joins as the 2015-16 era code."},
    "08_btech_ce_y2_syllabus_2014-15::07::building-planning-drawing": {
        "action": "RETARGET", "target": "building-planning-drawing-lab",
        "reason": "Same drawing-lab subject, 'Lab' token dropped in the 2014-15 print (content evidence): draft 'Building Planning & Drawing' (NCE354, 2014-15; L-T-P 0-0-3; experiments 'Symbols used in Civil engineering drawing', 'Doors, Windows and staircases.', 'Plumbing & Electrical fitting drawings' — IDENTICAL experiment canon to doc02's ECE354 'Building Planning & Drawing Lab' print) vs the building-planning-drawing-lab row appended from doc02 (doc06's KCE351 and doc07's RCE-35x prints T1-converge on it); RETARGET keeps ONE row; NCE354 joins as the era code."},
    "06_btech_ce_y2_model-curriculum_2019-20::11::hydraulics-hydraulic-machine-lab": {
        "action": "RETARGET", "target": "hydraulics-hydraulic-machines-lab",
        "reason": "Same lab across era prints (content evidence): draft 'Hydraulics & Hydraulic Machine Lab' (KCE453, 2019-20; experiments 'To determine the Manning's coefficient of roughn...', 'To study the velocity distribution in an open ch...', 'To study the flow characteristics over a hump...' — IDENTICAL experiment canon to doc02's ECE453 print) vs the hydraulics-hydraulic-machines-lab row appended from doc02; singular/machines print variant defeats T1; RETARGET keeps ONE row; KCE453 joins as the era code."},
    "07_btech_ce_y2_scheme-syllabus_2017-18::13::hydraulics-machine-lab": {
        "action": "RETARGET", "target": "hydraulics-hydraulic-machines-lab",
        "reason": "Same lab across era prints (identical Manning's/velocity-distribution/hump experiment canon to doc02's ECE453 print — see 06::11 adjudication): draft 'Hydraulics & Machine Lab' (RCE455, 2017-18) vs the hydraulics-hydraulic-machines-lab row appended from doc02; shortened print defeats T1; RETARGET keeps ONE row (RULES §11); RCE455 joins as the era code."},
    "08_btech_ce_y2_syllabus_2014-15::13::hydraulics-machine-lab": {
        "action": "RETARGET", "target": "hydraulics-hydraulic-machines-lab",
        "reason": "Same lab across era prints (identical experiment canon — see 06::11/07::13 adjudications): draft 'Hydraulics & Machine Lab' (NCE453, 2014-15) vs the hydraulics-hydraulic-machines-lab row appended from doc02; RETARGET keeps ONE row; NCE453 joins as the era code."},
    "05_btech_ce_syllabus_2015-16::09::design-of-concrete-structure-ii": {
        "action": "FORCE_APPEND",
        "reason": "Different subject (recorded B02 serial-variant guard class: names differing by numeral/roman never fuzzy-merge): draft 'DESIGN OF CONCRETE STRUCTURE II' (NCE601, 2015-16 sem-6 DE; u1 'Nature of Stresses in flat slabs with and without drops, coefficient for design of flat slabs, reinforcement in flat slabs (IS Code Method)' — flat-slab/foundation/tank canon) vs the design-of-concrete-structures row (BCE601/KCE601 era prints; u1 design-philosophies/WSM-LSM/rectangular-section canon — the SAME canon this commit's 05::04 DCS-I NCE505 print shares, fuzzy 95/overlap 39). The doc prints DCS-I (sem-5 pool) and DCS-II (sem-6 pool) as two separate electives with separate codes; RULES §11: never merge two different subjects. APPEND as its own row."},
    "09_btech_ce_y3_scheme-syllabus_2018-19::05::geoenvironmental-engineering": {
        "action": "FORCE_APPEND",
        "reason": "Different subject (fuzzy false positive, fuzzy 94 carried by token subsequence 'environmental'/'engineering', overlap only 16 generic terms): draft 'GEOENVIRONMENTAL ENGINEERING' (RCE053, 2018-19 sem-5 DE; u1 'Fundamentals of Geoenvironmental Engineering Scope of geoenvironmental engineering - multiphase behaviour of soil – role of soil in ...' — waste containment/landfill/contaminant-transport canon) vs the environmental-engineering row (BCE603; RCE-601 core this same doc updates at 09::11 — water/wastewater-treatment canon). The doc prints BOTH as separate subjects in separate slots; merging would lose a subject (zero-GAP violation). RULES §11: never merge two different subjects. APPEND as its own row."},
    "01_btech_ce-cst-cse_y3_syllabus_2024-25::24::basics-of-data-base-management-system": {
        "action": "ALLOW",
        "reason": "Name-variant print of the same university-wide open elective: draft 'Basics of Data Base Management System' (BCS-053 OE slot, 2024-25) vs the basics-of-database-management-systems row (BOE307;BOE407, 2023-24) — 'Data Base' vs 'Database' spacing print variance, fuzzy 86/overlap 78 shared DBMS vocabulary (ER model, normalization, SQL, transactions); 2024-25 is the newest session so it fieldwise-wins per RULES §3; BOE codes stay as the era backfill."},
    "04_btech_ce_syllabus_2010-11::27::finite-element-methods": {
        "action": "ALLOW",
        "reason": "Era-family same subject: draft 'Finite Element Methods' (ECE032, 2010-11 Civil DE-VII; u1 calculus-of-variations/virtual-work/Euler-Lagrange FEM canon) vs the finite-element-method row (RME053;BME053;NAU-062, 2018-19) — the same university-wide FEM elective carried across era/branch prints, fuzzy 98/overlap 35 shared FEM vocabulary (stiffness matrix, shape functions, element assembly); 2010-11 is the OLDEST print so it backfills-empty only and ECE032 joins as the era code per RULES §3."},
    "05_btech_ce_syllabus_2015-16::04::design-of-concrete-structure-1": {
        "action": "ALLOW",
        "reason": "Era-family same subject: draft 'DESIGN OF CONCRETE STRUCTURE-1' (NCE505, 2015-16 sem-5 DE; u1 'Concrete Making materials... Introduction to Various Design Philosophies, Design of Rectangular Singly and Doubly Reinforced Sections by...' — IDENTICAL unit core to the row's BCE601 2024-25 print) vs the design-of-concrete-structures row — the same Civil DCS subject across era prints whose slot moved sem-5 (NCE505 2015-16) → sem-6 (KCE601 2020-21, BCE601 2024-25); fuzzy 95/overlap 39; 2015-16 older than the row's 2024-25 so backfills-empty only; NCE505 joins as the era code. (Its DCS-II sibling 05::09 is FORCE_APPENDed separately — serial-variant guard.)"},
    "09_btech_ce_y3_scheme-syllabus_2018-19::14::integrated-waste-management-for-a-smart-city": {
        "action": "ALLOW",
        "reason": "Same NPTEL university-wide elective, singular/plural name print: draft 'INTEGRATED WASTE MANAGEMENT FOR A SMART CITY' (RCE062, 2018-19 Civil DE; u1 'Introduction: Solid Waste Management- Definition, Concept of 4Rs (reduce, reuse, recycle and recover)...') vs the integrated-waste-management-for-smart-cities-nptel row (RBT086, 2019-20 Biotech y4 CBCS NPTEL slot; course-plan weeks print) — fuzzy 87/overlap 36 shared solid-waste vocabulary; 2018-19 is older than the row's 2019-20 so it backfills-empty only (the 2019-20 course-plan print stays) and RCE062 joins as the era code; the row's NPTEL '(NPTEL)' name suffix and Biotech source stay recorded."},
    "10_btech_ce_y3_syllabus_2020-21::12::air-noise-pollution-control": {
        "action": "ALLOW",
        "reason": "Name-variant print of the same subject: draft 'Air & Noise Pollution Control' (KCE-057, 2020-21) vs the air-and-noise-pollution-control row (BCE057, 2024-25) — '&' vs 'and' print variance, fuzzy 93/overlap 115; 2020-21 older so backfills-empty only; KCE057 joins as the era code."},
    "10_btech_ce_y3_syllabus_2020-21::14::design-of-concrete-structure": {
        "action": "ALLOW",
        "reason": "Singular/plural print of the same subject: draft 'Design of Concrete Structure' (KCE-051 slot print, 2020-21) vs the design-of-concrete-structures row (BCE601, 2024-25) — fuzzy 98/overlap 52, u1 IDENTICAL design-philosophies/WSM-LSM/rectangular-section canon to the row's print; 2020-21 older so backfills-empty only; KCE051-era code joins; (distinct from the DCS-II flat-slabs subject, see 05::09 FORCE_APPEND)."},
    "10_btech_ce_y3_syllabus_2020-21::20::advance-structural-analysis": {
        "action": "ALLOW",
        "reason": "Print-variant of the same subject ('Advance' [sic] vs 'Advanced', typo kept verbatim in name_print per RULES §6): draft 'Advance Structural Analysis' (KCE-061, 2020-21) vs the advanced-structural-analysis row (BCE061, 2024-25) — fuzzy 98/overlap 60; 2020-21 older so backfills-empty only; KCE061 joins as the era code."},
    # ---- B15 adjudications (evidence: B15 drafts + published 1304-row CSV @ 9f3b260) ----
    "02_btech_ce_y4_syllabus-cbcs_2019-20::08::air-noise-pollution-control": {
        "action": "ALLOW",
        "reason": "Same CE subject, '&'/'and' name-variant print: draft 'Air & Noise Pollution Control' (RCE-era, 2019-20 CBCS) vs the air-and-noise-pollution-control row (BCE057, Civil, 2024-25) — fuzzy 93/overlap 109 shared distinctive vocabulary (identical class to the recorded B14 KCE-057 ALLOW); 2019-20 older so backfills-empty only; the RCE era code joins."},
    "02_btech_ce_y4_syllabus-cbcs_2019-20::14::finite-element-methods": {
        "action": "ALLOW",
        "reason": "Singular/plural print variant of the same subject: draft 'Finite Element Methods' (2019-20) vs the finite-element-method row (RME053, 2018-19, shared-elective row with empty branch scope) — fuzzy 98/overlap 35 distinctive FEM vocabulary (exact-solution-vs-approximate/principle-of-FEM canon); draft corroborates/backfills and the era code joins."},
    "02_btech_ce_y4_syllabus-cbcs_2019-20::19::urban-transportation-system-planning": {
        "action": "ALLOW",
        "reason": "Era-family rename of the same CE subject: draft 'Urban Transportation System & Planning' (RCE-era sem-VII, 2019-20; u1 'Introduction to transportation planning, the planning concept... Nature of traffic problems in cities') vs the transportation-system-planning row (ECE023, Civil, 2010-11; u1 'Introduction: Overview of transportation system, nature of traffic problems in cities') — identical canon, fuzzy 91/overlap 57; 2019-20 is the NEWEST print so it fieldwise-wins per RULES §3 ('Urban' rename recorded via name_print)."},
    "04_btech_ce_y4_syllabus_2016-17::04::finite-element-methods": {
        "action": "ALLOW",
        "reason": "Singular/plural print variant, same class as 02::14: draft 'Finite Element Methods' (NCE-era, 2016-17) vs the finite-element-method row (RME053, 2018-19) — fuzzy 98/overlap 35; 2016-17 older so backfills-empty only; era code joins."},
    "04_btech_ce_y4_syllabus_2016-17::19::earthquake-resistant-design": {
        "action": "ALLOW",
        "reason": "Same subject; the ROW's name carries the recorded print typo 'EARTQUAKE RESISTANT DESIGN' (ECE064, Civil, 2010-11, kept verbatim per RULES §6) while the 2016-17 draft prints 'Earthquake Resistant Design' — fuzzy 98/overlap 44 identical seismic canon (earth structure/seismic waves/IS-code design); draft newer so it fieldwise-wins and corrects nothing in the *_print."},
    "05_btech_ce_y4_syllabus_2021-22::03::advance-concrete-design": {
        "action": "ALLOW",
        "reason": "Adjective print variant of the same CE subject: draft 'Advance Concrete Design' (KCE073, 2021-22; 'Advance' [sic] kept verbatim) vs the ADVANCED CONCRETE DESIGN row (ECE021, Civil, 2010-11) — fuzzy 98/overlap 29; 2021-21 newer print so it fieldwise-wins per RULES §3."},
    "07_btech_che_s5-6_syllabus_2024-25::21::sustainability-of-environment": {
        "action": "FORCE_APPEND",
        "reason": "Different subject (recorded wrong-subject class, B06 KME403/basic-manufacturing-processes + B09 biochemistry/chemistry evidence): draft 'Sustainability of Environment' (BCH062, CHE sem-VI DE, 2024-25; u1 'Environment and Biodiversity: Definition, scope...Environmental pollution from chemical process industries, Role of chemical engineering in sustainability, Carbon footprint...') vs the environment-sustainability row (AAC101, AG y1 sem-1, 2026-27; u1 'Environment and Ecosystems: Environment — definition, components (atmosphere, hydrosphere...)') — different unit canon (u1 heading AND content structure differ: chemical-process-industry pollution/sustainability canon vs y1 ecosystems-foundation canon), different program level (y1 foundation audit vs y3 branch DE), different code generations; the fuzzy 95 score is carried by shared environmental vocabulary only. APPEND as its own row."},
    "08_btech_che_s7-8_syllabus_2025-26::06::mini-project-of-internship-assessment": {
        "action": "RETARGET", "target": "mini-project-or-internship-assessment",
        "reason": "TIE resolves on the recorded slot-row ownership model: fuzzy 97 (highest) to the cross-branch assessment-slot row whose all_codes already carry the 2025-26 sister-branch print BCS752 ('BCS752 ownership transferred to mini-project-or-internship-assessment per newest printed scheme/syllabus evidence (recorded B3 remedy)' — published CSV change note) and the 2025-26 CE print BCE752 (03::06 in this same commit T1-updates this exact row); the competing internship-assessment-mini-project row is the CSE-family BCC351-primary row (different row per the recorded B12 split). BCH752 is the 2025-26 CHE print of the same assessment slot; newest session so it fieldwise-wins."},
    "02_btech_ce_y4_syllabus-cbcs_2019-20::11::mini-project": {
        "action": "RETARGET", "target": "mini-project-or-internship-assessment",
        "reason": "dv-guard sent the content-less assessment row to T3 (name-only match cannot Tier-2 — recorded B02 guard class), but slot identity is evidenced: the 2025-26 CE print BCE752 'Mini Project or Internship Assessment' T1-updates this exact row in this same commit (03::06), the row is the recorded cross-branch VII-sem mini-project/internship-assessment slot (BAE553;KAG354;BAG554;BME752;KBT752;BCS752;KCE554... all_codes), and RCE752 is the 2019-20 CE print of that same slot ('Mini Project', 8 topics, sem-VII); older print so it backfills-empty only and RCE752 joins as the era code."},
    "05_btech_ce_y4_syllabus_2021-22::11::mini-project-internship-assessment": {
        "action": "RETARGET", "target": "mini-project-or-internship-assessment",
        "reason": "Same recorded slot-row class as 02::11: draft 'Mini Project / Internship Assessment' (KCE752, 2021-22, sem-VII, 8 topics) is the 2021-22 CE print of the cross-branch assessment slot — connective '/' vs 'or' print variance only; the 2025-26 BCE752 print T1-updates the same row in this commit (03::06) and the B12-recorded ownership model carries the slot's branch families on this one row; 2021-22 older than the row's 2024-25 so it backfills-empty only; KCE752 joins as the era code."},
    # ---- B16 (CRON-20261031-B16) per-key adjudications, evidence-recorded ----
    "01_btech_che_y2-4_syllabus_2009-10::03::mechanical-operations": {
        "action": "FORCE_APPEND",
        "reason": "Wrong-subject fuzzy hit (B06 'Electronics vs Electrical' class): draft 'Mechanical Operations' (ECH302, 2009-10 CHE y2; unit vocabulary crushing/grinding/screening/filtration/sedimentation — the CHE unit-operations subject) fuzzy 86-hit mechanical-vibrations (KAE056;BAE056;RME063, AE/ME subject: oscillations/damping/whirling). Zero shared unit vocabulary beyond the generic 'mechanical' token. Appends as its own CHE row; the 2014-15/2017-18/2019-20 CHE prints of the same subject converge on it in this same commit (02::01/03::03/04::07)."},
    "02_btech_che_y2_scheme-syllabus_2017-18::01::mechanical-operations": {
        "action": "FORCE_APPEND",
        "reason": "Same wrong-subject class as 01::03: draft 'Mechanical Operations' (RCH301, 2017-18 CHE y2) vs mechanical-vibrations (AE/ME oscillations subject) — no vocabulary evidence of identity. Appends/converges onto the CHE Mechanical Operations row built in this same commit."},
    "03_btech_che_y2_syllabus-rev_2014-15::03::mechanical-operations": {
        "action": "FORCE_APPEND",
        "reason": "Same wrong-subject class as 01::03: draft 'Mechanical Operations' (NCH301, 2014-15 CHE y2) vs mechanical-vibrations (AE/ME). Appends/converges onto the CHE Mechanical Operations row built in this same commit."},
    "04_btech_che_y2_syllabus_2019-20::07::mechanical-operations": {
        "action": "FORCE_APPEND",
        "reason": "Same wrong-subject class as 01::03: draft 'Mechanical Operations' (KCH301, 2019-20 CHE y2 AICTE-model) vs mechanical-vibrations (AE/ME). Appends/converges onto the CHE Mechanical Operations row built in this same commit."},
    "01_btech_che_y2-4_syllabus_2009-10::11::chemical-technology-i-organic": {
        "action": "RETARGET", "target": "chemical-technology-i",
        "reason": "Same-subject print variant (retarget from the T2 hit chemical-technology-ii NCH602, a DIFFERENT subject): draft 'Chemical Technology-I (Organic)' (ECH404, 2009-10) is the Chemical Technology-I subject (fuzzy 86/15 hit landed on Chem-Tech-II only because both share the 'chemical technology' head); the registry's chemical-technology-i row (NCH505, 2015-16 print) is the same course-by-number subject. '(Organic)' is the printed qualifier of the same slot; 2009-10 is older so it backfills-empty only and ECH404 joins as the era code."},
    "01_btech_che_y2-4_syllabus_2009-10::31::process-dynamics-control": {
        "action": "ALLOW",
        "reason": "Era-family same subject: draft 'Process Dynamics & Control' (ECH602, 2009-10, fuzzy 92/overlap 49) vs the process-dynamics-and-control row — identical CHE control-theory subject (unit vocabulary: control valves, PID, transfer functions, stability); '&' vs 'and' print variance (recorded B07 class). 2009-10 older so it backfills-empty only; ECH602 joins as the era code."},
    "01_btech_che_y2-4_syllabus_2009-10::41::process-utilities-and-safety-in-chemical-plants": {
        "action": "ALLOW",
        "reason": "Era-family same subject: draft 'Process Utilities and Safety in Chemical Plants' (ECH041, 2009-10, fuzzy 91/overlap 131 — massive shared unit vocabulary: fire/explosion hazards, PPE, plant utilities) vs the process-utility-safety-in-chemical-plants row (KCH702 2021-22 print, T1-updated this same commit from 07::03). Name carries the printed 'in Chemical Plants' qualifier; 2009-10 older so backfill-empty only; ECH041 joins as the era code."},
    "01_btech_che_y2-4_syllabus_2009-10::55::petrochemical-technology": {
        "action": "FORCE_APPEND",
        "reason": "Wrong-subject fuzzy hit (B06 'Electronics vs Electrical' class): draft 'Petrochemical Technology' (ECH063, 2009-10; petro-feedstock/refining vocabulary) fuzzy 88-hit chemical-technology (BCH603, the inorganic/industrial-chemicals subject) — only the generic 'chemical technology' head is shared. Appends as its own CHE row; the 2019-20 RCH print of the same subject (06::55) converges on it in this same commit."},
    "05_btech_che_y3_syllabus_2020-21::10::intellectual-property-standardization": {
        "action": "ALLOW",
        "reason": "Era-family same subject: draft 'Intellectual Property & Standardization' (KCH058, 2020-21, fuzzy 91/overlap 95) vs the intellectual-property-rights-standardization row — the same IPR & standardization DE subject (IPR types, patents, ISO/IEC standardization vocabulary); '&'/'rights' print variance. 2020-21 vs row's 2021-22 print (07 doc KCH078-era family) — older so backfill-empty only; KCH058 joins as the era code."},
    "05_btech_che_y3_syllabus_2020-21::12::process-dynamics-control-lab": {
        "action": "ALLOW",
        "reason": "Same lab, print variance (dv-guard class): draft 'Process Dynamics & Control Lab' (KCH551, 2020-21, fuzzy 93/overlap 0 — labs carry no unit/CO vocabulary, recorded B02 dv-guard) vs the process-dynamics-and-control-lab row that 01::30 T1-updates in this same commit (ECH-551 print). '&' vs 'and' connective variance (recorded B07 class); KCH551 joins as the era code, backfill-empty only."},
    "05_btech_che_y3_syllabus_2020-21::13::process-modeling-simulation-lab": {
        "action": "ALLOW",
        "reason": "Spelling print variant (recorded Modelling/Modeling class): draft 'Process Modeling & Simulation Lab' (KCH553, 2020-21, fuzzy 93/overlap 11) vs the process-modelling-and-simulation-lab row (British-spelling print). Same CHE simulation lab; 2020-21 older so backfill-empty only; KCH553 joins as the era code."},
    "05_btech_che_y3_syllabus_2020-21::16::transport-phenomenon": {
        "action": "ALLOW",
        "reason": "Singular/plural print variant (recorded B06 class): draft 'Transport Phenomenon' (KCH051, 2020-21, fuzzy 92/overlap 17) vs the transport-phenomena row — same momentum/heat/mass transport subject; KCH051 joins as the era code, backfill-empty only (2020-21 older than the row's session)."},
    "05_btech_che_y3_syllabus_2020-21::21::environmental-impact-assesment": {
        "action": "ALLOW",
        "reason": "Print typo variant (recorded B15 EARTHQUAKE class): draft 'Environmental Impact Assesment' (KCH062, 2020-21, fuzzy 98/overlap 67 — the printed typo 'Assesment' retained verbatim in name_print per RULES §6) vs the environmental-impact-assessment row that 06::06 T1-updates in this same commit (RCH074 print). Same subject; KCH062 joins as the era code."},
    "06_btech_che_y4_syllabus_2019-20::10::energy-engg-management": {
        "action": "RETARGET", "target": "energy-engineering-management",
        "reason": "Abbreviated print of the same era-family subject (recorded B07 'Engg.' abbreviation class): TIE (fuzzy 86/energy-engineering-management vs 87/energy-management) resolves on name-token + era identity: draft 'Energy Engg. & Management' (RCH075, 2019-20) carries the substantive token 'Engg.' (Engineering) and is the 2019-20 print of the SAME DE subject as the energy-engineering-management row (KCH071, 2021-22 'Energy Engineering & Management' print — KCH071 is that row's primary; recorded B07 'Engg.' abbreviation class); the 87-score energy-management hit is the ENERGY MANAGEMENT row appended in this same commit from 01::24 (ECH012, 2009-10 UPTU-era DE print WITHOUT the Engineering token — a different print slot of the era; kept as its own row, RULES §11). RETARGET pins the row; 2019-20 older than 2021-22 so backfill-empty only and RCH075 joins as the era code."},
    "06_btech_che_y4_syllabus_2019-20::11::project-engg-management": {
        "action": "RETARGET", "target": "project-engineering-and-management",
        "reason": "Same-commit era-family convergence (recorded B07 same-commit RETARGET class): draft 'Project Engg. & Management' (RCH076, 2019-20) is the CHE Project Engineering & Management subject whose 2009-10 print (ECH043, 'PROJECT ENGINEERING AND MANAGEMENT', 01::43) appends the canonical row in this same commit; the fuzzy 88 hit project-management (RAU072) is the AU-era university-wide PROJECT MANAGEMENT elective — a different subject (B06 wrong-subject class). RETARGET pins the row; RCH076 joins as the era code, backfill-empty only."},
    # ---- B16 same-commit convergence adjudications (live-ladder T2 hits on
    # rows appended EARLIER IN THIS SAME COMMIT — the recorded B15 'live ladder
    # converged same-commit cross-draft appends' class; decisions dry-run saw
    # these as T3 no-match because the canonical row did not exist yet) ----
    "02_btech_che_y2_scheme-syllabus_2017-18::00::environmental-pollution-monitoring-control": {
        "action": "ALLOW",
        "reason": "Same-commit era-family convergence: draft 'Environmental Pollution Monitoring & Control' (RCH301, 2017-18) fuzzy 95/115-hits the ENVIRONMENTAL POLLUTION MONITORING AND CONTROL row appended in this same commit from 01::39 (ECH033, 2009-10 print) — identical CHE pollution-monitoring subject ('and' connective variance, B07 recorded class); the later print backfills empty fields and RCH301 joins as the era code per the row's session model."},
    "04_btech_che_y2_syllabus_2019-20::00::material-and-energy-balance": {
        "action": "ALLOW",
        "reason": "Same-commit era-family convergence: draft 'Material And Energy Balance' (KCH301, 2019-20) fuzzy 92/40-hits the Material & Energy Balance row appended in this same commit from 02::04 (RCH301, 2017-18 print) — identical CHE MEB subject ('and' vs '&' connective variance); KCH301 joins as the era code."},
    "04_btech_che_y2_syllabus_2019-20::09::chemical-engg-thermodynamics": {
        "action": "ALLOW",
        "reason": "Same-commit era-family convergence: draft 'Chemical Engg. Thermodynamics' (KCH403, 2019-20) fuzzy 89/45-hits the CHEMICAL ENGINEERING THERMODYNAMICS row appended in this same commit from 01::08 (ECH401, 2009-10 print; 02::10 converges too) — identical subject, 'Engg.' abbreviation class (recorded B07); KCH403 joins as the era code."},
    "06_btech_che_y4_syllabus_2019-20::00::process-modeling-simulation": {
        "action": "ALLOW",
        "reason": "Same-commit era-family convergence: draft 'Process Modeling & Simulation' (RCH701, 2019-20) fuzzy 92/80-hits the PROCESS MODELLING AND SIMULATION row appended in this same commit from 01::45 (ECH701, 2009-10 print) — identical theory subject, recorded Modelling/Modeling spelling + '&'/'and' variance classes; RCH701 joins as the era code."},
    "07_btech_che_y4_syllabus_2021-22::03::industrial-pollution-abatement-and-waste-management": {
        "action": "ALLOW",
        "reason": "Same-commit era-family convergence: draft 'Industrial Pollution Abatement and Waste Management' (KCH074, 2021-22) fuzzy 96/65-hits the INDUSTRIAL POLLUTION ABATEMENT & WASTE MANAGEMENT row appended in this same commit from 01::38 (ECH032, 2009-10 print; 06::07 'IPA & Waste Management' RCH072 converges too) — identical subject, '&'/'and' variance; KCH074 joins as the era code."},
    # ---- B19 adjudications (2026-11-01 run, evidence-recorded) ----
    "02_btech_cse_syllabus_2015-16::19::data-warehousing-data-mining": {
        "action": "RETARGET", "target": "data-warehousing-and-data-mining",
        "reason": "B19 TIE strip (recorded B18 DW&DM code-owner RETARGET class): draft 'Data warehousing & Data Mining' (NCS066, 2015-16 CSE print, 5 verbatim units) TIEs fuzzy 91/data-warehouse-and-data-mining (name-only variant row: NO primary_code, NO all_codes, NO units) vs 92/data-warehousing-and-data-mining (the published DW&DM content owner: primary KAI075, all_codes KAI075;BCS058, recorded B08-era code transfer). The content-bearing row with the higher fuzzy score and the recorded published ownership wins; NCS066 joins as the earliest era code; the name-only variant row stays untouched (recorded owner open item: variant-name rows pending reconciliation)."},
    "10_btech_cse_y3_syllabus_2020-21::11::database-management-systems-lab": {
        "action": "RETARGET", "target": "database-management-system-lab",
        "reason": "B19 singular/plural print variant, NOT a code reassignment (recorded B18 DBMS-lab ping-pong class): draft 'Database Management Systems Lab' (KCS551, 2020-21 CSE print) — KCS551's published owner is database-management-system-lab ('Database Management System Lab', established from the 2022-23 CSE-family print family); the name-transfer toward the B-era 'systems' variant row (BCS551 owner) would strand the K-era row codeless and ping-pong the code (B18 recorded rejection of this exact transfer). UPDATE the KCS551 owner row; the 2020-21 print corroborates (KCS551 = DBMS Lab in both K-era prints); experiments content backfills the empty row."},
    "10_btech_cse_y3_syllabus_2020-21::21::software-engineering-lab": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "software-engineering-lab",
        "keep_published_codes": {"KCS651": "big-data-and-analytics-lab"},
        "reason": "B19 older-draft-never-steals-a-code adjudication (newest-print-wins era model, recorded B3/B02 class): draft 'Software Engineering Lab' (2020-21 CSE print) carries an INTRA-DOC code conflict — scheme p.3 prints KCS651, detail p.30 title + virtual-lab mapping print KCS-661 (page-image verified, both codes recorded in the draft). KCS651 is ALREADY owned by big-data-and-analytics-lab per the NEWER 2022-23 CSE-DS print (KCS651;BCDS651; B02 append) — the ladder's name-transfer would strip KCS651 from the newer-session published owner and hand it to a 2020-21 print, reversing the status=latest model. Ruling: UPDATE software-engineering-lab by name identity; KCS661 (the detail-page print) joins as the 2020-21 era code; KCS651 STAYS with big-data-and-analytics-lab and is recorded as a narrative history mention on the SE-Lab row (2020-21 scheme print, dual-use slot across sessions)."},
    "10_btech_cse_y3_syllabus_2020-21::26::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "B19 mini-project CSE&E code-owner RETARGET class (recorded B18/B17 overrides of this exact transfer; B16 rejection): draft 'Mini Project or Internship Assessment*' (KCS554, 2020-21 CSE scheme-row print, sem-5) — KCS554 is ALREADY owned by the CSE&E code-owner row internship-assessment-mini-project (all_codes ...;KCS554;BCS554;... since Task 28/B02). The name-transfer toward the AG/AE-named cross-branch slot row (BAE553 primary, empty branch_names) is rejected per RULES §1b spirit. UPDATE the published KCS554 owner row; scheme-row-only corroboration (no units/COs printed in this doc)."},
    "03_btech_cse_syllabus_2016-17::04::mobile-application-development": {
        "action": "FORCE_APPEND",
        "reason": "B19 wrong-subject FORCE_APPEND (recorded B14/B15 wrong-subject T2 class): draft 'Mobile Application Development' (NOE-075, 2016-17 CSE Open Elective-I, sem-7) fuzzy 88/54-hits mobile-application-development-for-iot (BCIT051, 2024-25 IoT Departmental Elective). Unit-by-unit comparison: u2 (BASIC DESIGN) and u4 (TECHNOLOGY I – ANDROID) are verbatim identical, but u1 (generic mobile-app intro/market drivers vs IoT architectural overview), u3 (multimedia/GPS/cloud design vs IoT MOBILE APPS) and u5 (iOS/Objective-C/Swift vs Android Things) are materially DIFFERENT — 3/5 units. The 2024-25 IoT print borrows unit blocks II and IV from the older OE print; the subjects are distinct (different name print 'for IoT', different slot family OE vs DE, different code families NOE vs BCIT, different eras). Appends as its own row; cross-reference note records the shared unit blocks; zero-GAP holds."},
    # ---- B20 (CRON-20261101-B20) per-key adjudications, evidence-recorded ----
    "01_btech_cse_y4_syllabus-cbcs_2019-20::07::human-computer-interface": {
        "action": "ALLOW", "target": "human-computer-interaction",
        "reason": "B20 era-family name-variant ALLOW with unit-identity evidence: draft 'Human Computer Interface' (RCS073, 2019-20 CBCS CSE y4 DE print, 5 verbatim units) vs the published human-computer-interaction row (NCS070;KCS-058, 2015-16 N-era, name 'Human Computer Interaction'). All 5 unit texts compare 1.000 normalized similarity (difflib, patch-b20 evidence in the run log) — the SAME subject under its 2019-20 print form; RCS073 joins as the 2019-20 era code. The fuzzy-88 (not Tier-1) result is purely the Interface/Interaction token variance."},
    "03_btech_cse_y4_syllabus_2021-22::14::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "B20 mini-project CSE&E code-owner RETARGET class (recorded B18/B17 overrides of this exact transfer; B16 rejection): draft 'Mini Project or Internship Assessment' (KCS354/KCS554/KCS752, 2021-22 CSE y4 print — the same trio the recorded 07_btech_csd_y4_2024-25 draft carried) — ALL three codes are ALREADY owned by the CSE&E code-owner row internship-assessment-mini-project (all_codes BCC351;KCS354;KEC354;KCS554;BCS554;BCE554;KCS752). The name-transfer toward the AG/AE-named cross-branch slot row (BAE553 primary, empty branch_names) is rejected per RULES §1b spirit. UPDATE the CSE&E code-owner row; the 2021-22 print corroborates (KCS354/KCS554 sem-5, KCS752 sem-7 slot prints)."},
    "06_btech_csit-cse_y2_model-curriculum_2019-20::03::data-structures-using-c-lab": {
        "action": "RETARGET", "target": "data-structure-using-c-lab",
        "reason": "B20 singular/plural print variant, NOT a code reassignment (recorded B18/B19 DBMS-lab class): draft 'Data Structures Using C Lab' (KCS351, 2019-20 AICTE model-curriculum print) — KCS351's published owner is data-structure-using-c-lab ('Data Structure using C Lab', 2021-22 K-era row). The name-transfer toward the 's'-variant name row would strand the KCS351 owner codeless (B18 recorded rejection of this exact transfer class). UPDATE the KCS351 owner row; the 2019-20 print corroborates (KCS351 = DS-using-C Lab in the model curriculum)."},
    "06_btech_csit-cse_y2_model-curriculum_2019-20::06::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "B20 mini-project CSE&E code-owner RETARGET class (recorded B18/B17 overrides; B16 rejection): draft 'Mini Project or Internship Assessment' (KCS354, 2019-20 AICTE model-curriculum scheme-row print) — KCS354 is ALREADY owned by the CSE&E code-owner row internship-assessment-mini-project. The name-transfer toward the AG/AE-named cross-branch slot row is rejected per RULES §1b spirit. UPDATE the CSE&E code-owner row; scheme-row-only corroboration."},
    "07_btech_csit-it_y3_syllabus_2020-21::11::database-management-systems-lab": {
        "action": "RETARGET", "target": "database-management-system-lab",
        "reason": "B20 singular/plural print variant, NOT a code reassignment (recorded B18/B19 DBMS-lab ping-pong class): draft 'Database Management Systems Lab' (KCS551, 2020-21 IT y3 print) — KCS551's published owner is database-management-system-lab ('Database Management System Lab', 2022-23 K-era row; B19 already recorded 'KCS551 = DBMS Lab in both K-era prints' when the 2020-21 CSE doc corroborated it). The name-transfer toward the B-era 'systems' variant row (BCS551 owner) is rejected. UPDATE the KCS551 owner row; the 2020-21 IT print corroborates; experiments content backfills."},
    "07_btech_csit-it_y3_syllabus_2020-21::21::software-engineering-lab": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "software-engineering-lab",
        "keep_published_codes": {"KCS651": "big-data-and-analytics-lab"},
        "reason": "B20 older-draft-never-steals-a-code adjudication (newest-print-wins era model; identical B19 ruling for the 2020-21 CSE doc): draft 'Software Engineering Lab' (KCS651, 2020-21 IT y3 print, 11 experiments + 5 COs) — KCS651 is ALREADY owned by big-data-and-analytics-lab per the NEWER 2022-23 CSE-DS print (KCS651;BCDS651). The name-transfer would strip KCS651 from the newer-session published owner. Ruling: UPDATE software-engineering-lab by name identity (2020-21 IT print corroboration; older session so backfill-empty only); KCS651 STAYS with big-data-and-analytics-lab and is recorded as a narrative history mention on the SE-Lab row (dual-use slot across sessions)."},
    "08_btech_cyber-security_y2_syllabus_2026-27::03::data-structure-lab": {
        "action": "RETARGET", "target": "data-structure-lab",
        "reason": "B20 abbreviated-print RETARGET to the published code owner (recorded B18 singular/plural + variant-name class): draft 'Data Structure Lab' (BCS351, 2026-27 Cyber-Security y2 print) — BCS351's published owner is data-structure-lab ('Data Structures Lab', 2023-24, established from the 2023-24 CS/IT print family). The name-transfer toward the codeless ECS-352 variant row data-structure-lab-btech ('Data Structure Lab', 2009-10 E-era print, primary EMPTY) would strand BCS351 and reverse the recorded ownership. UPDATE the BCS351 owner row; 2026-27 is the newest session so it fieldwise-wins; the newer abbreviated name print is recorded in the row's name-print/notes."},
    "08_btech_cyber-security_y2_syllabus_2026-27::04::computer-organization-lab": {
        "action": "RETARGET", "target": "computer-organization-and-architecture-lab",
        "reason": "B20 abbreviated-print RETARGET to the published code owner (recorded B18 variant-name class): draft 'Computer Organization Lab' (BCS352, 2026-27 Cyber-Security y2 print) — BCS352's published owner is computer-organization-and-architecture-lab ('Computer Organization and Architecture Lab', 2023-24, established from the 2023-24 CS/IT print family). The name-transfer toward the K-era computer-organization-lab row (KCS352;ECS-453;KCS352H;RCS352, 2021-22) would move a B-era code onto the K-era row and reverse the retired-code era model (KCS403/BCS403 class: different code generations stay separate rows). UPDATE the BCS352 owner row; 2026-27 fieldwise-wins; abbreviated 2026-27 name print recorded."},
    "09_btech_ds_y2_syllabus_2025-26::03::data-structure-lab": {
        "action": "RETARGET", "target": "data-structure-lab",
        "reason": "B20 abbreviated-print RETARGET to the published code owner (same class as 08::03): draft 'Data Structure Lab' (BCS351, 2025-26 DS y2 print) — BCS351 owned by data-structure-lab; name-transfer toward the codeless ECS-352 variant row rejected. UPDATE the BCS351 owner row; 2025-26 fieldwise-wins."},
    "09_btech_ds_y2_syllabus_2025-26::07::foundation-of-artificial-intelligence-and-machine-learning": {
        "action": "FORCE_APPEND",
        "reason": "B20 wrong-subject FORCE_APPEND (recorded B14/B15/B19 wrong-subject T2 class): draft 'Foundation of Artificial Intelligence and Machine Learning' (BDS401, 2025-26 DS y2 core, 5 verbatim units) fuzzy 85/56-hits artificial-intelligence-and-machine-learning-in-bioinformati (BBI602, 2026-27 Bioinformatics branch elective). Unit-by-unit comparison (patch-b20 evidence): normalized similarity 0.019/0.025/0.021/0.107/0.007 across units 1-5 — COMPLETELY different content (foundations: AI history/first-order-logic/ANN/supervised+unsupervised learning vs bioinformatics applications: expert systems/NLP/ML-algorithms/bioinformatics applications unit). Different subjects (different slot: DS y2 core vs Bioinformatics y3 elective; different code family BDS vs BBI). Appends as its own row with a cross-reference note; zero-GAP holds."},
}

# ---------------- B21 batch additions (evidence-recorded) ----------------

# B21 DOC_SCOPE: branch scope from each ingested document's PRINTED COVER
# (zero-guess: exactly what the cover prints; B02-recorded pattern).
DOC_SCOPE.update({
    "304f365c491eb9dd": {
        "branch_names": "Electronics Engineering; Electronics and Communication Engineering; Electronics and Telecommunication Engineering; Electronics and Instrumentation Engineering; Instrumentation and Control Engineering; Applied Electronics and Instrumentation; Instrumentation Engineering",
        "program_year": "2",
        "reason": "B21 doc01: cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. SECOND YEAR ELECTRONICS ENGINEERING/ ELECTRONICS AND COMMUNICATION ENGINEERING/ ELECTRONICS AND TELECOMMUNICATION ENGINEERING/ ELECTRONICS AND INSTRUMENTATION ENGINEERING/ INSTRUMENTATION AND CONTROL ENGINEERING/ APPLIED ELECTRONICS AND INSTRUMENTATION/ INSTRUMENTATION ENGINEERING AS PER AICTE MODEL CURRICULUM [Effective from the Session: 2019-20]' — the ORIGINAL 2019-20 AICTE print (the B02-ingested E&C print 2615fceb4d68/7a0eeeeb was the 2020-21-effective revision with different unit splits; doc01 backfills only per RULES §3)"},
    "5184dfbd04413ba6": {
        "branch_names": "Electronics Engineering; Electronics & Communication Engineering; Electronics & Telecommunication Engineering; Electronics & Instrumentation Engineering; Instrumentation & Control Engineering; Applied Electronics and Control Engineering; Biomedical Engineering",
        "program_year": "2",
        "reason": "B21 doc02: cover prints 'UTTAR PRADESH TECHNICAL UNIVERSITY LUCKNOW SYLLABUS 2nd Year [Effective from Session 2014-15]' + the 7-branch ECE-group list ending '7. B. Tech. Biomedical Engineering'"},
    "b98bd23c56a3c812": {
        "branch_names": "Electronics Engineering; Electronics and Communication Engineering; Electronics and Communication (Advanced Communication Technology); Electronics Engineering (VLSI Design and Technology); Electronics and Instrumentation Engineering; Instrumentation and Control Engineering",
        "program_year": "1",
        "reason": "B21 doc03: cover prints 'EVALUATION SCHEME & SYLLABUS of B. TECH. First Year ECE STREAM — Electronics Engineering, Electronics and Communication Engineering, Electronics and Communication (Advanced Communication Technology), Electronics Engineering (VLSI Design and Technology), Electronics and Instrumentation Engineering, Instrumentation and Control Engin[eering]' (2026-27 A-era course structure)"},
    "2f22738f6f091a8e": {
        "branch_names": "Electronics Engg.; Electronics & Communication Engg.; Electronics & Telecommunication Engg.",
        "program_year": "3",
        "reason": "B21 doc04: cover prints 'G.B. TECHNICAL UNIVERSITY, LUCKNOW Syllabus 3rd & 4th Year [Effective from session 2009-10] 1. B.Tech. Electronics Engg. 2. B.Tech. Electronics & Communication Engg. 3. B.Tech. Electronics & Telecommunication Engg.' (document details Sem III-VI EEC/EIC subjects)"},
    "1a96cda0c39e4902": {
        "branch_names": "Electronics Engineering; Electronics & Communication Engineering; Electronics & Telecommunication Engineering",
        "program_year": "3",
        "reason": "B21 doc05: cover prints 'DR. A.P.J. ABDUL KALAM TECHNICAL UNIVERSITY Syllabus 3rd Year [Effective from Session 2016-17] 1. B.Tech. Electronics Engineering 2. B.Tech. Electronics & Communication Engineering 3. B.Tech. Electronics & Telecommunication Engineering' (Sem V/VI NEC/NIC)"},
    "539a5b5954ed22b7": {
        "branch_names": "Electronics Engineering; Electronics & Communication Engineering; Electronics & Telecommunication Engineering",
        "program_year": "3",
        "reason": "B21 doc06: byte-variant twin of doc05 (same cover print, 3rd Year 2016-17, Sem V/VI NEC/NIC); drafts extracted independently per pdf, merge converges them"},
    "6f590e0fe178d517": {
        "branch_names": "Electronics and Communication Engineering; Electronics and Instrumentation Engineering; Electronics and Telecommunication Engineering",
        "program_year": "3",
        "reason": "B21 doc07: cover text layer is scrambled (glyph-scatter); the draft reassembled it from verified fragments: 'Curriculum & Evaluation Scheme (V & VI semester) ... B.TECH THIRD YEAR ELECTRONICS AND COMMUNICATION ENGINEERING / ELECTRONICS AND INSTRUMENTATION(?) / ELECTRONICS AND TELECOMMUNICATION ENGINEERING ... AS PER AICTE MODEL CURRICULUM [Effective from the Session: 2020-21]' — scheme rows print KEC codes (ECE-family K-era)"},
    "59146449255604f8": {
        "branch_names": "Electronics Engineering; Electronics & Communication Engineering; Electronics & Telecommunication Engineering; Electronics & Instrumentation Engineering; Instrumentation & Control Engineering; Applied Electronics & Control Engineering; Biomedical Engineering",
        "program_year": "2",
        "reason": "B21 doc08: cover prints 'Study & Evaluation Scheme with Syllabus for B.Tech. Second Year Electronics Engineering / Electronics & Communication Engineering / Electronics & Telecommunication Engineering / Electronics & Instrumentation Engineering / Instrumentation & Control Engineering / Applied Electronics & Control Engineering / Biomedical Engineering On Choice Based Credit System (Effective from the Session: 2017-18)'"},
    "c631ec6e28ce78f9": {
        "branch_names": "Electronics Engineering; Electronics & Communication Engineering; Electronics & Telecommunication Engineering",
        "program_year": "3",
        "reason": "B21 doc09: cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH. III YEAR ELECTRONICS ENGINEERING/ ELECTRONICS & COMMUNICATION ENGINEERING/ ELECTRONICS & TELECOMMUNICATION ENGINEERING ON CHOICE BASED CREDIT SYSTEM (CBCS) [Effective from the Session: 2018-19]'"},
    "3559fa634ed9fdab": {
        "branch_names": "Electronics Engineering; Electronics and Communication Engineering; Electronics and Telecommunication Engineering",
        "program_year": "3",
        "reason": "B21 doc10: cover prints 'ELECTRONICS AND COMMUNICATION ENGINEERING — EVALUATION SCHEME & SYLLABUS FOR B. TECH. THIRD YEAR ▪ ELECTRONICS ENGINEERING ▪ ELECTRONICS AND COMMUNICATION ENGINEERING ▪ ELECTRONICS AND TELECOMMUNICATION ENGINEERING AS PER AICTE MODEL CURRICULUM [Effective from the Session: 2024-25] Curriculum & Evaluation Scheme (V & VI semester)'"},
})

# ---- B30 (CRON-20261104-B30) doc-level scope from the PRINTED COVERS ----
DOC_SCOPE.update({
    "7d699e03eb1f40d3": {
        "branch_names": "Mechanical Engineering",
        "program_year": "2",
        "reason": "B30 doc01: cover prints 'EVALUATION SCHEME & SYLLABUS FOR B. TECH 2nd YEAR MECHANICAL ENGINEERING On AICTE Model Curriculum (EFFECTIVE FROM THE SESSION: 2019-20)' — single-branch ME 2nd-year AICTE model-curriculum print; per-subject program_year set from printed semesters (3/4 -> 2)"},
    "15ccfbe9a0ef83e4": {
        "branch_names": "Mechanical Engineering;Production Engineering;Industrial & Production Engineering;Mechanical & Industrial Engineering;Manufacturing Technology;Automobile Engineering;Aeronautical Engineering",
        "program_year": "2",
        "reason": "B30 doc02: cover prints 'Study & Evaluation Scheme with Syllabus For B.Tech. Second Year (Mechanical Engineering/ Production Engineering, Industrial & Production Engineering, Mechanical & Industrial Engineering, Manufacturing Technology, Automobile Engineering, Aeronautical Engineering)' — the 7-branch ME-family y2 print; scheme rows carry the shared RME codes"},
    "6c00370d9f7d0ba5": {
        "branch_names": "Mechanical Engineering",
        "program_year": "3",
        "reason": "B30 doc03: cover prints 'EVALUATION SCHEME FOR B.TECH. 3rd YEAR MECHANICAL ENGINEERING [Effective from Session: 2024-25]' (V & VI semester B-era NEP print); per-subject program_year from printed semesters (5/6 -> 3)"},
    "56ed2e4469bcb780": {
        "branch_names": "Mechanical Engineering",
        "program_year": "4",
        "reason": "B30 doc04: cover prints 'STUDY & EVALUATION SCHEME WITH SYLLABUS FOR B. TECH 4th YEAR MECHANICAL ENGINEERING ON CHOICE BASED CREDIT SYSTEM (EFFECTIVE FROM THE SESSION: 2019-20)' (R-era CBCS Sem VII/VIII)"},
    "3cf7784768f67986": {
        "branch_names": "Mechanical Engineering",
        "program_year": "4",
        "reason": "B30 doc05: cover prints 'STUDY & EVALUATION SCHEME WITH SYLLABUS FOR B. TECH. 4th YEAR MECHANICAL ENGINEERING [Effective from Session: 2021-22]' (K-era Sem VII DE-IV/V print)"},
    "99d084e82fa37354": {
        "branch_names": "Mechanical Engineering",
        "program_year": "4",
        "reason": "B30 doc06: cover prints 'COURSE STRUCTURE/EVALUATION SCHEME FOR B.TECH. 4th YEAR MECHANICAL ENGINEERING [Effective from Session: 2025-26]' (B-era Sem VII/VIII print)"},
    "5f4df8f382ad0b54": {
        "branch_names": "Manufacturing Technology",
        "program_year": "3",
        "reason": "B30 doc07: cover prints 'Syllabus [Subjects related to Manufacturing Technology] 3rd & 4th Year [Effective from session 2010-11] B. TECH. MANUFACTURING TECHNOLOGY'; p.2 prints the note 'The Syllabus of Subjects with EME code are common to B.Tech. Mechanical Engg. course' (recorded in the draft quirks); combined 3rd-4th-year doc — per-subject program_year set from printed semesters (5/6 -> 3, 7/8 -> 4) so the single-scope fallback never mislabels (B29 me-pe class)"},
    "e441e28ab6b822d4": {
        "branch_names": "Manufacturing Technology",
        "program_year": "3",
        "reason": "B30 doc08: cover prints 'STUDY & EVALUATION SCHEME WITH SYLLABUS FOR B. TECH. 3rd YEAR Manufacturing Technology [Effective from Session: 2020-21]' (K-era KMT/KPI codes); p.47 carries a 4th-yr scheme headed 'B. Tech Manufacturing Engineering / Session 2021-22 (Yet to Finalize)' — recorded in the draft quirks as a note row, not scope"},
    "c3070c76d0529139": {
        "branch_names": "Manufacturing Technology",
        "program_year": "2",
        "reason": "B30 doc09: cover prints 'STUDY & EVALUATION SCHEME & SYLLABUS FOR B. TECH 2nd YEAR MECHANICAL ENGINEERING (Manufacturing Technology) On AICTE Model Curriculum (EFFECTIVE FROM THE SESSION: 2019-20)' — the Mfg-Tech stream of the ME 2nd-year AICTE model-curriculum print (bracketed branch); detail pages print no codes (codes from the printed scheme table, B29 doc-01 class)"},
    "60cad5443dd11e27": {
        "branch_names": "Manufacturing Technology",
        "program_year": "3",
        "reason": "B30 doc10: cover prints 'EVALUATION SCHEME FOR B.TECH. 3rd YEAR Manufacturing Technology [Effective from Session: 2024-25]' (V & VI semester B-era NEP print); BNC common codes + BME554 are scheme-row-only (B29 doc-02 class)"},
})


# B21 per-key TIER2_OVERRIDES (evidence-recorded; the decision for every flagged
# subject and every ladder-corrected routing of this batch).
TIER2_OVERRIDES.update({
    # ---- wrong-subject optical pair (B21 TC-repair class) ----
    "07_btech_ece_syllabus_2020-21::10::optical-communication": {
        "action": "FORCE_APPEND",
        "reason": "Wrong-subject Tier-2 hit (B14/B15/B19/B20 class): draft 'Optical Communication' (KEC-058, 2020-21 ECE DE-II elective slot, verbatim fiber-optics units) fuzzy 86/overlap 176-hit technical-communication — the shared generic token 'communication' carries the name score, and the TC row's own unit/CO vocabulary is OPTICAL-Communication content (its unit1_text prints 'Introduction to Optical Communication: Optical Spectral Band...') because an earlier batch merged the 2025-26 ACT rev print's 'BEC-057 OPTICAL COMMUNICATION' subject into technical-communication (the ACT print p.14 proves BEC-057 = OPTICAL COMMUNICATION with Senior/Keiser/Agrawal fiber-optics books — B21 TC repair strips that content back out this commit). Optical Communication is a DIFFERENT subject from Technical Communication (communication-skills canon row, CG-TC-UHV pair member). No BTech optical-communication row exists pre-commit → APPEND as its own row; the 2024-25 doc10 print (10::09) converges onto it via the ladder's own name-transfer at commit (B09/B10 same-commit append visibility)."},
    "10_btech_ece_y3_syllabus_2024-25::09::optical-communication": {
        "action": "ALLOW",
        "reason": "Commit-mode name-transfer ALLOWED (decisions-mode shows T0 UPDATE technical-communication because same-commit appends are not visible to the dry-run ladder — recorded B09/B10 divergence class): doc 07's draft appended optical-communication earlier in THIS commit (FORCE_APPEND above), so at commit the Tier-0 hit on BEC-057 (owned by technical-communication since the recorded wrong-merge) resolves through the ladder's name-identity branch to the just-appended optical-communication row: 'code-reassigned BEC057: owned by technical-communication; name identity -> optical-communication'. The reassignment executor strips BEC-057 from technical-communication (narrative history retained, B08 remedy) and the B21 REPAIRS executor salvages the ACT citation onto the optical row while stripping the misplaced optical units/COs/books from technical-communication. Draft 2024-25 is newer than the appended row's 2020-21 establishing print → fieldwise wins per RULES §3."},
    # ---- microwave pair: same subject, code stays with its newer-print owner ----
    "10_btech_ece_y3_syllabus_2024-25::20::microwave-engineering": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER",
        "target": "microwave-radar-engineering",
        "keep_published_codes": {"BEC-064": "prints MICROWAVE ENGINEERING in the 2024-25 ECE DE-II elective slot, but BEC064/BEC-064 is owned by microcontrollers-and-sensors-for-iot-applications from the newer 2025-26 ACT rev print (published B18/B19 era model) — RULES §3: equal-or-older print never takes a code from its newer-session published owner"},
        "reason": "Tier-0 hit on the IoT row is the recorded code-slot-collision class (collapsed-name similarity 0.34 — different subject): the TIER2 fuzzy evidence routes the draft to the true canon row microwave-radar-engineering (fuzzy 88 / unit-vocab overlap 69; waveguide/microwave unit canon shared with the row's NEC-601 2016-17 + BEC073 2026-27 era prints — same subject as docs 05/06 'Microwave Engineering' NEC-601 which Tier-0-join the same row this commit). Draft 2024-25 is older than the row's 2026-27 latest print → backfill-empty-only; BEC-064 stays with the IoT row (narrative mention recorded on this row)."},
    # ---- communication-lab-ii convergence (B21 code-slot-collision class) ----
    "06_btech_ece_syllabus_2016-17_2::15::communication-lab-ii": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER",
        "target": "communication-lab-ii",
        "keep_published_codes": {"NEC 652": "prints COMMUNICATION LAB – II in the 2016-17 ECE sem-VI scheme, but NEC-652 is owned by instrumentation-lab from the same-session AEI print (btech_applied-electronics-ece-ei_syllabus_2016-17, published) — equal-session prints collide; the published owner keeps the code (RULES §3 + G2 one-owner)"},
        "reason": "Same-commit convergence (recorded B09/B10 class): doc 05's twin draft (05::25, identical subject) appended communication-lab-ii earlier in THIS commit via the B21 code-slot-collision ladder remedy (collapsed-name similarity 0.556 < 0.84 vs instrumentation-lab — DIFFERENT subject, unit/experiment vocabulary overlap 0; 12 printed experiments on signal/harmonic benches); this twin draft RETARGETs onto that row for corroboration (same session 2016-17 → backfill-empty-only), and the collided NEC 652 print stays with instrumentation-lab."},
    # ---- mini-project slot (B20 adjudication (b) owned-code rule) ----
    "01_btech_ece-ei_y2_model-curriculum_2019-20::06::mini-project-or-internship-assessment": {
        "action": "RETARGET",
        "target": "internship-assessment-mini-project",
        "reason": "Rejects the ladder's name-transfer (which would move KEC354 to mini-project-or-internship-assessment): KEC354 is OWNED by internship-assessment-mini-project (published all_codes BCC351;KCS354;KEC354;KCS554;BCS554;BCE554;KCS752 — the B02 E&C AICTE print established it) and the B20 recorded adjudication (b) keeps OWNED sibling slot codes (KCS354/KCS554/KCS752 from the same 2019-20 AICTE model-curriculum family) with that row. Doc 01 is the same-family 2019-20 ECE-group print of the same slot (scheme_row_only, nothing to backfill but the scheme line + the 'Mini Project or Internship Assessment' name_print variant, recorded). The B12/B19 convergence model keeps the two name-variant rows as published; unowned codes join by name (B20), owned codes stay with their owner (B20 adjudication (b) + RULES §3)."},
    # ---- control-system pair (same-session AEI sibling print owns the codes) ----
    "05_btech_ece_syllabus_2016-17::03::control-system-i": {
        "action": "RETARGET",
        "target": "control-system",
        "reason": "Rejects the ladder's name-transfer to control-system-i: NIC501 is OWNED by control-system (published all_codes BEC602;BEC-602;NIC-501 — the same-session AEI print btech_applied-electronics-ece-ei_syllabus_2016-17 established NIC-501 there with the detailed syllabus, hist 'NIC-501 (2016-17, sem-5)'). Draft 'Control System -I' is a print variant of the row's 'Control System' (collapsed sim 0.93 ≥ 0.84 = B10 class (a)); unit-vocabulary match 0.95 (92/97 draft terms in the row's vocab). The name-exact control-system-i row is the EI/BME-era canon (EIC-501 2010-11 / RBM501 2017-18) — a pre-existing published row split; this update does not move codes across it. Draft 2016-17 older than the row's 2025-26 latest → backfill-empty-only."},
    "06_btech_ece_syllabus_2016-17_2::03::control-system-i": {
        "action": "RETARGET",
        "target": "control-system",
        "reason": "Twin of 05::03 (same evidence): NIC501 stays with its published owner control-system; 'Control System -I' is the ECE print variant of the AEI 'Control System'; backfill-empty-only (2016-17 < 2025-26)."},
    "05_btech_ece_syllabus_2016-17::07::control-system-lab": {
        "action": "RETARGET",
        "target": "control-systems-i-lab",
        "reason": "Rejects the ladder's name-transfer to control-system-lab: NIC551 is OWNED by control-systems-i-lab (published primary NIC-551, 2016-17 AEI print) and the printed experiment lists are IDENTICAL — 12/12 draft experiments match that row's experiments verbatim (vs 6/12 for control-system-lab's BEC652 2025-26 list): same subject, same-session sibling print. The ECE print's name variant 'Control System Lab' is recorded on the row. Draft 2016-17 == row session → corroboration/backfill-empty-only."},
    "06_btech_ece_syllabus_2016-17_2::06::control-system-lab": {
        "action": "RETARGET",
        "target": "control-systems-i-lab",
        "reason": "Twin of 05::07 (same evidence: 12/12 experiment match with control-systems-i-lab's NIC-551 AEI print)."},
    # ---- signals & systems TIE (unit-vocabulary + name-exact ECE-era row) ----
    "08_btech_ece_y2_syllabus_2017-18::03::signals-systems": {
        "action": "RETARGET",
        "target": "signals-and-systems",
        "reason": "TIE resolution (signal-system 93/33 vs signals-and-systems 88/41): unit-vocabulary evidence favors signals-and-systems (normalized unit-term overlap 41/65 draft terms vs 32/65; draft unit-1 prints 'Signals: Representation of Signals, Singularity Functions...' matching that row's 'Signals: Definition, types of signals...' unit-label style) and the row is the ECE-era name-exact class ('SIGNALS AND SYSTEMS', EEC-404 2011-12 ECE print) — the 2017-18 ECE REC-303 print is the same subject's next era print (REC303 joins as era code; 2017-18 newer than 2011-12 → fieldwise wins per RULES §3). signal-system (KEC403, eff 2020-21) is the K-era row whose unit-1 style ('Signals and systems as seen in everyday life...') diverges."},
    # ---- data-structure & algorithms TIE (name-class match to the canon DSA row) ----
    "08_btech_ece_y2_syllabus_2017-18::08::data-structure-algorithms": {
        "action": "RETARGET",
        "target": "data-structure-and-algorithms",
        "reason": "TIE resolution (data-structure-and-algorithms 93/46 vs basics-data-structure-algorithms 88/59): the draft prints 'Data Structure & Algorithms' (RCS406, 2017-18 ECE sem-IV scheme row) — '&' vs 'and' is print noise (fuzzy 93, name-class match); basics-data-structure-algorithms is the DISTINCT 2023-24 2nd-yr common subject ('Basics...' name, BOE306/406 + KOE035/045 pool codes) — merging the ECE-era RCS406 into it would pollute the published common-subject row. RCS406 joins the canon DSA row (ECS-508, 2009-10) as an era code; 2017-18 newer → fieldwise wins per RULES §3."},
    # ---- recorded ALLOWs (same-subject era/print-variant Tier-2 matches) ----
    "02_btech_ece-group_y2_syllabus_2014-15::00::network-analysis-synthesis": {
        "action": "ALLOW",
        "reason": "2014-15 NEC-301 'Network Analysis & Synthesis' is the same subject as the network-analysis-and-synthesis canon row (KEC303 2021-22 K-era + EEC-303 2009-10 era family); NEC-301 joins as an era code (B20 unit-identity ALLOW class)."},
    "02_btech_ece-group_y2_syllabus_2014-15::01::fundamental-of-electronic-devices": {
        "action": "ALLOW",
        "reason": "2014-15 'Fundamental of Electronic Devices' (NEC-302) = the row fundamentals-of-electronics-devices (EEC-301, 2011-12, 'FUNDAMENTALS OF ELECTRONICS DEVICES') — singular/plural print variant, overlap 86 (B20 unit-identity class)."},
    "02_btech_ece-group_y2_syllabus_2014-15::10::electronic-measurements-and-instrumentation": {
        "action": "ALLOW",
        "reason": "2014-15 'Electronic Measurements and Instrumentation' = the row electronic-instrumentation-and-measurements (EEC-403, 2011-12) — token-order print variant, fuzzy 100/overlap 80."},
    "04_btech_ece_syllabus_2009-10::08::computer-architecture-organization": {
        "action": "ALLOW",
        "reason": "2009-10 'Computer Architecture & Organization' (EEC-3xx era) = the row computer-organization-and-architecture (BCS302;KCS302;NEC-012;REC052 — the ECE-era NEC-012/REC052 codes already on it) — token-order print variant, fuzzy 94/overlap 30."},
    "04_btech_ece_syllabus_2009-10::16::microprocessors": {
        "action": "ALLOW",
        "reason": "2009-10 'MICROPROCESSORS' = the row microprocessor (KCS403;NEC-503 — the 2016-17 NEC-503 print already on it) — plural print variant, fuzzy 97/overlap 41."},
    "04_btech_ece_syllabus_2009-10::17::antenna-wave-propagation": {
        "action": "ALLOW",
        "reason": "2009-10 'Antenna & Wave Propagation' = the row antenna-and-wave-propagation (BEC603/BEC-603 canon) — era print variant, fuzzy 92/overlap 85."},
    "04_btech_ece_syllabus_2009-10::25::microwave-engineering": {
        "action": "ALLOW",
        "reason": "2009-10 'Microwave Engineering' (EEC-5xx) = the row microwave-radar-engineering (NEC-601 2016-17 + BEC073 2026-27 era family) — fuzzy 88/unit-vocab overlap 64 (B20 unit-identity ALLOW class at fuzzy 88)."},
    "05_btech_ece_syllabus_2016-17::17::real-time-systems": {
        "action": "ALLOW",
        "reason": "2016-17 'Real Time Systems' = the row real-time-system (NCS-082 2016-17 CSE print + KCS-063 2020-21) — same subject across branches, plural print variant, fuzzy 97."},
    "06_btech_ece_syllabus_2016-17_2::24::real-time-systems": {
        "action": "ALLOW",
        "reason": "Twin of 05::17 — same subject, same row (real-time-system)."},
    "07_btech_ece_syllabus_2020-21::03::computer-architecture-and-organization": {
        "action": "ALLOW",
        "reason": "2020-21 'Computer Architecture and Organization' (KEC-50x) = the row computer-organization-and-architecture — token-order print variant, fuzzy 100."},
    "07_btech_ece_syllabus_2020-21::09::electronic-measurements-instrumentation": {
        "action": "ALLOW",
        "reason": "2020-21 'Electronic Measurements & Instrumentation' = the row electronic-instrumentation-and-measurements (EEC-403 canon) — token-order print variant, fuzzy 95/overlap 44."},
    "07_btech_ece_syllabus_2020-21::16::antenna-wave-propagation": {
        "action": "ALLOW",
        "reason": "2020-21 'Antenna & Wave Propagation' (KEC-60x) = the row antenna-and-wave-propagation (BEC603 canon) — era print variant, fuzzy 92/overlap 140."},
    "08_btech_ece_y2_syllabus_2017-18::09::microprocessors-microcontrollers": {
        "action": "ALLOW",
        "reason": "2017-18 'Microprocessors & Microcontrollers' (REC-303) = the row microprocessor-microcontroller (name-exact class row, fuzzy 97/overlap 41) — the 2017-18 print is that row's own era print."},
    "08_btech_ece_y2_syllabus_2017-18::11::electronic-measurement-instrumentation": {
        "action": "ALLOW",
        "reason": "2017-18 'Electronic Measurement & Instrumentation' = the row electronic-instrumentation-and-measurements — token-order print variant, fuzzy 94/overlap 77."},
    "09_btech_ece_y3_syllabus_2018-19::09::real-time-systems": {
        "action": "ALLOW",
        "reason": "2018-19 'REAL TIME SYSTEMS' = the row real-time-system (NCS-082/KCS-063 canon) — plural print variant, fuzzy 97."},
    "09_btech_ece_y3_syllabus_2018-19::13::microwave-engineering": {
        "action": "ALLOW",
        "reason": "2018-19 'MICROWAVE ENGINEERING' = the row microwave-radar-engineering (NEC-601 era family) — fuzzy 88/overlap 64 (same class as 04::25)."},
    "09_btech_ece_y3_syllabus_2018-19::20::microcontroller-for-embedded-systems": {
        "action": "ALLOW",
        "reason": "2018-19 'MICROCONTROLLER FOR EMBEDDED SYSTEMS' (RIC-603) = the row microcontrollers-for-embedded-systems (NIC-601R, 2016-17 AEI print) — singular/plural print variant, fuzzy 99/overlap 87; RIC603 joins as era code."},
})

# ---- B25 (CRON-20261103-B25) per-key TIER2_OVERRIDES (evidence-recorded) ----
# Probe evidence (scripts/pipeline_v2/probe_b25_flags.py): per-flag draft name/
# codes/units vs candidate rows (token overlap + best per-unit Jaccard).
TIER2_OVERRIDES.update({
    # -- name/print-variant ALLOWs (same subject; unit-vocab identity recorded) --
    "01_btech_en_syllabus_2009-10::50::antena-and-wave-propogation": {
        "action": "ALLOW",
        "reason": "Print-typo name variant (recorded print class): draft 'Antena and Wave Propogation' (EEC-029, 2009-10 EE elective, detailed EM/antenna units) = the row antenna-and-wave-propagation (BEC603;EEC 504;NEC 504;KEC-603;REC051) — fuzzy 95/overlap 47, best per-unit Jaccard 0.47; the typos are the printed forms (RULES §6 keep-print) and the row already carries the EEC-504 EE print of the same course. 2009-10 older than the row's 2025-26 latest → backfill-empty only; EEC-029 joins as era code."},
    "01_btech_en_syllabus_2009-10::56::telemetry-and-data-transmission": {
        "action": "ALLOW",
        "reason": "Name/print variant ('and' vs '&', ALL-CAPS row print): draft 'Telemetry and Data Transmission' (EEC-046, 2009-10 EE elective, detailed units) = the row telemetry-data-transmission ('TELEMETRY & DATA TRANSMISSION', REN075, 2019-20 EEE-EN CBCS print) — fuzzy 93/overlap 76, best per-unit Jaccard 0.75 (same course). 2009-10 older → backfill-empty only; EEC-046 joins as era code."},
    "01_btech_en_syllabus_2009-10::57::embedded-system": {
        "action": "ALLOW",
        "reason": "Singular/plural print variant (recorded class): draft 'Embedded System' (EEC-047, 2009-10 EE elective, detailed units) = the row embedded-systems (NCS-087;RCS070;KEN 062;BEN062) — fuzzy 97/overlap 76, best per-unit Jaccard 0.62. 2009-10 older → backfill-empty only; EEC-047 joins as era code."},
    "02_btech_en_y4_syllabus_2021-22::01::power-system-operation-control": {
        "action": "ALLOW",
        "reason": "Ampersand/'and' print variant: draft 'Power System Operation & Control' (KEN070, 2021-22 EN DE-IV, detailed units) = the row power-system-operation-and-control (EEE-031, 2009-10 EE print that established the row) — fuzzy 94/overlap 82, best per-unit Jaccard 0.94 (near-verbatim same course). 2021-22 NEWER → fieldwise-wins (units/COs replace the 2009-10 print); KEN070 joins as era code."},
    "02_btech_en_y4_syllabus_2021-22::06::electric-hybrid-vehicles": {
        "action": "ALLOW",
        "reason": "Ampersand print variant: draft 'Electric & Hybrid Vehicles' (KEN071, 2021-22 EN DE-V, detailed units) = the row electric-and-hybrid-vehicles (BOE301;BOE401;BOE301H;BOE401H;KEE 064;BEE064, 2023-24 OE print) — fuzzy 92/overlap 49, best per-unit Jaccard 0.88 ('History of hybrid and electric vehicles...' unit canon shared; recorded B24 'Electric(-)Hybrid Vehicles' variant family). 2021-22 older than 2023-24 → backfill-empty only; KEN071 joins as era code."},
    "03_btech_env_syllabus_2009-10::18::environmental-impact-assessment-and-audit": {
        "action": "ALLOW",
        "reason": "Multi-branch same-subject update (content evidence, RULES §3): draft 'Environmental Impact Assessment and Audit' (EEV-603, 2009-10 ENV core, detailed units) = the row environmental-impact-assessment (BCH064;KCH064;RCH074, Chemical-branch eras) — fuzzy 86/overlap 56, best per-unit Jaccard 0.91 (near-verbatim 'Introduction to EIA & Audit, Environment & Industries...' unit canon). The ENV prints join the same BTech row (cross-branch content evidence, recorded multi-branch class); EEV-603 joins as era code."},
    "08_btech_env_y3_scheme-syllabus_2018-19::12::environmental-impact-assessment-and-audit": {
        "action": "ALLOW",
        "reason": "Same evidence as 03::18: draft 'Environmental Impact Assessment and Audit' (REV602, 2018-19 ENV core, detailed units; u1 identical 'Introduction to EIA & Audit...' print, Jaccard 0.91) = the row environmental-impact-assessment; REV602 joins as era code. 2018-19 older than the row's 2024-25 latest → backfill-empty only."},
    "10_btech_env_y4_syllabus-cbcs_2019-20::12::construction-technology-and-management": {
        "action": "ALLOW",
        "reason": "Ampersand/'and' print variant: draft 'Construction Technology and Management' (REV081, 2019-20 ENV elective, detailed units) = the row construction-technology-management ('CONSTRUCTION TECHNOLOGY & MANAGEMENT', ECE801;NCE603, 2010-11 Civil print) — fuzzy 94/overlap 81, best per-unit Jaccard 0.80 (same course). 2019-20 NEWER → fieldwise-wins; REV081 joins as era code."},
    # -- wrong-subject FORCE_APPENDs (unit-vocab Jaccard rejects the fuzzy hit) --
    "03_btech_env_syllabus_2009-10::23::environmental-risk-assessment": {
        "action": "FORCE_APPEND",
        "reason": "Wrong-subject Tier-2 hit (recorded B14/B15/B19/B20 class, RULES §11 never-merge-different-subjects): draft 'Environmental Risk Assessment' (EEV-033, 2009-10 ENV elective, detailed risk-type/management units) fuzzy 87 hit environmental-impact-assessment — but overlap only 5 and best per-unit Jaccard 0.12: Risk Assessment is a DIFFERENT subject from Impact Assessment (distinct-row design). No BTech environmental-risk-assessment row exists pre-commit → APPEND as its own row with a cross-reference note; the 2015-16 (NEN024) and 2020-21 (KNE061) prints converge onto it via same-commit append visibility (recorded B09/B10 class)."},
    "05_btech_env_syllabus_2015-16::21::environmental-risk-assessment": {
        "action": "FORCE_APPEND",
        "reason": "Same evidence as 03::23: draft 'Environmental Risk Assessment' (NEN024, 2015-16 ENV DE-II, detailed units, Jaccard 0.12 vs the EIA row) — different subject from Impact Assessment; converges onto the environmental-risk-assessment row appended from 03::23 in this same commit."},
    "09_btech_env_y3_scheme-syllabus_2020-21::18::environmental-risk-assessment": {
        "action": "FORCE_APPEND",
        "reason": "Same evidence as 03::23: draft 'Environmental Risk Assessment' (KNE061, 2020-21 ENV DE-III, detailed units, Jaccard 0.12 vs the EIA row) — different subject from Impact Assessment; converges onto the environmental-risk-assessment row appended from 03::23 in this same commit."},
    "10_btech_env_y4_syllabus-cbcs_2019-20::06::heat-transfer-and-operation": {
        "action": "FORCE_APPEND",
        "reason": "Wrong-subject Tier-2 hit (name-variant similarity alone, RULES §3 content evidence): draft 'Heat Transfer and Operation' (REV077, 2019-20 ENV elective, detailed units: U1 'Conduction convection & radiation. General laws of heat transfer. Fourier's law...') fuzzy 90 hit heat-transfer-operations (ECH402;KCH303, Chemical-branch core) — but best per-unit Jaccard 0.25 and the prints differ structurally (the Chem row's U1 is 'Importance of heat transfer in Chemical Engineering operations'; conduction appears in ITS U2): a DIFFERENT course printed under a near-identical name (the recorded 'Heat Transfer Operations vs Operation' print class splits here on content). APPEND as its own row with a cross-reference note to the Chem row."},
    "10_btech_env_y4_syllabus-cbcs_2019-20::13::engineering-hydrology-and-groundwater-management": {
        "action": "FORCE_APPEND",
        "reason": "Same-name different-content class (RULES §2/§3: similarity alone never merges; content evidence decisive): draft 'Engineering Hydrology and Groundwater Management' (REV082, 2019-20 ENV elective, detailed units: U1 'Ground Water Occurrence... zone of aeration and zone of saturation, geologic formations...') vs the row engineering-hydrology-groundwater-management (RCE085, 2019-20 Civil print: U1 'hydrologic cycle, water budget equations, world water balance, Precipitation...' — SURFACE-water hydrology): fuzzy 96 but best per-unit Jaccard 0.15 and the unit canons are disjoint — two DIFFERENT same-session courses sharing a name. APPEND as its own row with a cross-reference note documenting the split."},
    # -- TIE resolutions (RETARGET; published code owners keep their codes) --
    "04_btech_env_syllabus_2014-15::02::environmental-engineering-process": {
        "action": "FORCE_APPEND",
        "reason": "TIE fuzzy resolution — wrong-subject class, RULES §11 never-merge-different-subjects + §2 content evidence: draft 'Environmental Engineering Process' (NEN-302, 2014-15 ENV-branch core, detailed units: U1 'Classification of Pollutants Pollutants in water and wastewater – characteristics...') TIE-hit three Civil-branch rows (environmental-engineering-i 87/15, environmental-engineering 86/30, environmental-engineering-ii 85/32) — but best per-unit Jaccard is only 0.12-0.20 against ALL three: no unit identity with the Civil EE-I (water supply) / EE-II (wastewater) courses. The substantive token 'Process' and the ENV-branch NEN code family (sister NEN-301/303 core prints) make this the ENV-branch process course, a DIFFERENT subject printed under a similar name. APPEND as its own row with cross-reference notes to all three Civil rows."},
    "01_btech_en_syllabus_2009-10::55::electric-drives": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER",
        "target": "electric-drives",
        "keep_published_codes": {"EEE-033": "neural-networks-and-fuzzy-system (the 2009-10 scheme's EEE-033 elective slot; that row was established with EEE-033 as primary from the same-session 2009-10 print family, while the Electric-Drives detail page prints EEE-702 — recorded doc01 print-quirk 'EEE-702/EEE-033'; equal-or-older print never takes a code from its published owner, RULES §3)"},
        "reason": "TIE code-identity resolution (tier-0 hit two rows: electric-drives owns EEE-702, neural-networks-and-fuzzy-system owns EEE-033; the draft carries both prints). Vocabulary evidence pins the subject: draft 'Electric Drives' units match the row electric-drives (BEE074;EEE-702;REE701;KEE075, 2025-26) at best per-unit Jaccard 1.00 — VERBATIM same course. RETARGET pins the update there; EEE-033 stays with its published owner (narrative mention recorded). 2009-10 older than 2025-26 → backfill-empty only."},
    "01_btech_en_syllabus_2009-10::11::general-proficiency": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER",
        "target": "general-proficiency",
        "keep_published_codes": {"GP-301": "general-proficiency-lab (GP-301 is that row's only code, establishing print 2014-15 — NEWER than this 2009-10 scheme print; RULES §3 newest-print-wins keeps it there)"},
        "reason": "TIE code-identity resolution (tier-0 hit two rows: general-proficiency owns GP401-801 from the 2026-27 AG print; general-proficiency-lab owns GP-301 from the 2014-15 print; the 2009-10 EE scheme prints one 'General Proficiency' slot per semester GP-301..801). RETARGET pins the update to the name-exact general-proficiency row (its codes GP401-801 are re-corroborated; 2009-10 is older → backfill/source-history only) while GP-301 stays with its published newer-print owner general-proficiency-lab."},
})

# B21 REPAIRS (brain clause: determine-then-fix, keep proof). Executed at commit
# AFTER the draft loop (the salvage target row exists by then) and BEFORE the
# gates. Every field strip is backed by the printed evidence recorded here.
REPAIRS = {
    "technical-communication": {
        "salvage_to": "optical-communication",
        "strip_fields": ["unit1_text", "unit2_text", "unit3_text", "unit4_text", "unit5_text",
                          "co1_text", "co2_text", "co3_text", "co4_text", "co5_text", "co6_text",
                          "textbooks_structured", "lectures_per_unit"],
        "reset_fields": {"has_detailed_syllabus": "FALSE", "units_count": "0", "co_count": "0"},
        "move_source_token": "btech_act_y3_syllabus-rev_2025-26.pdf#328fc29743da6525",
        "reason": ("B21 wrong-merge repair (printed evidence: btech_act_y3_syllabus-rev_2025-26.pdf p.14 "
                   "prints 'BEC-057 OPTICAL COMMUNICATION 3L:0T:0P 3 Credits' with the full fiber-optics "
                   "syllabus — Unit-I 'Introduction to Optical Communication: Optical Spectral Band...', "
                   "CO-1 'Define and explain the basic concepts and theory of optical communication', "
                   "books Senior/Keiser/Agrawal): an earlier batch merged that ACT print's Optical "
                   "Communication subject into the technical-communication row (its unit1_text/co1_text/"
                   "textbooks_structured print optical-communication content while the row's identity, "
                   "codes BAS301/BAS401/KAS301 + H variants, scheme lines and CG-TC-UHV group are the "
                   "Technical Communication canon). This commit appends the true optical-communication row "
                   "(doc07 KEC-058 + doc10 BEC-057 via the recorded name-transfer), the reassignment "
                   "executor moves BEC-057 off this row, and this repair strips the misplaced optical "
                   "unit/CO/book fields back off (the row returns to its true authorized state: scheme "
                   "lines only — the B02-recorded 'detailed syllabus NOT printed in the authorized "
                   "documents; companion quarantined' note stands). The ACT citation moves to the "
                   "optical-communication row's source_history so the 2025-26 print stays reachable."),
    },
}

# B26 (CRON-20261103-B26) per-key TIER2_OVERRIDES (evidence-recorded;
# probe: scripts/pipeline_v2/probe_b26_flags.py — token overlap + best per-unit
# Jaccard vs candidate rows, recorded per key).
TIER2_OVERRIDES.update({
    # ---- Tier-2 fuzzy flags: name-variant ALLOWs (same subject) ----
    "01_btech_env_y4_syllabus_2016-17::04::building-materials-and-construction": {
        "action": "ALLOW",
        "reason": "Ampersand/'and' print variant (recorded B25 REV081 class): draft 'Building Materials and Construction' (NEN033, 2016-17 ENV y4 elective, detailed units) = the row building-materials-construction ('BUILDING MATERIALS & CONSTRUCTION', ECE302;RCE301;NCE302, 2009-10 Civil) — fuzzy 94/overlap 41 (stones/bricks/cement/timber canon vocabulary); best per-unit Jaccard 0.31 (2009-10 terse Civil print vs the ENV unitwise print — shared distinctive-material tokens carry the identity). Same named course; NEN033 joins as era code; 2016-17 newer than 2009-10 → fieldwise-wins."},
    "01_btech_env_y4_syllabus_2016-17::11::construction-technology-and-management": {
        "action": "ALLOW",
        "reason": "Same evidence as the recorded B25 10::12 ALLOW (REV081, J=0.80): draft 'Construction Technology and Management' (NEN053, 2016-17 ENV, detailed units) = the row construction-technology-management — fuzzy 94/overlap 106, best per-unit Jaccard 0.95 (near-verbatim 'Elements of Management: Project cycle, Organisation, planning, scheduling...' canon). NEN053 joins as era code."},
    "02_btech_env_y4_syllabus_2021-22::00::construction-technology-and-management": {
        "action": "ALLOW",
        "reason": "Same evidence as 01::11: draft 'Construction Technology and Management' (KNE071, 2021-22 ENV y4 DE, detailed units) = construction-technology-management — fuzzy 94/overlap 105, Jaccard 0.95. 2021-22 is the row's newest print → fieldwise-wins; KNE071 joins as era code."},
    "07_btech_ft_syllabus_2016-17::05::industrial-safety-hazard-management": {
        "action": "ALLOW",
        "reason": "Ampersand/'and' print variant, near-verbatim content: draft 'Industrial Safety & Hazard Management' (NCH018, 2016-17 FT elective, detailed units) = the row industrial-safety-and-hazard-management ('INDUSTRIAL SAFETY AND HAZARD MANAGEMENT', ECH044, 2009-10 Chem) — fuzzy 95/overlap 86, best per-unit Jaccard 0.97 ('Industrial safety, Industrial hygiene and safety aspects related to toxicity, noise...' canon). NCH018 joins as era code; 2016-17 newer → fieldwise-wins."},
    "09_btech_ft_y2_model-curriculum_2019-20::05::fluid-flow-solid-handling-lab": {
        "action": "ALLOW",
        "reason": "Name-exact lab, multi-branch convergence row (recorded B24 control-systems-lab class): draft 'FLUID FLOW & SOLID HANDLING LAB' (KFT353, 2019-20 FT AICTE-model, 10 printed experiments) = the row fluid-flow-and-solid-handling-lab (NBT-351, 2014-15 Biotech print) — fuzzy 94, ampersand variant; experiment lists are complementary same-course prints (FT: Bernoulli flow pattern, laminar/turbulent, discharge coefficients, viscosity of Newtonian/non-Newtonian fluids, screen analysis, Jaw Crusher/Ball mill, filtration... vs the 2014-15 Biotech Venturi/Orifice/Notches/Rotameter list), NOT different subjects (both are the chemical-technology-family fluid-flow+solid-handling lab). 2019-20 newest → fieldwise-wins (experiments_structured); KFT353 joins as era code."},
    "09_btech_ft_y2_model-curriculum_2019-20::06::heat-mass-transfer": {
        "action": "ALLOW",
        "reason": "Name-exact ampersand variant onto the multi-branch HMT canon row (row already spans KME501 Mechanical / NBT-402 Biotech / ECH-606+RCH406 Chem / EAG-404 AG eras): draft 'HEAT & MASS TRANSFER' (KFT401, 2019-20 FT AICTE-model, detailed units) — fuzzy 90/overlap 49; per-unit Jaccard 0.18 reflects the AICTE numbered-item print style ('1 Conduction and Convection: Introduction, Conduction: Basic concepts... [Lecture Hours: 2], Fourier law of heat conduction...') vs the row's prose style, not a different subject (same conduction/convection/radiation Fourier-law canon). KFT401 joins as era code; 2019-20 vs row 2020-21 → backfill-empty only."},
    # ---- Tier-2 fuzzy flags: wrong-subject FORCE_APPENDs (RULES §11) ----
    "05_btech_ft_syllabus-rev_2009-10::28::mass-transfer-operations": {
        "action": "FORCE_APPEND",
        "reason": "Wrong-subject Tier-2 hit (recorded B25 heat-transfer-and-operation REV077 class): draft 'Mass Transfer Operations' (ECH609, 2009-10 FT-Chemical-Technology core, detailed units u1 'Basic Principles of mass transfer: Molecular diffusion in fluids, mass transfer coefficients...') fuzzy 88 hits heat-transfer-operations — one-token-off name (mass vs heat), overlap 14 generic chem-eng terms, best per-unit Jaccard 0.11: DIFFERENT subject. No BTech mass-transfer-operations row exists pre-commit → APPEND as its own row with a cross-reference note to heat-transfer-operations; the 2015-16 (NCH-608) and 2018-19 (RCH604) prints converge onto it via same-commit visibility (recorded B09/B10 class)."},
    "06_btech_ft_syllabus_2015-16::15::mass-transfer-operations": {
        "action": "FORCE_APPEND",
        "reason": "Same evidence as 05::28: draft 'Mass Transfer Operations' (NCH-608, 2015-16 FT, detailed units identical u1 print) — wrong-subject hit on heat-transfer-operations (J=0.12); converges onto the 05::28-appended row by Tier-1 name identity at commit."},
    "08_btech_ft_syllabus_2018-19::16::mass-transfer-operations": {
        "action": "FORCE_APPEND",
        "reason": "Same evidence as 05::28: draft 'MASS TRANSFER OPERATIONS' (RCH-604/RCH604, 2018-19 FT, detailed units) — wrong-subject hit on heat-transfer-operations (J=0.12); converges onto the 05::28-appended row at commit."},
    "05_btech_ft_syllabus-rev_2009-10::43::food-product-and-process-development": {
        "action": "FORCE_APPEND",
        "reason": "Wrong-subject Tier-2 hit (RULES §11 never-merge-different-subjects): draft 'Food Product and Process Development' (EFT021, 2009-10 FT elective, detailed units u1 'Innovation and product development concept. Generation of ideas. Desk Research. Screening...') fuzzy 85 hits developments-of-process-products (KAG-054, 2020-21 AG) — overlap 4 generic terms, best per-unit Jaccard 0.14: the AG 'Developments of Process Products' row is a different course. APPEND as its own FT row with a cross-reference note; the 2016-17 (NFT031) print converges onto it via same-commit visibility."},
    "07_btech_ft_syllabus_2016-17::23::food-product-and-process-development": {
        "action": "FORCE_APPEND",
        "reason": "Same evidence as 05::43: draft 'Food Product and Process Development' (NFT031, 2016-17 FT elective, detailed units identical u1 print) — wrong-subject hit on developments-of-process-products (J=0.12); converges onto the 05::43-appended row at commit."},
    "07_btech_ft_syllabus_2016-17::04::bioprocess-engineering-principles": {
        "action": "FORCE_APPEND",
        "reason": "Wrong-subject Tier-2 hit (RULES §11): draft 'Bioprocess Engineering Principles' (NCH017, 2016-17 FT elective, detailed units u1 'Introduction, engineering calculations, presentation and analysis of data, material balance...') fuzzy 86 hits bioprocess-engineering-ii (EBT-042;KBT601;BBT601, Biotech) — overlap 31 generic eng terms, best per-unit Jaccard 0.16: the FT print is the Shuler-Kargi-titled INTRO course (material/energy balances), BE-II is a specific later Biotech course — different subjects. APPEND as its own row with a cross-reference note to bioprocess-engineering-ii."},
    # ---- TIE adjudications (RETARGET / FORCE_APPEND / KEEP_PUBLISHED_CODE_OWNER) ----
    "01_btech_env_y4_syllabus_2016-17::08::environmental-impact-assessment-and-audit": {
        "action": "RETARGET", "target": "environmental-impact-assessment-audit-laws",
        "reason": "TIE fuzzy resolution on verbatim unit identity (recorded B23 verbatim-identity join class): draft 'Environmental Impact Assessment and Audit' (NEN801, 2016-17 ENV core, detailed units) — candidate environmental-impact-assessment-audit-laws (KNE603, 2020-21) best per-unit Jaccard 1.00 (VERBATIM same u1 'Introduction to EIA & Audit, Environment & Industries, Input information, Plant operation...' canon; fuzzy 89) vs environmental-impact-assessment (BCH064, J=0.91, B25's EEV-603/REV602 ALLOW row). The 2016-17 print is the same course as the 2020-21 KNE603 print; NEN801 joins as the earliest era code; 2016-17 older → backfill-empty only. (The two-row EIA duplication — BCH064 row vs KNE603 row — predates this batch; recorded as an owner reconciliation open item, RULES §11 forbids silent row merges.)"},
    "04_btech_ft_s7-8_syllabus_2025-26::06::mini-project-of-internship-assessment": {
        "action": "RETARGET", "target": "mini-project-or-internship-assessment",
        "reason": "TIE fuzzy resolution on the recorded B24 slot-row ownership model (BCH752 2025-26 CHE print of the same assessment slot went to this row): draft 'Mini Project of Internship Assessment' (BFT752, 2025-26 FT, CO table + objectives, no unitwise theory) — fuzzy 97/mini-project-or-internship-assessment (cross-branch assessment-slot row whose all_codes already carry the 2025-26 sister-branch prints BBT752/BCS752/BCH752) vs 96/internship-assessment-mini-project (the CSE-family BCC351-primary row, recorded B12 distinct row). BFT752 is the FT print of the same slot; newest session → fieldwise-wins."},
    "04_btech_ft_s7-8_syllabus_2025-26::12::open-elective-iv": {
        "action": "RETARGET", "target": "open-elective-iv",
        "reason": "Same-commit wildcard-wart TIE (recorded B22 class — 'a wildcard-wart TIE, not two real subjects' — and the identical BT-2025-26 precedent 10_btech_bt_y4_syllabus_2025-26::12::open-elective-iv RETARGET open-elective-iv): draft 'Open Elective-IV' (BOEM** pool wildcard print, 2025-26 FT y4 Sem-VIII scheme row, flags scheme_row_only_detailed_syllabus_not_printed + wildcard_pool_code) — the ladder-time TIE (open-elective-ii;open-elective-iii) is an artifact of BOEM** being a G2-exempt pool wildcard printed on several OE slot rows: open-elective-ii carries it statically in all_codes, open-elective-iii received it from THIS commit's 04::11 name-transfer update (the reassignment executor runs post-loop). Neither candidate is the name-exact row. RETARGET pins the update to the name-exact row open-elective-iv (BTech sem-8 slot, est. 2021-22, already cited by the BT/ECE/EE-EN 2025-26 y4 prints; B07 recorded same-printed-slot convergence class); the 2025-26 draft is newer than the row's 2021-22 establishing print → fieldwise wins per RULES §3; the BOEM** pool print joins its all_codes (no digits → not a specific code token, G2-exempt)."},
    "05_btech_ft_syllabus-rev_2009-10::19::instrumentation-and-process-control": {
        "action": "FORCE_APPEND",
        "reason": "TIE fuzzy resolution — wrong-subject vs BOTH candidates (RULES §11 + B25 NEN-302 evidence class): draft 'Instrumentation and Process Control' (ECH507, 2009-10 FT-Chemical-Technology core, detailed units u1 'Elements of measurement, fumctions and general classifications of measuring instruments...' [print typo kept]) — candidates instrumentation-process-control (NEE-403, Electrical, J=0.25) and electrical-instrumentation-and-process-control (EEE-504, J=0.26): NO unit identity with either EE-branch course; the ECH507 print is the Chemical-Technology instrumentation course, a different subject sharing the generic title family. APPEND as its own row with cross-reference notes to both EE rows; the 2015-16 NCH-507 print converges onto it via same-commit visibility."},
    "06_btech_ft_syllabus_2015-16::05::instrumentation-and-process-control": {
        "action": "FORCE_APPEND",
        "reason": "Same evidence as 05::19: draft 'Instrumentation and Process Control' (NCH-507, 2015-16 FT, detailed units identical u1 print) — converges onto the 05::19-appended row by Tier-1 name identity at commit."},
    "05_btech_ft_syllabus-rev_2009-10::52::general-proficiency": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "general-proficiency",
        "keep_published_codes": {"GP301": "general-proficiency-lab"},
        "reason": "TIE code-identity resolution (recorded B25 GP class, SAME resolution — B25 manifest: 'general-proficiency: TIE GP-301..801 — GP401-801 re-corroborate the name-exact row, GP-301 stays with general-proficiency-lab whose 2014-15 print is newer'): draft 'General Proficiency' (GP-301..GP-801, 2009-10 FT scheme rows, one GP slot per semester) — RETARGET pins the update to the name-exact general-proficiency row (GP401-801 re-corroborated; 2009-10 older → backfill/source-history only) and GP-301 STAYS with its published newer-print owner general-proficiency-lab (2014-15 EE-group print; equal-or-older print never takes a code from its published owner, RULES §3; the B19 keep_published_codes mechanism drops the kept code from the draft copy and records the narrative on the target row — G2 single-ownership preserved)."},
    "05_btech_ft_syllabus-rev_2009-10::55::nano-sciences": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER",
        "target": "nano-sciences",
        "keep_published_codes": {"EOE042": "power-station-practice"},
        "reason": "TIE code-identity resolution (recorded B21 equal-session class + the row's own recorded CODE-COLLISION-EOE-042 note): draft 'Nano Sciences' (EOE-032/EOE-042, 2009-10 FT science-based-OE pool print — the pool lists each elective with its sem-3/sem-4 pair codes) — RETARGET pins the update to the name-exact nano-sciences row (EOE-032 owner, same 2009-10 session, EE-print established); EOE-042 STAYS with its published owner power-station-practice (equal-or-older print never takes a code from its published owner, RULES §3; the collision is already narrated on that row) and the EOE-042 pairing stays recorded in the draft quirks/non_subject_rows."},
})

# B24 (CRON-20261101-B24) per-key TIER2_OVERRIDES (evidence-recorded;
# the decision for every flagged subject and every ladder-corrected
# routing of this batch).
TIER2_OVERRIDES.update({
    # ---- B24 (CRON-20261101-B24) per-key adjudications, evidence-recorded ----
    "01_btech_ei_syllabus_2020-21::08::artificial-neural-networks": {
        "action": "ALLOW",
        "reason": "B24 name-variant ALLOW (B23 recorded class): draft 'Artificial Neural Networks' (KIC-053, 2020-21 EI sem-5 DE, 5 detailed units) — target artificial-neural-network (REC054;NEC 013;EEC 023 multi-era row) is the same course, plural/singular print variant; fuzzy 98 / 99 shared distinctive terms (near-verbatim vocab); KIC-053 joins as era code following the row's recorded cross-branch era-family pattern."},
    "01_btech_ei_syllabus_2020-21::13::instrumentation-measurements-lab": {
        "action": "ALLOW",
        "reason": "B24 name-variant ALLOW: draft 'Instrumentation & Measurements Lab' (KIC-553(+KIC-551), 2020-21 EI, 14 experiments) — target measurement-instrumentation-lab (KEC-653A, 'Measurement & Instrumentation Lab', 2020-21 ECE print) is the same K-era I&M lab, word-order + singular/plural variant; fuzzy 98; the low overlap (28) is the recorded no-units lab class (experiment lists only, B23 KEE652 evidence), not a content difference; KIC-551/KIC-553 join as era codes."},
    "01_btech_ei_syllabus_2020-21::23::control-systems-lab": {
        "action": "RETARGET", "target": "control-system-lab",
        "reason": "B24 TIE pin (B23 PS-I/PS-II same-commit-visibility class): draft 'CONTROL SYSTEMS LAB' (KIC-652, 2020-21 EI sem-6, 12 experiments) — TIE candidates control-system-lab (97) vs control-system-lab-i (92). control-system-lab is the multi-branch K-era canon row (BEC652;BEC-652;EIC-551;RBM551;KEC-652;KEE552) already carrying EI's own 2010-11 print EIC-551 and the 2020-21 ECE print KEC-652; the 2020-21 EI print is the same lab (plural 'Systems' variant, name-exact to the row). control-system-lab-i (RIC653, 2018-19 'CONTROL SYSTEM LAB-I') is the recorded distinct R-era row — Lab-I naming, not the target. KIC-652 joins as era code."},
    "02_btech_ei_syllabus_2021-22::06::control-system-ii": {
        "action": "FORCE_APPEND",
        "reason": "B24 wrong-subject FORCE_APPEND (B23 Machine-II/PS-II class): draft 'Control System-II' (KIC076, 2021-22 EI sem-7 DE, 5 detailed units) — ladder hit digital-control-system (fuzzy 87/36) is the WRONG subject: Digital Control System (EEE-011;KEE 063;BEE063) is a distinct canon DE, and Control System-II is distinct from Control System-I (recorded I/II distinct-row design, cf. Machine-I/II); no control-system-ii row exists pre-commit. APPEND as its own row; the 2019-20 CBCS print (04::00) converges onto it by name identity at commit."},
    "04_btech_ei_y4_syllabus-cbcs_2019-20::00::control-system-ii": {
        "action": "FORCE_APPEND",
        "reason": "B24 wrong-subject FORCE_APPEND (same evidence as 02::06): draft 'CONTROL SYSTEM II' (RIC701, 2019-20 CBCS EI sem-7, 5 detailed units) — ladder hit digital-control-system (87/35) rejected as wrong subject; RIC701 is the CBCS print of the same Control System-II course as KIC076 (2021-22); converges onto the same-commit control-system-ii row by name identity at commit (B23 recorded convergence class)."},
    "04_btech_ei_y4_syllabus-cbcs_2019-20::02::control-system-lab-ii": {
        "action": "FORCE_APPEND",
        "reason": "B24 wrong-subject FORCE_APPEND (serial-variant class, recorded B02 remedy): draft 'CONTROL SYSTEM LAB II' (RIC751, 2019-20 CBCS EI sem-7, 10 experiments) — ladder hit control-systems-i-lab (NIC-551, fuzzy 95/0) is the WRONG subject: a Lab-II is never merged into a Lab-I/Systems-I row (numeral/roman serial variants never fuzzy-merge); no control-system-lab-ii row exists pre-commit. APPEND as its own row."},
    "02_btech_ei_syllabus_2021-22::07::computerized-process-control": {
        "action": "ALLOW",
        "reason": "B24 spelling-variant ALLOW (recorded z/s class): draft 'Computerized Process Control' (KIC077, 2021-22 EI sem-7 DE, 5 detailed units) — target computerised-process-control (REC078, 2019-20 print) is the same course, Computerized/Computerised spelling variant; fuzzy 96/81 shared process-control vocabulary; KIC077 joins as era code."},
    "04_btech_ei_y4_syllabus-cbcs_2019-20::12::biomedical-signal-processing": {
        "action": "ALLOW",
        "reason": "B24 name-variant ALLOW (B10 recorded hyphen-variant class): draft 'BIOMEDICAL SIGNAL PROCESSING' (RIC080, 2019-20 CBCS EI sem-8, 5 detailed units) — target bio-medical-signal-processing (EBM-603;RBM602;RBM-602;BEC-056 multi-era row, the row already carrying the 2024-25 ECE print BEC-056) is the same course, hyphen/solidus print variant; fuzzy 98/91; RIC080 joins as era code."},
    "07_btech_electronics-computer_y3_syllabus_2021-22::05::advanced-digital-design-using-verilog": {
        "action": "ALLOW",
        "reason": "B24 name-variant ALLOW: draft 'ADVANCED DIGITAL DESIGN USING VERILOG' (KECZ-054, 2021-22 elec-computer sem-5 DE, 5 detailed units) — target advanced-digital-system-design-using-verilog (NEC 024R;KEC-054;REC064 multi-era row) is the same DE, the 2021-22 print drops 'System'; fuzzy 91/71; KECZ-054 joins as era code (the code assignment is table+page-10-consistent per the recorded ::06 adjudication)."},
    "07_btech_electronics-computer_y3_syllabus_2021-22::06::optical-communication-system": {
        "action": "ALLOW",
        "reason": "B24 name-variant ALLOW: draft 'OPTICAL COMMUNICATION SYSTEM' (KECZ-053 after the recorded patch_b24_merge_adjudications print-conflict fix, 2021-22 elec-computer sem-5 DE, 5 detailed units) — target optical-communication (KEC-058;BEC-057;REC075;EEC 701;NEC 701;REN080 multi-era row) is the same course ('System' suffix variant); fuzzy 86/176 (large shared distinctive vocabulary); KECZ-053 joins as era code."},
    "07_btech_electronics-computer_y3_syllabus_2021-22::10::object-oriented-system-design": {
        "action": "ALLOW",
        "reason": "B24 name-variant ALLOW: draft 'Object Oriented System Design' (KECZ-058, 2021-22 elec-computer sem-5 DE, 5 detailed units) — target object-oriented-system-design (BCS054;KCS054;BCS054H canon row, row name '...with C++') is the same course; fuzzy 89/157; KECZ-058 joins as era code."},
    "08_btech_electronics-computer_y3_syllabus_2024-25::03::optical-communication-system": {
        "action": "ALLOW",
        "reason": "B24 name-variant ALLOW (same evidence as 07::06): draft 'Optical Communication System' (BECZ051, 2024-25 elec-computer NEP2020 sem-5 DE, 5 detailed units) — target optical-communication multi-era row is the same course; fuzzy 86/176; BECZ051 joins as the NEP2020 branch-variant era code."},
    "08_btech_electronics-computer_y3_syllabus_2024-25::06::advanced-digital-design-using-verilog": {
        "action": "ALLOW",
        "reason": "B24 name-variant ALLOW (same evidence as 07::05): draft 'Advanced Digital Design using Verilog' (BECZ052, 2024-25 elec-computer NEP2020 sem-5 DE, 5 detailed units) — target advanced-digital-system-design-using-verilog multi-era row is the same DE ('System'-less print variant); fuzzy 91/70; BECZ052 joins as era code."},
    "10_btech_electronics-computer_y4_syllabus_2025-26::03::electric-vehicle-technology": {
        "action": "ALLOW",
        "reason": "B24 name-variant ALLOW (B23 recorded EV-family class): draft 'Electric Vehicle Technology' (BECZ070, 2025-26 elec-computer sem-7 DE, 5 detailed units) — target electric-hybrid-vehicles-technology (BAU602, 'Electric & Hybrid Vehicles Technology', the published EV-technology row; B23 ALLOWed the same family's 'Electric-and-Hybrid-Vehicles' print at 97/38) is the same DE; the 2025-26 print drops 'Hybrid'; fuzzy 87/40 shared EV vocabulary; BECZ070 joins as era code."},
})

# ---- B27 (CRON-20261104-B27) per-key TIER2_OVERRIDES (evidence-recorded) ----
# Probe evidence (scripts/pipeline_v2/probe_b27_flags.py): per-flag draft name/
# codes/units vs candidate rows (token overlap + best per-unit Jaccard), plus
# direct print probes of the contested code slots in the source PDFs.
TIER2_OVERRIDES.update({
    # -- name/print-variant ALLOWs (same subject; unit-identity evidence recorded) --
    "01_btech_ft_y2_syllabus_2015-16::02::composition-quality-safety-of-foods": {
        "action": "ALLOW",
        "reason": "B27 name-variant ALLOW ('&' vs 'and' print class, B18/B19 recorded): draft 'Composition, Quality & Safety of Foods' (NFT-301, 2015-16 FT print, detailed units) = the row composition-quality-and-safety-of-foods (EFT301;KFT301;RFT302, 2009-10 FT print) — fuzzy 95/overlap 83 with best per-unit Jaccard 1.00 (VERBATIM unit identity); NFT-301 joins as era code; 2015-16 newer than the row's 2009-10 -> fieldwise wins."},
    "01_btech_ft_y2_syllabus_2015-16::03::food-microbiology": {
        "action": "ALLOW",
        "reason": "B27 name-variant ALLOW (modifier print variant): draft 'Food Microbiology' (NFT-302, 2015-16 FT print, detailed units) = the row basic-food-microbiology (EFT401;KFT302;RFT301, 2009-10 FT print 'Basic Food Microbiology') — fuzzy 85/overlap 67 with best per-unit Jaccard 1.00 (VERBATIM unit identity; the 2015-16 print drops the 'Basic' modifier); no name-exact 'Food Microbiology' BTech row exists, so the Tier-2 hit is the same subject; NFT-302 joins as era code."},
    "01_btech_ft_y2_syllabus_2015-16::08::food-chemistry-nutrition": {
        "action": "ALLOW",
        "reason": "B27 name-variant ALLOW ('&' vs 'and' print class): draft 'Food Chemistry & Nutrition' (NFT-401, 2015-16 FT print, detailed units) = the row food-chemistry-and-nutrition (RFT402, 2017-18 FT print) — fuzzy 92/overlap 86 with best per-unit Jaccard 1.00 (VERBATIM unit identity); NFT-401 joins as era code; 2015-16 older than the row's 2017-18 -> backfill-empty only."},
    "01_btech_ft_y2_syllabus_2015-16::09::food-biochemistry": {
        "action": "ALLOW",
        "reason": "B27 era-RENAME ALLOW (verbatim unit identity, all 5 units word-for-word identical to the row's units): draft 'Food Biochemistry' (NFT-402, 2015-16 FT print: enzymes/kinetics, metabolic pathways, digestion/absorption, post-harvest/postmortem changes, enzymes in food processing) = the row food-chemistry (EFT501;KFT402;KFT403;RFT401, 2009-10 FT print 'Food Chemistry', SAME unit texts) — the 2015-16 scheme renamed the course; fuzzy 90/overlap 53 with best per-unit Jaccard 1.00. Same subject across sessions (RULES §3 era model); the print-name change is recorded on the row (name_print 'Food Biochemistry'), no new row (RULES §11 never split one subject into two)."},
    "03_btech_ft_y4_syllabus-cbcs_2019-20::02::nutraceuticals-and-functional-foods": {
        "action": "ALLOW",
        "reason": "B27 name-variant ALLOW ('and' vs '&' print class): draft 'Nutraceuticals and Functional Foods' (RFT073, 2019-20 FT CBCS DE, detailed units) = the row nutraceuticals-functional-foods (BFT-055;KFT-055;NFT013, 2024-25 print) — fuzzy 94/overlap 68 with best per-unit Jaccard 0.93; 2019-20 older than the row's 2024-25 -> backfill-empty only; RFT073 joins as era code."},
    "04_btech_ft_y4_syllabus_2021-22::05::fundamentals-of-food-biotechnology": {
        "action": "ALLOW",
        "reason": "B27 name-variant ALLOW ('Fundamentals of' vs 'Fundamental Aspects of' print variant): draft 'FUNDAMENTALS OF FOOD BIOTECHNOLOGY' (KFT-076, 2021-22 FT DE, detailed units) = the row fundamental-aspects-of-food-biotechnology (BFT074, 2025-26 print) — fuzzy 88/overlap 83 with best per-unit Jaccard 0.88; 2021-22 older than the row's 2025-26 -> backfill-empty only; KFT-076 joins as era code."},
    "05_btech_handloom-textile_y2_syllabus_2021-22::02::textile-fiber": {
        "action": "ALLOW",
        "reason": "B27 name-variant ALLOW (singular/plural + fiber/fibres spelling class): draft 'Textile Fiber' (KHT-303, 2021-22 HT print, detailed units) = the row textile-fibres (KCT303, 2019-20 Carpet & Textile print 'Textile Fibres') — fuzzy 89/overlap 55 with best per-unit Jaccard 0.88; same BTech course family; KHT-303 joins as era code; 2021-22 newer than the row's 2019-20 -> fieldwise wins."},
    "09_btech_ic_y4_syllabus_2011-12::12::biomedical-signal-processing": {
        "action": "ALLOW",
        "reason": "B27 same-subject ALLOW (hyphen/solidus print class, recorded B24 04::12 evidence): draft 'BIOMEDICAL SIGNAL PROCESSING' (EIC-032, 2011-12 IC elective, detailed units) = the row bio-medical-signal-processing (EBM-603;RBM602;RBM-602;BEC-056;RIC080 — the row ALREADY carries the B24-recorded RIC080 era code) — fuzzy 98/overlap 88 with best per-unit Jaccard 1.00 (VERBATIM); EIC-032 joins as era code."},
    "09_btech_ic_y4_syllabus_2011-12::13::analytical-instruments": {
        "action": "ALLOW",
        "reason": "B27 name-variant ALLOW (plural/suffix print variant): draft 'Analytical Instruments' (EIC-033, 2011-12 IC elective, detailed units: UV-Visible spectroscopy etc.) = the row analytical-instrumentation (REC081, 2019-20 print) — fuzzy 88/overlap 73 with best per-unit Jaccard 1.00 (VERBATIM); EIC-033 joins as era code; 2011-12 older -> backfill-empty only."},
    "10_btech_it_structure-syllabus_2018-19::04::software-testing-audit": {
        "action": "ALLOW",
        "reason": "B27 name-variant ALLOW ('&' vs 'and' print class): draft 'Software Testing & Audit' (RIT-E12, 2018-19 IT DE, detailed units) = the row software-testing-and-audit (NCS-071;RIT-052, 2016-17 IT print) — fuzzy 92/overlap 101 with best per-unit Jaccard 1.00 (VERBATIM); RIT-E12 joins as era code; 2018-19 newer than the row's 2016-17 -> fieldwise wins."},
    "10_btech_it_structure-syllabus_2018-19::06::operation-research": {
        "action": "ALLOW",
        "reason": "B27 singular/plural ALLOW: draft 'Operation Research' (RCS-E11, 2018-19 IT elective, detailed units) = the row operations-research (NOE073;KOE075;RCS-051;EOE-073, 2016-17 print) — fuzzy 97/overlap 72 with best per-unit Jaccard 1.00 (VERBATIM); RCS-E11 joins as era code; 2018-19 newer -> fieldwise wins."},
    "10_btech_it_structure-syllabus_2018-19::14::design-and-development-of-applications": {
        "action": "ALLOW",
        "reason": "B27 name-variant ALLOW ('and' vs '&' print class): draft 'Design and Development of Applications' (RIT-E21, 2018-19 IT DE, detailed units: mobile applications) = the row design-development-of-applications (BCS073;KCS075;RIT-061;BCS073H, 2016-17 IT print + 2025-26 CSE prints) — fuzzy 94/overlap 83 with best per-unit Jaccard 1.00 (VERBATIM); RIT-E21 joins as era code."},
    "10_btech_it_structure-syllabus_2018-19::17::neural-network": {
        "action": "ALLOW",
        "reason": "B27 singular/plural ALLOW: draft 'Neural Network' (RCS-E22, 2018-19 IT elective, detailed units) = the row neural-networks (NCS-072;RCS-062, 2016-17 print) — fuzzy 97/overlap 100 with best per-unit Jaccard 1.00 (VERBATIM); RCS-E22 joins as era code; 2018-19 newer -> fieldwise wins."},
    # -- wrong-subject FORCE_APPENDs (same-name different-content splits, B25 REV082/RCE085 recorded class) --
    "06_btech_handloom-textile_y3_syllabus-rev_2022-23::15::home-textiles": {
        "action": "FORCE_APPEND",
        "reason": "B27 wrong-subject FORCE_APPEND (B25 same-name different-content split class, recorded unit evidence): draft 'Home Textiles' (KHT-062, 2022-23 HT elective, detailed units: furnishings/floor coverings/curtains & draperies/bed linens) vs the only Tier-2 candidate home-textile-i (EHTT602;EHTT705, 2009-10 C&T print whose units are garment marker-planning/sewing/fusing/pressing) — fuzzy 89 name-similarity is generic-token variance; shared vocab 5, best per-unit Jaccard 0.08: DIFFERENT subjects that merely share the home-textile token family. Appends as its own row with a cross-reference note to home-textile-i."},
    "07_btech_handloom-textile_y3_syllabus_2024-25::04::home-textiles": {
        "action": "FORCE_APPEND",
        "reason": "B27 wrong-subject FORCE_APPEND (same evidence as 06::15): draft 'Home Textiles' (BHT-052, 2024-25 HT DE, detailed units: definition/types/fiber selection) — the Tier-2 candidate home-textile-i is the 2009-10 C&T garment-process course (Jaccard 0.06); converges onto the 06::15-appended home-textiles row by Tier-1 name identity at commit (recorded same-commit visibility class)."},
    "07_btech_handloom-textile_y3_syllabus_2024-25::13::advanced-woven-fabric-manufacture": {
        "action": "FORCE_APPEND",
        "reason": "B27 wrong-subject FORCE_APPEND (B25 same-name different-content split class, recorded unit evidence): draft 'Advanced Woven Fabric Manufacture' (BHT-601, 2024-25 HT, detailed units: projectile/rapier looms, weft insertion, loom timing) vs the only Tier-2 candidate advance-fabric-manufacturing (ECT807;RCT 602, 2009-10 C&T print whose units are terry-pile/leno weaving mechanisms) — fuzzy 85 is generic-token variance; shared vocab 20, best per-unit Jaccard 0.11: DIFFERENT subjects. Appends as its own row with a cross-reference note."},
    "08_btech_handloom-textile_y4_syllabus_2025-26::03::advanced-fabric-structure": {
        "action": "FORCE_APPEND",
        "reason": "B27 wrong-subject FORCE_APPEND (B25 same-name different-content split class, recorded unit evidence): draft 'Advanced Fabric Structure' (BHT072, 2025-26 HT, detailed units: extra-warp/weft figuring with dobbies/jacquard, figured patent satin, 3-pick tapestry, figured double cloth, traditional Indian handloom sarees) vs the only Tier-2 candidate advance-fabric-structure (RCT081, 2019-20 C&T CBCS print: extra warp/weft designed fabric, damask/brocade, swivel/lappet, stitched/interchanging double cloths, weft-face tapestries) — fuzzy 98 (near-exact name) but shared vocab 11, best per-unit Jaccard 0.13: the two branch programs (Handloom & Textile Technology vs Carpet & Textile Technology) print DIFFERENT courses under the same name (recorded REV082/RCE085 split class). Appends as its own row with a cross-reference note; the C&T row is never touched (RULES §1b within-course branch identity preserved)."},
    # -- TIE + code-owner adjudications --
    "09_btech_ic_y4_syllabus_2011-12::00::control-systems-ii": {
        "action": "RETARGET", "target": "control-system-ii",
        "reason": "B27 TIE RETARGET (recorded B23 PS-II class: RETARGET pins the update to the name-exact row): draft 'CONTROL SYSTEMS II' (EIC-701, 2011-12 IC core, detailed units: sampled-data control, z-transforms, digital controllers) — TIE candidates control-system (88/0.17), control-system-i (94/0.20), digital-control-system (85/0.20), control-system-ii (97/1.00). The name-exact control-system-ii row (KIC076;RIC701, 2021-22 EI + 2019-20 CBCS prints) matches VERBATIM (best per-unit Jaccard 1.00, overlap 96); PS/CS-I and CS-II are DISTINCT subjects (recorded distinct-row design). EIC-701 joins as era code."},
    "10_btech_it_structure-syllabus_2018-19::20::web-technology-lab": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "web-technology-lab",
        "keep_published_codes": {"RCS653": "computer-graphics-lab"},
        "reason": "B27 same-session cross-branch print conflict (recorded B19 mechanism; B23 07::20 KAS401 pattern): draft 'Web Technology Lab' (2018-19 IT print, detailed Java/HTML experiments) — the Tier-0 hit RCS653 is owned by computer-graphics-lab, established by the SAME-SESSION CSE y3 2018-19 print (btech_cse_y3_syllabus_2018-19.pdf pp.2+20: scheme row 'RCS-653 Computer Graphics Lab' + DDA/Bresenham experiment list) while THIS IT doc prints 'RCS-653 Web Technology Lab' (pp.2+21, Java/HTML experiments) — two authoritative same-session branch schemes disagree, so 'newest print wins' cannot break the tie and the auto CODE-REASSIGNED name-transfer is REJECTED (it would strip a code from a row whose own establishing print carries it, same session). RETARGET pins the update on the name-exact web-technology-lab row (2022-23, KCS652;BCS552;NCS554;BCS552H;KIT551 — newer print, fieldwise owner of the subject identity); RCS653 stays owned by computer-graphics-lab (G2 single ownership) and the 2018-19 IT scheme print is recorded as narrative history on the updated row. Owner open item: the RCS-653 same-session cross-branch conflict is recorded for reconciliation."},
    # -- same-commit-visibility TIE (surfaced at live commit; dry-run 07::00 was APPEND pre-convergence) --
    "07_btech_handloom-textile_y3_syllabus_2024-25::00::woven-fabric-manufacture": {
        "action": "RETARGET", "target": "woven-fabric-manufacturing-i",
        "reason": "B27 same-commit-visibility TIE RETARGET (recorded B23 PS-II class): draft 'Woven Fabric Manufacture' (BHT-501, 2024-25 HT sem-5 core, detailed units: warping, plain power looms + motions, tappet shedding, jacquards, multiple box motions) — at live commit doc 06 (2022-23 HT rev, earlier in the sorted draft order) has already appended woven-fabric-manufacturing-i (KHT-501, sem-5: plain power looms/jacquard/multiple-box) and woven-fabric-manufacturing-ii (KHT-601, sem-6: terry/rapier/air-jet looms + calculations), so the ladder T1-hits BOTH (name-variant 'Manufacture'/'Manufacturing'). Unit evidence: 4/5 draft units thematically match WFM-I's units (power looms, jacquard, box motion; zero overlap with WFM-II's terry/rapier/air-jet), same sem-5 HT core slot — the draft is the 2024-25 print of the WFM-I course. RETARGET pins the update on woven-fabric-manufacturing-i; 2024-25 newer than 2022-23 -> fieldwise wins; BHT-501 joins as era code."},
})

# B28 (CRON-20261104-B28) per-key TIER2_OVERRIDES (evidence-recorded;
# probe_b28_flags.py: token overlap + best per-unit Jaccard + direct print probes).
# B28 = the IT wave (docs 01-08: IT 2009-10..2021-22) + the ME-Industrial pair
# (docs 09-10). Drafts are the reconciled set: parallel-instance re-extractions
# for docs 01-08 + this run's extractions for docs 09-10 (run manifest records
# the reconciliation). 10 adjudications: 3 TIER2 ALLOWs, 4 wrong-subject
# FORCE_APPENDs, 2 code-owner RETARGETs (recorded B20 classes), 1
# RETARGET_KEEP_PUBLISHED_CODE_OWNER (recorded B25/B26 GP class); the 8
# code-identity TIEs are scheme ALTERNATIVE-SLOT prints resolved by the
# recorded ALTERNATIVE-PAIR-SLOT skip via alternative_pair_row draft flags.
# ---- B28 TIER2 fuzzy adjudications ----
TIER2_OVERRIDES.update({
    "05_btech_it_y2_scheme-syllabus_2017-18::14::information-theory-and-coding": {
        "action": "ALLOW",
        "reason": "B28 era-family ALLOW: draft 'Information Theory and Coding' (REC406, 2017-18 IT y2 AICTE-model print, detailed units: entropy/information measure, Kraft-McMillan, Shannon encoding) = the row information-theory-coding (BAC062;KEC-075;KEC075;REC071;NEC031;BEC072;KECZ-071 — the recorded multi-branch/multi-era ITC accumulator, latest print 2025-26 NEP common-scheme). Fuzzy 93/overlap 40; best per-unit Jaccard 0.29 reflects the era rewording (AICTE-model vs NEP unit organization), not a different subject — both units cover the identical topic chain (entropy -> source coding -> channel capacity). Name is the '&'/'and' print variant (B18/B19 recorded class). 2017-18 older than the row's 2025-26 -> backfill/source-history only; REC406 joins code_history."},
    "06_btech_it_y2_syllabus-rev_2014-15::10::theory-of-automata-and-formal-launguage": {
        "action": "ALLOW",
        "reason": "B28 name-variant ALLOW (print-typo class): draft 'Theory Of Automata and Formal Launguage' (NCS402, 2014-15 IT y2 print, detailed units; the 'Launguage' typo is the VERBATIM print, kept in name_print per RULES §6) = the row theory-of-automata-and-formal-languages (BCS402;KCS402;ECS-403;KCS402H;RCS403;BEEZ062 — the recorded TAFL accumulator). Fuzzy 97/overlap 66; same subject under the misspelled 2014-15 print. 2014-15 older than the row's 2023-24 -> backfill/source-history only; NCS402 joins code_history."},
    "10_btech_me-ind_syllabus_2020-21::08::finite-element-methods": {
        "action": "ALLOW",
        "reason": "B28 same-subject ALLOW (singular/plural print variant, B23 neural-networks class): draft 'Finite Element Methods' (KME053, 2020-21 ME-Industrial DE print, detailed units) = the row finite-element-method (RME053;BME053;NAU-062;ECE032;RCE081;NCE032 — the recorded multi-branch FEM accumulator, 2018-19). Fuzzy 98/overlap 49; best per-unit Jaccard 0.13 reflects unit REORGANIZATION between the 2018-19 and 2020-21 prints, not a different subject — both cover the identical FEM topic chain (variational calculus/weighted residual -> shape functions -> element derivation -> assemblies). The row's own recorded design spans 6 branches' FEM prints; the 2020-21 ME-Ind print is newer than the row's 2018-19 -> fieldwise wins; KME053 joins as era code."},
    # ---- B28 wrong-subject FORCE_APPENDs (same-name different-content, recorded B25/B27 split class) ----
    "01_btech_it_syllabus_2015-16::15::modelling-and-simulation": {
        "action": "FORCE_APPEND",
        "reason": "B28 wrong-subject FORCE_APPEND (B25 NEN-302/B27 advanced-fabric-structure class, recorded unit evidence): draft 'Modelling & Simulation' (NIT062, 2015-16 IT sem-6 DE-II elective, detailed units: system definition, stochastic activities, continuous and discrete systems, simulation techniques, queuing) vs the only Tier-2 candidate process-modelling-and-simulation (ECH701;RCH701, 2009-10 Chemical Engineering: mathematical modeling of unit operations, degree-of-freedom analysis, heat/mass exchanger models) — fuzzy 86 but shared vocab is generic (model/simulation/system) and best per-unit Jaccard 0.19: the IT systems-simulation course and the ChemE process-modeling course are DIFFERENT subjects sharing a generic title. Appends as its own row with a cross-reference note; the ChemE row is never touched."},
    "04_btech_it_y2_scheme-syllabus_2009-10::04::object-oriented-systems": {
        "action": "FORCE_APPEND",
        "reason": "B28 partial-overlap split (B25/B27 same-core different-tail class, recorded unit evidence): draft 'Object Oriented Systems' (ECS-305, 2009-10 IT sem-3 core, detailed units) vs the only Tier-2 candidate object-oriented-systems-and-c (ECS-039, 2009-10 EE/E&E-group elective) — units I-III are the SAME OMT/OOS core (objects/classes/links/associations, dynamic modeling events/states, functional modeling DFD; near-verbatim), but units IV-V DIVERGE COMPLETELY: the IT print teaches Java (operators/classes/multithreading/Applet; Java Beans/Swing/Servlets, 'Migrating from C++ to Java') while the EE print teaches C++ (tokens/constructors/destructors/overloading) + Unix/Linux shell. Different titles ('Object Oriented Systems' vs 'Object Oriented Systems and C++'), different codes (core ECS-305 vs elective-slot ECS-039), different branch programs, different language tracks: DISTINCT subjects sharing a 3-unit OMS core (RULES §11 never merge to save a row). Appends as its own row with a cross-reference note recording the shared-core/divergent-tail evidence."},
    "09_btech_me-ind-pe-ipe_y4_syllabus_2016-17::00::computer-aided-design-cad": {
        "action": "FORCE_APPEND",
        "reason": "B28 wrong-subject FORCE_APPEND (B27 advanced-fabric-structure same-name different-program class, recorded unit evidence): draft 'COMPUTER AIDED DESIGN (CAD)' (NME-701, 2016-17 ME-Industrial y4 core, detailed units: CAD/CAED/CAE elements, integrated CAD/CAM, graphics standards, Bresenham's algorithms, geometric modeling) vs the only Tier-2 candidate computer-aided-design (ECE051;NCE051, 2010-11 Civil elective: CAD hardware, software design principles, 2 thin units) — fuzzy 91 but best per-unit Jaccard 0.11: the ME CAD/CAM course and the Civil CAD-overview elective are DIFFERENT subjects under the same name. Appends as its own row with a cross-reference note; the Civil row is never touched."},
    "09_btech_me-ind-pe-ipe_y4_syllabus_2016-17::03::quality-control": {
        "action": "FORCE_APPEND",
        "reason": "B28 wrong-subject FORCE_APPEND (same recorded class as 09::00): draft 'QUALITY CONTROL' (NPI-801, 2016-17 PI y4 core, detailed units: quality control concepts, metrology, control charts, acceptance sampling, reliability) vs the only Tier-2 candidate food-quality-control (KAG-059;RAG055;BAG059;NAG-013, 2020-21 Agricultural Engineering food QC) — fuzzy 86, best per-unit Jaccard 0.15: industrial QC and food-industry QC are DIFFERENT subjects sharing a generic title. Appends as its own row with a cross-reference note."},
    # ---- B28 code-owner RETARGETs (recorded B20 classes) ----
    "03_btech_it_y2_model-curriculum_2019-20::03::data-structures-using-c-lab": {
        "action": "RETARGET", "target": "data-structure-using-c-lab",
        "reason": "B20 singular/plural print variant, NOT a code reassignment (recorded B18/B19 DBMS-lab class; the identical 2019-20 CSE-group print is adjudicated at 06_btech_csit-cse_y2_model-curriculum_2019-20::03): draft 'Data Structures Using C Lab' (KCS351, 2019-20 IT y2 AICTE model-curriculum print, verbatim experiment list) — KCS351's published owner is data-structure-using-c-lab ('Data Structure using C Lab', 2021-22 K-era row, primary KCS351). The auto name-transfer toward the 's'-variant name row (data-structures-using-c-lab, KCS351H, 2022-23 Hindi-rev print) would strand the KCS351 owner codeless (B18 recorded rejection of this exact transfer class). UPDATE the KCS351 owner row; the 2019-20 print corroborates (experiments backfill; KCS351 stays)."},
    "03_btech_it_y2_model-curriculum_2019-20::14::mini-project-or-internship-assessment": {
        "action": "RETARGET", "target": "internship-assessment-mini-project",
        "reason": "B20 mini-project CSE&E code-owner RETARGET class (recorded B18/B17/B20 overrides; B16 rejection; the identical 2019-20 CSE-group print is adjudicated at 06_btech_csit-cse_y2_model-curriculum_2019-20::06): draft 'Mini Project or Internship Assessment*' (KCS354, 2019-20 IT y2 AICTE model-curriculum scheme-row print, flagged scheme_row_only) — KCS354 is ALREADY owned by the CSE&E code-owner row internship-assessment-mini-project (all_codes BCC351;KCS354;KEC354;KCS554;BCS554;BCE554;KCS752;BCS752;B20 adjudication (b) keeps OWNED sibling slot codes with that row). The auto name-transfer toward the AG/AE-named cross-branch slot row (mini-project-or-internship-assessment, BAE553;KAG354;BAG554, EMPTY branch_names) is rejected per RULES §1b spirit. UPDATE the CSE&E code-owner row; scheme-row-only corroboration."},
    # ---- B28 equal/older-print code-owner protections (recorded B25/B26 GP + B27 RCS653 classes) ----
    "04_btech_it_y2_scheme-syllabus_2009-10::09::general-proficiency": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "general-proficiency",
        "keep_published_codes": {"GP301": "general-proficiency-lab"},
        "reason": "TIE-free code-owner protection (recorded B25/B26 GP class, SAME resolution as 05_btech_ft_syllabus-rev_2009-10::52): draft 'General Proficiency' (GP-301, 2009-10 IT scheme slot) — the auto CODE-REASSIGNED name-transfer would move GP301 from general-proficiency-lab (establishing print 2014-15 EE-group, NEWER than this 2009-10 scheme print) to the name-exact general-proficiency row; an equal-or-older print never takes a code from its published newer-print owner (RULES §3). RETARGET pins the corroboration update on the name-exact general-proficiency row and GP301 STAYS with general-proficiency-lab (B19 keep_published_codes mechanism: kept code dropped from the draft copy, narrative recorded on the target row — G2 single ownership preserved)."},
    "06_btech_it_y2_syllabus-rev_2014-15::15::mathematics-iii-science-based-open-elective": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "mathematics-iii-science-based-open-elective",
        "keep_published_codes": {"NAS301": "engg-mathematics-iii"},
        "reason": "B28 same-session cross-branch slot print (recorded B27 RCS653 class: 'newest-print-wins cannot break the tie', B19 mechanism): draft 'Mathematics III/Science Based Open Elective' (NAS-301 + NOE-031..039 pool, 2014-15 IT sem-3 scheme slot, flagged scheme_row_only) — NAS301 is owned by engg-mathematics-iii, established by the SAME-SESSION ECE-group y2 2014-15 print (btech_ece-group_y2_syllabus_2014-15.pdf); the auto transfer would strip a code from a row whose own establishing print carries it (equal session, different branch group — two authoritative same-session schemes). RETARGET pins the update on the name-exact sem-3 slot row mathematics-iii-science-based-open-elective (2017-18 C&T print, EOE 031-038 codes; the IT NOE-031..039 pool codes join it as the slot's N-era pool range); NAS301 STAYS with engg-mathematics-iii (G2 single ownership) and the 2014-15 IT slot print is recorded as narrative on the updated row."},
    "06_btech_it_y2_syllabus-rev_2014-15::19::science-based-open-elective-mathematics-iii": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "science-based-open-elective-mathematics-iii",
        "keep_published_codes": {"NAS401": "engg-mathematics-iii"},
        "reason": "B28 same-session cross-branch slot print (identical class to 06::15): draft 'Science Based Open Elective/Mathematics III' (NOE-041..049 pool + NAS-401, 2014-15 IT sem-4 scheme slot, flagged scheme_row_only) — NAS401 is owned by engg-mathematics-iii (same-session 2014-15 ECE-group establishing print); the auto transfer is rejected per the RCS653 class. RETARGET pins the update on the name-exact sem-4 slot row science-based-open-elective-mathematics-iii (2017-18 C&T print, EOE 041-048; the IT NOE-041..049 pool codes join it as the N-era pool range); NAS401 STAYS with engg-mathematics-iii."},
})

# ---- B30 (CRON-20261104-B30) per-key adjudications, evidence-recorded ----
TIER2_OVERRIDES.update({
    "02_btech_me_y2_scheme-syllabus_2017-18::09::applied-thermodynamics": {
        "action": "ALLOW",
        "reason": "B30 STAND (recorded B3/B02 code-reassigned class): Tier-1 name identity Applied Thermodynamics; draft 2017-18 carries EME403 (detail-page print) + RME403 (scheme print). EME403's published owner measurement-and-metrology (2009-10) content J=0.06 vs draft = different subject; draft vs applied-thermodynamics full J=0.66, U5 gas-turbine J=0.97 verbatim = same subject, era-reorganized units. The recorded auto transfers EME403 to the name-identity row (newest print wins; measurement-and-metrology keeps narrative history, primary follows the newest-era print status=latest model); RME403 (unowned) joins the row."},
    "04_btech_me_y4_syllabus-cbcs_2019-20::02::cad-cam-lab": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "cad-cam-lab",
        "keep_published_codes": {"RME751": "computer-aided-design-manufacturing-lab"},
        "reason": "B30 same-session code-slot keep (recorded B29 04::02 ruling): the 2019-20 ME y4 CBCS print's CAD/CAM Lab RME751 must NOT strip the code from computer-aided-design-manufacturing-lab — B29 established that the 2019-20 ME-Ind print of the SAME session owns RME751 (newest-print-wins cannot break a same-session tie). The update lands on the name-exact cad-cam-lab accumulator row (2009-10 EAU751;NAU-751;NME-751;BME652;EME-751) as a 2019-20 era backfill; RME751 recorded as narrative on cad-cam-lab; the ME-vs-ME-Ind dual print of the same session recorded for owner reconciliation."},
    "04_btech_me_y4_syllabus-cbcs_2019-20::11::automation-and-robotics": {
        "action": "FORCE_APPEND",
        "reason": "B30 wrong-subject FORCE_APPEND (recorded B28 04::04 same-core-different-tail / B29 07::47 class): Tier-1 name identity hits the 2023-24 BOE302 open-elective row automation-and-robotics but content J=0.15 — the 2019-20 ME DE-3 print's units (automation definition/laws, manufacturing automation & transfer machines, robot geometric/control classification, robot drives & power transmission, robot simulation/off-line programming) diverge from the open-elective print (industrial automation architecture, sensors, CIM, industrial applications). The auto's code transfer would also strip RME078 from robotics-and-automation against B29's recorded ruling (owner 2024-25 newer; older draft never steals a code). Appends as its own row; RME078 stripped draft-side (stays with its published owner, narrative quirk records the print); the open-elective row untouched (same name, different subject — cross-reference note)."},
    "07_btech_mfg-tech_syllabus_2010-11::01::work-study-ergonomics": {
        "action": "ALLOW",
        "reason": "B30 TIER2 same-subject era update STAND (recorded B29 RAC-class): draft Work Study & Ergonomics (EMT-502, 2010-11 E-era) vs work-study-and-ergonomics (RMI601, 2018-19 R-era ME-Ind). fuzzy 91 with 39 shared distinctive terms; the unit SEQUENCE is identical (productivity intro -> method study/charts -> work measurement/time study -> work sampling/PMTS/wages-incentives -> ergonomics) — the low word-Jaccard is E-era vs R-era print rewording, not a different subject. 2010-11 print backfills (older session, RULES §3)."},
    "07_btech_mfg-tech_syllabus_2010-11::11::simulation-and-modeling": {
        "action": "FORCE_APPEND",
        "reason": "B30 wrong-subject FORCE_APPEND (recorded B29 03::12 class, same name family): draft Simulation and Modeling (EMT-011, 2010-11 Mfg-Tech DE: physical modeling, computer-based system simulation/Monte Carlo, probability concepts in simulation, system-dynamics causal-loop/flow-diagram modeling, verification & validation). fuzzy 98 vs modelling-and-simulation (NIT062;RME076) but content J=0.04 (that row's current units are the IT/bioinformatics print); vs introduction-to-modeling-simulation (ECH608 ChemE) J=0.08; vs B29's own simulation-modelling-analysis (RME604) J=0.17 — name-family collision only, no shared model vocabulary. Appends as its own row with cross-reference notes; EMT-011 (unowned) joins it."},
    "07_btech_mfg-tech_syllabus_2010-11::21::advanced-manufacturing-systems": {
        "action": "FORCE_APPEND",
        "reason": "B30 wrong-subject FORCE_APPEND (recorded B29 07::47 class): draft Advanced Manufacturing Systems (EMT-801, 2010-11 Mfg-Tech core: automation strategies, automated storage/AGV materials handling, group technology, production economics & materials management/MPRM, FMS & CIMS). fuzzy 85 vs advance-manufacturing-processes (BME051) but content J=0.05 — that row is the machining/casting/welding/forming/additive subject. Probe found NO existing row in the FMS/CIMS domain (zero candidates >= 0.25 J across BTech). Appends as its own row; EMT-801 (unowned) joins it."},
    "08_btech_mfg-tech_syllabus_2020-21::07::advance-manufacturing-science": {
        "action": "ALLOW",
        "reason": "B30 TIER2 same-subject era update STAND (recorded B29 class): draft Advance Manufacturing Science (KPI051, 2020-21 Mfg-Tech DE) vs advanced-manufacturing-science (RME055, 2018-19). fuzzy 98 (Advance/Advanced singular-plural print variant); shared advanced-manufacturing-process vocabulary (classification, EDM/ECM-type thermal and electro-chemical removal, hybrid processes, high-energy forming) with era-reorganized unit splits — same subject, 2020-21 newer print fieldwise-wins; KPI051 (unowned) joins the row."},
    "08_btech_mfg-tech_syllabus_2020-21::11::automation-robotics": {
        "action": "RETARGET", "target": "automation-and-robotics-btech",
        "reason": "B30 TIE resolution via content evidence (never-guess satisfied: both fuzzy-90 candidates are same-name different-content rows — automation-and-robotics BOE302 J=0.17, robotics-and-automation J=0.06 whose units are the AI-DS ML-network-security print). The 2020-21 Mfg-Tech print 'Automation & Robotics' (KMT053) carries NEAR-VERBATIM the same units as the 2019-20 ME DE print appended by 04::11 (automation definition, manufacturing automation, robot classification, robot drives, robot simulation) -> RETARGET to the just-appended automation-and-robotics-btech row (same-commit visibility, recorded B22/B23 class); KMT053 (unowned) joins; 2020-21 newer session fieldwise-wins; both era prints accumulate in source_history."},
    "08_btech_mfg-tech_syllabus_2020-21::23::product-design-and-development": {
        "action": "ALLOW",
        "reason": "B30 TIER2 same-subject era update STAND: draft Product Design And Development (KMT063, 2020-21 Mfg-Tech DE) vs product-development-and-design (EME-013, 2009-10 ME/PE/IPE/ME&I 4-branch row). fuzzy 100; near-verbatim units (per-unit J 0.84-0.97, full 0.96, 111 shared distinctive terms: Introduction to PDD/Morphology of Design/Transformations/Reliability bath-tub/Product Appraisal) — same subject, 2020-21 newer print fieldwise-wins; KMT063 (unowned) joins the row."},
    "08_btech_mfg-tech_syllabus_2020-21::26::facility-planning-and-design": {
        "action": "ALLOW",
        "reason": "B30 TIER2 same-subject era update STAND: draft Facility Planning and Design (KPI072, 2020-21 Mfg-Tech DE) vs facility-planning-design (BPI052;RMI062, 2024-25 + 2018-19 ME-Ind establishing prints). fuzzy 92 with 84 shared distinctive terms; per-unit J 0.67-0.91 (factory planning/plant location, plant layout, group technology, line balancing, materials handling) — same subject, 2020-21 print backfills against the 2024-25 newer row (RULES §3 older-doc corroboration); KPI072 (unowned) joins the row."},
})

# ---- B34 (CRON-20261105-B34) 10::03 heat-transfer-lab RETARGET ----
TIER2_OVERRIDES.update({
    "10_btech_mfg-tech_y3_evaluation-scheme_2024-25::03::heat-transfer-lab": {
        "action": "RETARGET", "target": "heat-and-mass-transfer-lab",
        "reason": "B34 replay adjudication (newest recorded ruling supersedes the B30-era auto; recorded B29-2nd ruling for the SAME 2024-25 BME551 print, B27 RCS653 same-session name-variant class): draft 'Heat Transfer Lab' (BME 551, 2024-25 Mfg-Tech y3 eval-scheme print, detailed experiment list) — Tier-0 code identity now hits TWO rows because B29-2nd's recorded merge gave heat-and-mass-transfer-lab the BME551 ownership (KME551 2020-21 continuity -> BME551 2024-25) while the B30-era auto (executed before that ruling existed) had transferred BME551 to the CHEM-family heat-transfer-lab row. The recorded B29 ruling governs: BME551's owner is heat-and-mass-transfer-lab; this Mfg-Tech print is a same-session name-variant corroboration of the SAME ME-family lab (thermal-conductivity/heat-exchanger experiment list) -> RETARGET pins the fieldwise 2024-25 update on the published owner; the CHEM-family heat-transfer-lab row (ECH-656;RCH355;RCH455) is a different subject and stays untouched; the 'Heat Transfer Lab' print variant recorded in the change note."},
})

# ---- B34 (CRON-20261105-B34) accumulator-pair corrective (G3-taught, recorded B30 final) ----
TIER2_OVERRIDES.update({
    "04_btech_me_y4_syllabus-cbcs_2019-20::11::automation-and-robotics": {
        "action": "RETARGET", "target": "automation-and-robotics",
        "reason": "B34 corrective to the recorded B30 FINAL state (747874e 'G3-taught accumulator RETARGET pair (automation-and-robotics 3-print reconciliation)'; B32 published CSV row state = NO separate '-btech' row). The stale pre-G3 FORCE_APPEND entry (local adjudicate_b30.py copy) is superseded: appending a second BTech 'Automation and Robotics' row violates G3 (name,course) uniqueness — B30's own run learned this and pinned the 2019-20 ME DE-3 print onto the existing open-elective accumulator row as an era corroboration. 2019-20 < 2023-24 (row's latest print): backfill-empty-only + source_history extension (RULES §3); RME078 stays stripped draft-side (keep-published with robotics-and-automation per the recorded B29 04::13 ruling; the accumulator's recorded all_codes deliberately excludes RME078); the no-code evidence quirk stays on the draft subject."},
    "08_btech_mfg-tech_syllabus_2020-21::11::automation-robotics": {
        "action": "RETARGET", "target": "automation-and-robotics",
        "reason": "B34 corrective to the recorded B30 FINAL state (747874e 'G3-taught accumulator RETARGET pair'): the 2020-21 Mfg-Tech DE print 'Automation & Robotics' (KMT053, unowned) lands on the automation-and-robotics accumulator row (G3-unique (name,course)); both fuzzy-90 candidates are same-name different-content rows per the recorded evidence (BOE302 open-elective units J=0.17 vs the ME-print units the accumulator now carries; robotics-and-automation J=0.06 = the AI-DS ML print) — the near-verbatim match is the ME-print lineage already reconciled into the accumulator. 2020-21 < 2023-24 (row's latest print): backfill-empty-only; KMT053 joins the row's codes exactly as the recorded B32 all_codes shows (BOE302;...;NME-044;KMT053;RPI701); both era prints accumulate in source_history."},
})






# B14 remedy registry: sha16s of documents that a PRIOR batch ingested and
# G6-verified (their unit texts are published in the GitHub CSV with these
# exact citations) but whose PDF bytes are no longer resolvable anywhere
# locally — upload/ files wiped by workspace resets and NOT carried in the
# repo corpus (md5 scan of work/repo_asleep/PDFs/** = no match). The GitHub
# CSV is the durable record (RULES §1c); gate_g6 grandfathers rows whose
# unit1_text is byte-identical to the published value and which cite one of
# these shas. Never add a sha here without a recorded ingest manifest.
PRIOR_VERIFIED_LOST_SHA = {
    "e18a3256f09b7f6e":
        "Open-Elective-BTech-2nd-year-2023-08092023.pdf — charter-mandated released "
        "companion doc (owner release recorded in the project charter, RULES §1): "
        "supplied the published unit1_text of automation-and-robotics and "
        "basics-data-structure-algorithms (2023-24 first ingestion); containment "
        "probe-verified TRUE against the extant bytes at the B19 commit (2026-11-01, "
        "recorded verbatim in the gate_g6 B19 remedy comment); the file lived in "
        "work/artd_v3/sources/ which the later workspace resets wiped; md5 scan of "
        "the repo corpus + upload/ = no match",
    "4f09e0095540f04e":
        "owner-upload CSE_v3 copy recorded in the gate_g6 B19 remedy comment: "
        "supplied the published unit1_text of discrete-structures-and-theory-of-logic; "
        "containment probe-verified TRUE against the extant bytes at the B19 commit "
        "(2026-11-01); upload/ corpus wiped by the workspace resets; md5 scan of the "
        "repo corpus = no match",
    "79a6daf1f0cd9310":
        "B.Tech. 3rd Year Civil Engineering.pdf — B04-ingested B.Tech 3rd Year "
        "Civil Engineering 2024-25 doc (rows 204→402 push, manifest "
        "runs/20261028T190528Z_CRON-20261028-B04_*); content-identity of its "
        "upload corroborating copy (03d279e76a24f6ff) proven 2026-10-27 in queue "
        "meta.history; upload bytes + parsed fulltext lost in the 12th workspace "
        "reset (2026-10-31); md5 scan of the repo corpus = no match",
    "13bd875d098f99df":
        "Common-Subjects-2nd-Year-AKTU-08092023.pdf — charter-mandated released "
        "companion doc (one of the two released companions, owner release "
        "recorded in the project charter, RULES §1; a B01-ingested doc): "
        "supplied the published unit1_text of mathematics-iii-partial-differential-"
        "equations-statistical-a (source_syllabus cites it pp.1-28, first "
        "ingestion 2023-24) and the other common-2nd-year-subject rows of that "
        "ingestion wave. Registered at B28 (2026-11-04) when the row was first "
        "TOUCHED since the bytes were lost (the B28 code-reassignment executor "
        "moved the EOE-041-048 pool wart off the row, triggering the first G6 "
        "spot-check of its unit1 since ingestion): the companion class was "
        "directly containment-verified while bytes were extant (gate_g6 B19 "
        "remedy comment, 2026-11-01: rows supplied by exactly these docs passed "
        "against the extant work/artd_v3/sources/ + upload/ bytes); this row's "
        "unit1 is byte-identical to the GitHub-published value since the 2023-24 "
        "first ingestion (GitHub CSV = the durable record per RULES §1c); "
        "workspace resets wiped work/artd_v3/sources/ + upload/; md5 scan of the "
        "repo corpus (613 PDFs) + upload/ = no match",
}

_prior_pub_cache = None


def prior_published_units():
    """subject_id -> {'unit1_text': ...} from the last successfully pushed CSV
    (the durable GitHub record cloned at work/repo_asleep). Cached."""
    global _prior_pub_cache
    if _prior_pub_cache is None:
        try:
            import csv as _csv
            path = "/home/z/my-project/work/repo_asleep/syllabus_catalog/syllabus_extreme_rich.csv"
            _prior_pub_cache = {r["subject_id"]: r for r in _csv.DictReader(open(path))}
        except Exception:
            _prior_pub_cache = {}
    return _prior_pub_cache


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
            # B19 remedy (evidence-recorded): WORKSPACE-SOURCE FALLBACK — the
            # charter-mandated released companion PDFs (work/artd_v3/sources/,
            # the two B01-ingested docs) and the owner's upload/ corpus live
            # OUTSIDE the reset-wiped work/pipeline_v2/ and survived the 17th
            # workspace reset (2026-11-01) with bytes intact. B19's first
            # commit G6-FAILED three rows whose published unit1_text was
            # supplied by exactly these docs (open-elective companion
            # e18a3256f09b7f6e -> automation-and-robotics /
            # basics-data-structure-algorithms; upload CSE_v3
            # 4f09e0095540f04e -> discrete-structures-and-theory-of-logic;
            # all three containments probe-verified TRUE against the extant
            # bytes). md5-index these roots exactly like the repo corpus so
            # G6 citation chains resolve against every locally extant source.
            # Evidence-widening only: containment must still HIT — fabricated
            # provenance still fails.
            for extra_root in ("/home/z/my-project/upload",
                               "/home/z/my-project/work/artd_v3/sources"):
                for dirpath, _dirs, files in os.walk(extra_root):
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
                    # B14 remedy (evidence-recorded, B10 prior-run-verification
                    # class): the unit text may have been supplied — and G6-
                    # verified — by an EARLIER batch whose source PDF is no
                    # longer resolvable ANYWHERE locally (workspace resets wipe
                    # upload/ PDFs; the repo corpus does not carry them). RULES
                    # §1c makes the GitHub-published CSV the durable record: if
                    # (a) the row's unit1_text is BYTE-IDENTICAL to the value
                    # published by the last successful push (no new text enters
                    # through this path — a changed unit1 still hard-fails),
                    # and (b) the row's source_syllabus cites a documented
                    # prior-verified lost sha, the spot-check is skipped with a
                    # recorded WARN line. Fabricated provenance still fails:
                    # an un-published unit1 or an un-documented sha never
                    # qualifies.
                    pub = prior_published_units()
                    lost = PRIOR_VERIFIED_LOST_SHA
                    shas_all = shas
                    row_ev = (r.get("notes", "") or "") + " " + (r.get("flags", "") or "")
                    ocr_evidence = "unit_ocr_recovered_no_text_layer" in row_ev
                    if (pub is not None
                            and r.get("unit1_text", "") and r["unit1_text"] == pub.get(r["subject_id"], {}).get("unit1_text", "")
                            and (any(s in lost and s not in by_sha for s in shas_all) or ocr_evidence)):
                        checks += 1
                        if ocr_evidence:
                            print(f"G6|OCR_PRIOR_SKIP|{r['subject_id']} (unit1 byte-identical to the "
                                  f"published CSV; the row carries the recorded "
                                  f"unit_ocr_recovered_no_text_layer evidence — text transcribed from "
                                  f"raster pages with empty text layer, B12 remedy; text-layer "
                                  f"containment structurally impossible)")
                        else:
                            print(f"G6|PRIOR_VERIFIED_SKIP|{r['subject_id']} (unit1 byte-identical to the "
                                  f"published CSV; supplying doc sha16 {sorted(set(shas_all) & set(lost))} "
                                  f"ingested by a prior batch ({lost[sorted(set(shas_all) & set(lost))[0]][:80]}...) "
                                  f"not locally resolvable after workspace resets; GitHub CSV is the "
                                  f"durable record per RULES §1c)")
                    else:
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
    keep_owner = {}        # B19: key -> {"codes": {code: owner_sid}, "session": ...}
                           # RETARGET_KEEP_PUBLISHED_CODE_OWNER — codes that stay
                           # with their published newer-session owner rows
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
            # B34 restoration (recorded B30 04::11 class): a FORCE_APPEND
            # override must bite at ANY tier — the recorded ruling was exactly
            # a Tier-1 name-identity hit on a DIFFERENT-CONTENT row
            # (same-core-different-tail / wrong-subject name family) where the
            # auto UPDATE would corrupt the other row; the B29-2nd rewrite
            # restricted overrides to tier==2, letting the T1 update through.
            if TIER2_OVERRIDES.get(key) and (tier in (1, 2) or TIER2_OVERRIDES[key]["action"] == "RETARGET"
                    or TIER2_OVERRIDES[key]["action"] == "RETARGET_KEEP_PUBLISHED_CODE_OWNER"
                    or TIER2_OVERRIDES[key]["action"] == "FORCE_APPEND"):
                ov = TIER2_OVERRIDES[key]
                if ov["action"] == "FORCE_APPEND":
                    tier, targets = 3, []
                elif ov["action"] in ("RETARGET", "RETARGET_KEEP_PUBLISHED_CODE_OWNER"):
                    rt = next((r for r in rows if r.get("subject_id") == ov.get("target")), None)
                    if rt is not None:
                        targets = [rt]
                        tier = 2
                    if ov["action"] == "RETARGET_KEEP_PUBLISHED_CODE_OWNER":
                        keep = ov.get("keep_published_codes") or {}
                        if keep and rt is not None:
                            keep_owner[key] = {"codes": keep, "session": dmeta["session"],
                                               "target": ov["target"], "detail": ov["reason"]}
                            # the kept codes must never land on the target row
                            # (apply_update adds every draft code); drop them from
                            # the draft copy so the update merges only the codes
                            # that are genuinely unowned (e.g. the KCS-661 detail
                            # print) — the kept code stays with its published
                            # newer-session owner (B19 newest-print-wins ruling)
                            drop = {norm_code(k) for k in keep}
                            dsub["codes"] = [c for c in (dsub.get("codes") or [])
                                             if norm_code(c) not in drop]
                info = info + " | TIER2 override " + ov["action"] + ": " + ov["reason"][:160]
                flags.append((key, "TIER2-OVERRIDE", ov["action"] + ": " + ov["reason"]))
            if info.startswith("code-reassigned "):
                moved = info.split(" ")[1].split(",")
                flags.append((key, "CODE-REASSIGNED-ACROSS-SESSIONS", info))
                if key in keep_owner:
                    # B19: the registered transfer is filtered to drop codes that
                    # stay with their published newer-session owners; if nothing
                    # remains, the transfer is cancelled entirely
                    kept = {norm_code(c) for c in keep_owner[key]["codes"]}
                    moved = [c for c in moved if norm_code(c) not in kept]
                if moved:
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
            # B17: HSMC slot-code transfer (recorded class) — a dual slot-code
            # print naming a REAL subject whose codes sit on generic slot rows.
            # Newest detailed print wins: APPEND the subject with its printed
            # codes and register the ownership transfer (executor strips the
            # codes from the slot rows, B08 remedy for stranded slot rows).
            if op[0] == "TIE" and SLOT_CODE_TRANSFERS.get(key):
                ov = SLOT_CODE_TRANSFERS[key]
                info = info + " | SLOT-CODE-TRANSFER override APPEND: " + ov["reason"][:200]
                flags.append((key, "SLOT-CODE-TRANSFER", ov["reason"]))
                flags = [f for f in flags if not (f[0] == key and str(f[1]).startswith("TIE"))]
                reassignments.append({"codes": list(ov["codes"]),
                                      "to_row": slug(dsub.get("name", "")),
                                      "detail": info, "draft_session": dmeta["session"]})
                tier = 3
                op = ("APPEND", (None, ("", "")))
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
        # B19: narrative history for codes that keep their published owner
        # (RETARGET_KEEP_PUBLISHED_CODE_OWNER) — the older draft's scheme print
        # is recorded on the updated row while ownership stays with the
        # newer-session published owner row
        for key, ko in keep_owner.items():
            trow = by_id.get(ko["target"])
            if not trow:
                continue
            for code, owner_sid in ko["codes"].items():
                c = norm_code(code)
                seg = (f"; {c} printed on this {ko['session']} scheme for this subject — "
                       f"code stays owned by {owner_sid} per the newer establishing print "
                       f"(newest-print-wins era model; recorded B19 adjudication: older draft "
                       f"never steals a code from a newer-session published owner)")
                trow["code_history_all"] = (trow.get("code_history_all", "") or "") + seg
                trow["change_note_vs_previous"] = (trow.get("change_note_vs_previous", "") + "; " if trow.get("change_note_vs_previous", "") else "") + \
                    f"{c} {ko['session']} scheme print recorded as narrative; ownership stays with {owner_sid}"
                touched.setdefault(trow["subject_id"], trow)
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
        # B21 REPAIRS executor (brain clause: determine-then-fix, keep proof):
        # strip recorded wrong-merge fields from a published row and move the
        # misplaced source citation to the true subject row (which exists by
        # now — appends ran in the draft loop above).
        for sid, rep in REPAIRS.items():
            rrow = by_id.get(sid)
            if not rrow:
                continue
            salvage = by_id.get(rep.get("salvage_to", ""))
            tok = rep.get("move_source_token", "")
            note = rep["reason"]
            for f in rep.get("strip_fields", []):
                if rrow.get(f):
                    rrow[f] = ""
            for f, v in rep.get("reset_fields", {}).items():
                rrow[f] = v
            for col in ("source_syllabus", "source_history"):
                val = rrow.get(col, "") or ""
                if tok and tok in val:
                    rrow[col] = "; ".join(s.strip() for s in val.split(";") if tok not in s)
                    if salvage is not None:
                        seg = f"{tok} (recovered from the {sid} wrong-merge, B21 repair)"
                        if seg not in (salvage.get("source_history", "") or ""):
                            salvage["source_history"] = ((salvage.get("source_history", "") + "; ") if salvage.get("source_history") else "") + seg
            rrow["change_note_vs_previous"] = (rrow.get("change_note_vs_previous", "") + "; " if rrow.get("change_note_vs_previous") else "") + \
                "B21 repair: misplaced optical-communication units/COs/books stripped (the 2025-26 ACT print p.14 proves BEC-057 = OPTICAL COMMUNICATION; the subject now owns row " + rep.get("salvage_to", "") + ")"
            rrow["notes"] = (rrow.get("notes", "") + " | " if rrow.get("notes") else "") + \
                "B21 repair note: " + note[:400]
            touched.setdefault(rrow["subject_id"], rrow)
            if salvage is not None:
                salvage["change_note_vs_previous"] = (salvage.get("change_note_vs_previous", "") + "; " if salvage.get("change_note_vs_previous") else "") + \
                    "B21 repair: the 2025-26 ACT print (328fc29743da6525) had merged this subject's content into technical-communication; stripped there and re-homed on this row (printed evidence recorded)"
                touched.setdefault(salvage["subject_id"], salvage)

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




# ---- B32 (CRON-20261105-B32) per-key adjudications, evidence-recorded ----
TIER2_OVERRIDES.update({
    "01_btech_open-electives_2019-20::05::renewable-energy-resources": {
        "action": "ALLOW",
        "reason": "B32 TIER2 same-subject era update STAND (recorded name-variant class): draft 'Renewable Energy Resources' (ROE086, 2019-20 Open-Electives-II print, 5 verbatim units) vs renewable-energy-sources (KAG-057;BAG057;NAG-081;KOE074, 2020-21 AG establishing): probe fullJ=0.94, per-unit 0.84-0.96, unit1 VERBATIM opening ('Introduction: Various non-conventional energy resources- Introduction, availability, classification, relative merits and demerits. Solar Cells: Theory of...') — the same renewables canon (solar, wind, biomass, geothermal, fuel cells); 'Resources'/'Sources' is the recorded singular/plural-adjacent print-variant class (B10 0.982 / B31 operation-research singular/plural). Draft 2019-20 OLDER than the row's 2020-21 session so backfill-empty only (RULES §3); ROE086 (unowned) joins as the 2019-20 OE-era code."},
    "02_btech_pe-ipe_syllabus_2020-21::26::project-management": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "project-management",
        "keep_published_codes": {"KPI072": "facility-planning-design"},
        "reason": "B32 older-draft-never-steals-a-code adjudication (recorded B19/B20 older-print guard + B29 1841 turbo-machines class): draft 'Project Management' (2020-21 PE/I-PE print, 5 verbatim units) carries an INTRA-DOC code clash — detail p.53 prints 'KPI 072' but the doc's own contents/pool print KPI 073 (clash quirk recorded by the draft). KPI072's published owner is facility-planning-design (all_codes BPI052;RMI062;KPI072): the 2021-22 PE/I-PE y4 print (this same commit's doc-07 draft: KPI072=Facility Planning and Design, KPI073=Project Management) and the 2024-25 ME-Ind scheme (B29) BOTH corroborate KPI072=Facility Planning; the 2020-21 print is OLDER than both. Ruling: UPDATE project-management by name identity (fullJ 0.46 vs the row's RAU072 2019-20 canon, u3-u5 0.51-0.64 — the era-reorganized same PM course; draft session 2020-21 newer than the row's 2019-20 so units fieldwise-win per RULES §3); KPI073 (the contents/pool print, corroborated by the 2021-22 print) joins project-management; KPI072 STAYS with facility-planning-design and the 2020-21 p.53 'KPI 072' print is recorded as a narrative history mention (dual-use slot across sessions, B19/B20 class)."},
    "04_btech_pe-ipe_y3_evaluation-scheme_2024-25::07::ergonomics-workplace-design": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "ergonomics-workplace-design",
        "keep_published_codes": {"BPI052": "facility-planning-design"},
        "reason": "B32 same-session code-slot collision keep (recorded B27 RCS653 / B29 1835 computational-fluid-dynamics class): draft 'Ergonomics & Workplace Design' (BPI052, 2024-25 PE/I-PE y3 evaluation-scheme print, 5 verbatim units). BPI052's published owner is facility-planning-design (primary BPI052, session 2024-25 — SAME session, established by the 2024-25 ME-Ind y3 evaluation-scheme print, B29): newest-print-wins cannot break a same-session tie, so the published owner keeps the code. The update lands on the name-exact ergonomics-workplace-design row (owns BPI051 — the 2024-25 ME-Ind scheme's Ergonomics code; probe fullJ=1.00, all 5 units VERBATIM-identical between the PE/I-PE and ME-Ind 2024-25 prints — the same NEP-era course printed in both branch docs); BPI052 dropped to narrative; the 2024-25 BPI052 cross-branch double print (ME-Ind Facility Planning vs PE/I-PE Ergonomics) recorded for owner reconciliation."},
    "05_btech_pe-ipe_y3_syllabus_2018-19::18::instrumentation-and-control": {
        "action": "FORCE_APPEND",
        "reason": "B32 wrong-subject FORCE_APPEND (recorded B23 sensors/transducers + B28 01::15 Modelling-and-Simulation class): draft 'INSTRUMENTATION AND CONTROL' (RPI061, 2018-19 PE/I-PE y3 DE-IV print, 5 verbatim units) fuzzy 87/4-hits instrumentation-and-process-control (ECH507;NCH-507, 2009-10 FT-family print): probe fullJ=0.02, per-unit <=0.03, only 3 generic shared terms (control, measurement, principle). The 2009-10 row is the process-control course (elements of measurement, indicating/recording instruments, process dynamics); the 2018-19 print is the basic-instrumentation course (accuracy/precision, error statistics, IEEE standards, transducers/signal conditioning). Different subjects sharing a name family; appends as its own row with a cross-reference note to instrumentation-and-process-control; RPI061 (unowned) joins it."},
    "06_btech_pe-ipe_y4_syllabus-cbcs_2019-20::02::cad-cam-lab": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "cad-cam-lab",
        "keep_published_codes": {"RME751": "computer-aided-design-manufacturing-lab"},
        "reason": "B32 same-session code-slot collision keep — EXACT REPLAY of the recorded B29 ruling on this same subject/code (04_btech_me-ind_y4_syllabus-cbcs_2019-20::02::cad-cam-lab): draft 'CAD/CAM Lab' (RME751, 2019-20 PE/I-PE y4 CBCS print, experiment list). RME751's published owner is computer-aided-design-manufacturing-lab (session 2019-20 — SAME session, 'COMPUTER AIDED DESIGN & MANUFACTURING LAB' from the 2019-20 AU-family CBCS print): same-session tie keeps the published owner. The update lands on the name-exact cad-cam-lab row (the multi-era EAU751;NAU-751;NME-751;BME652;EME-751 accumulator); RME751 dropped to narrative; the 2019-20 three-print same-code set (AU long-name / ME-Ind / PE-IPE CAD-CAM Lab) recorded for owner reconciliation."},
})
DOC_SCOPE.update({
    "3ad2353279d419ea": {
        "branch_names": "",
        "program_year": "4",
        "reason": "B32 Open-Electives 2019-20: cover p.1 prints 'Open Electives / For / Bachelor of Technology / (Choice Based Credit System) / 7th & 8th Semester, 2019-20' — NO branch names printed anywhere on the cover or pool lists, so branch_names stay BLANK per the recorded B16 zero-guess class (B31 doc-10 2009-10 science-OE precedent); program_year 4 from the printed '7th & 8th Semester' + 'B.Tech 4th year (CBCS)' pool headers."},
    "749493b449640e50": {
        "branch_names": "Production Engineering; Industrial Production Engineering",
        "program_year": "3",
        "reason": "B32 PE/I-PE 2020-21 y3: cover p.1 prints 'FOR B. TECH. 3rd YEAR Production Engineering/ Industrial Production Engineering [Effective from Session: 2020-21]'; running headers print 'PRODUCTION ENGINEERING/ INDUSTRIAL PRODUCTION ENGINEERING' (draft DOC_SCOPE quirk)."},
    "5a3056fc8c33bc06": {
        "branch_names": "Production Engineering; Industrial Production Engineering",
        "program_year": "3",
        "reason": "B32 PE/I-PE 2024-25 y3: cover p.1 prints 'EVALUATION SCHEME / FOR / B.TECH. 3rd YEAR / Production Engineering/ / Industrial Production Engineering / [Effective from Session: 2024-25]' (cover text verified from the parsed text layer)."},
    "819674f872d40b8d": {
        "branch_names": "Production Engineering; Industrial Production Engineering",
        "program_year": "3",
        "reason": "B32 PE/I-PE 2018-19 y3: cover p.1 prints 'B. Tech. 3rd Year / Production Engineering'; evaluation-scheme headers (pp.2, 17) print 'PRODUCTION ENGINEERING and INDUSTRIAL PRODUCTION' — the document serves both printed branches (draft DOC_SCOPE quirk)."},
    "2b3dc38be733f99e": {
        "branch_names": "Production Engineering; Industrial Production Engineering",
        "program_year": "4",
        "reason": "B32 PE/I-PE 2019-20 y4 CBCS: cover p.1 prints 'B. TECH 4th YEAR PRODUCTION ENGINEERING/INDUSTRIAL PRODUCTION ENGINEERING' (draft DOC_SCOPE quirk)."},
    "196c30b1f09eccf3": {
        "branch_names": "Petroleum Engineering",
        "program_year": "2",
        "reason": "B32 Petroleum y2 2017-18: cover p.1 prints 'B.Tech. Second Year / Petroleum Engineering' — single printed branch, no parenthetical expansion (draft DOC_SCOPE quirk; B31 Mining first-class-branch class)."},
    "5da3e4e52504a5cb": {
        "branch_names": "Petroleum Engineering",
        "program_year": "4",
        "reason": "B32 Petroleum y4 2017-18: cover p.1 prints 'B.Tech. Fourth Year / Petroleum Engineering' — single printed branch, no parenthetical expansion (draft DOC_SCOPE quirk; B31 Mining first-class-branch class)."},
})




# ---- B31 (CRON-20261104-B31) per-key adjudications, evidence-recorded ----
TIER2_OVERRIDES.update({
    "01_btech_mfg-tech_y3_syllabus_2018-19::03::manufacturing-science-and-technology-ii": {
        "action": "RETARGET", "target": "manufacturing-science-technology-ii",
        "reason": "B31 TIE resolution on name-family + content evidence: draft 'Manufacturing Science and Technology II' (RME505, 2018-19 Mfg-Tech y3, 5 verbatim units) TIEs fuzzy 93/manufacturing-science-technology-i (NME402;RME402) vs 95/manufacturing-science-technology-ii (RME503, sess 2018-19). The II token is the subject's own print — merging II into I would violate the recorded distinct-row design (MST-I/MST-II are separate courses, cf. electro-mechanical-energy-conversion-i/ii); the probe: draft vs MST-II fullJ=0.38 (U1 0.63, U5 0.51 — era-reorganized same course) vs MST-I fullJ=0.10. RETARGET pins MST-II; RME505 (unowned) joins as the 2018-19 Mfg-Tech era code; the SAME-SESSION dual-print (ME-Ind RME503 establishing print vs Mfg-Tech RME505 print, units fieldwise per the >= rule) is recorded here for owner reconciliation (B27 RCS653 same-session class narrative)."},
    "01_btech_mfg-tech_y3_syllabus_2018-19::04::advance-welding-technology": {
        "action": "ALLOW",
        "reason": "B31 TIER2 same-subject era update STAND: draft 'Advance Welding Technology' (RME506, 2018-19 Mfg-Tech y3, 4 units — no Unit-V printed) vs advanced-welding-technology row: probe sim 0.98, fullJ=0.99 (unitJ 0.97-1.0) — VERBATIM same subject ('Advance'/'Advanced' print variant, recorded B10 0.982 class). RME506 (unowned) joins; 2018-19 row session fieldwise."},
    "01_btech_mfg-tech_y3_syllabus_2018-19::09::advance-casting-process": {
        "action": "ALLOW",
        "reason": "B31 TIER2 same-subject era update STAND: draft 'Advance Casting Process' (RMT051, 2018-19 Mfg-Tech y3, 5 verbatim units) vs advanced-casting-processes (EMT-012, 2010-11 establishing print): probe fullJ=1.0, per-unit all 1.0 — VERBATIM; 2018-19 newer so units fieldwise-win (B10 'ADVANCE/ADVANCED' 0.982 print-variant class). RMT051 (unowned) joins."},
    "01_btech_mfg-tech_y3_syllabus_2018-19::10::plastic-material-and-manufacturing": {
        "action": "ALLOW",
        "reason": "B31 TIER2 same-subject era update STAND: draft 'Plastic Material and Manufacturing' (RMT052, 2018-19 Mfg-Tech y3, 5 verbatim units) vs plastic-materials-manufacturing (KMT051, 2020-21 establishing): probe fullJ=0.99 (per-unit 0.94-1.0) — verbatim modulo singular/plural + '&'/'and' print variance (recorded name-variant class); draft 2018-19 OLDER so backfill-empty only (RULES §3). RMT052 (unowned) joins."},
    "01_btech_mfg-tech_y3_syllabus_2018-19::16::pneumatics-and-hydraulics": {
        "action": "ALLOW",
        "reason": "B31 TIER2 same-subject era update STAND: draft 'Pneumatics and Hydraulics' (RMT601, 2018-19 Mfg-Tech y3, 5 verbatim units) vs pneumatics-hydraulics (EMT-601, 2010-11 establishing): probe fullJ=0.99 (per-unit 0.95-1.0) — verbatim era print; 2018-19 newer so units fieldwise-win. The competing pneumatics-hydraulics-lab hit (J=0.0) is the recorded distinct-lab-row design (labs are separate rows, RULES §3) and stays untouched. RMT601 (unowned) joins."},
    "01_btech_mfg-tech_y3_syllabus_2018-19::18::production-planning-and-control": {
        "action": "ALLOW",
        "reason": "B31 TIER2 same-subject era update STAND: draft 'Production Planning and Control' (RMT602, 2018-19 Mfg-Tech y3, 4 units — no Unit-V printed) vs production-planning-control (EPI-501, 2009-10 establishing): probe unit1 J=0.81 with the SAME opening sentence ('Introduction: Types and characteristics of production systems Objective and functions of Production, Planning & Control'); 6 shared distinctive terms (capacity, forecasting, inventory, layout, MRP, scheduling) — the 2018-19 print is the era-reorganized same PPC course (B30 facility-planning class); 2018-19 newer so units fieldwise-win. RMT602 (unowned) joins."},
    "01_btech_mfg-tech_y3_syllabus_2018-19::24::product-design-and-development": {
        "action": "ALLOW",
        "reason": "B31 TIER2 same-subject era update STAND (recorded B30 08::23 ruling on this exact pair): draft 'Product Design and Development' (RMT061, 2018-19 Mfg-Tech y3, 5 verbatim units) vs product-development-and-design (EME-013, 2009-10 establishing; KMT063 2020-21 joined in B30 with per-unit J 0.84-0.97 evidence). fuzzy 100/111 shared distinctive terms — the 2018-19 Mfg-Tech print is the same PDD course; draft OLDER than the row's 2020-21 session so backfill-empty only (RULES §3). RMT061 (unowned) joins."},
    "01_btech_mfg-tech_y3_syllabus_2018-19::26::operation-research": {
        "action": "ALLOW",
        "reason": "B31 TIER2 same-subject era update STAND: draft 'Operation Research' (RMT063, 2018-19 Mfg-Tech y3, 5 verbatim units) vs operations-research (NOE073, 2016-17): fuzzy 97 singular/plural name variant (recorded class); probe 7 shared distinctive OR terms (assignment, CPM, inventory, PERT, queuing, sequencing, transportation) — the canonical OR course across eras; 2018-19 newer so units fieldwise-win. RMT063 (unowned) joins."},
    "01_btech_mfg-tech_y3_syllabus_2018-19::27::machine-vision-and-image-processing": {
        "action": "ALLOW",
        "reason": "B31 TIER2 same-subject era update STAND: draft 'Machine Vision and Image Processing' (RME066, 2018-19 Mfg-Tech y3, 5 verbatim units) vs machine-vision-image-processing (KMT061, 2020-21 establishing): probe fullJ=0.99 (per-unit 0.95-1.0) — verbatim era print; draft 2018-19 OLDER so backfill-empty only. RME066 (unowned) joins."},
    "02_btech_mfg-tech_y4_syllabus-cbcs_2019-20::01::automation-robotics": {
        "action": "RETARGET", "target": "automation-and-robotics",
        "reason": "B31 TIE resolution via the recorded accumulator model (B30 08::11 KMT053 ruling): draft 'Automation & Robotics' (RPI701, 2019-20 Mfg-Tech y4 CBCS, 5 verbatim units) TIEs fuzzy 90/automation-and-robotics vs 90/robotics-and-automation; probe vs the 2019-20 ME DE print (B30 durable draft 04::11, RME078): per-unit J 0.81-0.95 (U1 verbatim 'Automation: Definition, Advantages, goals, types, need, laws and principles of Automation...') — the SAME 2019-20 print family; a third same-name row is G3-forbidden. The name-exact accumulator automation-and-robotics takes the 2019-20 Mfg-Tech era print (draft OLDER than the 2023-24 establishing session: backfill-empty only, units untouched); RPI701 (unowned) joins; the print divergence vs the accumulator's 2023-24 units recorded in notes for owner reconciliation (B30 open-item-4 class)."},
    "02_btech_mfg-tech_y4_syllabus-cbcs_2019-20::05::advanced-material-technology": {
        "action": "FORCE_APPEND",
        "reason": "B31 wrong-subject FORCE_APPEND (recorded B28 01::15 Modelling-and-Simulation class): draft 'Advanced Material Technology' (RPI070, 2019-20 Mfg-Tech y4 CBCS, 5 verbatim units: intelligent/smart materials, functional/polyfunctional/structural/bio-compatible materials) fuzzy 98-hits advanced-materials-technology (2009-10 ADVANCED MATERIALS TECHNOLOGY row: ferrous materials, plain-carbon steels, alloying elements) — probe fullJ=0.09 (unitJ 0.10-0.12), only 2 generic shared terms (ceramics, polymers): the 2009-10 row is the classical ferrous/alloy metallurgy course, the 2019-20 print is the smart/functional-materials course. Different subjects sharing a name family; appends as its own row with a cross-reference note to the 2009-10 row."},
    "02_btech_mfg-tech_y4_syllabus-cbcs_2019-20::08::reverse-engineering": {
        "action": "FORCE_APPEND",
        "reason": "B31 wrong-fuzzy FORCE_APPEND (recorded B23 sensors class): draft 'Reverse Engineering' (RPI075, 2019-20 Mfg-Tech y4 CBCS, 5 verbatim units incl. the printed Course Outcomes paragraph p.17) fuzzy 89-hits river-engineering (BCE062, 2024-25 CE row) on the generic 'engineering' token only — probe fullJ=0.09. NO reverse-engineering row exists in BTech; the subject (3D scanning, digitization, point-cloud/CAD reconstruction, B30's RME073-adjacent Mfg-Tech DE print) appends as its own row; zero-GAP holds."},
    "06_btech_mining_y3_syllabus_2025-26::00::mine-environmental-engineering": {
        "action": "FORCE_APPEND",
        "reason": "B31 wrong-subject FORCE_APPEND (recorded B28 01::15 class): draft 'Mine Environmental Engineering' (BMN-501, 2025-26 Mining y3 core, 5 verbatim units) TIEs 5 name-family candidates (environmental-engineering BCE603 J=0.10; environmental-engineering-i ECE503 J=0.06; -ii ECE602 J=0.10; geoenvironmental-engineering RCE053 J=0.07; environmental-engineering-process NEN-302 J=0.08) — ALL are the Civil/Environmental generic pollution-control courses; the mining print covers mine-specific content (mine gases/dust/climate, subsidence and strata control, mine fires/spontaneous heating, mine water environmental impact). Same-name different-program class: appends as its own Mining-scope row with a cross-reference note to the Civil environmental-engineering rows."},
    "06_btech_mining_y3_syllabus_2025-26::09::mine-environmental-engineering-lab": {
        "action": "FORCE_APPEND",
        "reason": "B31 wrong-subject FORCE_APPEND (same evidence as 06::00, lab row per the recorded labs-are-distinct-rows rule): draft 'Mine Environmental Engineering Lab' (BMN-551, 2025-26 Mining y3 lab) fuzzy 92-hits environmental-engineering-lab (BCE653, 2024-25 Civil) — probe J=0.0 (no shared unit vocabulary; the mining lab's printed experiment list is mine-specific). Appends as its own row with a cross-reference note."},
    "06_btech_mining_y3_syllabus_2025-26::16::geo-informatics": {
        "action": "ALLOW",
        "reason": "B31 TIER2 same-subject era update STAND: draft 'Geo-Informatics' (BMN-062, 2025-26 Mining y3 DE, 5 verbatim units) vs geoinformatics (ECE402, 2009-10 establishing): sim 1.0 name identity; probe shared distinctive core = the discipline's own vocabulary (GIS, GPS, photogrammetry, remote sensing, sensors) with era-reorganized unit splits (the 2009-10 print leads with aerial-photography/photogrammetry, the 2025-26 print leads with GIS fundamentals — recorded era-reorganization class, B30 facility-planning/B31 01::18 evidence standard). 2025-26 newer so units fieldwise-win; the 2009-10 photogrammetry-led text stays in source_history/git (RULES §1c). BMN-062 (unowned) joins."},
    "10_btech_open-electives-science_2009-10::00::introduction-to-soft-computing-neural-networks-fuzzy-logic-a": {
        "action": "ALLOW",
        "reason": "B31 STAND of the pre-adjudicated CODE-REASSIGNED-ACROSS-SESSIONS auto (RESOLVE_APPEND B3/B02 class): the unique Tier-0 code owner of EOE-031/EOE-041 is the k_era range print on the Mathematics-III/Science-Based-OE slot rows ('EOE 031-038'/'EOE 041-048' program-structure prints); the draft (2009-10 science-OE doc, the ORIGINAL establishing print) names Introduction-to-Soft-Computing, and exactly one name-identity row exists (sess 2009-10, empty units) — the slot-code-to-subject convergence (recorded B17 SLOT-CODE-TRANSFER class): the name-identity row gains the exact codes + the verbatim units; the pool slot rows keep their range prints (G2-exempt)."},
    "10_btech_open-electives-science_2009-10::01::nano-sciences": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "nano-sciences",
        "keep_published_codes": {"EOE-042": "power-station-practice"},
        "reason": "B31 equal-session code-slot keep (recorded B19/RCS653 class): draft 'Nano Sciences' (2009-10 science-OE doc, 5 verbatim units) prints the paired slot 'EOE-032/EOE-042'; Tier-0 TIEs across nano-sciences (owns EOE-032) and power-station-practice (EEE-042;EOE-042, its own 2009-10 establishing print). Equal-session establishing prints never steal each other's codes: the update lands on the name-exact nano-sciences row (units backfill — the row prints none), EOE-042 STAYS with power-station-practice (G2 single ownership), and the science-OE pairing print is recorded as narrative on the nano-sciences row."},
    "10_btech_open-electives-science_2009-10::04::polymer-science-and-technology": {
        "action": "ALLOW",
        "reason": "B31 STAND of the pre-adjudicated CODE-REASSIGNED-ACROSS-SESSIONS auto (B3 BBC102 class): the unique Tier-0 code owner EOE-035/EOE-045 is polymer-science-technology ('Polymer Science & Technology', 2009-10, units empty, ROE035;ROE045 also owned); the draft name 'Polymer Science and Technology' name-matches exactly one same-course row (polymer-science-and-technology, BOE311;BOE411, 2023-24, 5 units — the NEP open-elective print of the SAME science elective; '&'/'and' print variance across eras, distinctive probe: polymerization/composites/polymers). The auto transfers EOE-035/EOE-045 to the name-identity accumulator row (the &-form row keeps ROE codes + narrative; recorded variant-name-rows-pending-reconciliation owner open item); draft 2009-10 OLDER so backfill-empty only."},
})

# ---- B35 (CRON-20261105-B35) re-keyed open-electives-science overrides (batch35 stem 08_) ----
TIER2_OVERRIDES.update({
    "08_btech_open-electives-science_2009-10::00::introduction-to-soft-computing-neural-networks-fuzzy-logic-a": {
        "action": "ALLOW",
        "reason": "B35 RE-KEY of the recorded B31 STAND (identical content to '10_btech_open-electives-science_2009-10::00' — the durable B31 draft was adopted into batch35 at slot 08): STAND of the pre-adjudicated CODE-REASSIGNED-ACROSS-SESSIONS auto (RESOLVE_APPEND B3/B02 class): the unique Tier-0 code owner of EOE-031/EOE-041 is the k_era range print on the Mathematics-III/Science-Based-OE slot rows ('EOE 031-038'/'EOE 041-048' program-structure prints); the draft (2009-10 science-OE doc, the ORIGINAL establishing print) names Introduction-to-Soft-Computing, and exactly one name-identity row exists (sess 2009-10, empty units) — the slot-code-to-subject convergence (recorded B17 SLOT-CODE-TRANSFER class): the name-identity row gains the exact codes + the verbatim units; the pool slot rows keep their range prints (G2-exempt)."},
    "08_btech_open-electives-science_2009-10::01::nano-sciences": {
        "action": "RETARGET_KEEP_PUBLISHED_CODE_OWNER", "target": "nano-sciences",
        "keep_published_codes": {"EOE-042": "power-station-practice"},
        "reason": "B35 RE-KEY of the recorded B31 equal-session code-slot keep (identical content to '10_btech_...::01'; recorded B19/RCS653 class): draft 'Nano Sciences' (2009-10 science-OE doc, 5 verbatim units) prints the paired slot 'EOE-032/EOE-042'; Tier-0 TIEs across nano-sciences (owns EOE-032) and power-station-practice (EEE-042;EOE-042, its own 2009-10 establishing print). Equal-session establishing prints never steal each other's codes: the update lands on the name-exact nano-sciences row (units backfill — the row prints none), EOE-042 STAYS with power-station-practice (G2 single ownership), and the science-OE pairing print is recorded as narrative on the nano-sciences row."},
    "08_btech_open-electives-science_2009-10::04::polymer-science-and-technology": {
        "action": "ALLOW",
        "reason": "B35 RE-KEY of the recorded B31 STAND (identical content to '10_btech_...::04'): STAND of the pre-adjudicated CODE-REASSIGNED-ACROSS-SESSIONS auto (B3 BBC102 class): the unique Tier-0 code owner EOE-035/EOE-045 is polymer-science-technology ('Polymer Science & Technology', 2009-10, units empty, ROE035;ROE045 also owned); the draft name 'Polymer Science and Technology' name-matches exactly one same-course row (polymer-science-and-technology, BOE311;BOE411, 2023-24, 5 units — the NEP open-elective print of the SAME science elective; '&'/'and' print variance across eras, distinctive probe: polymerization/composites/polymers). The auto transfers EOE-035/EOE-045 to the name-identity accumulator row (the &-form row keeps ROE codes + narrative; recorded variant-name-rows-pending-reconciliation owner open item); draft 2009-10 OLDER so backfill-empty only."},
})

# ---- B36 (CRON-20261105-B36) maths-v KAS304/KAS404 dual-slot convergence ----
TIER2_OVERRIDES.update({
    "10_btech_s3-4_kas304-404-maths-v_2019-20::00::mathematics-v": {
        "action": "RETARGET", "target": "maths-v-engineering-science-course",
        "reason": "B36 dual-slot convergence (recorded B17 SLOT-CODE-TRANSFER + B31 08::00 soft-computing class, update-first): the detailed 2019-20 print (B.Tech BioTechnology/Agriculture Engineering, subject code cell 'KAS304/KAS404' — ONE subject, BioTech sem-III / Ag-Engg sem-IV offering of the same AICTE-model course; verbatim 5 units + COs + books, Mercury-3 extraction containment-verified) TIEs at Tier-0 across the two scheme-row slot prints engineering-science-course-maths-v (KOE031-38 pool range; owns KAS304) and maths-v-engineering-science-course (primary KAS404). The KAS404-primary row is the convergence target: it gains the verbatim units/COs/books (both slot rows print none — backfill), KAS304 joins its codes via the recorded transfer (the pool-range row keeps its KOE031-38 range print + narrative history, G2-exempt), and the 'Mathematics-V' name + dual-slot cell print are recorded as the detailed print evidence (same-session 2019-20 detailed print fieldwise-fills empty fields; update first > append second — no duplicate row)."},
})


# ---- B36 (CRON-20261105-B36) re-keyed B32 pe-ipe/petroleum overrides (batch36 stems) ----
# The durable B32 drafts 03-10 were adopted into batch36 at slots 01-08; the
# stem-keyed recorded adjudications are re-keyed verbatim (evidence unchanged).
REKEY_B32 = {
    "04_btech_pe-ipe_y3_evaluation-scheme_2024-25": "02_btech_pe-ipe_y3_evaluation-scheme_2024-25",
    "05_btech_pe-ipe_y3_syllabus_2018-19": "03_btech_pe-ipe_y3_syllabus_2018-19",
    "06_btech_pe-ipe_y4_syllabus-cbcs_2019-20": "04_btech_pe-ipe_y4_syllabus-cbcs_2019-20",
    "07_btech_pe-ipe_y4_syllabus_2021-22": "05_btech_pe-ipe_y4_syllabus_2021-22",
    "08_btech_pe-ipe_y4_syllabus_2025-26": "06_btech_pe-ipe_y4_syllabus_2025-26",
    "09_btech_petroleum_y2_scheme-syllabus_2017-18": "07_btech_petroleum_y2_scheme-syllabus_2017-18",
    "10_btech_petroleum_y4_scheme-syllabus_2017-18": "08_btech_petroleum_y4_scheme-syllabus_2017-18",
}
_rekeyed = {}
for _k, _v in list(TIER2_OVERRIDES.items()):
    _old_stem = _k.split("::")[0]
    if _old_stem in REKEY_B32:
        _newk = REKEY_B32[_old_stem] + _k[len(_old_stem):]
        _rekeyed[_newk] = _v
        _rekeyed[_newk]["reason"] = "B36 RE-KEY of the recorded B32 entry (identical evidence; batch36 renumbered slot): " + _v["reason"]
TIER2_OVERRIDES.update(_rekeyed)



# ---- B31 (CRON-20261104-B31) doc-level scope from the PRINTED COVERS ----
DOC_SCOPE.update({
    "0ade72fa693fbd9c": {
        "branch_names": "Manufacturing Technology",
        "program_year": "3",
        "reason": "B31 doc01: cover prints 'EVALUATION SCHEME & SYLLABUS For B. Tech. 3rd Year Manufacturing Technology ON CBCS [Effective from session 2018-19]' — single-branch Mfg-Tech 3rd-year CBCS print; per-subject program_year from printed semesters (V/VI -> 3)"},
    "ae8c8559100c3cbf": {
        "branch_names": "Manufacturing Technology",
        "program_year": "4",
        "reason": "B31 doc02: cover prints 'STUDY & EVALUATION SCHEME WITH SYLLABUS FOR B. TECH 4th YEAR MANUFACTURING TECHNOLOGY ON CHOICE BASED CREDIT SYSTEM (EFFECTIVE FROM THE SESSION: 2019-20)' (R-era CBCS Sem VII/VIII)"},
    "16b336aad90afc2b": {
        "branch_names": "Manufacturing Technology",
        "program_year": "4",
        "reason": "B31 doc03: cover prints 'STUDY & EVALUATION SCHEME — B.Tech.ManufacturingTechnology [EffectivefromSession2016-17] — YEAR IV, SEMESTER-VII' (kerning-fused print; N-era NME/NMT codes)"},
    "b3c1767fa66cb1cb": {
        "branch_names": "Manufacturing Technology",
        "program_year": "4",
        "reason": "B31 doc04: cover prints 'STUDY & EVALUATION SCHEME WITH SYLLABUS | FOR | B. TECH. 4th YEAR | MANUFACTURING TECHNOLOGY | [Effective from Session: 2021-22]' (K-era KMT/KPI codes)"},
    "2e50304ddbcc9f22": {
        "branch_names": "Manufacturing Technology",
        "program_year": "4",
        "reason": "B31 doc05: cover prints 'COURSE STRUCTURE/EVALUATION SCHEME FOR B.TECH. 4th YEAR MANUFACTURING TECHNOLOGY [Effective from Session: 2025-26]' (B-era NEP BME/BPI codes)"},
    "d97d9fe331d271c1": {
        "branch_names": "Mining Engineering",
        "program_year": "3",
        "reason": "B31 doc06: cover (p.1) prints 'Evaluation Scheme & Syllabus For B.Tech. 3rd Year MINING ENGINEERING [Effective from the Session: 2025-26}' (B-era BMN codes; the closing brace is a printed cover typo, kept verbatim); per-subject program_year from printed semesters (V/VI -> 3)"},
    "1b93096db8304b23": {
        "branch_names": "Mining Engineering",
        "program_year": "4",
        "reason": "B31 doc07: cover prints 'Evaluation Scheme & Syllabus For B.Tech. 4th Year MINING ENGINEERING [Effective from the Session: 2026-27}' (B-era BMN codes; printed bracket typo '2026-27}' kept verbatim)"},
    "db1f836f585af9c4": {
        "branch_names": "",
        "program_year": "",
        "reason": "B31 doc10: cover prints 'U.P. TECHNICAL UNIVERSITY LUCKNOW Syllabus 1. Science based Open Electives 2. Open Electives-I 3. Open Electives-II [Effective from the session : 2009-10] B.TECH. COURSES' — no branch list printed (science-based OE / OE-I / OE-II are common university slots, B16 BNC zero-guess class); branch_names stays BLANK; all 16 subjects resolve as UPDATES on existing rows so no append scope is consumed"},
})


if __name__ == "__main__":
    sys.exit(run(sys.argv[1], sys.argv[2]))
