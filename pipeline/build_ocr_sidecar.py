#!/usr/bin/env python3
"""build_ocr_sidecar.py <parsed_json> — render every page and OCR it into a sidecar.

Evidence base (B03): document 08 (BPharm 2026-27, 295pp) has DOCUMENTED PyMuPDF
silent text-layer drops (segments' page-image recoveries: pp.11/12/15/20/22/23/
25/33, 97/100/102/104/105/108/110/112/114/116, 123/124/127/132/133/135/140/142/
146, 177/180/184/188/190/191/194, BP708T-AEC6 units I-V, and more). Draft text
transcribed from the visible print can therefore never be contained in the text
layer alone. RULES §6 makes the visible print authoritative — so the verifier
gets an OCR sidecar: a second, independently-derived haystack from the same
pages (pdftoppm 300dpi + tesseract). Containment passes if the needle is in the
text layer OR the OCR layer; fabrication still fails (the OCR of the true print
does not contain invented text).

Outputs: <stem>.ocr.json ({"stem","sha16","n_pages","pages":[{"page","text"}]})
         <stem>.ocr.txt  (===== PAGE n ===== joined, same shape as fulltext.txt)
"""
import json, os, subprocess, sys, tempfile
from concurrent.futures import ProcessPoolExecutor

PYMUPDF = True
try:
    import fitz  # PyMuPDF for rendering (already a pipeline dependency)
except ImportError:
    PYMUPDF = False


def ocr_page(args):
    pdf, pno, dpi = args
    import fitz
    doc = fitz.open(pdf)
    page = doc[pno]
    pix = page.get_pixmap(dpi=dpi)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        pix.save(tf.name)
        png = tf.name
    try:
        out = subprocess.run(["tesseract", png, "stdout", "--psm", "4", "-l", "eng"],
                             capture_output=True, text=True, timeout=120)
        text = out.stdout
    finally:
        os.unlink(png)
    return pno, text


def main():
    parsed = sys.argv[1]
    rec = json.load(open(parsed))
    stem, pdf, sha = rec["stem"], rec["pdf_path"], rec["sha16"]
    outdir = os.path.dirname(parsed)
    pages = rec["pages"]
    n = len(pages)
    # optional page selection: --pages 1,2,3 (1-based) or --pages-file <file>
    want = None
    if "--pages" in sys.argv:
        want = {int(x) for x in sys.argv[sys.argv.index("--pages") + 1].split(",")}
    elif "--pages-file" in sys.argv:
        want = {int(x) for x in open(sys.argv[sys.argv.index("--pages-file") + 1]).read().split()}
    idxs = sorted([x - 1 for x in want]) if want else list(range(n))
    # merge with an existing sidecar (keep previously OCR'd pages)
    merged = {}
    sidecar_path = os.path.join(outdir, f"{stem}.ocr.json")
    if os.path.isfile(sidecar_path):
        try:
            for p in json.load(open(sidecar_path)).get("pages", []):
                merged[p["page"]] = p["text"]
        except Exception:
            pass
    jobs = [(pdf, i, 300) for i in idxs]
    results = {}
    with ProcessPoolExecutor(max_workers=8) as ex:
        for pno, text in ex.map(ocr_page, jobs, chunksize=1):
            results[pno] = text
    for pno, text in results.items():
        merged[pno + 1] = text
    ocr_pages = [{"page": p, "text": merged[p]} for p in sorted(merged)]
    json.dump({"stem": stem, "sha16": sha, "n_pages": n, "pages": ocr_pages},
              open(sidecar_path, "w"), ensure_ascii=False)
    with open(os.path.join(outdir, f"{stem}.ocr.txt"), "w") as f:
        for p in ocr_pages:
            f.write(f"===== PAGE {p['page']} =====\n{p['text']}\n")
    empty = sum(1 for p in ocr_pages if not p["text"].strip())
    print(f"OCR|{stem}|pages={len(ocr_pages)}/{n}|empty={empty}|chars={sum(len(p['text']) for p in ocr_pages)}")


if __name__ == "__main__":
    main()
