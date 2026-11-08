#!/usr/bin/env python3
"""w8b_kls_apply.py — W8b phase 2: apply OCR/text-evidence K-sequence backfills
(probe results from w8b_kls_ocr.py checkpoint) + auditor upgrade for the rest.

Zero-guess disposition of the 519 KLS raster-candidate leftovers:
  - sequence_found (2 rows): co_kls filled with the verbatim printed K column
    (multi-level prints joined 'Ka/Kb' per catalog convention; title-affinity
    >=2 subject tokens required for compendium attribution). RULES §6b writes.
  - no_clean_sequence (498 rows): probe-confirmed — no recoverable printed K
    sequence in the cited docs (text-layer pages read directly + raster pages
    OCR'd). NO data change; auditor upgrade reclassifies the flag from
    'fix:W3' to 'needs_review' with the probe evidence in the detail.
  - sha_unresolved (19 rows): cited doc missing locally after workspace
    resets (3 distinct shas). NO data change; flag -> needs_review with
    re-supply note (documented G6-gap-adjacent class).
Gates G1/G2/G3/G6 must PASS before commit; push handled by the caller."""
import json
import sys

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

rows = WC.load_rows()
by_id = {r["subject_id"]: i for i, r in enumerate(rows)}
ck = json.load(open(f"{WC.BASE}/w8b_ocr_ckpt.json"))
results = ck["results"]

pre_rows = {r["subject_id"]: dict(r) for r in rows}
touched = set()
edits_by_sid = {}


def corrections_append(r, entry):
    cj = r.get("corrections_json", "") or ""
    try:
        arr = json.loads(cj) if cj.strip() else []
    except Exception:
        arr = []
    arr.append(entry)
    r["corrections_json"] = json.dumps(arr, ensure_ascii=False)


def qf_tag(r, tag):
    qf = r.get("quality_flags", "") or ""
    tags = [t for t in qf.split(";") if t]
    if tag not in tags:
        tags.append(tag)
    r["quality_flags"] = ";".join(tags)


def note_seg(r, seg):
    if seg not in (r.get("change_note_vs_previous", "") or ""):
        prev = r.get("change_note_vs_previous", "") or ""
        r["change_note_vs_previous"] = (prev + "; " if prev else "") + seg


n_apply = 0
for sid, res in results.items():
    if res.get("status") != "sequence_found":
        continue
    r = rows[by_id[sid]]
    before = (r.get("co_kls", "") or "").strip()
    new_json = json.dumps(res["kls"], ensure_ascii=False)
    if before == new_json:
        continue  # already applied (idempotent re-run)
    if before:
        # KLS_SHORT/partial already present: only fill nulls, conflict => skip.
        # A NON-JSON legacy string is invalid by definition (auditor flags it
        # precisely because it is not a K-list) — replace it, before preserved.
        try:
            cur = json.loads(before)
        except Exception:
            r["co_kls"] = new_json
            corrections_append(r, {"field": "co_kls", "before": before[:400],
                                   "after": new_json, "rule": "W3/KLS_OCR_EVIDENCE",
                                   "evidence": res["evidence"] + "; replaced invalid "
                                               "non-JSON legacy value (preserved verbatim)",
                                   "wave": "W8b"})
            qf_tag(r, "corrected_KLS_OCR_EVIDENCE")
            note_seg(r, "W8b §6b replace (invalid legacy co_kls string -> printed K column; "
                        "before preserved in corrections_json)")
            touched.add(sid)
            edits_by_sid[sid] = edits_by_sid.get(sid, 0) + 1
            n_apply += 1
            print(f"W8B-APPLY|replace_invalid|{sid}")
            continue
        new = []
        conflict = False
        for j, v in enumerate(res["kls"]):
            old = cur[j] if j < len(cur) else None
            if old is None:
                new.append(v)
            elif old != v:
                conflict = True
                break
            else:
                new.append(old)
        if conflict or len(cur) > len(res["kls"]):
            print(f"W8B-APPLY|skip_conflict|{sid}")
            continue
        res = dict(res, kls=new)
    r["co_kls"] = new_json
    corrections_append(r, {"field": "co_kls", "before": before or "(empty)",
                           "after": r["co_kls"], "rule": "W3/KLS_OCR_EVIDENCE",
                           "evidence": res["evidence"], "wave": "W8b"})
    qf_tag(r, "corrected_KLS_OCR_EVIDENCE")
    note_seg(r, "W8b §6b fill (co_kls from printed CO/K column of cited doc; "
                "probe evidence in corrections_json)")
    touched.add(sid)
    edits_by_sid[sid] = edits_by_sid.get(sid, 0) + 1
    n_apply += 1

print(f"W8B-APPLY|applied={n_apply} touched={len(touched)}")

# --- auditor upgrade (zero data change): reclassify the probe-confirmed rows --
flags_doc = json.load(open(WC.AUDIT_FLAGS))
n_rec = n_unres = 0
for sid, fl in flags_doc.get("rows", {}).items():
    res = results.get(sid)
    if not res:
        continue
    for f in fl:
        if f.get("rule") in ("KLS_MISSING", "KLS_SHORT") and f.get("action", "").startswith("fix:"):
            if res["status"] == "no_clean_sequence":
                f["action"] = "needs_review"
                f["detail"] = (f"{f['detail']} | W8b probe: no recoverable printed K sequence in cited docs "
                               f"({res.get('pages_probed', 0)} pages: text-layer + OCR raster)")
                n_rec += 1
            elif res["status"] == "sha_unresolved":
                f["action"] = "needs_review"
                f["detail"] = (f"{f['detail']} | W8b probe: cited doc sha not locally resolvable "
                               f"post-workspace-reset — re-supply PDF to resume evidence read")
                n_unres += 1
flags_doc["w8b_probe"] = {
    "applied": n_apply,
    "probed_no_print": sum(1 for r_ in results.values() if r_.get("status") == "no_clean_sequence"),
    "doc_unresolved": sum(1 for r_ in results.values() if r_.get("status") == "sha_unresolved"),
    "total": len(results)}
json.dump(flags_doc, open(WC.AUDIT_FLAGS, "w"), indent=1, ensure_ascii=False)
print(f"W8B-APPLY|flags_reclassified|probed_no_print={n_rec} doc_unresolved={n_unres}")

# --- gates + commit -----------------------------------------------------------
def run_and_maybe_defer(rows, touched, pre_rows):
    gates = WC.run_gates(rows, touched, pre_rows)
    deferred = []
    if gates["g6"]:
        for part in gates["g6"].split(";"):
            sid = part.split(":")[0].strip()
            if sid in touched:
                deferred.append(sid)
        for sid in deferred:
            rows[rows.index(next(r for r in rows if r["subject_id"] == sid))] = dict(pre_rows[sid])
            touched.discard(sid)
        if deferred:
            print(f"W8B-APPLY|g6_gap_deferred={len(deferred)}: {', '.join(deferred)}")
            gates = WC.run_gates(rows, touched, pre_rows)
    return gates, deferred


gates, deferred = run_and_maybe_defer(rows, touched, pre_rows)
print(f"G1|{'PASS' if not gates['g1'] else 'FAIL ' + gates['g1']}")
print(f"G2|{'PASS' if not gates['g2'] else 'FAIL ' + gates['g2']}|codes={gates['g2_codes']}")
print(f"G3|{'PASS' if not gates['g3'] else 'FAIL ' + gates['g3']}")
print(f"G6|{'PASS' if not gates['g6'] else 'FAIL ' + gates['g6']}|checks={gates['g6_checks']}|pre_edit_hits={gates['g6_pre_edit_hits']}")
if any([gates["g1"], gates["g2"], gates["g3"], gates["g6"]]):
    print("ABORT: gate failure")
    sys.exit(2)
applied = sum(edits_by_sid.get(s, 0) for s in touched)
WC.commit(rows, "W8b", applied, gates,
          {"kls_applied": n_apply, "probed_no_print": n_rec,
           "doc_unresolved": n_unres, "probe_total": len(results),
           "g6_gap_deferred": deferred})
print("W8B-APPLY|COMMIT_OK")
