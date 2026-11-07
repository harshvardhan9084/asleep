#!/usr/bin/env python3
"""b48_draft_resume.py — resumable engine drafting for sandbox-recycled sessions.

The sandbox reaps background processes between tool calls, so long extractions
must run FOREGROUND in bounded rounds. This wrapper reuses mercury_engine's
chat/inventory/extract functions but adds DRAFT RESUME: existing subjects
(matched by normalized first code, falling back to name) are never re-extracted;
only missing subjects are submitted (2 workers). The draft is re-saved
incrementally after every subject (RULES §7). The inv cache (validated in
b47_inv_all.py) is always honored.

Usage: python3 b48_draft_resume.py <stem> [<stem> ...]
"""
import json, os, re, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
from concurrent.futures import ThreadPoolExecutor, as_completed
import mercury_engine as E

PARSED = "/home/z/my-project/work/pipeline_v2/parsed"
DRAFTS = "/home/z/my-project/work/pipeline_v2/drafts"
INVD = "/home/z/my-project/work/pipeline_v2/inv"


def norm_code(c):
    return re.sub(r"[^A-Za-z0-9*]", "", c or "").upper()


def subj_key(obj):
    codes = [norm_code(c) for c in (obj.get("codes") or [])]
    if codes and codes[0]:
        return codes[0]
    return "N:" + re.sub(r"\W+", "", (obj.get("name") or obj.get("name_print") or "")).upper()


def draft_doc_resume(stem):
    rec = json.load(open(f"{PARSED}/{stem}.json"))
    meta = rec.get("meta", rec)
    pdf_name = meta.get("file", stem + ".pdf")
    q = json.load(open("/home/z/my-project/work/pipeline_v2/queue.json"))
    pdf_rel, session, course = "", meta.get("session", ""), "BTech"
    qe = E.queue_meta_for(stem, {"pdf_path": pdf_name})
    if qe:
        pdf_rel = qe["rel"]
        session = qe.get("session", "") or session
        course = qe.get("course", "") or course
    else:
        for e in q["entries"]:
            if os.path.basename(e["rel"]) in (os.path.basename(pdf_name), stem + ".pdf",
                                              re.sub(r"^\d+_", "", stem) + ".pdf"):
                pdf_rel, session, course = e["rel"], e.get("session", ""), e.get("course", "BTech")
                break
    fulltext = open(f"{PARSED}/{stem}.fulltext.txt", encoding="utf-8").read()
    PAGES = E.pages_of(fulltext)
    sha16 = meta.get("sha16", "")
    INVP = f"{INVD}/{stem}.inv.json"
    subs = json.load(open(INVP))  # validated inventory (cache must exist)
    OUT = f"{DRAFTS}/{stem}.draft.json"

    draft = None
    if os.path.exists(OUT):
        try:
            draft = json.load(open(OUT))
        except Exception:
            draft = None
    if not isinstance(draft, dict) or "subjects" not in draft:
        draft = {"pdf_rel": pdf_rel, "session": session, "course": course, "sha16": sha16,
                 "stem": stem, "subjects": [], "non_subject_rows": [], "quirks": [], "flags": []}
    draft.update({"pdf_rel": pdf_rel, "session": session, "course": course,
                  "sha16": sha16, "stem": stem})
    have = {subj_key(o) for o in draft["subjects"]}

    def save():
        json.dump(draft, open(OUT, "w"), indent=1, ensure_ascii=False)

    save()
    detail_subs = [s for s in subs if s.get("class") == "detail"]
    scheme_subs = [s for s in subs if s.get("class") != "detail"]
    todo_detail = []
    for s in detail_subs:
        k = "N:" + re.sub(r"\W+", "", s.get("name_print", "")).upper()
        k = norm_code(s.get("code_print", "")) or k
        if k not in have:
            todo_detail.append(s)
    todo_scheme = [s for s in scheme_subs
                   if (norm_code(s.get("code_print", "")) or "N:" + re.sub(r"\W+", "", s.get("name_print", "")).upper()) not in have]
    print(f"RESUME|{stem}|have={len(draft['subjects'])} todo_detail={len(todo_detail)} "
          f"todo_scheme={len(todo_scheme)}", flush=True)

    # scheme-only rows: ONE consolidated call (only if some are missing)
    if todo_scheme:
        try:
            all_scheme = scheme_subs  # batch call needs the full list context
            results = E.extract_scheme_batch(fulltext, session, course, all_scheme)
            for code, obj in results:
                k = norm_code(code) or "N:" + re.sub(r"\W+", "", obj.get("name_print", "")).upper()
                if k in have:
                    continue
                obj.setdefault("name", obj.get("name_print", ""))
                obj.setdefault("codes", [norm_code(code)] if code else [])
                obj.setdefault("quirks", [])
                obj.setdefault("flags", [])
                draft["subjects"].append(obj)
                have.add(k)
                save()
                print(f"SUBJ|{stem}|{code}|{obj.get('name', '')[:40]}|scheme", flush=True)
        except Exception as e:  # noqa: BLE001
            draft.setdefault("flags", []).append(f"scheme_batch_failed:{repr(e)[:80]}")
            save()

    if todo_detail:
        with ThreadPoolExecutor(max_workers=2) as ex:
            futs = {ex.submit(E.extract_one, pdf_name, fulltext, meta, s, session, course): s
                    for s in todo_detail}
            for fut in as_completed(futs):
                s = futs[fut]
                code = s.get("code_print", "?")
                try:
                    _, obj = fut.result()
                except Exception as e:  # noqa: BLE001 — record and continue; verify catches gaps
                    draft.setdefault("flags", []).append(
                        f"extraction_failed:{code}:{repr(e)[:120]}")
                    save()
                    print(f"FAIL|{stem}|{code}|{repr(e)[:100]}", flush=True)
                    continue
                obj.setdefault("name", obj.get("name_print", ""))
                obj.setdefault("codes", [norm_code(code)] if code else [])
                obj.setdefault("quirks", [])
                obj.setdefault("flags", [])
                k = norm_code(code) or "N:" + re.sub(r"\W+", "", obj.get("name", "")).upper()
                if k in have:  # completed in an earlier round of the same run
                    continue
                draft["subjects"].append(obj)
                have.add(k)
                save()
                print(f"SUBJ|{stem}|{code}|{obj.get('name', '')[:40]}|units={len(obj.get('units') or {})}", flush=True)
    draft["subjects"].sort(key=lambda o: (o.get("codes") or [""])[0])
    save()
    print(f"DRAFT|{stem}|{len(draft['subjects'])} subjects -> {OUT}", flush=True)


if __name__ == "__main__":
    for stem in sys.argv[1:]:
        draft_doc_resume(stem)
