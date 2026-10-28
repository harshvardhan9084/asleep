#!/usr/bin/env python3
"""parse_batch.py <staging_dir> <parsed_out>
PyMuPDF-parse each staged PDF into parsed/<stem>.json:
  {"stem","pdf_path","rel","session","sha16","n_pages",
   "pages":[{"no":n,"text":"..."}]}
Prints PARSE|<stem>|<pages>|<sha16>|OK or PARSE|...|FAIL.
"""
import json, os, sys, glob, hashlib
import fitz


def main():
    staging, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    q = json.load(open("/home/z/my-project/work/pipeline_v2/queue.json"))
    rel_by_file = {e["file"]: e for e in q["entries"]}
    fails = 0
    for link in sorted(glob.glob(os.path.join(staging, "*.pdf"))):
        stem = os.path.basename(link)[:-4]
        target = os.path.realpath(link)
        e = rel_by_file.get(target, {})
        try:
            doc = fitz.open(link)
            pages = [{"no": i + 1, "text": doc[i].get_text("text")} for i in range(doc.page_count)]
            n = doc.page_count
            doc.close()
            md5 = hashlib.md5(open(target, "rb").read()).hexdigest()
            rec = {"stem": stem, "pdf_path": target, "rel": e.get("rel", ""),
                   "session": e.get("session", ""), "sha16": md5[:16],
                   "n_pages": n, "pages": pages}
            with open(os.path.join(out, stem + ".json"), "w") as f:
                json.dump(rec, f, ensure_ascii=False)
            print(f"PARSE|{stem}|{n}|{md5[:16]}|OK")
        except Exception as ex:
            fails += 1
            print(f"PARSE|{stem}|0||FAIL|{ex}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
