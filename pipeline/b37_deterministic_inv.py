#!/usr/bin/env python3
"""b37_deterministic_inv.py <stem> — build a DETERMINISTIC subject inventory
for a doc whose mercury-3 inventory is unstable (recorded B37 engine lesson:
open-ended inventory re-asks returned 50/1/9/4 subjects for the same PDF).

Method (zero-guessing, print-anchored):
  1. unit-bearing pages: >=3 standalone roman-numeral lines (lecture-plan
     tables print unit numbers I..V on their own lines) or >=2 `Unit <roman>`
     inline markers;
  2. detail headers: `CODE<spaces>Name` at line start on a unit-bearing page
     (or the page right before one) -> class=detail at that page;
  3. scheme pages ("Evaluation Scheme"): remaining codes paired with the name
     lines that FOLLOW the code line (flattened-table pairing; the row's name
     runs until the L-T-P line / next code / row number);
  4. runs of >=3 consecutive numbers with the same prefix+suffix collapse into
     ONE slot print (e.g. 'EOE-031 to EOE-038', slot_print=true);
  5. ONE mercury-3 code-anchored annotation call fills any scheme name the
     pairing missed.
Output: work/pipeline_v2/inv/<stem>.inv.json
"""
import json, os, re, sys
sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import mercury_engine as me

stem = sys.argv[1]
parsed_dir = "/home/z/my-project/work/pipeline_v2/parsed"
fulltext = open(f"{parsed_dir}/{stem}.fulltext.txt").read()
PAGES = me.pages_of(fulltext)
PAGEMAP = dict(PAGES)
os.makedirs("/home/z/my-project/work/pipeline_v2/inv", exist_ok=True)

CODE = r"([A-Z]{2,4})\s?-?(\d{3})([A-Z]?)"
LTP_LINE = re.compile(r"^\s*\d{1,2}\s+\d{1,2}\s+\d{1,2}\s*$")

scheme_pages = {p for p, t in PAGES if re.search(r"Evaluation\s+Scheme|Study\s+and\s+Evaluation", t, re.I)}
unit_bearing = {}
for pno, ptext in PAGES:
    standalone = len(re.findall(r"^\s*(?:I|II|III|IV|V)\s*$", ptext, re.M))
    inline = len(re.findall(r"Unit\s*[-–—:]?\s*(?:I{1,3}|IV|V|\d{1,2})\b", ptext, re.I))
    unit_bearing[pno] = (standalone >= 3 and pno not in scheme_pages) or inline >= 2

detail, scheme = {}, {}
CODELINE = re.compile(r"^\s*\(?([A-Z]{2,4}\s?-?\d{3}[A-Z]?(?:\s*/\s*[A-Z]{2,4}\s?-?\d{3}[A-Z]?)*)\)?[\s:.]*$")
NAMELINE = re.compile(r"^[A-Za-z][A-Za-z0-9 ,&()/\.\-–—:'\u2019]{3,60}$")

def _codes_of(cline):
    out = []
    for tok in cline.replace("(", "").replace(")", "").split("/"):
        m = re.match(r"^\s*([A-Z]{2,4})\s?-?(\d{3})([A-Z]?)\s*$", tok)
        if m:
            out.append(m.group(1) + m.group(2) + (m.group(3) or ""))
    return out

def _add_detail(ncode, cp, name, pno):
    if ncode in detail:
        return
    detail[ncode] = {"class": "detail", "code_print": cp, "name_print": name.strip()[:70], "page": pno}

for pno, ptext in PAGES:
    if pno in scheme_pages:
        continue
    near_unit = unit_bearing.get(pno) or unit_bearing.get(pno + 1)
    if not near_unit:
        continue
    lines = [ln.strip() for ln in ptext.splitlines()]
    # (a) same-line header: CODE  Name   |   Name (CODE)
    for m in re.finditer(rf"^\s*{CODE}\s{{1,}}([A-Za-z][^\n]{{3,70}})$", ptext, re.M):
        a, b, c, name = m.groups()
        _add_detail(a + b + (c or ""), (a + " " + b + (c or "")).strip(), name, pno)
    for m in re.finditer(rf"^\s*([A-Za-z][^\n]{{3,60}}?)\s*\(\s*{CODE}\s*\)\s*$", ptext, re.M):
        name, b, c = m.group(1), m.group(2), m.group(3) or ""
        _add_detail(b + c, b + " " + c, name, pno)
    # (a3) dual/single code prefix + colon separator: 'NAS-104/NAS-204 : NAME'
    for m in re.finditer(r"^\s*([A-Z][A-Z0-9\s/\-–]{4,26}?)\s*[:.\-–]\s{0,2}([A-Za-z][^\n]{3,70})$", ptext, re.M):
        pref, name = m.group(1).strip(), m.group(2)
        toks = re.findall(r"([A-Z]{2,4})\s?-?(\d{3})([A-Z]?)", pref)
        if not toks:
            continue
        name = re.split(r"\s{2,}L\s+T\s+P\b|\s+L\s+T\s+P\s+\[", name)[0].strip()
        codes = [t[0] + t[1] + (t[2] or "") for t in toks]
        _add_detail(codes[0], "/".join(codes), name, pno)
    # (a4) numbered-list header with code in parens: '4. Fabric Manufacture-II (ETE402)'
    for m in re.finditer(r"^\s*\d{1,2}(?:\.\d{1,2})?[\.\)]\s+([A-Za-z][^\n]{3,64}?)\s*\(\s*([A-Z]{2,4}\s?-?\s?\d{3}[A-Z]?(?:\s*/\s*[A-Z]{2,4}\s?-?\s?\d{3}[A-Z]?)*)\s*\)\s*([^\n]{0,40})$", ptext, re.M):
        name, cp, tail = m.group(1), m.group(2), (m.group(3) or "").strip()
        toks = re.findall(r"([A-Z]{2,4})\s?-?\s?(\d{3})([A-Z]?)", cp)
        if not toks:
            continue
        name = re.split(r"\s{2,}L\s+T\s+P\b", name)[0].strip()
        codes = [t[0] + t[1] + (t[2] or "") for t in toks]
        ent = {"class": "detail", "code_print": "/".join(codes), "name_print": name.strip()[:70], "page": pno}
        if tail and re.search(r"as provided|as per|U\.?P\.?T\.?U|BoS", tail, re.I):
            ent["note"] = tail[:60]
        if codes[0] not in detail:
            detail[codes[0]] = ent
    # (b) standalone code line with the name on an ADJACENT line (doc-03 style)
    for idx, ln in enumerate(lines):
        m = CODELINE.match(ln)
        if not m:
            continue
        codes = _codes_of(m.group(1))
        if not codes or any(c in detail for c in codes):
            continue
        cand = None
        for j in (idx + 1, idx + 2, idx - 1):
            if 0 <= j < len(lines):
                t = lines[j]
                if NAMELINE.match(t) and not CODELINE.match(t) and not LTP_LINE.match(t) \
                   and not re.match(r"^\d", t) and not re.search(r"Unit\b", t, re.I):
                    cand = t
                    break
        if cand:
            cp = "/".join(codes)
            _add_detail(codes[0], cp, cand, pno)

detail_norms = set(detail)
# scheme-page pairing: name lines FOLLOW the code line until LTP / next code / row no
for pno in sorted(scheme_pages):
    lines = [ln.strip() for ln in PAGEMAP[pno].splitlines()]
    for idx, ln in enumerate(lines):
        m = re.match(rf"^(?:{CODE})\b(.*)$", ln)
        if not m:
            continue
        a, b, c = m.group(1), m.group(2), m.group(3) or ""
        ncode = a + b + c
        if ncode in detail_norms:
            continue
        rest = m.group(4).strip(" :-–")
        name_parts = [rest] if len(rest) >= 3 else []
        for nxt in lines[idx + 1: idx + 5]:
            if not nxt or LTP_LINE.match(nxt):
                break
            if re.match(rf"^{CODE}\b", nxt) or re.match(r"^\d{1,2}$", nxt):
                break
            if re.match(r"^\d", nxt) and len(nxt) < 12:
                break
            name_parts.append(nxt)
            if len(" ".join(name_parts)) > 60:
                break
        nm = " ".join(name_parts).strip()
        if ncode not in scheme or (nm and not scheme[ncode]["name_print"]):
            scheme[ncode] = {"class": "scheme_only", "code_print": ncode,
                             "name_print": nm[:70], "page": pno}

inv = list(detail.values()) + list(scheme.values())
print(f"DETERMINISTIC|{stem}|detail={len(detail)} scheme={len(scheme)} "
      f"(slot prints: {sum(1 for x in scheme.values() if x.get('slot_print'))}) "
      f"scheme pages: {sorted(scheme_pages)}")

need = [x for x in scheme.values() if not x["name_print"]]
if need:
    lst = "\n".join(f"{x['code_print']} (page {x['page']})" for x in need)
    pages_txt = "\n\n".join(t for p, t in PAGES if p in {x["page"] for x in need})
    prompt = ("AKTU scheme table lines follow. For EACH course code below, copy the printed "
              "Subject Name EXACTLY as printed in that code's table row (verbatim; keep "
              "slashes like 'Sociology/ Cyber Security'; join wrapped lines with a space; a "
              "slot print like 'EOE-031 to EOE-038' gets the printed elective-group name). "
              "Return JSON {\"names\": [{\"code_print\":\"...\",\"name_print\":\"...\"}]} "
              "covering every listed code.\nCODES:\n" + lst + "\n=== SCHEME PAGES ===\n" + pages_txt)
    try:
        out = me.chat([{"role": "system", "content": me.SYS},
                       {"role": "user", "content": prompt}], max_tokens=4000)
        rows = out.get("names") if isinstance(out, dict) else out
        if isinstance(rows, list):
            by_code = {}
            for r in rows:
                if isinstance(r, dict):
                    nm = (r.get("name_print") or "").strip()
                    for cp in re.findall(r"[A-Z]{2,4}\s?-?\d{3}[A-Z]?", (r.get("code_print") or "")):
                        by_code.setdefault(re.sub(r"[^A-Z0-9]", "", cp), nm)
            hit = 0
            for x in need:
                key = re.sub(r"[^A-Z0-9]", "", x["code_print"].split(" to ")[0])
                nm = by_code.get(key) or ""
                if nm:
                    x["name_print"] = nm
                    hit += 1
            print(f"ANNOTATED|{hit}/{len(need)} scheme names")
    except Exception as e:  # noqa: BLE001
        print("ANNOTATE-FAIL|", repr(e)[:120])

OUT = f"/home/z/my-project/work/pipeline_v2/inv/{stem}.inv.json"
json.dump(inv, open(OUT, "w"), indent=1, ensure_ascii=False)
print("INV|" + OUT)
