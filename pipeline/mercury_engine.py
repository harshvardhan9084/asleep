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
MODEL = _cfg.get("MERCURY_MODEL", "mercury-3")


def _key_pool():
    """Owner 5-key pool (2026-11-06): rotate every call; crying keys rest, never die."""
    keys = []
    for i in range(1, 6):
        k = (_cfg.get("INCEPTIONLABS_API_KEY" if i == 1 else "INCEPTIONLABS_API_KEY_%d" % i) or "").strip()
        if k and not k.upper().startswith("PENDING"):
            keys.append(k)
    if not keys:
        k = (_cfg.get("MERCURY_API_KEY") or "").strip()
        if k:
            keys.append(k)
    return keys


KEYS = _key_pool()
REST_S = float(_cfg.get("INCEPTIONLABS_COOLDOWN_SECONDS", "") or 300)
STATS = "/home/z/my-project/work/pipeline_v2/mercury_stats.json"
import fcntl as _fcntl
import threading as _threading
_TL = _threading.Lock()
_ROT = {"i": 0}
_CD = {}


def _stats(fn):
    """Cross-process-safe stats merge (flock) — same file mercury_call.py uses."""
    os.makedirs(os.path.dirname(STATS), exist_ok=True)
    with _TL:
        with open(STATS + ".lock", "a") as lf:
            _fcntl.flock(lf, _fcntl.LOCK_EX)
            try:
                st = json.load(open(STATS))
            except Exception:
                st = {"totals": {}, "per_key": {}}
            st.setdefault("totals", {})
            st.setdefault("per_key", {})
            r = fn(st)
            st["keys_active"] = len(KEYS)
            json.dump(st, open(STATS, "w"), indent=1, sort_keys=True)
            _fcntl.flock(lf, _fcntl.LOCK_UN)
    return r


def _bump(st, klabel, field, rest=False):
    pk = st["per_key"].setdefault(klabel, {})
    pk["calls"] = pk.get("calls", 0) + 1
    pk[field] = pk.get(field, 0) + 1
    st["totals"][field] = st["totals"].get(field, 0) + 1
    if rest:
        pk["cooldown_until"] = time.time() + REST_S
        pk["cooldown_count"] = pk.get("cooldown_count", 0) + 1


def chat(messages, max_tokens=8000, temperature=0.5, json_mode=True, retries=8):
    body = {"model": MODEL, "messages": messages, "max_tokens": max_tokens,
            "temperature": temperature}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    last = None
    for attempt in range(retries + 1):
        now = time.time()

        def _pick(st):
            for i in range(len(KEYS)):
                cd = float(st["per_key"].get(str(i + 1), {}).get("cooldown_until", 0) or 0)
                if cd > now:
                    _CD[i] = max(_CD.get(i, 0), cd)
            elig = [i for i in range(len(KEYS)) if _CD.get(i, 0) <= now]
            if not elig:
                return -1
            i = elig[_ROT["i"] % len(elig)]
            _ROT["i"] += 1
            return i

        i = _stats(_pick)
        if i < 0:  # every key resting — let them rest (owner directive), then retry
            wake = min(_CD.values()) if _CD else now + REST_S
            last = "all %d keys resting" % len(KEYS)
            time.sleep(max(5, min(60, wake - time.time())))
            continue
        klabel = str(i + 1)
        try:
            req = urllib.request.Request(
                BASE + "/chat/completions",
                data=json.dumps(body).encode(),
                headers={"Authorization": "Bearer " + KEYS[i],
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=240) as r:
                out = json.loads(r.read())
            msg = out["choices"][0]["message"]
            fr = out["choices"][0].get("finish_reason")
            if msg.get("content") is None:
                last = f"empty content (key {klabel}, finish_reason={fr})"
                _stats(lambda st: _bump(st, klabel, "empty", rest=True))
                _CD[i] = time.time() + REST_S
                if fr == "length":
                    body["max_tokens"] = min(60000, int(body["max_tokens"] * 2))
                time.sleep(3)
                continue
            _stats(lambda st: _bump(st, klabel, "ok"))
            return json.loads(msg["content"])
        except urllib.error.HTTPError as e:
            err = e.read()[:200]
            last = f"HTTP {e.code} (key {klabel}): {err!r}"
            if e.code in (429, 402) or e.code >= 500:
                _stats(lambda st, code=e.code: _bump(
                    st, klabel, "http_429" if code == 429 else "key_fail", rest=True))
                _CD[i] = time.time() + REST_S
                if e.code == 429:  # honor Retry-After, then rotate to the next key
                    time.sleep(float(e.headers.get("Retry-After") or 0) or min(20, 4 * (attempt + 1)))
                    continue
                time.sleep(2)
                continue
            _stats(lambda st: _bump(st, klabel, "key_fail"))
            if e.code in (401, 403):  # auth rejected: rest this key too
                _CD[i] = time.time() + REST_S
        except Exception as e:  # noqa: BLE001 — engine retries any transport error
            last = repr(e)[:200] + f" (key {klabel})"
            _stats(lambda st: _bump(st, klabel, "network_fail"))
        if attempt < retries:
            time.sleep(min(30, 4 * (attempt + 1)))
    raise RuntimeError(f"mercury chat failed after {retries+1} attempts: {last}")


def fulltext_of(pages):
    return "\n\n".join(t for _, t in pages)


def norm_al(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())




def safe_pg(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0


def pages_of(fulltext):
    """split the dumped fulltext into (page_no, text) pairs"""
    parts = re.split(r"===== PAGE (\d+) =====", fulltext)
    out = []
    for i in range(1, len(parts) - 1, 2):
        out.append((int(parts[i]), parts[i + 1]))
    return out


def slice_pages(pages, p_from, p_to):
    lo = min(p for p, _ in pages) if pages else 1
    sel = [t for p, t in pages if p >= int(p_from or lo) and (p_to is None or p < int(p_to))]
    return "\n\n".join(sel) if sel else fulltext_of(pages)



def units_dict(u):
    """coerce the model's units (dict or list-of-{unit,text}) into a {'1': text} dict;
    list-valued entries (bare-array unit text) are joined to strings (B37 hardening)"""
    def _s(v):
        if isinstance(v, str):
            return v
        if isinstance(v, list):
            return "\n".join(str(x) for x in v)
        if isinstance(v, dict):
            return v.get("text") or v.get("content") or json.dumps(v, ensure_ascii=False)
        return str(v) if v is not None else ""
    if isinstance(u, dict):
        return {str(k): _s(v) for k, v in u.items()}
    if isinstance(u, list):
        out = {}
        for i, x in enumerate(u, 1):
            if isinstance(x, dict):
                k = str(x.get("unit") or x.get("no") or i)
                out[k] = _s(x.get("text") or x.get("unit_text") or x.get("content") or "")
            else:
                out[str(i)] = _s(x)
        return out
    return {}

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


def inventory(pdf_name, fulltext, session, course, max_tokens=6000):
    """validated inventory call: the model sometimes returns junk/bare title
    strings or non-dict entries — re-ask up to 3 attempts, else raise."""
    msgs = [{"role": "system", "content": SYS},
            {"role": "user", "content": INVENTORY % (pdf_name, session, course) + "\n=== PDF TEXT ===\n" + fulltext}]
    last = None
    for tries in range(3):
        inv = chat(msgs, max_tokens=max_tokens)
        if isinstance(inv, list):
            inv = {"subjects": inv}
        if not isinstance(inv, dict):
            last = repr(inv)[:120]
            continue
        subs = inv.get("subjects", []) or []
        good = [s for s in subs if isinstance(s, dict) and (s.get("code_print") or s.get("name_print"))]
        if good:
            return inv, good
        last = f"{len(subs)} entries, none valid dicts with code/name"
    raise RuntimeError(f"inventory returned no valid subject dicts after 3 attempts: {last}")


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
    if isinstance(out, list):  # model sometimes returns the bare array
        out = next((x for x in out if isinstance(x, dict)), {})
    if out.get("scheme_row_only"):
        out.setdefault("flags", []).append("scheme_row_only_detailed_syllabus_not_printed")
        out.setdefault("quirks", []).append(
            "scheme table row only (p.%s): detailed syllabus not printed in this document "
            "(recorded B23/B25/B27 zero-GAP class — flagged subject candidate for the ladder)" % sub.get("page", "?"))
        if sub.get("slot_print"):
            out.setdefault("flags", []).append("alternative_pair_row")
    if is_detail:
        out["units"] = units_dict(out.get("units"))
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
            if isinstance(fix, list):
                fix = next((x for x in fix if isinstance(x, dict)), {})
            fu = units_dict(fix.get("units"))
            for uk in bad:
                if fu.get(uk) and contained(fu[uk], fulltext) >= 0.85:
                    out["units"][uk] = fu[uk]
                else:
                    out.setdefault("flags", []).append("unit_containment_low_print_quirk")
                    out.setdefault("quirks", []).append(
                        "unit %s containment below threshold after one corrective re-extraction; text-layer "
                        "fragment likely garbled or off-page (RULES §6 — page image is authoritative); kept "
                        "as extracted, flagged for verify evidence" % uk)
    return sub.get("code_print", ""), out


def queue_meta_for(stem, rec_meta):
    """B41 fix: parse records stage files as NN_<stem>.pdf and carry rel=''/session=''
    (the B40 defect: drafts fell back to course=BTech/session='' — §3 fieldwise
    silently degraded to backfill-only). Match the queue entry by the stem with
    its NN_ index prefix stripped, falling back to the basename forms."""
    q = json.load(open("/home/z/my-project/work/pipeline_v2/queue.json"))
    base = os.path.basename(rec_meta.get("pdf_path", "") or (stem + ".pdf"))
    cands = {base, stem + ".pdf", re.sub(r"^\d+_", "", stem) + ".pdf"}
    for e in q["entries"]:
        b = os.path.basename(e["rel"])
        if b in cands or re.sub(r"^\d+_", "", stem) + ".pdf" == b:
            return e
    return None


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
    # B41 fix (root cause of the B40 empty-session drafts): the staged basename
    # carries the NN_ index prefix so the basename lookup above fails; resolve
    # via the stem-based queue match and OVERRIDE the fallback fields.
    qe = queue_meta_for(stem, meta)
    if qe:
        pdf_rel = qe["rel"]
        session = qe.get("session", "") or session
        course = qe.get("course", "") or course
    fulltext = open(f"{parsed_dir}/{stem}.fulltext.txt").read()
    PAGES = pages_of(fulltext)
    sha16 = meta.get("sha16", "")
    # Inventory cache (bounded-round/resume class): never re-pay the inventory
    # call once validated; b37_resume.py reads the same file.
    INVP = f"/home/z/my-project/work/pipeline_v2/inv/{stem}.inv.json"
    if os.path.exists(INVP):
        try:
            subs = json.load(open(INVP))
            inv = {"doc_title_print": ""}
            print(f"INVENTORY|{stem}|{len(subs)} subjects (cached)")
        except Exception:
            subs = None
    else:
        subs = None
    if subs is None:
        inv, subs = inventory(pdf_name, fulltext, session, course)
        try:
            os.makedirs(os.path.dirname(INVP), exist_ok=True)
            json.dump(subs, open(INVP, "w"), indent=1, ensure_ascii=False)
        except Exception:
            pass
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
            first_det = min([int(s.get("page") or 10**9) for s in detail_subs], default=None)
            scheme_txt = fulltext if first_det is None else fulltext_of([p for p in PAGES if first_det is None or p["n"] < first_det]) if False else (fulltext if first_det is None else "\n\n".join(t for p, t in PAGES if p < first_det))
            results.extend(extract_scheme_batch(scheme_txt, session, course, scheme_subs))
        except Exception as e:  # noqa: BLE001
            draft.setdefault("flags", []).append(f"scheme_batch_failed:{repr(e)[:80]}")
            for s in scheme_subs:
                draft["subjects"].append({"name": s.get("name_print", ""), "name_print": s.get("name_print", ""),
                                          "codes": [re.sub(r"[^A-Za-z0-9*]", "", s.get("code_print", ""))],
                                          "flags": ["extraction_failed_scheme_batch"], "quirks": [], "units": {}})
            save()
    with ThreadPoolExecutor(max_workers=2) as ex:
        def safe_pg(x):
            try:
                return int(x)
            except (TypeError, ValueError):
                return 0
        det_pages = sorted({safe_pg(s.get("page")) for s in detail_subs if safe_pg(s.get("page"))})
        det_pages = sorted(set(det_pages))
        def slice_for(s):
            p = safe_pg(s.get("page"))
            if not p:
                return fulltext
            nxt = next((q for q in det_pages if q > p), None)
            return "\n\n".join(t for pp, t in PAGES if pp >= p and (nxt is None or pp < nxt))
        futs = {ex.submit(extract_one, pdf_name, slice_for(s), meta, s, session, course): s for s in detail_subs}
        for fut in as_completed(futs):
            s = futs[fut]
            try:
                results.append(fut.result())
            except Exception as e:  # noqa: BLE001 — record and continue; verify will catch gaps
                import traceback
                draft.setdefault("flags", []).append(
                    f"extraction_failed:{s.get('code_print','?')}:{repr(e)[:80]}:{traceback.format_exc()[-300:]!s}")
                traceback.print_exc()
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
