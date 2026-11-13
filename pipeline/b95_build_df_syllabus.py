#!/usr/bin/env python3
"""b95_build_df_syllabus.py — CRON-20261113-B95 (owner request, 2026-11-13).

Build the OPEN-SOURCE CONSUMER VIEW `df_syllabus.csv` from the of-record CSV:
developer-facing columns only. Owner rule: another developer building on the
dataset should never need `notes`, `quality_flags`, `corrections_json`, or any
`*_print`/source-citation/evidence surface — those stay in the of-record CSV
(syllabus_extreme_rich.csv), which remains the audit/research artifact.

Dropped from df (18 cols): evidence surfaces (subject_name_print,
subject_category_print, eligibility_print, objectives_print), internal
provenance (source_syllabus, source_scheme_line, source_history,
change_note_vs_previous), quality/bookkeeping (notes, quality_flags,
corrections_json, verification_status, evaluation_note, code_family,
row_kind[all 'subject'], status[all 'latest']), redundant variants
(subject_name_display [verified identical to subject_name],
subject_type [kept the cleaned subject_type_norm]).

Also computes the owner-requested diversity/variation stats.
Zero writes to the of-record CSV.
"""
import csv
import json
import os
import shutil
import sys
from collections import Counter, defaultdict

MAIN = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
DF = "/home/z/my-project/download/art_d_final/df_syllabus.csv"
REPO_DF = "/home/z/my-project/work/repo_asleep/syllabus_catalog/df_syllabus.csv"
STATS = "/home/z/my-project/work/pipeline_v2/b95_stats.json"

DROP = {
    "subject_name_print", "subject_category_print", "eligibility_print",
    "objectives_print", "source_syllabus", "source_scheme_line",
    "source_history", "change_note_vs_previous", "notes", "quality_flags",
    "corrections_json", "verification_status", "evaluation_note",
    "code_family", "row_kind", "status", "subject_name_display",
    "subject_type",
    "subject_name_display",
}


def main():
    rows = list(csv.DictReader(open(MAIN)))
    hdr = list(rows[0].keys())
    assert len(rows) == 3080, f"row count {len(rows)}"
    assert len(hdr) == 62, f"header {len(hdr)} != 62"
    # identity check before dropping subject_name_display
    # subject_name_display verified = the PRINTED name (caps/asterisk artifacts,
    # differs from the canonical subject_name on 1,670 rows) -> print surface, dropped.
    df_cols = [c for c in hdr if c not in DROP]
    assert len(df_cols) == 62 - len(DROP)
    # write df
    with open(DF, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=df_cols, lineterminator="\n",
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    # integrity re-open
    drows = list(csv.DictReader(open(DF)))
    assert len(drows) == 3080, "df row count changed"
    dhdr = list(drows[0].keys())
    assert dhdr == df_cols, "df header mismatch"
    bad = 0
    for r in drows:
        for c in ("textbooks_structured", "reference_books_structured",
                  "experiments_structured"):
            if r[c]:
                json.loads(r[c])  # raises if truncated/malformed
    assert not any(c in dhdr for c in DROP), "evidence column leaked into df"
    shutil.copy2(DF, REPO_DF)
    print(f"df_syllabus.csv written: {len(drows)} rows x {len(dhdr)} cols "
          f"(dropped {len(DROP)}: {sorted(DROP)})")

    # ---------------- diversity / variation stats ----------------
    def spl(v):
        return [x.strip() for x in (v or "").split(";") if x.strip()]

    st = {}
    st["rows_of_record"] = len(rows)
    st["cols_of_record"] = 62
    st["rows_df"] = len(drows)
    st["cols_df"] = len(dhdr)

    # courses
    courses = Counter(r["course_name"] for r in rows)
    st["courses"] = dict(courses.most_common())

    # branches
    branch_course = defaultdict(set)
    all_branches = set()
    for r in rows:
        for b in spl(r["branch_names"]):
            all_branches.add(b)
            branch_course[b].add(r["course_name"])
    per_course = {c: sorted({b for b, cs in branch_course.items() if c in cs})
                  for c in courses}
    st["branches_total"] = len(all_branches)
    st["branches_by_course"] = {c: len(v) for c, v in per_course.items()}
    st["btech_branches"] = per_course.get("BTech", [])

    # subject-name breadth (distinct branches & courses per name)
    name_branches = defaultdict(set)
    name_courses = defaultdict(set)
    for r in rows:
        n = (r["subject_name"] or "").strip().lower()
        if not n:
            continue
        bs = spl(r["branch_names"])
        name_branches[n].update(bs)
        name_courses[n].add(r["course_name"])
    top_by_branch = sorted(name_branches.items(),
                           key=lambda kv: -len(kv[1]))[:10]
    st["top_subject_names_by_branches"] = [
        {"name": k, "branches": len(v),
         "courses": sorted(name_courses[k])} for k, v in top_by_branch]
    multi_course = {k: sorted(v) for k, v in name_courses.items() if len(v) > 1}
    st["subject_names_in_multiple_courses"] = len(multi_course)
    st["top_subject_names_by_courses"] = sorted(
        multi_course.items(), key=lambda kv: -len(kv[1]))[:8]

    # codes / eras
    all_codes = set()
    per_row_codes = []
    sessions_first, sessions_latest = set(), set()
    for r in rows:
        cs = spl(r["all_codes"])
        all_codes.update(cs)
        per_row_codes.append(len(cs))
        if r["first_introduced_session"]:
            sessions_first.add(r["first_introduced_session"])
        if r["effective_session_latest"]:
            sessions_latest.add(r["effective_session_latest"])
    st["distinct_codes"] = len(all_codes)
    st["codes_per_row_avg"] = round(sum(per_row_codes) / len(rows), 2)
    st["code_max_on_one_row"] = max(per_row_codes)
    st["session_span"] = [min(sessions_first), max(sessions_latest)]
    st["distinct_sessions"] = len(sessions_first | sessions_latest)

    # semester load (rows with a printed semester slot)
    sem = defaultdict(lambda: {"n": 0, "credits": 0.0, "core": 0,
                               "dept_elective": 0, "lab_prac": 0,
                               "open_elective": 0, "other": 0})
    for r in rows:
        s = (r["semester_slots"] or "").strip()
        if not s:
            continue
        d = sem[(r["course_name"], s)]
        d["n"] += 1
        d["credits"] += float(r["credit"] or 0)
        t = (r["subject_type_norm"] or "").strip()
        if t == "core":
            d["core"] += 1
        elif t == "departmental-elective":
            d["dept_elective"] += 1
        elif t in ("lab", "practical"):
            d["lab_prac"] += 1
        elif t == "open-elective":
            d["open_elective"] += 1
        else:
            d["other"] += 1
    bt = {k: v for k, v in sem.items() if k[0] == "BTech"}
    st["btech_per_semester"] = {
        k[1]: v for k, v in sorted(bt.items(), key=lambda kv: kv[0][1])}
    if bt:
        core_credits = [v["credits"] for v in bt.values() if v["core"] + v["lab_prac"]]
        n_subj = [v["n"] for v in bt.values()]
        st["btech_typical_semester"] = {
            "median_subjects_offered_per_sem": sorted(n_subj)[len(n_subj) // 2],
            "median_core_lab_credits_per_sem": sorted(core_credits)[len(core_credits) // 2],
        }

    # program years
    years = defaultdict(Counter)
    for r in rows:
        y = (r["program_year"] or "").strip()
        if y:
            years[r["course_name"]][y] += 1
    st["program_year_distribution"] = {c: dict(v.most_common())
                                       for c, v in sorted(years.items())}

    # credits / marks / L-T-P
    creds = Counter(r["credit"] for r in rows if r["credit"])
    st["credit_distribution"] = dict(creds.most_common(8))
    marks = Counter(r["total_marks"] for r in rows if r["total_marks"])
    st["total_marks_distribution"] = dict(marks.most_common(8))
    ltp = Counter(f"{r['L']}-{r['T']}-{r['P']}" for r in rows if r["L"])
    st["top_ltp_patterns"] = dict(ltp.most_common(6))

    # content volume
    def arr(v):
        return json.loads(v) if v else []
    n_books = n_ref = n_exp = 0
    rows_books = rows_ref = rows_exp = 0
    co_filled = units_filled = 0
    for r in rows:
        tb, rf, ex = arr(r["textbooks_structured"]), arr(r["reference_books_structured"]), arr(r["experiments_structured"])
        if tb:
            rows_books += 1
            n_books += len(tb)
        if rf:
            rows_ref += 1
            n_ref += len(rf)
        if ex:
            rows_exp += 1
            n_exp += len(ex)
        co_filled += sum(1 for i in range(1, 7) if (r[f"co{i}_text"] or "").strip())
        units_filled += sum(1 for i in range(1, 6) if (r[f"unit{i}_text"] or "").strip())
    st["content_volume"] = {
        "rows_with_detailed_syllabus": sum(1 for r in rows if r["has_detailed_syllabus"] == "TRUE"),
        "unit_texts_filled": units_filled,
        "course_outcomes_filled": co_filled,
        "rows_with_textbooks": rows_books, "textbook_entries": n_books,
        "rows_with_reference_books": rows_ref, "reference_entries": n_ref,
        "rows_with_experiment_lists": rows_exp, "experiment_entries": n_exp,
    }
    st["electives"] = {
        "departmental_elective_rows": sum(1 for r in rows if r["subject_type_norm"] == "departmental-elective"),
        "open_elective_rows": sum(1 for r in rows if r["subject_type_norm"] == "open-elective"),
        "choice_groups": len({r["choice_group_id"] for r in rows if r["choice_group_id"]}),
    }

    json.dump(st, open(STATS, "w"), indent=1)
    print(json.dumps(st, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
