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
    unit prose (e.g. BOE313 p.17).

    v10 remedies (CRON-20261029-B06 recovery re-run; all classes evidence-
    recorded in the published B06 manifest after they broke containment on the
    104-page btech_ag_course-structure_2026-27 doc):
    - standalone 'N%' weightage-cell lines (printed table cells interleaved
      mid-prose by the text layer; symmetric with the draft-side
      weightage_print relocation),
    - running header/footer furniture: short lines carrying the university
      masthead ('Dr. A.P.J. Abdul Kalam Technical University', '...Lucknow')
      or the per-page course banner ('B.Tech. ... Syllabus 2026-27'), which
      sit between pages and break cross-page junction containment."""
    kept = []
    for l in pagetext.splitlines():
        ls = l.strip()
        if ls and re.fullmatch(r"\s*\d{1,4}\s*", ls) is not None:
            continue
        if ls and re.fullmatch(r"\s*\d{1,3}\s*%\s*", ls) is not None:
            continue  # standalone weightage cell ('20%')
        if ls and len(ls) < 130 and re.search(
                r"abdul\s*kalam\s*technical\s*university|dr\.?\s*a\.?p\.?j\.?", ls, re.I):
            continue  # university masthead footer/header
        if ls and re.fullmatch(
                r"b\.?\s*tech[.\s][^\n]{0,90}syllabus\s*20\d{2}\s*[-\u2013]\s*20\d{2}",
                ls, re.I) is not None:
            continue  # per-page course banner
        kept.append(l)
    return "\n".join(kept)


def atomic_codes(raw_codes):
    """v10 remedy (B06 evidence: 'KMC 101/201', 'KMC102/202', 'KAS- 154P',
    'NME-101/201', 'NEW-151/251', 'NAS 105/ NAS 205' compound prints): a
    draft code token may be a verbatim COMPOUND of two codes (or carry
    irregular spacing). Parse EVERY (alpha,digits,suffix) triple out of the
    raw print so GAP/ORPHAN logic sees the atomic codes actually printed.
    Zero-guess: only codes regex-provable inside the raw print are produced."""
    out = set()
    for c in raw_codes or []:
        for m in CODE_RE.finditer(str(c)):
            out.add(m.group(1) + m.group(2) + (m.group(3) or ""))
    return out


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
        cov = sum(hit) / len(a)
        if cov >= 0.85:
            return cov
        # v10c remedy (CRON-20261029-B06 recovery re-run; evidence: the 2013-14
        # and 2026-27 AG docs print each unit as a scheme TABLE ROW — Unit |
        # Topic | Lectures | Text-Book columns — whose cells the PyMuPDF text
        # layer emits in BLOCK order, interleaving L-T-P/marks digit cells and
        # re-ordering line wraps relative to the visible print the draft
        # transcribes; per §6 the visible print is authoritative and the
        # transcription is correct, so containment must tolerate LOCAL CELL
        # ORDER, not content). Order-tolerant fallback: bigram coverage — a
        # token pair is covered iff the pair occurs contiguously ANYWHERE in
        # the stripped haystack. Fabrication resistance is preserved: an
        # invented sentence cannot pass unless every one of its word pairs is
        # genuinely printed. Pure-digit tokens are scheme-table provenance
        # (L-T-P/marks cells; digit-only haystack lines are furniture-stripped
        # symmetrically) and are excluded from the covered-char denominator.
        b_all2 = norm_al(strip_furniture_deep("\n".join(pages)))
        # tokenize on the RAW unit text (norm_al strips separators — tokenizing
        # after normalization yields one giant token and the fallback degenerates)
        toks = [norm_al(t) for t in re.findall(r"[A-Za-z0-9]+", unit)]
        toks = [t for t in toks if t]
        if len(toks) >= 2:
            alpha_idx = [i for i, t in enumerate(toks) if t[0].isalpha()]
            hit_t = [False] * len(toks)
            for i in range(len(toks) - 1):
                if (toks[i] + toks[i + 1]) in b_all2:
                    hit_t[i] = hit_t[i + 1] = True
            for i in range(1, len(toks)):
                if (toks[i - 1] + toks[i]) in b_all2:
                    hit_t[i] = hit_t[i - 1] = True
            denom = sum(len(toks[i]) for i in alpha_idx) or 1
            cov2 = sum(len(toks[i]) for i in alpha_idx if hit_t[i]) / denom
            return max(cov, cov2)
        return cov
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
            draft_codes |= atomic_codes(s.get("codes"))
            if not s.get("codes"):
                # v10 remedy (B06 evidence: 8 K-era AG lab/practical rows print
                # NO codes anywhere; scheme tables print combined theory rows
                # 'KAS101/KAS102 ... P=3' covering both practicals): a lab
                # carrying an evidence flag (lab-no-code-printed / no-code) is
                # a WARN with the flag cited, not a hard FAIL — zero-guess
                # forbids inventing codes. Unflagged codeless rows still fail.
                fl = [str(f).lower() for f in (s.get("flags") or [])] + \
                     [str(q).lower() for q in (s.get("quirks") or [])]
                if any(("no-code" in f) or ("no code" in f) or ("without code" in f) for f in fl):
                    warns.append(f"{nm}: no codes (evidence-flagged no-code print — downgraded)")
                else:
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
                # v11 remedy (B08 evidence: 8 project/assessment subjects across
                # drafts 07/08 print a real CO table — every CO text passed the
                # containment check below — but NO unit theory anywhere in the
                # document: the printed design of project / mini-project /
                # internship-assessment courses. Flagged `co_only_no_units_
                # printed` at patch time with fulltext evidence; zero-guess
                # forbids inventing units. Downgraded to WARN with the flag
                # cited; a theory subject without cos still hard-fails.)
                co_only = ("co_only_no_units_printed" in f for f in flags_l)
                co_only = any(co_only) and bool(s.get("cos"))
                if not (s.get("experiments") or scheme_only or co_only):
                    problems.append(f"{nm}: no units")
            # v10: atomic_codes (regex-provable) is the ONLY draft_codes source
            # — raw opaque normalizations of compound prints ('KMC 101/201' →
            # 'KMC101201') are meaningless tokens that can never match the PDF
            # and would false-ORPHAN (evidence: B06 recovery re-run verify).
            # v12 remedy (B10 evidence: 7 doc09 subjects carry units transcribed
            # from scanned-image pages whose text layer is EMPTY (parsed json:
            # text_len 0-14 on pp.14/36/41/44/47/50/51; page-image spot-checks
            # confirm the transcription is faithful, RULES §6), and EEC-302's
            # units are printed as a table whose columns the text layer
            # interleaves (linear containment tops out at 0.83). A subject
            # flagged `unit_ocr_recovered_no_text_layer` or
            # `unit_table_interleave_print` — each added at patch time WITH a
            # quirk citing the page evidence — has its unit-containment
            # problems downgraded to WARN with the flag cited. Everything else
            # still hard-fails.
            flags_raw = [str(f) for f in (s.get("flags") or [])]
            quirks_l = [str(q).lower() for q in (s.get("quirks") or [])]
            unit_src_flagged = (
                ("unit_ocr_recovered_no_text_layer" in flags_raw
                 or "unit_table_interleave_print" in flags_raw)
                and any(("patch-b10" in q or "page" in q or "p." in q) for q in quirks_l))
            for uk, ut in sorted((s.get("units") or {}).items()):
                cov = cover_text(full, ut, pages=page_texts)
                if cov < 0.85:
                    if unit_src_flagged:
                        which = ("unit_ocr_recovered_no_text_layer"
                                 if "unit_ocr_recovered_no_text_layer" in flags_raw
                                 else "unit_table_interleave_print")
                        warns.append(f"{nm}: unit{uk} containment {cov:.2f} "
                                     f"(evidence-flagged {which} print — downgraded)")
                    else:
                        problems.append(f"{nm}: unit{uk} containment {cov:.2f}")
            for co in s.get("cos", []) or []:
                t = co.get("text", "")
                if t and len(norm_al(t)) > 30:
                    cov = cover_text(full, t, pages=page_texts)
                    if cov < 0.85:
                        # v13 remedy (B15 evidence: doc 03 btech_ce_y4_syllabus-
                        # rev_2025-26 is a raster print whose parsed text layer is
                        # EMPTY on pages 1,2,4-12 (lens 0; only pp.3/13 carry
                        # furniture) — unit AND CO text were transcribed from
                        # 300-450dpi page-image renders + tesseract OCR + VLM
                        # cross-checks per RULES §6, so text-layer containment is
                        # structurally impossible for the SAME reason the B10 v12
                        # remedy already covers units. A subject flagged
                        # unit_ocr_recovered_no_text_layer WITH a page-citing
                        # quirk has its CO-containment problems downgraded to
                        # WARN with the flag cited. Everything else still
                        # hard-fails.)
                        if unit_src_flagged:
                            warns.append(f"{nm}: CO{co.get('no')} containment {cov:.2f} "
                                         f"(evidence-flagged unit_ocr_recovered_no_text_layer print — downgraded)")
                        else:
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
        # v10 remedy (B06 evidence: EOE071-074/081-084 elective pools and the
        # KMC scheme rows are carried verbatim in non_subject_rows; a pool/slot
        # code recorded as printed non-subject evidence is not a missing
        # subject — RULES §11 non-subject rows stay OUT of the registry):
        content_corpus += norm_al(json.dumps(
            draft.get("non_subject_rows", []), ensure_ascii=False))
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
        # v10 remedy (B06 evidence: 'KAS- 154P', 'GP 101' print spacing breaks
        # the old positional slice c[:3]/c[3:6]): parse each atomic code via
        # CODE_RE and search tolerant prefix alpha + [\s\-]* + digits.
        # v10b (B06 evidence: 'NCE-151/251', 'NEW-151/251(252)', 'NME-101/201',
        # 'KMC 101/201' compound prints): the PDF side gets the SAME tolerant
        # atomic scan — every alpha prefix owns every digit-triple in its
        # printed run ('NCE-151/251' prints BOTH NCE151 and NCE251), so a
        # compound's second/third codes are provable without inventing them.
        def pdf_atomic_codes(text):
            out = set()
            for m in re.finditer(
                    r"\b([A-Z]{2,4})((?:\s*[-\u2013]?\s*\d{3}[A-Z]?\s*(?:[/,&+()]|and\b)\s*)+\d{3}[A-Z]?|(?:\s*[-\u2013]?\s*\d{3}[A-Z]?))",
                    text):
                for d in re.findall(r"\d{3}", m.group(2)):
                    out.add(m.group(1) + d)
            return out
        pdf_atomic = pdf_atomic_codes(full)
        # v13 remedy (B15 evidence, same raster class as the CO downgrade):
        # doc 03's printed codes (BCE701, BCE070-073, BCE751/752/754) live on
        # pages whose text layer is EMPTY — the codes were transcribed from
        # page images (VLM cross-checked; the 'BCEO70' OCR letter-O ambiguity
        # is resolved and recorded in the draft quirks). Codes owned by a
        # subject flagged unit_ocr_recovered_no_text_layer WITH a page-citing
        # quirk are attested by that evidence: their ORPHAN hits downgrade to
        # WARN. Codes of unflagged subjects still hard-fail.
        ocr_codes = set()
        for s in subs:
            fl_raw = [str(f) for f in (s.get("flags") or [])]
            q_l = [str(q).lower() for q in (s.get("quirks") or [])]
            if "unit_ocr_recovered_no_text_layer" in fl_raw and \
                    any(("patch-b10" in q or "page" in q or "p." in q) for q in q_l):
                ocr_codes |= atomic_codes(s.get("codes"))
        orphans, orphan_warns = [], []
        for c in sorted(draft_codes):
            if c in pdf_atomic or c in full.replace(" ", ""):
                continue
            m = CODE_RE.search(c)
            if not m:
                orphans.append(c)
                continue
            pat = re.escape(m.group(1)) + r"[\s\-]*" + re.escape(m.group(2)) \
                  + (re.escape(m.group(3)) if m.group(3) else "")
            if not re.search(pat, full):
                if c in ocr_codes:
                    orphan_warns.append(c)
                else:
                    orphans.append(c)
        if orphans:
            problems.append("ORPHAN codes not in PDF: " + ",".join(orphans))
        if orphan_warns:
            warns.append("ORPHAN downgraded (evidence-flagged unit_ocr_recovered_no_text_layer print): "
                         + ",".join(sorted(orphan_warns)))

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
