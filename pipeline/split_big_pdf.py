#!/usr/bin/env python3
"""split_big_pdf.py <stem> <parsed_dir> <frags_dir> <ranges CSV like 1-50,51-100>

Splits a parsed record into page-range fragments for the S05 large-PDF
segmentation pattern (proven in batch S05/B02-era runs):
- <frags_dir>/<stem>__frag<i>.parsed.json   (same schema, pages subset)
- <frags_dir>/<stem>__frag<i>.fulltext.txt  (===== PAGE n ===== markers)
Each fragment subagent reads ONLY its own fragment files + the PDF page
images for its range; fragment drafts are .frag.json (never .draft.json so
the merge glob cannot see them) and are deterministically concatenated by
concat_fragments.py into the single drafts/<stem>.draft.json.
"""
import json, os, sys


def main():
    stem, parsed_dir, frags_dir, ranges_csv = sys.argv[1:5]
    rec = json.load(open(os.path.join(parsed_dir, stem + ".json")))
    os.makedirs(frags_dir, exist_ok=True)
    ranges = []
    for part in ranges_csv.split(","):
        a, b = part.split("-")
        ranges.append((int(a), int(b)))
    meta = {k: rec[k] for k in ("pdf_path", "rel", "session", "sha16", "n_pages") if k in rec}
    for i, (a, b) in enumerate(ranges, 1):
        pages = [p for p in rec["pages"] if a <= p["no"] <= b]
        frag = dict(meta)
        frag.update({"stem": f"{stem}__frag{i}", "base_stem": stem, "frag_no": i,
                     "page_from": a, "page_to": b, "n_pages_frag": len(pages),
                     "pages": pages})
        jp = os.path.join(frags_dir, f"{stem}__frag{i}.parsed.json")
        with open(jp, "w") as f:
            json.dump(frag, f, ensure_ascii=False)
        tp = os.path.join(frags_dir, f"{stem}__frag{i}.fulltext.txt")
        with open(tp, "w") as f:
            for p in pages:
                f.write(f"\n===== PAGE {p['no']} =====\n")
                f.write(p["text"])
        size = os.path.getsize(tp)
        print(f"FRAG|{stem}__frag{i}|pages {a}-{b}|n={len(pages)}|fulltext_bytes={size}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
