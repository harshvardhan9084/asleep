#!/usr/bin/env python3
"""b48_repairs.py — recorded-class repairs for B48 drafts (B43/B44/B46/B47 classes):
 1. codeless Elective slot rows -> non_subject_rows with verbatim print (B47 doc-04/09 class)
 2. empty-name rows restored from the hand-built inventory's verbatim name_print
    (print-anchored restore, B47 class)
 3. REX: truly-empty rows (no units AND no experiments AND no cos AND no books)
    re-extracted from their detail-page slices (B44 16-REX class; engine
    extract_one = extract + containment self-check)
Run AFTER b48_draft_resume.py rounds complete. Idempotent: repaired rows are
flagged b48_repair_* and skipped on re-run.
"""
import json, os, re, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as E

PARSED = "/home/z/my-project/work/pipeline_v2/parsed"
DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"
INVD = "/home/z/my-project/work/pipeline_v2/inv"

STEMS = [
    "01_mca_y2_syllabus_2025-26",
    "02_mca_y3_syllabus_2010-11",
    "03_mca_y3_syllabus_2015-16",
    "04_mca_y3_syllabus_2018-19",
    "05_mca_y5_syllabus_2021-22",
    "06_bpharm_syllabus",
    "07_bpharm_y3_scheme-syllabus-cbcs-rev",
    "08_bpharm_y4_syllabus",
    "09_btech_ae_y4_syllabus_2016-17",
    "10_btech_ag_syllabus",
]


def load(stem):
    return json.load(open(f"{DRAFTS}/{stem}.draft.json"))


def save(d):
    json.dump(d, open(f"{DRAFTS}/{d['stem']}.draft.json", "w"), indent=1, ensure_ascii=False)


def pages_of(stem):
    t = open(f"{PARSED}/{stem}.fulltext.txt", encoding="utf-8").read()
    parts = re.split(r"===== PAGE (\d+) =====", t)
    P = {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}
    return P


def inv_entries(stem):
    try:
        return [s for s in json.load(open(f"{INVD}/{stem}.inv.json")) if isinstance(s, dict)]
    except Exception:
        return []


def skey(c):
    return re.sub(r"[^A-Za-z0-9]", "", c or "").upper()


def is_blank_content(s):
    return (not (s.get("units") or {})) and (not (s.get("experiments") or [])) \
        and (not (s.get("cos") or [])) and (not (s.get("textbooks") or [])) \
        and (not (s.get("reference_books") or []))


def main():
    only = sys.argv[1:] or STEMS
    stats = {"slots_moved": 0, "names_restored": 0, "rex_ok": 0, "rex_still_blank": 0}
    for stem in only:
        d = load(stem)
        changed = False
        inv = inv_entries(stem)
        P = pages_of(stem)
        # --- 1. codeless elective slot rows -> non_subject_rows (doc 01 class) ---
        keep = []
        for s in d["subjects"]:
            codes = s.get("codes") or []
            nm = (s.get("name") or s.get("name_print") or "").strip()
            if not codes and re.match(r"(?i)^elective\b", nm) and not any(
                    "b48_repair_slot_moved" in str(f) for f in (s.get("flags") or [])):
                d.setdefault("non_subject_rows", []).append({
                    "kind": "elective_slot_codeless",
                    "print": nm,
                    "locator": f"scheme p.2 ({nm}; no codes printed; pool members not itemized in-doc)"})
                s2 = dict(s)
                s2["flags"] = list(dict.fromkeys((s.get("flags") or []) + ["b48_repair_slot_moved"]))
                stats["slots_moved"] += 1
                changed = True
                continue
            keep.append(s)
        d["subjects"] = keep
        # --- 2 + 3. name restoration + REX ---
        for s in d["subjects"]:
            codes = [skey(c) for c in (s.get("codes") or [])]
            ie = next((e for e in inv if skey(e.get("code_print", "")) in codes
                       and skey(e.get("code_print", ""))), None)
            if (s.get("name") or "").strip() == "" or (s.get("name_print") or "").strip() == "":
                np = (ie or {}).get("name_print", "") if ie else ""
                if np:
                    if not (s.get("name_print") or "").strip():
                        s["name_print"] = np
                    if not (s.get("name") or "").strip():
                        s["name"] = np
                    s["quirks"] = list(dict.fromkeys((s.get("quirks") or []) + [
                        "name restored verbatim from the document's own scheme/detail print (b48 print-anchored class)"]))
                    s["flags"] = list(dict.fromkeys((s.get("flags") or []) + ["b48_repair_name_restored"]))
                    stats["names_restored"] += 1
                    changed = True
            if is_blank_content(s) and not any(str(f).startswith("b48_repair_rex") for f in (s.get("flags") or [])) \
                    and not any("scheme_row_only" in str(f) for f in (s.get("flags") or [])):
                pg = (ie or {}).get("page")
                if not pg:
                    continue
                nxt = next((q for q in sorted(P) if q > int(pg)), max(P) + 1)
                slice_txt = "\n\n".join(P[p] for p in sorted(P) if int(pg) <= p < nxt)
                sub = {"class": "detail", "code_print": (s.get("codes") or [""])[0],
                       "name_print": s.get("name_print") or s.get("name") or "", "page": pg}
                try:
                    _, obj = E.extract_one(stem, slice_txt, {}, sub,
                                           d.get("session", ""), d.get("course", ""))
                    got = False
                    for f in ("units", "experiments", "cos", "textbooks", "reference_books"):
                        v = obj.get(f)
                        if isinstance(v, dict) and v:
                            s[f] = v; got = True
                        elif isinstance(v, list) and v:
                            s[f] = v; got = True
                    if got:
                        s.setdefault("quirks", []).append(
                            f"re-extracted from detail-page slice p.{pg} after a blank first pass (b48 REX class)")
                        s["flags"] = list(dict.fromkeys((s.get("flags") or []) + ["b48_repair_rex_ok"]))
                        if not (s.get("name") or "").strip() and obj.get("name"):
                            s["name"] = obj["name"]
                        if not (s.get("name_print") or "").strip() and obj.get("name_print"):
                            s["name_print"] = obj["name_print"]
                        stats["rex_ok"] += 1
                    else:
                        s["flags"] = list(dict.fromkeys((s.get("flags") or []) + [
                            "b48_repair_rex_still_blank"]))
                        s.setdefault("quirks", []).append(
                            f"detail-page slice p.{pg} re-extraction returned no unit/CO/experiment/book "
                            "content; print may be a header-only or training row (page image authoritative; "
                            "RULES §6 evidence class)")
                        stats["rex_still_blank"] += 1
                    changed = True
                except Exception as e:  # noqa: BLE001
                    s["flags"] = list(dict.fromkeys((s.get("flags") or []) + [
                        f"b48_repair_rex_failed:{repr(e)[:80]}"]))
                    changed = True
        if changed:
            save(d)
        print(f"REPAIR|{stem}|slots_moved+={stats['slots_moved']} names+={stats['names_restored']} "
              f"rex_ok+={stats['rex_ok']} rex_blank+={stats['rex_still_blank']}", flush=True)
    print("STATS|", stats)


def cleanup():
    """relabel rows mislabeled by the first repair pass: rows carrying BOTH
    b48_repair_rex_still_blank and the engine's scheme_row_only flag are
    legitimate scheme-row-only subjects (zero-GAP class) — drop the wrong flag
    and the speculative quirk, keep the scheme_row_only evidence."""
    n = 0
    for stem in STEMS:
        try:
            d = load(stem)
        except Exception:
            continue
        ch = False
        for s in d["subjects"]:
            fl = [str(f) for f in (s.get("flags") or [])]
            if "b48_repair_rex_still_blank" in fl and any("scheme_row_only" in f for f in fl):
                s["flags"] = [f for f in s["flags"] if f != "b48_repair_rex_still_blank"]
                s["quirks"] = [q for q in (s.get("quirks") or [])
                               if not str(q).startswith("detail-page slice")]
                n += 1
                ch = True
        if ch:
            save(d)
    print(f"CLEANUP|relabeled {n} scheme-row-only rows")


if __name__ == "__main__":
    if "--cleanup" in sys.argv:
        cleanup()
    else:
        main()
