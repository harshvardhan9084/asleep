#!/usr/bin/env python3
"""b37_resume.py — resume an in-progress Mercury-drafted doc (in-flight batch
class, recorded B26): re-inventory once, extract only subjects whose codes are
missing from the durable draft (detail = per-subject calls; scheme_only = one
consolidated batch call), append incrementally. Usage:
  python3 b37_resume.py <stem>"""
import json, os, re, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as me

stem = sys.argv[1]
parsed_dir = "/home/z/my-project/work/pipeline_v2/parsed"
drafts_dir = "/home/z/my-project/work/pipeline_v2/drafts"
rec = json.load(open(f"{parsed_dir}/{stem}.json"))
meta = rec.get("meta", rec)
pdf_name = meta.get("file", stem + ".pdf")
fulltext = open(f"{parsed_dir}/{stem}.fulltext.txt").read()
PAGES = me.pages_of(fulltext)
q = json.load(open("/home/z/my-project/work/pipeline_v2/queue.json"))
session = course = ""
for e in q["entries"]:
    if e["rel"].endswith("/" + os.path.basename(pdf_name)):
        pdf_rel, session, course = e["rel"], e.get("session", ""), e.get("course", "BTech")
        break
else:
    pdf_rel, session, course = "", meta.get("session", ""), "BTech"

P = f"{drafts_dir}/{stem}.draft.json"
if os.path.exists(P):
    draft = json.load(open(P))
else:
    draft = {"pdf_rel": pdf_rel, "session": session, "course": course,
             "sha16": meta.get("sha16", ""), "stem": stem, "subjects": [],
             "non_subject_rows": [], "quirks": [], "flags": []}

def have(codes):
    return {re.sub(r"[^A-Z0-9]", "", (c or "").upper()) for s in draft["subjects"] for c in (s.get("codes") or [])}

inv = me.chat([{"role": "system", "content": me.SYS},
               {"role": "user", "content": me.INVENTORY % (pdf_name, session, course) + "\n=== PDF TEXT ===\n" + fulltext}],
              max_tokens=8000)
if isinstance(inv, list):
    inv = {"subjects": inv}
subs = inv.get("subjects", []) or []
have_set = have(None)
missing_detail = [s for s in subs if s.get("class") == "detail"
                  and not any(re.sub(r"[^A-Z0-9]", "", (s.get("code_print") or "").upper()) in h or h in re.sub(r"[^A-Z0-9]", "", (s.get("code_print") or "").upper())
                              for h in have_set) if s.get("code_print")]
missing_scheme = [s for s in subs if s.get("class") != "detail"]
print(f"inventory {len(subs)}; missing detail {len(missing_detail)}; missing scheme {len(missing_scheme)}")

def save():
    json.dump(draft, open(P, "w"), indent=1, ensure_ascii=False)

save()
if missing_scheme:
    try:
        for code, obj in me.extract_scheme_batch(fulltext, session, course, missing_scheme):
            obj.setdefault("name", obj.get("name_print", ""))
            obj.setdefault("codes", [re.sub(r"[^A-Za-z0-9*]", "", code)] if code else [])
            obj.setdefault("quirks", []); obj.setdefault("flags", [])
            draft["subjects"].append(obj)
        save()
        print(f"scheme batch appended ({len(missing_scheme)} rows)")
    except Exception as e:
        print("scheme batch FAILED:", repr(e)[:120])

det_pages = sorted({me.safe_pg(s.get("page")) for s in missing_detail if me.safe_pg(s.get("page"))})
def slice_for(s):
    p = me.safe_pg(s.get("page"))
    if not p:
        return fulltext
    nxt = next((q2 for q2 in det_pages if q2 > p), None)
    return "\n\n".join(t for pp, t in PAGES if pp >= p and (nxt is None or pp < nxt))

for s in missing_detail:
    try:
        code, obj = me.extract_one(pdf_name, slice_for(s), meta, s, session, course)
        obj.setdefault("name", obj.get("name_print", ""))
        obj.setdefault("codes", [re.sub(r"[^A-Za-z0-9*]", "", c) for c in [code] if c])
        obj.setdefault("quirks", []); obj.setdefault("flags", [])
        draft["subjects"].append(obj)
        save()
        print("SUBJ", code, obj.get("name", "")[:40], "units:", len(obj.get("units") or {}))
    except Exception as e:
        draft.setdefault("flags", []).append(f"extraction_failed:{s.get('code_print','?')}:{repr(e)[:100]}")
        save()
        print("FAIL", s.get("code_print"), repr(e)[:100])
print("DRAFT", stem, len(draft["subjects"]), "subjects ->", P)
