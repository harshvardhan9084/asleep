#!/usr/bin/env python3
"""b92_te_directive_complete.py — close the TYPE_EMPTY gap: the audit
recomputes flags from values (token drift ignored), so the owner-directive
list must come from the audit's active set, not from CSV tokens. Adds the
missing sids to b92_owner_directive.json and the reviewed_ token to their rows.
"""
import csv, hashlib, io, json, re

CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
DIR_J = "/home/z/my-project/work/pipeline_v2/b92_owner_directive.json"
AF = "/home/z/my-project/work/pipeline_v2/audit_flags.json"

def slugify(s):
    return re.sub(r"\s+", "-", re.sub(r"[^a-z0-9 ]", "", (s or "").lower())).strip()

af = json.load(open(AF))
te_sids = [k for k, fl in af["rows"].items() if any(f.get("rule") == "TYPE_EMPTY" for f in fl)]
print("audit TYPE_EMPTY sids:", len(te_sids))

d = json.load(open(DIR_J))
have = set(d.get("type_empty_removed", []))
missing = [s for s in te_sids if s not in have]
print("missing from directive:", len(missing))
d["type_empty_removed"] = sorted(have | set(te_sids))
json.dump(d, open(DIR_J, "w"), indent=1)

orig = open(CSV, "rb").read()
rows = list(csv.DictReader(open(CSV)))
n_tok = 0
for r in rows:
    if slugify(r["subject_name"]) in missing and "reviewed_TYPE_EMPTY_owner_directive" not in (r["quality_flags"] or ""):
        toks = [t.strip() for t in re.split(r"[;,]", r["quality_flags"] or "") if t.strip()]
        toks.append("reviewed_TYPE_EMPTY_owner_directive")
        r["quality_flags"] = ";".join(toks)
        n_tok += 1
buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
w.writeheader()
w.writerows(rows)
new = buf.getvalue().encode("utf-8")

o = list(csv.reader(io.StringIO(orig.decode("utf-8"))))
n_ = list(csv.reader(io.StringIO(new.decode("utf-8"))))
assert len(o) == len(n_)
hdr = o[0]
diff = Counter_ = 0
for a, b in zip(o, n_):
    if a != b:
        cols = [hdr[j] for j, (x, y) in enumerate(zip(a, b)) if x != y]
        assert set(cols) == {"quality_flags"}, cols
        diff += 1
print("rows token-updated:", n_tok, "| diff rows:", diff)
with open(CSV, "wb") as fh:
    fh.write(new)
print("md5:", hashlib.md5(orig).hexdigest(), "->", hashlib.md5(new).hexdigest())
