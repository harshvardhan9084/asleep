#!/usr/bin/env python3
"""patch_b13_alt_pair_slots.py — B13 TIE resolution evidence + alternative_pair_row
flags (B12 ALTERNATIVE-PAIR-SLOT precedent, merge_draft.py line ~1299).

The 7 TIE subjects are paired/alternative slot prints: one scheme line names TWO
university-wide subjects with BOTH their printed codes (units=0, cos=0,
scheme_row_only_no_detailed_syllabus in every case; no draft in this batch
details either named subject separately — verified by full-batch scan). Tier-0
code identity matches both member rows → TIE.

Patch policy (zero-guess): for each subject, EVERY specific printed code is
checked against the published BTech catalog (download/art_d_final/
syllabus_extreme_rich.csv @ c38cb37, 1113 rows): ownership = token in a BTech
row's primary_code/all_codes; mention = token in code_history_all. The flag
`alternative_pair_row` is added ONLY when every specific printed code resolves
to an existing BTech row (owner or history mention) and at least one is a live
owner. Pool ranges (e.g. KOE031-38) are exempt wildcards (RULES §2 Tier 0).
Evidence string recorded in the subject's quirks. Idempotent.
"""
import csv, json, re, sys
from datetime import datetime, timezone

CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")
SPEC = re.compile(r"^[A-Z]{2,4}[0-9]{3}[A-Z]?$")

TARGETS = {
    "02_btech_carpet-textile_y2_model-curriculum_2019-20": [12, 13, 15, 16, 18],
    "03_btech_carpet-textile_y2_scheme-syllabus_2017-18": [1, 13],
}


def norm(code):
    return re.sub(r"[\s\-]", "", str(code)).upper()


def main():
    rows = list(csv.DictReader(open(CSV)))
    owner, mention = {}, {}
    for r in rows:
        sid, course = r["subject_id"], r["course_name"]
        for col in ("primary_code", "all_codes"):
            for tok in (r.get(col, "") or "").split(";"):
                tok = norm(tok)
                if SPEC.match(tok):
                    owner.setdefault(tok, []).append((sid, course))
        for tok in (r.get("code_history_all", "") or "").split(";"):
            tok = norm(tok)
            if SPEC.match(tok):
                mention.setdefault(tok, []).append((sid, course))

    total = 0
    for stem, idxs in TARGETS.items():
        path = f"{DRAFTS}/{stem}.draft.json"
        d = json.load(open(path))
        for i in idxs:
            s = d["subjects"][i]
            if "alternative_pair_row" in (s.get("flags") or []):
                continue
            codes = [c for c in (s.get("codes") or [])]
            ev, ok = [], True
            owned = 0
            for c in codes:
                if not SPEC.match(norm(c)):
                    ev.append(f"{c}=pool-range(wildcard-exempt)")
                    continue
                ow = [x for x in owner.get(norm(c), []) if x[1] == "BTech"]
                men = [x for x in mention.get(norm(c), []) if x[1] == "BTech"]
                if ow:
                    owned += 1
                    ev.append(f"{c}=BTech:{ow[0][0]}")
                elif men:
                    ev.append(f"{c}=BTech-history-mention:{men[0][0]}")
                else:
                    ok = False
                    ev.append(f"{c}=UNOWNED!")
            if not (ok and owned >= 1):
                print(f"NO-PATCH|{stem}::{i}|evidence: {'; '.join(ev)}")
                continue
            s.setdefault("flags", []).append("alternative_pair_row")
            s.setdefault("quirks", []).append(
                f"{NOW} B13 patch: paired/alternative slot print (both printed codes "
                f"resolve to existing BTech rows: {'; '.join(ev)}; neither named "
                f"subject detailed separately in this doc or batch — full-batch scan; "
                f"scheme_row_only + units=0/cos=0). Slot is program structure, not a "
                f"subject (B12 ALTERNATIVE-PAIR-SLOT precedent; RULES §11).")
            print(f"PATCH|{stem}::{i}|{s['name'][:50]}|{'; '.join(ev)}")
            total += 1
        with open(path, "w") as f:
            json.dump(d, f, indent=1, ensure_ascii=False)
    print(f"TOTAL|{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
