#!/usr/bin/env python3
"""restore_parsed_fulltexts.py — re-parse every done queue doc whose parsed
fulltext was lost in a workspace reset (B08 evidence: G6 by_sha only covered
the current batch's 10 parses + the 2 companions + 6 B02 leftovers, so
touched rows carrying unit text from B04-B07 docs failed gate G6 containment
against unresolvable citations).

For each queue entry with status done/failed and a resolvable repo PDF:
  - if sha16 already present in parsed/*.json → SKIP
  - else parse with PyMuPDF per-page text and write parsed/<stem>.json in the
    parse_batch.py record format ({rel, file, sha16, pages:[{page,text}]}).
Idempotent. ~40 docs, seconds each.
"""
import glob, hashlib, json, os, sys
import fitz

QUEUE = "/home/z/my-project/work/pipeline_v2/queue.json"
PARSED = "/home/z/my-project/work/pipeline_v2/parsed"
ROOT = "/home/z/my-project/work"


def main():
    q = json.load(open(QUEUE))
    have = set()
    for jf in glob.glob(os.path.join(PARSED, "*.json")):
        if jf.endswith(".fulltext.json") or os.path.basename(jf) == "verify_report.json":
            continue
        try:
            rec = json.load(open(jf))
            if isinstance(rec, dict) and rec.get("sha16"):
                have.add(rec["sha16"])
        except Exception:
            pass
    n_ok = n_skip = n_miss = 0
    for e in q["entries"]:
        st = str(e.get("status", ""))
        if not (st.startswith("done") or st.startswith("failed")):
            continue
        sha = e.get("sha16", "")
        if not sha or sha in have:
            n_skip += 1
            continue
        pdf = os.path.join(ROOT, e["rel"])
        if not os.path.exists(pdf):
            print(f"MISSING_PDF|{e['rel']}")
            n_miss += 1
            continue
        h = hashlib.md5(open(pdf, "rb").read()).hexdigest()
        if h[:16] != sha:
            print(f"SHA_MISMATCH|{e['rel']}|queue={sha}|actual={h[:16]}")
            n_miss += 1
            continue
        doc = fitz.open(pdf)
        pages = [{"page": i + 1, "text": p.get_text() or ""} for i, p in enumerate(doc)]
        doc.close()
        stem = os.path.basename(e["rel"])[:-4]
        rec = {"rel": e["rel"], "file": os.path.basename(e["rel"]), "sha16": sha, "pages": pages}
        with open(os.path.join(PARSED, f"{stem}.json"), "w") as f:
            json.dump(rec, f, ensure_ascii=False)
        # fulltext dump with page markers (same format as dump_fulltext.py)
        with open(os.path.join(PARSED, f"{stem}.fulltext.txt"), "w") as f:
            for p in pages:
                f.write(f"===== PAGE {p['page']} =====\n{p['text']}\n")
        have.add(sha)
        n_ok += 1
    print(f"RESTORED|{n_ok} SKIPPED|{n_skip} MISSING|{n_miss}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
