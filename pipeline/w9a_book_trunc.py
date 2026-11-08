#!/usr/bin/env python3
"""w9a_book_trunc.py — W9a: BOOK_TRUNC 574 adjudication wave (owner go
"Do [BOOK_TRUNC 574, scheme adjudications 401, W8c memo 71] now", 2026-11-08).

Three-stage, evidence-first (RULES §4/§6/§6b; W8a auditor-FP precedent):

  stage classify — split every BOOK_TRUNC flag into
      fp_end_ok      : entry starts author-like AND ends with a publisher-ish
                       token (extended whitelist observed in the corpus ending
                       distribution) — auditor false positive, zero data change
                       (the auditor upgrade mirrors this whitelist)
      start_broken   : entry starts lowercase / with a year+comma (missing
                       head) — the text layer lost the entry head; probe
      end_suspect    : start ok but the ending is not publisher-like — probe
  stage probe    — per target: read the cited docs' printed books list
                       (pinned pp.N cluster first, then all text pages, then
                       bounded raster OCR — sha-keyed cache shared with W8b).
                       Matching is squash-key based (spacing/punctuation/
                       quote/&-vs-and invariant) with progressive mid-trims.
                       verdicts: healed (print whole & longer) /
                       verified_complete (print == stored, containment) /
                       print_truncated (hit but print does not cover stored) /
                       sha_unresolved (post-reset missing doc) /
                       no_print_found.
  stage apply    — healed entries backfilled VERBATIM from the print with
                       corrections_json before/after + page-cited evidence
                       (§6b); no spell-corrections inside the healed entry
                       (§6 verbatim print). Re-audit + gates by the caller.

Owner directives honored: budget-guarded synchronous chunks (W9A_BUDGET
seconds) + checkpoint resume (sandbox kills long runs between tool calls);
no keys involved (local text/OCR reads only); no rr_sid assigned.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

import fitz  # PyMuPDF

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

BASE = WC.BASE
CSV_PATH = WC.CSV_PATH
PLAN = f"{BASE}/w9a_plan.json"
CKPT = f"{BASE}/w9a_ckpt.json"
OCR_CACHE = f"{BASE}/w9a_ocr_cache"
W8B_CKPT = f"{BASE}/w8b_ocr_ckpt.json"
BUDGET_S = float(os.environ.get("W9A_BUDGET", "240"))
SMOKE = os.environ.get("W9A_SMOKE", "") == "1"
DPI = 200

CORPUS = json.load(open(f"{BASE}/corpus_map.json"))

START_LOWER = re.compile(r"^['\"“”‘’]?[a-z]")
START_YEAR = re.compile(r"^['\"“”]?(?:19|20)\d{2}\b.*,")

END_SINGLE = {
    "hill", "wiley", "phi", "tmh", "pearson", "springer", "kluwer", "narosa",
    "elsevier", "cambridge", "oxford", "cengage", "kaufmann", "wesley",
    "press", "publishers", "publication", "publications", "publishing",
    "delhi", "mumbai", "chand", "rai", "khanna", "katson", "education",
    "learning", "house", "hall", "sons", "company", "india", "university",
    "ibh", "galgotia", "wheeler", "prakashan", "international",
}
END_MULTI = [
    "new delhi", "mcgraw hill", "mcgraw-hill", "graw hill", "tata mcgraw",
    "prentice hall", "crc press", "morgan kaufmann", "addison wesley",
    "addision wesley", "universities press", "university press",
    "pearson education", "wiley india", "john wiley", "phi learning",
    "s. chand", "dhanpat rai", "khanna publishers", "himalaya publishing",
    "publishing house", "india publication", "oxford publication",
    "cengage learning", "learning publication", "jones and bartlett",
    "and sons", "& sons", "and co", "& co", "& company", "and company",
    "of india", "prentice-hall",
]
END_OK_TAIL = re.compile(r"[.,;]?\s*['\"“”]*$")


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip(" ")


def squash(s):
    """spacing/punctuation/quote/&-vs-and invariant key (substring safe)."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower().replace("&", " and "))


def entry_end_ok(t):
    s = END_OK_TAIL.sub("", t.strip()).rstrip()
    if re.search(r"(?:19|20)\d{2}[.,;)]?['\"“”]*$", s):
        return True  # edition/year-ending print is a complete citation form
    low = s.lower()
    for mw in END_MULTI:
        if low.endswith(mw):
            return True
    toks = s.split()
    if not toks:
        return False
    last = re.sub(r"[^A-Za-z.]", "", toks[-1]).lower().rstrip(".")
    return last in END_SINGLE


def entry_start_broken(t):
    return bool(START_LOWER.match(t)) or bool(START_YEAR.match(t))


def iter_flags():
    fl = json.load(open(f"{BASE}/audit_flags.json"))
    for sid, lst in fl["rows"].items():
        for f in lst:
            if f.get("rule") == "BOOK_TRUNC":
                yield sid, f


# --- stage: classify ---------------------------------------------------------
def stage_classify():
    rows = WC.load_rows()
    by_id = {r["subject_id"]: r for r in rows}
    plan = {"fp_end_ok": [], "probe": []}
    seen = set()
    for sid, f in iter_flags():
        field = f["field"]
        key = (sid, field)
        if key in seen:
            continue
        seen.add(key)
        r = by_id.get(sid)
        if r is None:
            continue
        t = WC.field_get(r, field)
        if not t:
            continue
        if entry_start_broken(t):
            plan["probe"].append({"sid": sid, "field": field, "text": t,
                                  "why": "start_broken"})
        elif entry_end_ok(t):
            plan["fp_end_ok"].append({"sid": sid, "field": field,
                                      "text": t[-120:]})
        else:
            plan["probe"].append({"sid": sid, "field": field, "text": t,
                                  "why": "end_suspect"})
    if SMOKE:
        plan["probe"] = plan["probe"][:3]
    json.dump(plan, open(PLAN, "w"), indent=1, ensure_ascii=False)
    print(f"W9A_CLASSIFY|fp_end_ok={len(plan['fp_end_ok'])}|probe={len(plan['probe'])}")
    return 0


# --- probe machinery ---------------------------------------------------------
def resolve(sha):
    if sha in CORPUS:
        return CORPUS[sha]
    hits = [v for k, v in CORPUS.items() if k.startswith(sha)]
    return hits[0] if len(hits) == 1 else None


def sha16(path):
    import hashlib
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


_W8B_MEM = None
_OCR_MEM = {}


def _w8b_cache():
    global _W8B_MEM
    if _W8B_MEM is None:
        try:
            _W8B_MEM = json.load(open(W8B_CKPT)).get("ocr_cache", {})
        except Exception:
            _W8B_MEM = {}
    return _W8B_MEM


def ocr_page(path, pno, sha=None):
    """0-based pno; consults w9a memory + w8b sha-keyed cache; persists to memory."""
    key = f"{sha or os.path.basename(path)}:p{pno + 1}"
    if key in _OCR_MEM:
        return _OCR_MEM[key]
    if sha:
        w8 = _w8b_cache().get(key)
        if w8 is not None:
            _OCR_MEM[key] = w8
            return w8
    os.makedirs(OCR_CACHE, exist_ok=True)
    try:
        doc = fitz.open(path)
        pix = doc[pno].get_pixmap(dpi=DPI)
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            pix.save(tf.name)
            tmp = tf.name
        out = subprocess.run(["tesseract", tmp, "stdout", "--psm", "6"],
                             capture_output=True, text=True, timeout=120)
        os.unlink(tmp)
        txt = out.stdout or ""
    except Exception:
        txt = ""
    _OCR_MEM[key] = txt
    return txt


def page_text(doc, pno, weak=80, sha=None):
    if pno < 0 or pno >= doc.page_count:
        return ""
    t = doc[pno].get_text() or ""
    if len(t.strip()) < weak:  # raster page
        t = ocr_page(doc.name, pno, sha=sha)
    return t


def citations_for(r):
    """[(stem, sha, pinned_page_or_None)] from source_syllabus + source_history."""
    out = []
    for col in ("source_syllabus", "source_history"):
        s = r.get(col, "") or ""
        for m in re.finditer(r"([^;#]+?\.pdf)#([0-9a-f]{12,16})", s):
            stem, sha = m.group(1).strip(), m.group(2)
            tail = s[m.end():m.end() + 24]
            pm = re.match(r"\s+pp?\.(\d{1,4})\b", tail)
            out.append((os.path.basename(stem), sha, int(pm.group(1)) if pm else None))
    return out


ENDISH = re.compile(r"(?:\b(?:Press|Publishers|Publications?|Publishing|Wiley|PHI|TMH|"
                    r"Pearson|Springer|Narosa|Elsevier|Hill|Hall|Oxford|Cambridge|"
                    r"Chand|Rai|Khanna|Katson|Delhi|Mumbai|Wesley|Kaufmann|"
                    r"Learning|Education|India|University|Sons|Company|Cengage|"
                    r"Kluwer|Bartlett|House)[.,;]?|\b(?:19|20)\d{2}[.,;)]?|"
                    r"[.\"”]+\s*)$", re.I)
STARTISH = re.compile(r"^(?:\d{1,2}[\.\)]\s+)?(?:['\"“”]?[A-Z0-9])")


def extract_printed_entry(page, frag_sq):
    """Find the printed entry containing the squashed fragment on one page.
    Sliding windows of 1..5 lines (print wraps entries across lines).
    Returns (verbatim_entry, hit_lo) or (None, None)."""
    lines = [ln.strip() for ln in page.splitlines() if ln.strip()]
    sq_lines = [squash(ln) for ln in lines]
    hit = None
    hit_w = 1
    for w in (1, 2, 3, 4, 5):
        for i in range(len(sq_lines) - w + 1):
            if frag_sq and frag_sq in "".join(sq_lines[i:i + w]):
                hit = i
                hit_w = w
                break
        if hit is not None:
            break
    if hit is None:
        return None, None
    lo = hit
    # walk up while the start-line looks like a wrapped continuation
    while lo > 0 and not STARTISH.match(lines[lo]) and not re.match(r"^\d{1,2}[\.)]\s", lines[lo]):
        lo -= 1
    endx = hit + hit_w - 1
    cur = "".join(sq_lines[lo:endx + 1])
    # extend until the fragment is fully covered (entry may wrap 3+ lines)
    while frag_sq not in cur and endx + 1 < len(lines) \
            and not re.match(r"^\d{1,2}[\.)]\s", lines[endx + 1]):
        endx += 1
        cur += sq_lines[endx]
    # absorb lowercase continuation lines to reach a sane end
    while endx + 1 < len(lines) and not ENDISH.search(lines[endx]) \
            and not re.match(r"^\d{1,2}[\.)]\s", lines[endx + 1]) \
            and re.match(r"^[a-z('\"“”]", lines[endx + 1]):
        endx += 1
        cur += sq_lines[endx]
    out_lines = lines[lo:endx + 1]
    while len(out_lines) > 1 and re.match(r"^\d{1,2}[\.)]\s", out_lines[-1]) \
            and frag_sq not in squash(out_lines[-1]):
        out_lines.pop()
    entry = re.sub(r"\s+", " ", " ".join(out_lines)).strip()
    m = re.match(r"^(\d{1,2}[\.)]\s+)(.*)$", entry)
    if m and frag_sq in squash(m.group(2)):
        entry = m.group(2).strip()
    if frag_sq in squash(entry) and len(entry) > 20:
        return entry, hit
    return None, None



# --- stage: index (global page-squash index for cross-doc fallback) ----------
PAGE_INDEX = f"{BASE}/w9a_page_index.json"


def stage_index():
    import pickle
    t0 = time.time()
    if os.path.exists(PAGE_INDEX) and os.environ.get("W9A_REINDEX", "") != "1":
        print(f"W9A_INDEX|cached|{PAGE_INDEX}")
        return 0
    idx = {}
    paths = {}
    n_raster = 0
    for sha, path in CORPUS.items():
        if not os.path.exists(path):
            continue
        paths[sha] = path
        try:
            d = fitz.open(path)
        except Exception:
            continue
        for i in range(d.page_count):
            t = (d[i].get_text() or "").strip()
            if len(t) < 40:
                n_raster += 1
                continue
            idx[f"{sha}:p{i + 1}"] = squash(t)
        d.close()
    with open(PAGE_INDEX, "wb") as fh:
        pickle.dump({"idx": idx, "paths": paths}, fh, protocol=4)
    print(f"W9A_INDEX|pages={len(idx)}|docs={len(paths)}|raster_skipped={n_raster}"
          f"|{time.time() - t0:.0f}s")
    return 0


def verdict_for(entry, p, path, pno, probed, cross_ok=False):
    # split multi-entry text-layer lines at internal numbering ('...Hill. 2. Author...')
    segs = re.split(r"(?:(?<=\.)|(?<=\?))\s+(?=\d{1,2}[\.)]\s)", entry)
    if len(segs) > 1:
        for sg in segs:
            if p["sq_stored"] in squash(sg) or any(fs in squash(sg) for fs in p["frag_cands"]):
                entry = re.sub(r"^\d{1,2}[\.)]\s+", "", sg.strip())
                break
    m = re.match(r"^(\d{1,2}[\.)]\s+)(.*)$", entry)
    if m and p["sq_stored"][:40] in squash(m.group(2))[:40]:
        entry = m.group(2).strip()
    ne, ns = squash(entry), p["sq_stored"]
    ev = f"{os.path.basename(path)}#{sha16(path)} p.{pno + 1}"
    ends_sane = bool(ENDISH.search(entry)) \
        or bool(re.search(r"\b(?:by|ed\.?|eds\.?|vol\.?)\s*[A-Za-z.\s]{1,40}$", entry, re.I)) \
        or bool(re.search(r"\b(?:19|20)\d{2}[.,;)]?['\"“”]*$", entry))
    if ne == ns:
        if ends_sane:
            return {"status": "verified_complete", "evidence": ev,
                    "pages_probed": probed + 1}
        return {"status": "print_garbled", "print": entry[:220],
                "evidence": ev, "pages_probed": probed + 1}
    if ns in ne:
        added = ne[len(ns):]
        meaningful = bool(added) and not added.isdigit() and bool(re.search(r"[a-z]", added))
        # merge guard: a second list item ('; FSSAI Act.') must not ride in
        raw_tail = entry[-(min(len(entry), len(added) * 3 + 14)):]
        merged = bool(re.search(r";\s*[A-Z]", raw_tail))
        raw_prefix = re.sub(r"\s+", " ", p["text"]).strip().startswith(
            re.sub(r"\s+", " ", entry)[:1] and re.sub(r"\s+", " ", entry).strip()[:0] + "")
        # cross-doc heal only when the RAW stored string is a strict prefix of
        # the RAW printed entry (character-for-character until stored ends) —
        # rejects junction-convention conflicts ('-SS Rao' vs ', SS Rao')
        stored_ws = re.sub(r"\s+", " ", p["text"]).strip()
        entry_ws = re.sub(r"\s+", " ", entry).strip()
        raw_prefix = cross_ok and entry_ws.startswith(stored_ws)
        if len(ne) > len(ns) and meaningful and not merged \
                and STARTISH.match(entry) and ends_sane and (not cross_ok or raw_prefix):
            v = {"status": "healed", "print": entry, "evidence": ev,
                 "pages_probed": probed + 1}
            if cross_ok:
                v["via"] = "global-index"
                v["note"] = "completed from the fuller verbatim print in corpus doc " + ev + \
                            " (stored head preserved character-for-character; §6b corpus evidence)"
            return v
        return {"status": "verified_complete", "evidence": ev + " (containment)",
                "pages_probed": probed + 1}
    if ne in ns and ns.startswith(ne) and p["text"].rstrip().endswith(tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ ")) \
            and re.search(r"[A-Z][A-Z0-9 &/.\-]{3,60}$", p["text"].rstrip()):
        # stored carries an ALL-CAPS extraction bleed (e.g. 'SEMESTER VI')
        # beyond the printed entry — trim heal (§6b, print = the boundary)
        m_ex = re.search(r"[A-Z][A-Z0-9 &/.\-]{3,60}$", p["text"].rstrip())
        return {"status": "healed_trim", "print": entry, "evidence": ev,
                "trim_note": f"extraction bleed removed: {m_ex.group(0)[:48]!r}",
                "pages_probed": probed + 1}
    return {"status": "print_truncated", "print": entry[:200],
            "evidence": ev, "pages_probed": probed + 1}


_PAGE_IDX = None


def load_page_index():
    global _PAGE_IDX
    if _PAGE_IDX is None:
        import pickle
        try:
            with open(PAGE_INDEX, "rb") as fh:
                _PAGE_IDX = pickle.load(fh)
        except Exception:
            _PAGE_IDX = {"idx": {}, "paths": {}}
    return _PAGE_IDX


def index_fallback(p, t0, budget):
    pi = load_page_index()
    idx = pi["idx"]
    cands = [c for c in p["frag_cands"] if len(c) >= 25]
    hits = []
    for key, sq in idx.items():
        for fs in cands:
            if fs in sq:
                hits.append(key)
                break
        if len(hits) >= 8 or time.time() - t0 > budget + 60:
            break
    for key in hits:
        sha, pg = key.split(":p", 1)
        path = pi["paths"].get(sha) or CORPUS.get(sha)
        if not path or not os.path.exists(path):
            continue
        try:
            d = fitz.open(path)
            txt = d[int(pg) - 1].get_text() or ""
            d.close()
        except Exception:
            continue
        entry = None
        for fs in cands:
            entry, _hx = extract_printed_entry(txt, fs)
            if entry is not None:
                break
        if entry is None:
            continue
        v = verdict_for(entry, p, path, int(pg) - 1, 0, cross_ok=True)
        if v is None:
            continue
        st = v["status"]
        if st in ("healed", "healed_trim") and not v.get("note"):
            # fuller print lives in a NON-cited doc but junction conflicts —
            # corroboration only, stored form kept (zero-guess)
            v = {"status": "corroborated_elsewhere", "evidence": v["evidence"],
                 "note": "fuller print of this book exists in a non-cited corpus doc "
                         "(different print convention); row's own print not recoverable — stored form kept",
                 "pages_probed": v.get("pages_probed", 0)}
        elif st == "print_truncated":
            v = {"status": "corroborated_elsewhere", "evidence": v["evidence"],
                 "note": "same book printed in a different form in a non-cited corpus doc; "
                         "stored form kept — its own doc's print not recoverable",
                 "pages_probed": v.get("pages_probed", 0)}
        else:
            v["via"] = "global-index"
        return v
    return None


# --- stage: probe ------------------------------------------------------------
def stage_probe():
    plan = json.load(open(PLAN))
    ck = json.load(open(CKPT)) if os.path.exists(CKPT) else {"results": {}, "ocr_cache": {}}
    res = ck["results"]
    _OCR_MEM.update(ck.get("ocr_cache", {}))
    t0 = time.time()
    todo = [dict(p, key=f"{p['sid']}::{p['field']}") for p in plan["probe"]]
    todo = [p for p in todo if p["key"] not in res]
    if SMOKE:
        todo = todo[:3]
    print(f"W9A_PROBE|todo={len(todo)}|budget={BUDGET_S}s", flush=True)

    rows = WC.load_rows()
    by_id = {r["subject_id"]: r for r in rows}

    for p in todo:
        f = norm(p["text"])
        toks = f.split()
        if p["why"] == "start_broken" and len(toks) > 3:
            f = " ".join(toks[1:])  # drop the broken head word
        if p["why"] == "end_suspect" and len(toks) > 4:
            f = " ".join(toks[:-1])  # drop the suspect tail word
        sq = squash(f)
        cands = [sq]
        if len(sq) > 50:
            cands.append(sq[10:-10])
        if len(sq) > 80:
            cands.append(sq[25:-25])
        p["frag_cands"] = [c for c in cands if len(c) >= 25]
        p["sq_stored"] = squash(p["text"])
        order, seen = [], set()
        if p["sid"] in by_id:
            cits = citations_for(by_id[p["sid"]])
            for stem, sha, pin in ([c for c in cits if c[2] is not None] +
                                   [c for c in cits if c[2] is None]):
                if sha not in seen:
                    seen.add(sha)
                    order.append((sha, pin))
        p["doc_order"] = order
    todo.sort(key=lambda p: p["doc_order"][0][0] if p["doc_order"] else "")

    open_docs, doc_state = {}, {}

    def get_doc(sha):
        if sha in open_docs:
            return open_docs[sha]
        path = resolve(sha)
        d = None
        if path and os.path.exists(path):
            try:
                d = fitz.open(path)
            except Exception:
                d = None
        open_docs[sha] = None if d is None else (d, path)
        return open_docs[sha]

    def doc_pages(sha, d):
        st = doc_state.get(sha)
        if st is None:
            texts = {i: (d[i].get_text() or "") for i in range(d.page_count)}
            weak = [i for i, t in texts.items() if len(t.strip()) < 80]
            doc_state[sha] = st = (texts, weak)
        return st

    def try_page(txt, p, path, pno, probed):
        entry = None
        for fs in p["frag_cands"]:
            entry, _hx = extract_printed_entry(txt, fs)
            if entry is not None:
                break
        if entry is None:
            return None
        return verdict_for(entry, p, path, pno, probed)

    OCR_CAP = int(os.environ.get("W9A_OCR_CAP", "60"))
    done = 0
    for p in todo:
        if time.time() - t0 > BUDGET_S:
            print(f"W9A_PROBE|budget_stop|done={done}", flush=True)
            break
        if p["sid"] not in by_id:
            res[p["key"]] = {"status": "row_missing"}
            continue
        verdict, probed = None, 0
        for sha, pin in p["doc_order"]:
            if verdict in ("healed", "verified_complete"):
                break
            gd = get_doc(sha)
            if gd is None:
                verdict = {"status": "sha_unresolved", "sha": sha}
                continue
            d, path = gd
            texts, weak = doc_pages(sha, d)
            pin_idx = pin - 1 if (pin is not None and 0 <= pin - 1 < d.page_count) else None
            # pass 1: pinned cluster (OCR allowed), then all text pages
            if pin_idx is not None:
                for pj in (pin_idx - 1, pin_idx, pin_idx + 1):
                    if 0 <= pj < d.page_count:
                        probed += 1
                        verdict = try_page(page_text(d, pj, sha=sha), p, path, pj, probed - 1)
                        if verdict in ("healed", "verified_complete"):
                            break
            if verdict is None:
                for i in range(d.page_count):
                    if i == pin_idx or len(texts[i].strip()) < 80:
                        continue
                    probed += 1
                    verdict = try_page(texts[i], p, path, i, probed)
                    if verdict in ("healed", "verified_complete"):
                        break
                    if time.time() - t0 > BUDGET_S + 60:
                        break
            # pass 2: raster/weak pages, OCR (bounded)
            if verdict is None:
                cap = 0
                for i in weak:
                    if i == pin_idx or cap >= OCR_CAP:
                        continue
                    if time.time() - t0 > BUDGET_S + 90:
                        break
                    probed += 1
                    cap += 1
                    verdict = try_page(ocr_page(path, i, sha), p, path, i, probed - 1)
                    if verdict in ("healed", "verified_complete"):
                        break
            if verdict is None:
                verdict = index_fallback(p, t0, BUDGET_S)
        if verdict is None:
            verdict = {"status": "no_print_found", "pages_probed": probed}
        res[p["key"]] = verdict
        done += 1
        if done % 10 == 0:
            ck["results"] = res
            ck["ocr_cache"] = dict(list(_OCR_MEM.items())[:4000])
            json.dump(ck, open(CKPT, "w"), indent=1, ensure_ascii=False)

    ck["results"] = res
    ck["ocr_cache"] = dict(list(_OCR_MEM.items())[:4000])
    json.dump(ck, open(CKPT, "w"), indent=1, ensure_ascii=False)
    from collections import Counter
    c = Counter(v["status"] for v in res.values())
    print(f"W9A_PROBE|done_this_run={done}|total={len(res)}|{dict(c)}")
    return 0


# --- stage: apply ------------------------------------------------------------
def stage_apply():
    ck = json.load(open(CKPT))
    res = ck["results"]
    healed = {k: v for k, v in res.items() if v["status"] == "healed"}
    edits = []
    for key, v in healed.items():
        sid, field = key.split("::", 1)
        edits.append({"sid": sid, "field": field, "before": None, "after": v["print"],
                      "rule": "W9a/BOOK_TRUNC_HEAL",
                      "evidence": f"printed books list at {v['evidence']} (verbatim print; "
                                  "stored text-layer fragment was a truncated head/tail of this entry)"})
    rows = WC.load_rows()
    by_id = {r["subject_id"]: r for r in rows}
    for e in edits:
        e["before"] = WC.field_get(by_id[e["sid"]], e["field"])
    rows, per_sid, skipped = WC.apply_edits(rows, edits, "W9a", None,
                                            note_extra="W9a BOOK_TRUNC verbatim backfill")
    WC.commit(rows, "W9a", len(edits) - len(skipped), {"note": "gates by caller"},
              meta_extra={"wave": "W9a", "healed": len(edits) - len(skipped),
                          "skipped": len(skipped)})
    if skipped:
        print("W9A_APPLY_SKIPS:", skipped[:5])
    print(f"W9A_APPLY|healed={len(edits) - len(skipped)}")
    return 0


def stage_status():
    plan = json.load(open(PLAN)) if os.path.exists(PLAN) else {"fp_end_ok": [], "probe": []}
    ck = json.load(open(CKPT)) if os.path.exists(CKPT) else {"results": {}}
    from collections import Counter
    c = Counter(v["status"] for v in ck["results"].values())
    print(f"W9A_STATUS|plan_fp={len(plan['fp_end_ok'])}|plan_probe={len(plan['probe'])}"
          f"|probed={len(ck['results'])}|{dict(c)}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["classify", "index", "probe", "apply", "status"])
    a = ap.parse_args()
    sys.exit({"classify": stage_classify, "index": stage_index, "probe": stage_probe,
              "apply": stage_apply, "status": stage_status}[a.stage]())
