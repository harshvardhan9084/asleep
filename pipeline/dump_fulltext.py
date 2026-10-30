#!/usr/bin/env python3
"""dump_fulltext.py <staging_dir> <parsed_out>
Write parsed/<stem>.fulltext.txt from parsed/<stem>.json with page markers.
Prints FULLTEXT|<stem>|<chars>|OK.
"""
import json, os, sys, glob

MARK = "\n\n===== PAGE {n} =====\n\n"


def main():
    staging, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for j in sorted(glob.glob(os.path.join(out, "*.json"))):
        stem = os.path.basename(j)[:-5]
        if stem.endswith(".fulltext"):
            continue
        rec = json.load(open(j))
        if not isinstance(rec, dict) or "pages" not in rec:
            print(f"SKIP|{stem}|not-a-parse-record")
            continue
        parts = []
        for p in rec["pages"]:
            n = p.get("no", p.get("page"))  # parse_batch writes "no"; restore_parsed_fulltexts (pre-fix) wrote "page"
            parts.append(MARK.format(n=n).strip("\n") + "\n" + p["text"])
        txt = "\n\n".join(parts)
        fp = os.path.join(out, stem + ".fulltext.txt")
        with open(fp, "w") as f:
            f.write(txt)
        print(f"FULLTEXT|{stem}|{len(txt)}|OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
