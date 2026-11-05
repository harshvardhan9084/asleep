#!/usr/bin/env python3
"""mercury_engine.py — T2T drafting engine on the owner's InceptionLabs Mercury-3 API.

Owner directive (2026-11-05): shift ALL text-to-text load off the agent loop
onto 'mercury-3' (api.inceptionlabs.ai/v1, key in .env) — the diffusion LLM
runs 5-10x faster than speed-optimized frontier models, and per-subject
parallel extraction calls replace the slow subagent loop.

Usage:
  python3 mercury_engine.py <parsed_dir> <drafts_dir> <stem> [<stem> ...]

Per doc: (1) one inventory call lists every subject printed with a detailed
syllabus + every scheme-row-only slot; (2) parallel per-subject extraction
calls produce verbatim RULES §7 subject objects (incremental draft writes
after each subject — a lost call never loses extracted data); (3) a
self-containment check re-asks once for any unit below threshold, else records
the print-quirk evidence (RULES §6). Temperature clamped to the API's allowed
[0.5, 1] (0.5 = most deterministic the endpoint offers); json_mode on.
"""
import json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ENV = "/home/z/my-project/.env"
_cfg = {}
for line in open(ENV):
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        _cfg[k] = v
BASE = _cfg["MERCURY_BASE_URL"].rstrip("/")
KEY = _cfg["MERCURY_API_KEY"]
MODEL = _cfg.get("MERCURY_MODEL", "mercury-3")


def chat(messages, max_tokens=8000, temperature=0.5, json_mode=True, retries=5):
    body = {"model": MODEL, "messages": messages, "max_tokens": max_tokens,
            "temperature": temperature}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                BASE + "/chat/completions",
                data=json.dumps(body).encode(),
                headers={"Authorization": "Bearer " + KEY,
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=240) as r:
                out = json.loads(r.read())
            return json.loads(out["choices"][0]["message"]["content"])
        except urllib.error.HTTPError as e:
            err = e.read()[:200]
            last = f"HTTP {e.code}: {err!r}"
            if e.code == 429:  # rate-limited: back off hard, honor Retry-After
                wait = float(e.headers.get("Retry-After") or 0) or min(90, 15 * (attempt + 1))
                time.sleep(wait)
                continue
        except Exception as e:  # noqa: BLE001 — engine retries any transport error
            last = repr(e)[:200]
        if attempt < retries:
            time.sleep(min(60, 10 * (attempt + 1)))
    raise RuntimeError(f"mercury chat failed after {retries+1} attempts: {last}")


def norm_al(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def contained(needle, hay, w=60, step=30):
    """sliding-window containment approximating the verifier's check"""
    n = norm_al(needle)
    if not n:
        return 1.0
    h = norm_al(hay)
    if len(h) <= w:
        return 1.0 if n[:40] in h or h.find(n[: min(40, len(n))]) >= 0 else 0.0
    hit = [False] * len(n)
    for i in range(0, len(h) - w + 1, step):
        win = h[i:i + w]
        start = 0
        while True:
            j = n.find(win[:40], start)
            if j < 0:
                break
            for k in range(j, min(j + w, len(n))):
                hit[k] = True
            start = j + 1
            if start >= len(n):
                break
    return sum(hit) / len(n)


SYS = (
    "You are a precise archival extraction engine for an AKTU syllabus catalog. "
    "Extract VERBATIM text only — never invent, never paraphrase, never correct printed typos. "
    "Blank/absent prints stay blank. Record odd prints (broken tables, wrapped cells, stray glyphs) in 'quirks'. "
    "Answer with a single JSON object only."
)

INVENTORY = """Below is the text layer of AKTU syllabus PDF '%s' (session %s, course %s).
List EVERY subject this document prints. Two classes:
 - "detail": a subject whose detailed syllabus IS printed in this doc (units and/or COs/experiments/books) — give code_print (exactly as printed), name_print (exactly as printed), and page (the '===== PAGE N =====' number where its detail begins).
 - "scheme_only": a subject printed ONLY in a scheme/evaluation table row with NO detail page in this doc — same fields, page = the scheme page; if the code cell is a pool/slot print (e.g. 'BPE071 to BPE074', 'BOEP**') copy that whole print into code_print and set flag "slot_print": true.
Also set "doc_title_print" (verbatim first cover lines) and "ltp_note" if the scheme table header differs from L-T-P.
Return JSON: {"doc_title_print": "...", "subjects": [{"class":"detail","code_print":"...","name_print":"...","page":N}, ...]}"""

EXTRACT = """PDF text layer follows. Extract subject '%s' (code print '%s', detail from page %s onward, session %s, course %s).
Return ONE JSON object, RULES §7 shape:
{"name": "<canonical spelling of the printed name>", "name_print": "<verbatim>", "codes": ["<codes exactly as printed, spaces removed>"],
 "semester": <int or null>, "ltp": {"l":<int|null>,"t":<int|null>,"p":<int|null>}, "credit": <num|null>,
 "marks": {"sessional_ct":<int|null>,"sessional_ta":<int|null>,"sessional_total":<int|null>,"ese_te_pe":<int|null>,"total":<int|null>} or null,
 "subject_type": "<core|departmental-elective-<n>|open-elective|value-added|... as printed/category>",
 "units": {"1": "<VERBATIM unit-I text>", ...only units actually printed},
 "lectures_per_unit": <int|null>,
 "cos": [{"no":1,"text":"<verbatim>","kl":"<K-level if printed>"}],
 "textbooks": [{"no":1,"book":"<verbatim>"}], "reference_books": [{"no":1,"book":"<verbatim>"}],
 "experiments": [{"no":1,"exp":"<verbatim>"}],
 "objectives_print": ["<verbatim objective lines>"], "prerequisites": "<verbatim>",
 "quirks": ["<print oddities: broken glyphs, wrapped cells, stray numbering>"], "flags": []}
Rules: unit/CO/book text byte-verbatim (line breaks normalized to \\n); do NOT merge other subjects' content into this one; if the subject has no detail page here return {"scheme_row_only": true, "name_print": "...", "codes": [...], "semester": ..., "ltp": ..., "credit": ..., "marks": {...}, "quirks": ["scheme table row only; detailed syllabus not printed in this document"]}.
SUBJECT: '%s' | CODE: '%s'
=== PDF TEXT ===
%s"""


SCHEME_ONLY_BATCH = """PDF text layer follows. This AKTU syllabus doc (session %s, course %s) prints the following subjects ONLY as scheme/evaluation table rows (no detail pages): %s.
For EACH, return one object in the array: {"name_print": verbatim, "codes": [codes exactly as printed, spaces removed; a pool/slot print like 'BPE071 to BPE074' or 'BOEP**' stays ONE verbatim string], "semester": int or null, "ltp": {"l":..,"t":..,"p":..}, "credit": .. or null, "marks": {"sessional_ct":..,"sessional_ta":..,"sessional_total":..,"ese_te_pe":..,"total":..} or null, "subject_type": "as printed", "quirks": ["scheme table row only (p.N); detailed syllabus not printed in this document"]}.
Return JSON: {"rows": [ ... one per listed subject, same order ... ]}.
=== PDF TEXT ===
%s"""


def extract_scheme_batch(fulltext, session, course, subs):
    lst = "; ".join(f"{s.get('code_print','')} {s.get('name_print','')} (p.{s.get('page','?')})" for s in subs)
    out = chat([{"role": "system", "content": SYS},
                {"role": "user", "content": SCHEME_ONLY_BATCH % (session, course, lst, fulltext)}],
               max_tokens=8000)
    if isinstance(out, list):  # model sometimes returns the bare array
        out = {"rows": out}
    rows = out.get("rows") or []
    res = []
    for s, obj in zip(subs, rows + [None] * len(subs)):
        if not isinstance(obj, dict):
            obj = {"name_print": s.get("name_print", ""), "quirks": ["scheme-row extraction empty"]}
        obj["flags"] = list(dict.fromkeys((obj.get("flags") or []) + [
            "scheme_row_only_detailed_syllabus_not_printed"] +
            (["alternative_pair_row"] if s.get("slot_print") else [])))
        res.append((s.get("code_print", ""), obj))
    return res


def extract_one(pdf_name, fulltext, meta, sub, session, course):
    is_detail = sub.get("class") == "detail" and not sub.get("slot_print")
    prompt = EXTRACT % (sub.get("name_print", ""), sub.get("code_print", ""),
                        sub.get("page", "?"), session, course,
                        sub.get("name_print", ""), sub.get("code_print", ""), fulltext)
    out = chat([{"role": "system", "content": SYS},
                {"role": "user", "content": prompt}], max_tokens=8000)
    if out.get("scheme_row_only"):
        out.setdefault("flags", []).append("scheme_row_only_detailed_syllabus_not_printed")
        out.setdefault("quirks", []).append(
            "scheme table row only (p.%s): detailed syllabus not printed in this document "
            "(recorded B23/B25/B27 zero-GAP class — flagged subject candidate for the ladder)" % sub.get("page", "?"))
        if sub.get("slot_print"):
            out.setdefault("flags", []).append("alternative_pair_row")
    if is_detail:
        bad = []
        for uk, ut in (out.get("units") or {}).items():
            if ut and contained(ut, fulltext) < 0.85:
                bad.append(uk)
        if bad:
            fix = chat([{"role": "system", "content": SYS},
                        {"role": "user", "content":
                         "Units %s of subject '%s' failed verbatim containment against the PDF text "
                         "(you likely paraphrased or dropped fragments). Re-extract those units BYTE-VERBATIM "
                         "from the text below. Return the FULL corrected subject JSON object.\n%s"
                         % (",".join(bad), sub.get("name_print", ""), fulltext)}], max_tokens=8000)
            for uk in bad:
                if fix.get("units", {}).get(uk) and contained(fix["units"][uk], fulltext) >= 0.85:
                    out["units"][uk] = fix["units"][uk]
                else:
                    out.setdefault("flags", []).append("unit_containment_low_print_quirk")
                    out.setdefault("quirks", []).append(
                        "unit %s containment below threshold after one corrective re-extraction; text-layer "
                        "fragment likely garbled or off-page (RULES §6 — page image is authoritative); kept "
                        "as extracted, flagged for verify evidence" % uk)
    return sub.get("code_print", ""), out


def draft_doc(parsed_dir, drafts_dir, stem):
    rec = json.load(open(f"{parsed_dir}/{stem}.json"))
    meta = rec.get("meta", rec)
    pdf_name = meta.get("file", stem + ".pdf")
    pdf_rel = ""
    q = json.load(open("/home/z/my-project/work/pipeline_v2/queue.json"))
    for e in q["entries"]:
        if e["rel"].endswith("/" + os.path.basename(pdf_name)):
            pdf_rel = e["rel"]
            session = e.get("session", "")
            course = e.get("course", "BTech")
            break
    else:
        session, course = meta.get("session", ""), "BTech"
    fulltext = open(f"{parsed_dir}/{stem}.fulltext.txt").read()
    sha16 = meta.get("sha16", "")
    inv = chat([{"role": "system", "content": SYS},
                {"role": "user", "content": INVENTORY % (pdf_name, session, course) + "\n=== PDF TEXT ===\n" + fulltext}],
               max_tokens=6000)
    if isinstance(inv, list):  # model sometimes returns the bare array
        inv = {"subjects": inv}
    subs = inv.get("subjects", []) or []
    print(f"INVENTORY|{stem}|{len(subs)} subjects (detail {sum(1 for s in subs if s.get('class')=='detail')}, "
          f"scheme_only {sum(1 for s in subs if s.get('class')!='detail')})")
    draft = {"pdf_rel": pdf_rel, "session": session, "course": course, "sha16": sha16,
             "stem": stem, "subjects": [], "non_subject_rows": [],
             "quirks": [f"doc_title_print: {inv.get('doc_title_print','')}"] if inv.get("doc_title_print") else [],
             "flags": []}
    OUT = f"{drafts_dir}/{stem}.draft.json"

    def save():
        json.dump(draft, open(OUT, "w"), indent=1, ensure_ascii=False)

    save()
    # scheme-only rows: ONE consolidated call (tiny table rows; fewer API calls)
    scheme_subs = [s for s in subs if s.get("class") != "detail"]
    detail_subs = [s for s in subs if s.get("class") == "detail"]
    results = []
    if scheme_subs:
        try:
            results.extend(extract_scheme_batch(fulltext, session, course, scheme_subs))
        except Exception as e:  # noqa: BLE001
            draft.setdefault("flags", []).append(f"scheme_batch_failed:{repr(e)[:80]}")
            for s in scheme_subs:
                draft["subjects"].append({"name": s.get("name_print", ""), "name_print": s.get("name_print", ""),
                                          "codes": [re.sub(r"[^A-Za-z0-9*]", "", s.get("code_print", ""))],
                                          "flags": ["extraction_failed_scheme_batch"], "quirks": [], "units": {}})
            save()
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = {ex.submit(extract_one, pdf_name, fulltext, meta, s, session, course): s for s in detail_subs}
        for fut in as_completed(futs):
            s = futs[fut]
            try:
                results.append(fut.result())
            except Exception as e:  # noqa: BLE001 — record and continue; verify will catch gaps
                draft.setdefault("flags", []).append(
                    f"extraction_failed:{s.get('code_print','?')}:{repr(e)[:80]}")
                save()
                print(f"FAIL|{stem}|{s.get('code_print','?')}|{repr(e)[:80]}")
                continue
    for code, obj in results:
        obj.setdefault("name", obj.get("name_print", ""))
        obj.setdefault("name_print", obj.get("name_print", ""))
        obj.setdefault("codes", [re.sub(r"[^A-Za-z0-9*]", "", c) for c in [code] if c])
        obj.setdefault("quirks", [])
        obj.setdefault("flags", [])
        draft["subjects"].append(obj)
        save()  # incremental append after EVERY subject (RULES §7)
        print(f"SUBJ|{stem}|{code}|{obj.get('name','')[:40]}|units={len(obj.get('units') or {})}")
    draft["subjects"].sort(key=lambda o: (o.get("codes") or [""])[0])
    save()
    print(f"DRAFT|{stem}|{len(draft['subjects'])} subjects -> {OUT}")


if __name__ == "__main__":
    parsed_dir, drafts_dir = sys.argv[1], sys.argv[2]
    for stem in sys.argv[3:]:
        draft_doc(parsed_dir, drafts_dir, stem)
