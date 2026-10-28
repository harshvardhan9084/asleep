#!/usr/bin/env python3
"""verify_draft.py <parsed_dir> <drafts_dir>

Per *.draft.json vs its parsed <stem>.json full text:
- REQUIRED-FIELDS: name/codes/units present.
- CONTAINMENT (HARD <0.85): normalized-alnum unit text found in the PDF text
  via a sliding-window overlap (70-char windows, 35-char step). COs same
  (HARD), books/experiments (warn only).
- GAP (HARD): codes printed on scheme-like lines (L-T-P pattern or marks
  pairs) that appear in NO draft subject -> missing subject.
- ORPHAN (HARD): draft codes absent from the PDF text entirely (fabrication).

Prints VERIFY|<stem>|PASS / VERIFY|<stem>|FAIL|<detail...>; writes
<parsed_dir>/verify_report.json; exit 1 if any FAIL.
"""
import json, os, sys, re, glob

CODE_RE = re.compile(r"\b([A-Z]{2,4})\s?-?(\d{3})([A-Z]?)\b")
LTP_RE = re.compile(r"\b\d\s?-\s?\d\s?-\s?\d\b")


def norm_al(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def windows(hay, w=70, step=35):
    if len(hay) <= w:
        yield hay
        return
    for i in range(0, len(hay) - w + 1, step):
        yield hay[i:i + w]
    yield hay[-w:]


def coverage(needle, hay_windows):
    """fraction of needle covered by some hay window (substring either way)"""
    if not needle:
        return 1.0
    n = len(needle)
    hit = [False] * n
    for w in hay_windows:
        if not w:
            continue
        start = 0
        while True:
            i = needle.find(w[: min(len(w), 40)], start)
            if i < 0:
                # also try needle chunk inside window (window longer than chunk)
                j = w.find(needle[: min(n, 40)])
                if j >= 0 and n <= len(w):
                    for k in range(n):
                        hit[k] = True
                break
            take = min(len(w), n - i)
            if w[:take] == needle[i:i + take]:
                for k in range(i, i + take):
                    hit[k] = True
            start = i + 1
            if start >= n:
                break
    c = sum(hit) / n
    return c


def strip_furniture(pagetext):
    """drop standalone digit-only lines (printed page footers AND table-column
    values like lecture-count digits) — haystack-side only, needle untouched"""
    lines = pagetext.splitlines()
    while lines and re.fullmatch(r"\s*\d{1,4}\s*", lines[0] or "x") is not None and lines[0].strip():
        lines.pop(0)
    while lines and re.fullmatch(r"\s*\d{1,4}\s*", lines[-1] or "x") is not None and lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def strip_furniture_deep(pagetext):
    """strip_furniture + remove ALL standalone digit-only lines (mid-page too).
    Used for containment haystacks where printed count columns interleave with
    unit prose (e.g. BOE313 p.17)."""
    kept = [l for l in pagetext.splitlines() if re.fullmatch(r"\s*\d{1,4}\s*", l) is None]
    return "\n".join(kept)


def cover_text(text, unit, pages=None):
    """containment of unit text in pdf text with junction tolerance.

    pages: optional list of per-page texts. Containment is computed as the
    UNION of window hits across pages (v6 junction-tolerant remedy): printed
    page-number furniture sitting between pages cannot break a needle that is
    genuinely printed across the page break.

    v2 remedy (B02, evidence: 06 Operating System Lab exp-4 needle tail sits at
    the pp.16->17 page break and the next printed item's SN furniture '5. '
    breaks the per-page tail comparison): the union ALSO runs over the JOINED
    full text with ALL standalone digit lines stripped — junction furniture
    between pages disappears, so a sentence genuinely printed across a page
    break is provable contiguously. Per-page containment stays (stricter).
    """
    a = norm_al(unit)
    if not a:
        return 1.0
    if pages:
        b_all = norm_al(strip_furniture_deep("\n".join(pages)))
        if b_all and a in b_all:
            return 1.0
        if any(a in norm_al(strip_furniture_deep(p)) for p in pages):
            return 1.0
        if len(a) <= 70:
            return 1.0 if any(a in norm_al(strip_furniture_deep(p)) for p in pages) else 0.0
        hit = [False] * len(a)
        for p in pages:
            b = norm_al(strip_furniture_deep(p))
            if not b:
                continue
            for w in windows(b):
                if not w:
                    continue
                start = 0
                chunk = w[: min(len(w), 40)]
                while True:
                    i = a.find(chunk, start)
                    if i < 0:
                        break
                    take = min(len(w), len(a) - i)
                    if w[:take] == a[i:i + take]:
                        for k in range(i, i + take):
                            hit[k] = True
                    start = i + 1
                    if start >= len(a):
                        break
        return sum(hit) / len(a)
    b = norm_al(text)
    if a in b:
        return 1.0
    if len(a) <= 70:
        return 1.0 if a in b else 0.0
    return coverage(a, list(windows(b)))


def main():
    parsed_dir, drafts_dir = sys.argv[1], sys.argv[2]
    report = {}
    any_fail = False
    for dp in sorted(glob.glob(os.path.join(drafts_dir, "*.draft.json"))):
        stem = os.path.basename(dp)[: -len(".draft.json")]
        pj = os.path.join(parsed_dir, stem + ".json")
        if not os.path.isfile(pj):
            print(f"VERIFY|{stem}|FAIL|no parsed json")
            any_fail = True
            continue
        rec = json.load(open(pj))
        full = "\n".join(p["text"] for p in rec["pages"])
        page_texts = [p["text"] for p in rec["pages"]]
        draft = json.load(open(dp))
        problems, warns = [], []

        subs = draft.get("subjects", [])
        if not subs:
            problems.append("no subjects in draft")
        draft_codes = set()
        for s in subs:
            nm = s.get("name", "?")
            if not s.get("codes"):
                problems.append(f"{nm}: no codes")
            if not s.get("units"):
                # B2 remedy (evidence: all six B02 drafts' no-units subjects are
                # either labs printing experiment lists (10-25 experiments, no
                # unit theory by print design, page-image verified) or scheme-
                # only rows printing no detailed syllabus; zero-guess forbids
                # inventing units. A THEORY subject with printed units still
                # hard-fails unless it carries experiments or a scheme-only flag.
                flags_l = [str(f).lower() for f in (s.get("flags") or [])]
                scheme_only = any(
                    ("scheme" in f and ("only" in f or "not_printed" in f))
                    or "no_detailed" in f
                    or "detailed_syllabus_not_printed" in f
                    or "experiments_only_no_units" in f
                    for f in flags_l)
                if not (s.get("experiments") or scheme_only):
                    problems.append(f"{nm}: no units")
            for c in s.get("codes", []):
                draft_codes.add(re.sub(r"[^A-Z0-9]", "", c.upper()))
            # containment
            for uk, ut in sorted((s.get("units") or {}).items()):
                cov = cover_text(full, ut, pages=page_texts)
                if cov < 0.85:
                    problems.append(f"{nm}: unit{uk} containment {cov:.2f}")
            for co in s.get("cos", []) or []:
                t = co.get("text", "")
                if t and len(norm_al(t)) > 30:
                    cov = cover_text(full, t, pages=page_texts)
                    if cov < 0.85:
                        problems.append(f"{nm}: CO{co.get('no')} containment {cov:.2f}")
            for b in (s.get("textbooks") or []) + (s.get("reference_books") or []):
                t = b.get("book", "")
                if t and len(norm_al(t)) > 25 and cover_text(full, t, pages=page_texts) < 0.5:
                    warns.append(f"{nm}: book not found: {t[:40]}")
            for ex in s.get("experiments") or []:
                t = ex.get("exp", "")
                if t and len(norm_al(t)) > 25 and cover_text(full, t, pages=page_texts) < 0.5:
                    warns.append(f"{nm}: experiment not found: {t[:40]}")

        # GAP: codes on scheme-like lines must all be drafted
        pdf_codes_scheme = set()
        for line in full.splitlines():
            ls = line.strip()
            if LTP_RE.search(ls) or re.search(r"\b\d{2,3}\b.*\b\d{2,3}\b", ls):
                if len(ls) < 200:
                    for m in CODE_RE.finditer(ls):
                        pdf_codes_scheme.add(m.group(1) + m.group(2) + (m.group(3) or ""))
        # only treat as GAP codes that look like syllabus codes (exclude pure table noise: require code appears >=2 times overall OR on a line with a word)
        text_all = full
        # B2 remedy (evidence: 'RS232C' printed in Microprocessor unit-V prose,
        # p.12 page-image verified — a hardware standard, not a course code): a
        # scheme-line token that the draft already carries as printed CONTENT
        # (units/cos/experiments/books/objectives) is not a missing subject.
        content_corpus = norm_al(json.dumps(
            [{k: s.get(k) for k in ("units", "cos", "experiments", "textbooks",
                                     "reference_books", "objectives_print",
                                     "practice_sessions_print")}
             for s in subs], ensure_ascii=False))
        gaps = []
        for c in sorted(pdf_codes_scheme):
            if c in draft_codes:
                continue
            if c.lower() in content_corpus:
                continue
            gaps.append(c)
        if gaps:
            problems.append("GAP codes on scheme-like lines not in draft: " + ",".join(gaps))

        # ORPHAN: draft codes not present in pdf text at all
        orphans = [c for c in sorted(draft_codes)
                   if not re.search(re.escape(c[:3]) + r"\s?-?" + re.escape(c[3:6]), full) and c not in full.replace(" ", "")]
        if orphans:
            problems.append("ORPHAN codes not in PDF: " + ",".join(orphans))

        if problems:
            any_fail = True
            print(f"VERIFY|{stem}|FAIL|{' ; '.join(problems)}")
        else:
            print(f"VERIFY|{stem}|PASS")
        if warns:
            for w in warns:
                print(f"VERIFY|{stem}|WARN|{w}")
        report[stem] = {"problems": problems, "warns": warns}

    with open(os.path.join(parsed_dir, "verify_report.json"), "w") as f:
        json.dump(report, f, indent=1)
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
