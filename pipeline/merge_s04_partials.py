#!/usr/bin/env python3
"""merge_s04_partials.py v2 — deterministically merge the 3 page-range partial
drafts (04a/04b/04c) of the 295-page BPharm scheme-syllabus 2026-27 doc into
one RULES §7 draft. Remedy for repeated single-agent context-deadline deaths
(recorded in worklog CRON-20261028-B04).

v2 grouping (recorded reasoning):
- Group candidates by NORMALIZED NAME (dedupes cross-partial overlap; keeps
  same-code elective VARIANTS — e.g. six AEC subjects all printed 'BP607T' —
  as separate subjects, per RULES §11 never-merge-two-subjects).
- Slot-level pool entries from 04a ('SEC* - Elective N', ELECTIVE-SYLLABUS-
  IN-APPENDIX, no units/cos/books) are DROPPED as superseded by 04c's detailed
  variants (their scheme prints also live in non_subject_rows) — logged.
- Shared-code elective slots: the FIRST printed variant owns the code in
  codes[]; later variants get codes=[] + code_note recording the printed
  shared code + slot + owner name (G2 course-scoped idempotency without
  losing any subject). Code-owner choice = printed order (a<b<c, list order).
- Non-pool duplicate codes with different names: keep higher-preference
  entry, log the conflict loudly (investigate before commit).
- Same-name groups: preference non-truncated > more unit/experiment text >
  earlier partial; fieldwise backfill of empty keys; quirks/flags concat.
"""
import json, re, os

D = "/home/z/my-project/work/pipeline_v2/drafts"
PARTIALS = ["/home/z/my-project/work/pipeline_v2/drafts_archive/B04_partials/04a_bpharm_scheme-syllabus_2026-27.draft.json",
            "/home/z/my-project/work/pipeline_v2/drafts_archive/B04_partials/04b_bpharm_scheme-syllabus_2026-27.draft.json",
            "/home/z/my-project/work/pipeline_v2/drafts_archive/B04_partials/04c_bpharm_scheme-syllabus_2026-27.draft.json"]
OUT = f"{D}/04_bpharm_scheme-syllabus_2026-27.draft.json"

# shared-code elective slots discovered in this doc (printed scheme codes that
# carry multiple alternative subjects; zero-guess: exactly what the doc prints)
POOL_CODES = {"BP212P", "BP312P", "BP607T", "BP610P", "BP611P", "BP708T",
              "BP806T", "BP809P"}


def norm_name(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()


def base_code(c):
    n = re.sub(r"[^A-Z0-9]", "", c.upper())
    m = re.match(r"^([A-Z]{2,4}\d{3}[A-Z]?)", n)
    return m.group(1) if m else n


def is_slot_pool_entry(s):
    """04a-style slot-level entry: SEC*/AEC* name, ELECTIVE-SYLLABUS-IN-APPENDIX
    flag, no units/cos/experiments/books detail."""
    fl = " ".join(str(f) for f in (s.get("flags") or []))
    return ("ELECTIVE-SYLLABUS-IN-APPENDIX" in fl and not (s.get("units") or {})
            and not (s.get("cos") or []) and not (s.get("experiments") or []))


def content_size(s):
    return (sum(len(v) for v in (s.get("units") or {}).values())
            + sum(len(e.get("exp", "")) for e in s.get("experiments") or [])
            + len(json.dumps(s.get("cos") or [], ensure_ascii=False)))


def truncated(s):
    return any("TRUNCATED-AT" in str(f).upper() for f in (s.get("flags") or []))


def main():
    parts = [json.load(open(os.path.join(D, p))) for p in PARTIALS]
    for p in parts:
        assert p["sha16"] == "97b5d901f34c75a4" and p["course"] == "BPharm"
    merged = {
        "pdf_rel": parts[0]["pdf_rel"], "session": parts[0]["session"],
        "course": parts[0]["course"], "sha16": parts[0]["sha16"],
        "stem": "04_bpharm_scheme-syllabus_2026-27",
    }
    # ---- flatten with partial order preserved (printed-order proxy) ----
    flat = []  # (pi, idx, subject)
    for pi, part in enumerate(parts):
        for idx, s in enumerate(part.get("subjects", [])):
            flat.append((pi, idx, s))
    # ---- drop 04a slot-level pool entries (logged) ----
    kept, dropped_slots = [], []
    for pi, idx, s in flat:
        if is_slot_pool_entry(s):
            dropped_slots.append(f"{'abc'[pi]}{idx:02d}:{s.get('name','')[:40]}:{','.join(s.get('codes', []))}")
            continue
        kept.append((pi, idx, s))
    # ---- group by normalized name ----
    groups, order = {}, []
    for pi, idx, s in kept:
        k = norm_name(s.get("name", ""))
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append((pi, idx, s))
    subjects, log = [], []
    for k in order:
        g = groups[k]
        pref = sorted(g, key=lambda t: (truncated(t[2]), -content_size(t[2]), t[0], t[1]))
        win = json.loads(json.dumps(pref[0][2]))
        if truncated(win) and any(not truncated(t[2]) and content_size(t[2]) >= content_size(win) for t in pref[1:]):
            win["flags"] = [f for f in win.get("flags", []) if "TRUNCATED-AT" not in str(f).upper()]
        for pi, idx, other in pref[1:]:
            for kk, v in other.items():
                if kk in ("quirks", "flags"):
                    continue
                if kk == "units":
                    for un, uv in (v or {}).items():
                        if not (win.get("units") or {}).get(un):
                            win.setdefault("units", {})[un] = uv
                elif kk == "experiments":
                    if not win.get("experiments"):
                        win["experiments"] = v
                elif kk == "cos":
                    if not win.get("cos"):
                        win["cos"] = v
                elif (not win.get(kk)) and v:
                    win[kk] = v
        qset = []
        for t in pref:
            for q in t[2].get("quirks", []):
                if q not in qset:
                    qset.append(q)
        win["quirks"] = qset
        fset = [f for f in win.get("flags", []) if f]
        for t in pref[1:]:
            for f in t[2].get("flags", []):
                if f and f not in fset and not ("TRUNCATED-AT" in str(f).upper() and not truncated(win)):
                    fset.append(f)
        win["flags"] = fset
        if len(g) > 1:
            log.append({"kind": "DEDUPE", "name": k[:60],
                        "kept": "abc"[pref[0][0]], "from": "".join("abc"[t[0]] for t in pref[1:])})
        subjects.append(win)
    # ---- shared-code slot ownership: first printed variant owns the code ----
    code_variants = {}
    for i, s in enumerate(subjects):
        for c in s.get("codes", []):
            b = base_code(c)
            if b in POOL_CODES:
                code_variants.setdefault(b, []).append(i)
    for b, idxs in sorted(code_variants.items()):
        if len(idxs) < 2:
            continue
        owner = subjects[idxs[0]]
        owner.setdefault("quirks", []).append(
            f"elective slot {b}: printed code carries {len(idxs)} alternative subjects; "
            f"code ownership assigned to the first printed variant '{owner.get('name','')}' "
            f"(course-scoped G2 idempotency); alternatives recorded on their own rows")
        for i in idxs[1:]:
            s = subjects[i]
            s["code_note"] = (f"printed code {b} is the SHARED elective-slot code; "
                              f"this subject is a printed alternative under slot {b}; "
                              f"code owned by '{owner.get('name','')}' row (course-scoped G2); "
                              f"never merged per RULES §11")
            s["codes"] = []
            s.setdefault("flags", []).append(f"SHARED-CODE-ELECTIVE-VARIANT:{b}")
        log.append({"kind": "SLOT", "code": b, "variants": len(idxs),
                    "owner": owner.get("name", "")[:50]})
    # ---- non-pool code conflicts: same specific code, different names ----
    byc = {}
    for i, s in enumerate(subjects):
        for c in s.get("codes", []):
            b = base_code(c)
            if b not in POOL_CODES and re.fullmatch(r"[A-Z]{2,4}\d{3}[A-Z]?", b):
                byc.setdefault(b, set()).add(i)
    for b, idxs in sorted(byc.items()):
        if len(idxs) > 1:
            names = "; ".join(subjects[i].get("name", "")[:40] for i in sorted(idxs))
            log.append({"kind": "CODE-CONFLICT-CHECK", "code": b, "names": names})
    # ---- non_subject_rows ----
    nsr, seen = [], set()
    for part in parts:
        for r in part.get("non_subject_rows", []):
            kk = (r.get("kind", ""), r.get("print", ""))
            if kk not in seen:
                seen.add(kk)
                nsr.append(r)
    dq, df = [], []
    for part in parts:
        for q in part.get("quirks", []):
            if q not in dq:
                dq.append(q)
        for f in part.get("flags", []):
            if f not in df:
                df.append(f)
    merged.update({"subjects": subjects, "non_subject_rows": nsr,
                   "quirks": dq, "flags": df,
                   "merge_note": ("merged from 3 page-range partials 04a/04b/04c "
                                  "(single-agent context-deadline remedy); name-grouped dedupe; "
                                  "shared-code elective variants kept separate per RULES §11")})
    json.dump(merged, open(OUT, "w"), indent=1, ensure_ascii=False)
    print(f"MERGED|subjects={len(subjects)}|nsr={len(nsr)}")
    for d in dropped_slots:
        print(f"DROPPED_SLOT_ENTRY|{d}")
    for d in log:
        print(f"LOG|{json.dumps(d, ensure_ascii=False)}")
    allc = [base_code(c) for s in subjects for c in s.get("codes", [])]
    dupes = {c for c in allc if allc.count(c) > 1}
    print(f"CODE_DUPES|{sorted(dupes) if dupes else 'NONE'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
