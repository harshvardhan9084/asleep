#!/usr/bin/env python3
"""Deterministic schema converter (Task CRON-20261028-B03).

Source : drafts_archive/pre-reset-original/05_bpharm_scheme-syllabus_2026-27.draft.json
         (pre-reset S05 stitched draft; sha16 97b5d901f34c75a4 — byte-identical to the
          current corpus copy work/repo_asleep/PDFs/5-course/2026-27/bpharm_scheme-syllabus_2026-27.pdf,
          so its verbatim extraction is content-identical for this batch's stem 08).
Output : drafts/08_bpharm_scheme-syllabus_2026-27.draft.json  (current RULES §7 spec)

Zero content invention: pure field mapping. Every printed value is preserved
verbatim (units/COs/books/experiments/objectives/scheme_line_print/quirks).
Anything unmappable aborts loudly instead of guessing.
Evidence for reuse: parsed sha16 identity (97b5d901f34c75a4 == current corpus
copy) + the objective verifier runs against the current parsed fulltext after
conversion; any infidelity fails containment there.
"""
import json, re, sys

SRC = "/home/z/my-project/work/pipeline_v2/drafts_archive/pre-reset-original/05_bpharm_scheme-syllabus_2026-27.draft.json"
OUT = "/home/z/my-project/work/pipeline_v2/drafts/08_bpharm_scheme-syllabus_2026-27.draft.json"

SEM = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}


def abort(msg):
    print("CONVERT-ABORT:", msg)
    sys.exit(2)


def sem_int(v):
    if isinstance(v, int):
        return v
    s = str(v).strip().upper().rstrip(".")
    if s in SEM:
        return SEM[s]
    if s.isdigit():
        return int(s)
    abort(f"unmappable semester {v!r}")


def num_or_none(v):
    s = str(v).strip()
    if s in ("--", "-", "", "—"):
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def ltp_num(v):
    """printed '--' = zero hours (same convention as the B02 drafts)."""
    n = num_or_none(v)
    return 0 if n is None else n


def conv_lpu(v):
    """'6 Hours' -> '6'; '6 Hours, 6 Hours, ...' -> '6;6;...'; no digits -> verbatim."""
    s = (v or "").strip()
    if not s:
        return ""
    if re.fullmatch(r"\d+", s):
        return str(int(s))
    nums = re.findall(r"\d+(?:\.\d+)?", s)
    if nums:
        return ";".join(str(int(float(n))) if "." not in n else n for n in nums)
    return s


def cat_from_notes(notes):
    for n in notes or []:
        m = re.search(r"Course Type printed:\s*([^.|\n]+)", str(n))
        if m:
            return m.group(1).strip()
    return ""


def strip_leading_no(s):
    m = re.match(r"^\s*(\d{1,2})\s*\.\s*(.*)$", s or "", re.S)
    if m:
        return int(m.group(1)), m.group(2).strip()
    return None, (s or "").strip()


def main():
    d = json.load(open(SRC))
    subs_in = d.get("subjects") or []
    if len(subs_in) != 113:
        abort(f"expected 113 subjects, got {len(subs_in)}")

    # doc-level flags reference specific subjects by printed code — route them
    doc_flags = d.get("doc_level_flags") or []

    subs_out = []
    for s in subs_in:
        name = (s.get("subject_name") or "").strip()
        if not name:
            abort(f"subject without name: {s.get('primary_code')}")
        codes = [c for c in (s.get("all_codes") or []) if c] or ([s.get("primary_code")] if s.get("primary_code") else [])
        if not codes:
            abort(f"{name}: no codes")
        # primary first, preserve printed order otherwise
        pc = s.get("primary_code")
        if pc and pc in codes:
            codes = [pc] + [c for c in codes if c != pc]

        sem = sem_int((s.get("placement") or {}).get("semesters", [None])[0])
        sch = s.get("scheme") or {}
        ltp = {"l": ltp_num(sch.get("L")), "t": ltp_num(sch.get("T")), "p": ltp_num(sch.get("P"))}
        credit = num_or_none(sch.get("credit"))
        marks = {}
        for k_out, k_in in (("sessional_ct", "sessional_ct"), ("sessional_ta", "sessional_ta"),
                            ("sessional_total", "sessional_total"), ("ese_te_pe", "ese_te_pe"),
                            ("total", "total_marks")):
            n = num_or_none(sch.get(k_in))
            if n is not None:
                marks[k_out] = n

        units_in = s.get("units") or {}
        units, overflow = {}, []
        for k, v in units_in.items():
            m = re.fullmatch(r"unit([1-9])", str(k), re.I)
            if not m:
                abort(f"{name}: unmappable unit key {k!r}")
            if not isinstance(v, str):
                abort(f"{name}: unit{k} not a string")
            n = int(m.group(1))
            if n > 5:
                # frozen 57-col schema has unit1-5 only (G1): overflow printed
                # unit rows are preserved VERBATIM in row notes + needs_review
                # (brain clause: keep proof; evidence BP802T pp.204-205 prints
                # 9 unit rows with a duplicated 'VII' numeral, VIII not printed)
                overflow.append((n, v))
            else:
                units[str(n)] = v

        co_texts = s.get("co_texts") or []
        if len(co_texts) > 6:
            abort(f"{name}: {len(co_texts)} CO texts exceeds registry co1-6 columns")
        cos = [{"no": i + 1, "text": t} for i, t in enumerate(co_texts) if (t or "").strip()]

        def books(lst):
            out = []
            for i, b in enumerate(lst or []):
                if not isinstance(b, str):
                    abort(f"{name}: non-string book entry {b!r}")
                out.append({"no": i + 1, "book": b.strip()})
            return out

        experiments = []
        for i, e in enumerate(s.get("experiments") or []):
            if not isinstance(e, str):
                abort(f"{name}: non-string experiment entry {e!r}")
            no, txt = strip_leading_no(e)
            experiments.append({"no": no if no is not None else i + 1, "exp": txt})

        flags, quirks = [], [q for q in (s.get("print_quirks") or []) if (q or "").strip()]
        if s.get("needs_review"):
            flags.append("needs_review")
        if overflow:
            quirks.append("Printed unit table has " + str(len(units) + len(overflow)) +
                          " rows — registry unit1-5 columns hold rows 1-5 verbatim; the further printed rows are preserved here verbatim: " +
                          " || ".join(f"printed unit row {n}: {v}" for n, v in overflow))
            if "needs_review" not in flags:
                flags.append("needs_review")
        notes = [n for n in (s.get("notes") or []) if (n or "").strip() and str(n).strip() != "segment " + str(s.get("_segment", ""))]
        for n in notes:
            quirks.append(str(n))

        no_units = not units
        no_exp = not experiments
        blank_list_flag = any(c in df and "no experiment items follow" in df for df in doc_flags for c in codes)
        if no_units and no_exp:
            # scheme-only card (internship/research-project prints "Refer Section NN of the ordinance";
            # BP611P prints a practice-list header with a printed-blank item list)
            flags.append("scheme_only_print")
            if blank_list_flag:
                flags.append("needs_review")
            elif s.get("has_detailed_syllabus") is True:
                abort(f"{name}: has_detailed=True but no units and no experiments — inspect")
            if "BP611P" in codes:
                flags.append("needs_review")

        # route doc-level flags that name this subject's printed code
        for df in doc_flags:
            if any(re.search(re.escape(c), df, re.I) for c in codes):
                quirks.append("doc-level flag: " + df)
                if "needs_review" in df.lower() or "no experiment items follow" in df or "prints_" in df:
                    if "needs_review" not in flags:
                        flags.append("needs_review")

        out_sub = {
            "name": name,
            "name_print": (s.get("subject_name_print") or name).strip(),
            "codes": codes,
            "semester": sem,
            "program_year": (sem + 1) // 2,
            "ltp": ltp,
            "credit": credit,
            "marks": marks,
            "subject_type": "lab" if s.get("is_lab") else "theory",
            "category_print": cat_from_notes(s.get("notes")),
            "units": units,
            "lectures_per_unit": conv_lpu(s.get("lectures_per_unit")),
            "cos": cos,
            "textbooks": books(s.get("textbooks")),
            "reference_books": books(s.get("reference_books")),
            "experiments": experiments,
            "objectives_print": [o for o in (s.get("objectives") or []) if (o or "").strip()],
            "prerequisites": (s.get("prerequisites") or "").strip(),
            "scheme_line_print": (sch.get("scheme_line_print") or "").strip(),
            "quirks": quirks,
            "flags": flags,
        }
        subs_out.append(out_sub)

    # draft-level in/out
    def ns_convert(ns):
        kind = ns.get("row_kind", "note")
        payload = ns.get("payload") or {}
        verbatim_candidates = {
            "semester_summary": ["row_print", "scheme_row_print", "total_row_print", "totals_print"],
            "elective_pool": ["slot_card_print", "group_print", "slot_print", "card_scheme_print",
                              "pool_page_scheme_print", "scheme_line_print", "members_print",
                              "member_labels_print"],
        }.get(kind, [])
        chosen = ""
        for k in verbatim_candidates:
            if payload.get(k):
                chosen = str(payload[k])
                break
        if not chosen:
            chosen = json.dumps(payload, ensure_ascii=False)
        loc = payload.get("semester") or payload.get("semester_print") or ""
        locator = f"scheme/section print{', semester ' + str(loc) if loc else ''}"
        return {"kind": kind, "print": chosen, "locator": locator, "payload": payload}

    out = {
        "pdf_rel": "repo_asleep/PDFs/5-course/2026-27/bpharm_scheme-syllabus_2026-27.pdf",
        "session": "2026-27",
        "course": "BPharm",
        "sha16": "97b5d901f34c75a4",
        "stem": "08_bpharm_scheme-syllabus_2026-27",
        "locator": "pp.1-295",
        "subjects": subs_out,
        "non_subject_rows": [ns_convert(ns) for ns in (d.get("non_subject_rows") or [])],
        "quirks": [str(n) for n in (d.get("doc_level_notes") or [])],
        "flags": [],
    }

    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    n_units = sum(1 for s in subs_out if s["units"])
    n_exp = sum(1 for s in subs_out if s["experiments"])
    n_nr = sum(1 for s in subs_out if "needs_review" in s["flags"])
    print(f"CONVERT-OK subjects={len(subs_out)} with_units={n_units} with_exp={n_exp} "
          f"needs_review={n_nr} non_subject={len(out['non_subject_rows'])} -> {OUT}")


if __name__ == "__main__":
    main()
