#!/usr/bin/env python3
"""w8b_kls_ocr.py — W8b phase 1: page-image OCR evidence reads for the KLS
raster-candidate leftovers (owner go 2026-11-08 "continue with both").

The W3 text-layer scan + mercury-3 T2T REX exhausted every row whose cited
pages carry a machine-readable K column. The remaining KLS_MISSING/KLS_SHORT
rows cite pages whose K table is raster (or whose text layer scrambles table
order). This wave renders the CITED pages to images and reads them with
tesseract OCR — a deterministic mechanical read of the print, not a model
guess. Acceptance is strict zero-guess:

  - page OCR text must show CO1..COn markers AND a clean K1..K6 token sequence
  - per-CO association must be conflict-free; exactly co_count tokens
  - KLS_SHORT partials merge only into null positions; any conflict => reject
  - anything ambiguous => row stays flagged (evidence probe recorded)

Citation reality (probed 2026-11-08): 510/519 targets cite pp.as-drafted (no page
number) — probe enumerates the doc's raster-suspect pages (weak text layer, capped);
3 rows carry pinned p.N pages (probed first). A persistent per-(sha,page) OCR cache
is shared across rows — many targets cite the same model-curriculum docs, so each
page is OCR'd at most once across the whole wave (and across runs, via checkpoint).

Owner directives: tiny smoke test first (W8B_SMOKE=1); <=5 concurrent workers;
budget-guarded (W8B_OCR_BUDGET seconds, default 240) with checkpoint resume
(sandbox kills long runs between calls); no API keys involved (OCR is local).
RULES §6b on every write. mercury-3 has no image-capable client in this
workspace (mercury_call.py is T2T-only) — OCR is the image-evidence path."""
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

BASE = WC.BASE
BUDGET_S = float(os.environ.get("W8B_OCR_BUDGET", "240"))
SMOKE = os.environ.get("W8B_SMOKE", "") == "1"
WORKERS = 5
DPI = 200

PAIR = re.compile(r"CO[\s\-–—]?(\d{1,2})\b[^K]{0,200}?\bK[\s\-–—]?([1-6])\b", re.I | re.S)
KRUN = re.compile(r"\bK[\s\-–—]?([1-6])\b", re.I)
# corpus uses MIXED sha lengths (12-char older citations, 16-char md5-first-16)
CIT = re.compile(r"([^;#]+\.pdf)#([0-9a-f]{12,16})\s+p\.(\d{1,4})\b", re.I)
SHA = re.compile(r"([0-9a-f]{12,16})")


def resolve(sha):
    if sha in corpus:
        return corpus[sha]
    hits = [v for k, v in corpus.items() if k.startswith(sha)]
    return hits[0] if len(hits) == 1 else None

rows = WC.load_rows()
by_id = {r["subject_id"]: i for i, r in enumerate(rows)}
flags_doc = json.load(open(f"{BASE}/audit_flags.json"))
targets = []
for sid, fl in flags_doc.get("rows", {}).items():
    for f in fl:
        if f.get("rule") in ("KLS_MISSING", "KLS_SHORT") and f.get("action", "").startswith("fix:"):
            targets.append(sid)
            break
# audit v19 (2026-11-09): raster-candidate rows carry needs_review KLS flags —
# still the real OCR evidence path. Select them from the CSV tags directly.
for r in rows:
    if r.get("row_kind") != "subject":
        continue
    qf = r.get("quality_flags", "") or ""
    if "kls_raster_candidate" not in qf:
        continue
    sid = r["subject_id"]
    if sid in targets:
        continue
    kls = None
    try:
        kls = json.loads(r.get("co_kls", "") or "[]") if (r.get("co_kls", "") or "").strip() else None
    except Exception:
        kls = None
    ncos = sum(1 for i in range(1, 7) if (r.get(f"co{i}_text", "") or "").strip())
    if not ncos:
        continue
    if not isinstance(kls, list) or len(kls) < ncos:
        targets.append(sid)
targets = sorted(set(targets))
if SMOKE:
    targets = targets[:2]
print(f"W8B|targets={len(targets)} smoke={SMOKE} budget={BUDGET_S}s", flush=True)

# corpus sha16 -> path (same cache contract as w3_kls_scan)
CORPUS_CACHE = f"{BASE}/corpus_map.json"
CORPUS_TS = f"{BASE}/corpus_map.stamp"


def corpus_signature():
    sig = []
    for dp, _d, fs in os.walk("/home/z/my-project/work/repo_asleep/PDFs"):
        for fn in fs:
            if fn.lower().endswith(".pdf"):
                p = os.path.join(dp, fn)
                try:
                    st = os.stat(p)
                    sig.append(f"{p}:{st.st_size}:{int(st.st_mtime)}")
                except OSError:
                    pass
    return hashlib.md5("|".join(sorted(sig)).encode()).hexdigest()


if os.path.exists(CORPUS_CACHE) and os.path.exists(CORPUS_TS) and \
        open(CORPUS_TS).read().strip() == corpus_signature():
    corpus = json.load(open(CORPUS_CACHE))
else:
    corpus = {}
    for dp, _d, fs in os.walk("/home/z/my-project/work/repo_asleep/PDFs"):
        for fn in fs:
            if fn.lower().endswith(".pdf"):
                p = os.path.join(dp, fn)
                try:
                    h = hashlib.md5()
                    with open(p, "rb") as fh:
                        for chunk in iter(lambda: fh.read(1 << 20), b""):
                            h.update(chunk)
                    corpus.setdefault(h.hexdigest()[:16], p)
                except Exception:
                    pass
    json.dump(corpus, open(CORPUS_CACHE, "w"))
    open(CORPUS_TS, "w").write(corpus_signature())
print(f"W8B|corpus={len(corpus)} pdfs", flush=True)

# pinned-page rows first (cheap wins), then as-drafted
PAGED = re.compile(r"\.pdf#[0-9a-f]{12,16}\s+p\.\d{1,4}\b", re.I)
targets.sort(key=lambda s: 0 if PAGED.search(rows[by_id[s]].get("source_syllabus", "") or "") else 1)

CKPT = f"{BASE}/w8b_ocr_ckpt.json"
start_i, results, ocr_cache = 0, {}, {}
if os.path.exists(CKPT):
    try:
        c = json.load(open(CKPT))
        if c.get("targets") == targets:
            start_i = c.get("i", 0)
            results = c.get("results", {})
            ocr_cache = c.get("ocr_cache", {})
            print(f"W8B|resume i={start_i} done={len(results)} cache={len(ocr_cache)}pages", flush=True)
    except Exception:
        pass


def doc_raster_pages(pdf_path, cap=40):
    """pages worth OCR-ing: weak/empty text layer (raster suspects), in order"""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        out = []
        for pno in range(min(cap, doc.page_count)):
            try:
                txt = doc[pno].get_text("text") or ""
            except Exception:
                txt = ""
            if len(txt.strip()) < 200:
                out.append(pno + 1)
        doc.close()
        return out
    except Exception:
        return []


def cached_ocr(sha, pg, path):
    key = f"{sha}:p{pg}"
    if key in ocr_cache:
        return ocr_cache[key]
    t = ocr_page(path, pg)
    ocr_cache[key] = t if t is not None else ""
    return ocr_cache[key]


def ocr_page(pdf_path, pageno):
    """render page -> tesseract text (None on any failure)"""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        if not (1 <= pageno <= doc.page_count):
            doc.close()
            return None
        pix = doc[pageno - 1].get_pixmap(dpi=DPI)
        doc.close()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            pix.save(tf.name)
            tmp_png = tf.name
        try:
            out = subprocess.run(["tesseract", tmp_png, "stdout", "--psm", "6"],
                                 capture_output=True, timeout=60)
            return out.stdout.decode("utf-8", "replace") if out.returncode == 0 else None
        finally:
            os.unlink(tmp_png)
    except Exception:
        return None


CO_LINE = re.compile(r"^\s*c\s*o\s*[\s\-–—_]?(\d{1,2})(?![0-9])[\s\.\:_\-–—]*(.*)$", re.I)
KTOK = re.compile(r"K[\s\-–—]?([1-6])\b", re.I)
LEGEND = re.compile(r"K\s*[\s\-–—]?\d\s*[-–—:]\s*[A-Za-z]{3,}|bloom", re.I)
SECTION = re.compile(r"^\s*(unit\b|course\b|total\b|note\b|teaching|evaluation|scheme\b|references?\b|text\s*books?\b)", re.I)


def extract_sequence(text, ncos):
    """conflict-free K-sequence for CO1..ncos from page text, else None.
    Block state-machine handling BOTH layouts:
      - one-line (OCR): 'CO1_ Identify ... K1, K2'
      - cell-split (text layer): 'CO 1' / 'Understand ...' / 'K2, K4'
    A CO marker opens a block; K tokens join it until a legend/section line
    or the next CO marker. Multi-level prints join as 'K1/K2' (catalog
    convention, auditor-accepted composite). Strict: exactly ncos distinct
    CO blocks, each with >=1 K token, no conflicting repeats. The legacy
    PAIR fallback was REMOVED: it paired CO->K across newlines and matched
    wrong-course tables inside compendium PDFs (caught 2026-11-08 on
    cyber-crimes-and-law vs a Computer Graphics table)."""
    if not text:
        return None
    blocks, cur, collecting = {}, None, False
    max_co = 0

    def add(co, ks):
        for k in ks:
            kk = "K" + k
            if kk not in blocks[co]:
                blocks[co].append(kk)

    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        m = CO_LINE.match(s)
        if m:
            co = int(m.group(1))
            max_co = max(max_co, co)
            if 1 <= co <= ncos:
                if co in blocks:
                    return None  # repeated CO block with content => conflict
                blocks[co] = []
                cur, collecting = co, True
                rest = m.group(2)
                if LEGEND.search(rest):
                    collecting = False
                else:
                    add(co, KTOK.findall(rest))
                    if blocks[co]:
                        collecting = "got"
            else:
                cur, collecting = None, False
            continue
        if cur is None or not collecting:
            continue
        if LEGEND.search(s) or SECTION.match(s):
            collecting = False
            continue
        ks = KTOK.findall(s)
        if ks:
            add(cur, ks)
            collecting = "got"
        elif collecting == "got":
            collecting = False  # first non-K line after K values closes the block
    if len(blocks) != ncos or any(not v for v in blocks.values()) or max_co != ncos:
        return None
    return ["/".join(blocks[i]) for i in range(1, ncos + 1)]


MAXP = int(os.environ.get("W8B_PAGES_PER_ROW", "14"))
TXTCAP = int(os.environ.get("W8B_TEXT_PAGES", "60"))
STOP = set("a an and of or for the to in with by on ii iii iv v i".split())


def title_affinity(text, name):
    """soft disambiguation for compendium docs: does the page mention the
    row's subject words? 0 = no signal (page still valid evidence, cited doc
    is course-attributed by earlier waves)"""
    toks = [t for t in re.split(r"[^a-z0-9]+", (name or "").lower()) if len(t) >= 4 and t not in STOP]
    if not toks:
        return 0
    tl = (text or "").lower()
    return sum(1 for t in toks if t in tl)


def probe(sid):
    r = rows[by_id[sid]]
    ncos = int(r.get("co_count") or 0)
    if ncos <= 0:
        return {"sid": sid, "status": "no_co_count"}
    src = r.get("source_syllabus", "") or ""
    cites, seen = [], set()
    for m in CIT.finditer(src):
        key = (m.group(2), int(m.group(3)))
        if key not in seen:
            seen.add(key)
            cites.append(key)  # pinned (sha, page)
    docs = []
    for m in re.finditer(r"([^;#]+\.pdf)#([0-9a-f]{12,16})", src):
        if m.group(2) not in [d[0] for d in docs]:
            docs.append((m.group(2), resolve(m.group(2))))
    docs = [(sha, p) for sha, p in docs if p]
    if not cites and not docs:
        return {"sid": sid, "status": "sha_unresolved"}
    pages_probed = 0
    txt_done = 0
    cands = []  # (score, sha, pg, seq, src_kind)

    def consider(sha, pg, text, src_kind):
        seq = extract_sequence(text, ncos)
        if seq:
            cands.append((title_affinity(text, r.get("subject_name")), sha, pg, seq, src_kind))

    # 1) pinned pages first
    for sha, pg in cites:
        path = resolve(sha)
        if not path:
            continue
        text = cached_ocr(sha, pg, path)
        pages_probed += 1
        consider(sha, pg, text, "OCR")
        if pages_probed >= MAXP or cands:
            break
    # 2) as-drafted: per cited doc — text-layer pages FIRST (free, and the
    #    dominant failure mode: multi-level K tables in text layers that W3's
    #    single-K regexes could not parse), then raster-suspect pages via OCR
    if not cands:
        import fitz
        for sha, path in docs:
            if pages_probed >= MAXP and txt_done >= TXTCAP:
                break
            try:
                doc = fitz.open(path)
                npages = min(TXTCAP, doc.page_count)
                tlens = []
                for pno in range(npages):
                    try:
                        tlens.append(len((doc[pno].get_text("text") or "").strip()))
                    except Exception:
                        tlens.append(0)
                doc.close()
            except Exception:
                tlens = []
            for pno, tlen in enumerate(tlens, start=1):
                if txt_done >= TXTCAP:
                    break
                if tlen >= 200:  # strong text layer: read it directly, no OCR
                    try:
                        doc = fitz.open(path)
                        text = doc[pno - 1].get_text("text") or ""
                        doc.close()
                    except Exception:
                        continue
                    txt_done += 1
                    consider(sha, pno, text, "text-layer")
            for pg in doc_raster_pages(path):
                if pages_probed >= MAXP:
                    break
                text = cached_ocr(sha, pg, path)
                pages_probed += 1
                consider(sha, pg, text, "OCR")
    if cands:
        # zero-guess gate: compendium PDFs bundle many courses; a K table is
        # only attributable when >=2 distinct subject-name tokens appear on
        # the same page (title affinity). ts<2 candidates are DISCARDED.
        cands = [c for c in cands if c[0] >= 2]
    if cands:
        cands.sort(key=lambda c: -c[0])
        score, sha, pg, seq, src_kind = cands[0]
        note = "" if score > 0 else "; title affinity 0 (compendium doc, course attribution per cited-doc convention)"
        read = (f"text-layer pp.{pg}" if src_kind == "text-layer"
                else f"OCR pp.{pg} (tesseract psm6 {DPI}dpi)")
        return {"sid": sid, "status": "sequence_found", "kls": seq,
                "evidence": f"{read} of {sha}; CO1..CO{ncos} printed with K column; "
                            f"verbatim multi-level read joined K1/K2 per catalog "
                            f"convention{note}",
                "pages_probed": pages_probed, "title_score": score}
    return {"sid": sid, "status": "no_clean_sequence", "pages_probed": pages_probed}


t0 = time.time()
stats = {"pages": 0, "found": 0, "no_seq": 0, "skipped": 0}
i = start_i
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    while i < len(targets):
        if time.time() - t0 > BUDGET_S:
            print(f"W8B|budget stop at i={i}", flush=True)
            break
        batch = targets[i:i + WORKERS]
        futs = {ex.submit(probe, sid): sid for sid in batch}
        for fut in futs:
            res = fut.result()
            results[res["sid"]] = res
            if res["status"] == "sequence_found":
                stats["found"] += 1
            elif res["status"] in ("no_clean_sequence", "sha_unresolved", "no_resolvable_citation"):
                stats["no_seq"] += 1
            else:
                stats["skipped"] += 1
            stats["pages"] += res.get("pages_probed", 0)
        i += len(batch)
        json.dump({"targets": targets, "i": i, "results": results,
                   "ocr_cache": ocr_cache}, open(CKPT, "w"))
        print(f"W8B|i={i}/{len(targets)} found={stats['found']} pages={stats['pages']} "
              f"cache={len(ocr_cache)} elapsed={time.time() - t0:.0f}s", flush=True)

json.dump({"targets": targets, "i": i, "results": results,
           "ocr_cache": ocr_cache}, open(CKPT, "w"))
json.dump({"run_ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "stats": stats,
           "done": len(results), "total": len(targets)},
          open(f"{BASE}/w8b_ocr_stats.json", "w"), indent=1)
print(f"W8B|PROBE_DONE|i={i}/{len(targets)}|found={stats['found']}|no_seq={stats['no_seq']}|"
      f"pages={stats['pages']}", flush=True)
sys.exit(3 if i < len(targets) else 0)
