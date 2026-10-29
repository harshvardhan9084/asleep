#!/usr/bin/env python3
"""repair_baseline_g2g3.py — pre-merge baseline repair (B06-prep redo).

The 526-row published baseline (B05 state, GitHub @2d7a5ec) violates the
published RULES §5 gates with era-model artifacts its (lost) B05 gate
implementation tolerated — recorded verbatim in the published B06 manifest
(runs/20261029T012603Z_CRON-20261029-B06_*.md, "Baseline repair (B06-prep)"):

  34 (course,code) multi-ownership G2 groups (BP1xxP-BP8xxP BPharm era prints
  incl. 2026-27 elective pools + members; KCS/BCS lab twins from B05's R1
  verdict) and 4 BPharm (name,course) G3 dups.

This script re-derives that repair deterministically with recorded reasoning
(the B06 session's repair script was lost with its workspace — the manifest's
rule text is the authority):

  G2 winner per (course,code), in order:
    1. elective-pool rows win slot codes (the pool row IS the slot's owner);
    2. else the primary-code claimant with the newest effective_session_latest;
    3. ties -> the row whose subject_id carries no course-suffix marker.
  Losers DROP the contested code from all_codes (and from primary_code, whose
  replacement is another still-owned code or empty) into the code_history_all
  NARRATIVE + a change note. Zero rows deleted, zero content fields touched.

  G3 losers (older session of each (name,course) dup pair) get a
  " [<session> print]" subject_name qualifier; subject_name_print keeps the
  verbatim print. Era-model rows stay separate (RULES §1b/§11: never merge).

Post-condition: gate_g2 groups = 0, gate_g3 dups = 0 (verified at the end).
"""
import csv, json, re, sys
from datetime import datetime, timezone

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
from merge_draft import (CSV_PATH, gate_g2, gate_g3, canon_course, norm_code,
                         exact_code, norm_name)

SUFFIX_RE = re.compile(r"-(bpharm|btech|bca|mca|mba)([0-9].*)?$")


def owned_codes(r):
    toks = set()
    for f in ("primary_code", "all_codes"):
        for c in (r.get(f, "") or "").split(";"):
            c = norm_code(c)
            if exact_code(c):
                toks.add(c)
    return toks


def main():
    rows = list(csv.DictReader(open(CSV_PATH)))
    order = {r["subject_id"]: i for i, r in enumerate(rows)}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    repairs = []

    # ---- G2 ----
    owner = {}
    for r in rows:
        ck = canon_course(r.get("course_name", ""))
        for t in owned_codes(r):
            owner.setdefault((ck, t), {})[r["subject_id"]] = r
    groups = {k: v for k, v in owner.items() if len(v) > 1}

    def sess(r):
        return r.get("effective_session_latest", "") or ""

    def unsuffixed(r):
        return 0 if SUFFIX_RE.search(r["subject_id"] or "") else 1

    for (ck, code), members in sorted(groups.items()):
        mrows = list(members.values())
        pool = [r for r in mrows if r.get("row_kind") == "elective_pool"
                or "elective-pool" in (r.get("subject_id", "") or "")]
        if pool:
            pool.sort(key=lambda r: (order[r["subject_id"]]))
            winner = pool[0]
            reason = "elective-pool row owns the printed slot code (B06-prep rule 1)"
        else:
            prim = [r for r in mrows
                    if code in {norm_code(c) for c in (r.get("primary_code", "") or "").split(";")}]
            cands = prim if prim else mrows
            # deterministic stable-sort chain: base row order, then unsuffixed
            # preferred, then newest session first (last sort is primary key)
            cands = sorted(cands, key=lambda r: order[r["subject_id"]])
            cands = sorted(cands, key=lambda r: unsuffixed(r), reverse=True)
            cands = sorted(cands, key=lambda r: sess(r), reverse=True)
            winner = cands[0]
            reason = ("primary-code claimant, newest session"
                      if prim else "sole remaining claimant class") + " (B06-prep rule 2/3)"
        for r in mrows:
            if r is winner:
                continue
            sid = r["subject_id"]
            toks = [c.strip() for c in (r.get("all_codes", "") or "").split(";") if c.strip()]
            keep = [c for c in toks if norm_code(c) != code]
            r["all_codes"] = ";".join(keep)
            if norm_code(r.get("primary_code", "")) == code:
                r["primary_code"] = keep[-1] if keep else ""
            seg = (f" - {code} slot print owned by {winner['subject_id']} per the {sess(winner)} "
                   f"era scheme ({reason}); narrative mention retained (baseline G2 repair, "
                   f"RULES §5 course-scoped idempotency; B06-prep rule re-derived from the "
                   f"published B06 manifest)")
            r["code_history_all"] = (r.get("code_history_all", "") or "") + seg
            r["change_note_vs_previous"] = (r.get("change_note_vs_previous", "") + "; " if
                                            r.get("change_note_vs_previous", "") else "") + \
                f"{now}: baseline G2 repair — code {code} dropped to narrative (owner: {winner['subject_id']})"
            repairs.append({"group": f"{code} [{ck}]", "loser": sid, "winner": winner["subject_id"],
                            "reason": reason})

    # ---- G3 ----
    seen = {}
    for r in rows:
        if r.get("row_kind") != "subject":
            continue
        key = (norm_name(r.get("subject_name", "")), canon_course(r.get("course_name", "")))
        seen.setdefault(key, []).append(r)
    for key, members in sorted(seen.items()):
        if len(members) < 2:
            continue
        members_sorted = sorted(members, key=lambda r: (sess(r), order[r["subject_id"]]))
        for older in members_sorted[:-1]:  # every row older than the newest gets the qualifier
            if "[print]" in (older.get("subject_name", "") or ""):
                continue  # already qualified (idempotent)
            s = sess(older) or "undated"
            old_name = older.get("subject_name", "")
            older["subject_name"] = f"{old_name} [{s} print]"
            older["change_note_vs_previous"] = (older.get("change_note_vs_previous", "") + "; " if
                                                older.get("change_note_vs_previous", "") else "") + \
                (f"{now}: baseline G3 repair — (name,course) qualified with era print marker; "
                 f"subject_name_print keeps the verbatim print (era-model rows stay separate, "
                 f"RULES §11; B06-prep rule)")
            repairs.append({"group": f"name-dup {key[0][:40]} [{key[1]}]", "loser": older["subject_id"],
                            "winner": members_sorted[-1]["subject_id"],
                            "reason": f"older-session row qualified [{s} print]"})

    # ---- verify + write ----
    g2, ncodes = gate_g2(rows)
    g3 = gate_g3(rows)
    print(f"post-repair G2: {'PASS' if not g2 else 'FAIL ' + g2[:200]}")
    print(f"post-repair G3: {'PASS' if not g3 else 'FAIL ' + g3[:200]}")
    if g2 or g3:
        print("ABORT: repair did not clear the gates — no write")
        return 2
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    json.dump({"ts": now, "repairs": repairs, "rows": len(rows)},
              open("/home/z/my-project/work/pipeline_v2/baseline_repair_report.json", "w"),
              indent=1, ensure_ascii=False)
    print(f"REPAIR OK rows={len(rows)} repairs={len(repairs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
