#!/usr/bin/env python3
"""b92_token_cleanup.py — remove LEGACY bare flag tokens (TYPE_EMPTY /
BOOK_TRUNC / DISPLAY_MISSING) from quality_flags. The audit-of-record
recomputes from values (currently 0 flags); these bare tokens are stale
marks from pre-B92 waves (e.g. DISPLAY_MISSING stamped on 3,078 rows while
only 2 were ever active). Owner directive 2026-11-12: no un-fixable flags
in the final CSV. corrected_/reviewed_ history marks are preserved.
"""
import csv, hashlib, io, re
from collections import Counter

CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
BARE = {"TYPE_EMPTY", "BOOK_TRUNC", "DISPLAY_MISSING"}

orig = open(CSV, "rb").read()
rows = list(csv.DictReader(open(CSV)))
n_rows = 0
removed = Counter()
for r in rows:
    toks = [t.strip() for t in re.split(r"[;,]", r["quality_flags"] or "") if t.strip()]
    keep = [t for t in toks if t not in BARE]
    if keep != toks:
        for t in toks:
            if t in BARE:
                removed[t] += 1
        r["quality_flags"] = ";".join(keep)
        n_rows += 1

buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
w.writeheader()
w.writerows(rows)
new = buf.getvalue().encode("utf-8")

o = list(csv.reader(io.StringIO(orig.decode("utf-8"))))
n_ = list(csv.reader(io.StringIO(new.decode("utf-8"))))
assert len(o) == len(n_)
hdr = o[0]
diff = 0
for a, b in zip(o, n_):
    if a != b:
        cols = [hdr[j] for j, (x, y) in enumerate(zip(a, b)) if x != y]
        assert set(cols) == {"quality_flags"}, cols
        diff += 1
print("rows changed:", diff, "| tokens removed:", dict(removed))
with open(CSV, "wb") as fh:
    fh.write(new)
print("md5:", hashlib.md5(orig).hexdigest(), "->", hashlib.md5(new).hexdigest())
