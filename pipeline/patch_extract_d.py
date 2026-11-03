#!/usr/bin/env python3
"""Patch _s05d/extract_d.py: fix mangled T[m] indices + close UNIT_OVERRIDES dict."""
import re

P = "/home/z/my-project/work/pipeline_v2/drafts/_s05d/extract_d.py"
src = open(P, encoding="utf-8").read()

n1 = src.count("T] !=")
n2 = src.count("T].strip()")
print("occurrences:", n1, n2)

src = src.replace("T] !=", "T[m] !=").replace("T].strip()", "T[m].strip()")

# close UNIT_OVERRIDES: insert '}' before 'def extract_header' if dict unclosed
if "\ndef extract_header" in src:
    i = src.index("'BP606T': {")
    j = src.index("\ndef extract_header", i)
    if not src[i:j].rstrip().endswith("},"):
        print("WARN: BP606T entry tail:", repr(src[i:j][-60:]))
    if re.search(r"\n\}\n\ndef extract_header", src) is None:
        src = src[:j] + "\n}\n" + src[j + 1:]
        print("dict closed")
else:
    print("WARN: no extract_header def found")

open(P, "w", encoding="utf-8").write(src)

import ast
ast.parse(open(P, encoding="utf-8").read())
print("syntax OK")
