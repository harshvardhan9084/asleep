#!/usr/bin/env python3
"""t9_quality_probe.py — quality-test cascade T9 (owner plan 2026-11-11), batch CRON-20261112-B88.

T9 = book-entry identity within row (P3, expected yield: low).
  Stage 1: within a single subject row, over textbooks_structured and
           reference_books_structured entries (single 'book' strings):
             exact_within_TB / exact_within_RB — identical squashed entry
                repeated inside one list;
             cross_list — identical entry present in BOTH TB and RB of the row
                (plan: "same title/author across textbooks and references");
             near-dup — token-Jaccard >= 0.85 between two entries of the row
                (same row, within-list or cross-list), not exact. Recorded as a
                WEAKER class: Jaccard on "Author, Title, Publisher" strings also
                catches genuinely different sibling books ("Machine Design" vs
                "Machine Design Data Book") — the print decides.
  Stage 2: for every flagged row, own-cited-doc page evidence: count
           occurrences of each duplicate entry's title fragment (longest quoted
           segment if the entry quotes a title, else first ~6 words, squashed)
           in the CITED pages of the row's own docs; whole-doc count recorded as
           fallback context (a year-wide scheme book legitimately prints one
           book under several courses — whole-doc-only counts are tagged weaker).
             cited-pages count >= 2      -> attested_print_duplication
                                            (print wins per 6b/B76; no fix)
             cited < 2, whole-doc >= 2   -> attested_in_doc_fallback_review
             whole-doc == 1              -> drafting_side_duplication_review
                                            (stored twice, print once; fix/flag
                                             candidate for a LATER batch)
             whole-doc == 0              -> book_print_unverified
             sha unresolvable / no cite  -> inconclusive classes.

LEDGER-ONLY: writes work/pipeline_v2/probes/t9_probe_ledger.json (+ copy into
syllabus_catalog/owner_requests/). No CSV write, no quality_flags change
(standing mechanics: multi-stage confirmation first). Never invents a value —
every candidate carries stored + printed evidence.
"""
import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
PROBE_DIR = "/home/z/my-project/work/pipeline_v2/probes"
REPO = "/home/z/my-project/work/repo_asleep"
RUN_ID = "CRON-20261112-B88"

JAC_NEAR = 0.85


def norm_name(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()


def squash(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def parse_books(field):
    try:
        v = json.loads(field) if (field or "").strip() else []
        return [e.get("book", "") for e in v if isinstance(e, dict) and e.get("book")]
    except Exception:
        return []


def tokens(s):
    return set(re.findall(r"[a-z0-9]+", (s or "").lower())) - {
        "the", "a", "an", "of", "and", "for", "in", "ed", "publication", "pub"}


def jac(a, b):
    A, B = tokens(a), tokens(b)
    return len(A & B) / len(A | B) if A and B else 0.0


def title_fragment(entry):
    """longest quoted segment if present, else first ~6 words; squashed, >=12 chars."""
    q = re.findall(r"[\"'\u201c\u201d]([^\"'\u201c\u201d]{8,})[\"'\u201c\u201d]", entry)
    frag = max(q, key=len) if q else " ".join(entry.split()[:6])
    f = squash(frag)
    if len(f) < 12:
        f = squash(entry)
    return f


def doc_session(stem):
    m = re.search(r"(\d{4})-(\d{2})", os.path.basename(stem or ""))
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2))
    return a if (a + 1) % 100 == b else None


def sha_index():
    idx = {}
    for base, dirs, files in os.walk(REPO):
        parts = base.split(os.sep)
        if "other_courses" in parts:
            dirs[:] = []
            continue
        for fn in files:
            if not fn.lower().endswith(".pdf"):
                continue
            p = os.path.join(base, fn)
            try:
                h = hashlib.md5(open(p, "rb").read()).hexdigest()[:16]
                idx[h] = p
            except OSError:
                pass
    return idx


def cite_docs(field):
    out = []
    for m in re.finditer(r"([A-Za-z0-9_.\- ]+\.pdf)#([0-9a-f]{16})([^;]*)", field or ""):
        pg = [int(x) for x in re.findall(r"p{1,2}\.(\d+)", m.group(3))]
        out.append((m.group(2), pg, m.group(1)))
    return out


def code_regex(code):
    parts = [re.escape(ch) for ch in re.sub(r"[^A-Za-z0-9]", "", code)]
    if not parts:
        return None
    return re.compile(r"[-\s.:()/]*".join(parts), re.IGNORECASE)


STOPW = {"and", "of", "the", "for", "in", "i", "ii", "iii", "iv", "v", "lab",
         "practical", "theory", "a", "its", "with"}


def name_near(stored_norm, lines, i):
    win = " ".join(lines[max(0, i - 1):i + 6]).lower()
    wt = {t for t in re.split(r"[^a-z0-9]+", win) if len(t) >= 4}
    st = [t for t in stored_norm.split() if t not in STOPW and len(t) >= 3]
    if not st:
        return False
    hit = sum(1 for t in st
              if any(w.startswith(t[:4]) or t.startswith(w[:4]) for w in wt))
    return hit / len(st) >= 0.6 or (hit >= 2 and len(st) <= 3)


class DocTexts:
    def __init__(self, idx):
        self.idx = idx
        self.cache = {}
        self.raw = {}

    def pages(self, sha):
        if sha in self.cache:
            return self.cache[sha]
        p = self.idx.get(sha)
        if not p:
            self.cache[sha] = None
            return None
        import fitz
        doc = fitz.open(p)
        texts = [squash(pg.get_text("text")) for pg in doc]
        raws = [pg.get_text("text") for pg in doc]
        doc.close()
        self.cache[sha] = texts
        self.raw[sha] = [[l.strip() for l in rw.splitlines() if l.strip()]
                         for rw in raws]
        return texts

    def course_block_pages(self, sha, code, stored_norm):
        """pages where the code prints NEAR the row's own subject name (T7
        name_near machinery, no early return) = the row's course block."""
        texts = self.pages(sha)
        if texts is None:
            return None
        cre = code_regex(code)
        if not cre:
            return []
        lines_pp = self.raw[sha]
        hits = []
        for pi, lines in enumerate(lines_pp):
            for i, l in enumerate(lines):
                if not cre.search(l.replace(" ", "")):
                    continue
                n_codes = len({m.group(0) for m in re.finditer(
                    r"[A-Z]{2,4}[-\s]?\d{2,4}", l.upper())})
                if n_codes >= 2 and not name_near(stored_norm, lines, i):
                    continue
                hits.append(pi)
                break
        return hits

    def count_on_pages(self, sha, frags, page_idxs):
        texts = self.pages(sha)
        if texts is None:
            return None
        return sum(texts[pi].count(f) for pi in page_idxs for f in frags)

    def count_occurrences(self, sha, frag, pages):
        texts = self.pages(sha)
        if texts is None:
            return "doc_unresolvable", 0, 0
        n = len(texts)
        cited = [p for p in pages if 1 <= p <= n] or []
        cnt_cited = sum(texts[p - 1].count(frag) for p in cited)
        cnt_all = sum(t.count(frag) for t in texts)
        return "ok", cnt_cited, cnt_all


# ---------------------------------------------------------------- main
def main():
    os.makedirs(PROBE_DIR, exist_ok=True)
    with open(CSV_PATH) as f:
        rows = [r for r in csv.DictReader(f) if r["row_kind"] == "subject"]

    stage1 = []          # per-row findings (pre stage-2)
    n_tb = n_rb = n_either = 0
    for r in rows:
        tb = parse_books(r["textbooks_structured"])
        rb = parse_books(r["reference_books_structured"])
        if not tb and not rb:
            continue
        n_tb += bool(tb)
        n_rb += bool(rb)
        groups = []
        # exact repeats within one list
        for name, L in (("exact_within_TB", tb), ("exact_within_RB", rb)):
            sq = [squash(x) for x in L]
            for s in set(sq):
                if sq.count(s) > 1:
                    ex = next(x for x in L if squash(x) == s)
                    groups.append({"kind": name, "entries": [ex], "n_entries": sq.count(s)})
        # identical entry in both lists
        both = []
        for x in tb:
            sx = squash(x)
            if sx and any(squash(y) == sx for y in rb):
                both.append(x)
        if both:
            groups.append({"kind": "cross_list_TB_RB", "entries": [both[0]], "n_entries": len(both)})
        # near-dup pairs (within or across lists)
        for i, x in enumerate(tb + rb):
            for y in (tb + rb)[i + 1:]:
                if squash(x) == squash(y):
                    continue
                j = jac(x, y)
                if j >= JAC_NEAR:
                    groups.append({"kind": "near_dup", "entries": [x, y], "n_entries": 2,
                                   "jaccard": round(j, 3)})
        if groups:
            stage1.append({"row": r, "groups": groups})

    kclass = Counter(g["kind"] for s in stage1 for g in s["groups"])
    print(f"T9 stage1: {len(stage1)} flagged rows "
          f"(TB nonempty {n_tb}, RB nonempty {n_rb}); groups {dict(kclass)}")

    # ---- stage 2: cited-pages occurrence counting
    idx = sha_index()
    dt = DocTexts(idx)
    cands = []
    for s in stage1:
        r = s["row"]
        cites = [(sha, pg, stem, fn) for fn in ("source_scheme_line", "source_syllabus")
                 for sha, pg, stem in cite_docs(r[fn])]
        seen = set()
        uniq = []
        for sha, pg, stem, fn in cites:
            if sha not in seen:
                seen.add(sha)
                uniq.append((sha, pg, stem, fn))
        gout = []
        for g in s["groups"]:
            frags = []
            for e in g["entries"]:
                f = title_fragment(e)
                if f not in frags:
                    frags.append(f)
            ev = []
            for sha, pg, stem, fn in uniq:
                texts = dt.pages(sha)
                if texts is None:
                    ev.append({"src": fn, "sha16": sha, "doc": stem,
                               "doc_session": doc_session(stem), "cited_pages": pg,
                               "verdict": "doc_unresolvable", "block_pages": [],
                               "count_cited": 0, "count_scoped": 0, "count_whole": 0})
                    continue
                block = dt.course_block_pages(sha, r["primary_code"],
                                              norm_name(r["subject_name"]))
                per = [sum(texts[pi].count(f) for pi in block) for f in frags] if block else []
                cited = [p for p in pg if 1 <= p <= len(texts)]
                ev.append({"src": fn, "sha16": sha, "doc": stem,
                           "doc_session": doc_session(stem), "cited_pages": pg,
                           "verdict": "ok", "block_pages": [b + 1 for b in block],
                           "count_cited": sum(texts[p - 1].count(frags[0]) for p in cited),
                           "count_scoped": sum(per),
                           "per_frag_scoped": per,
                           "count_whole": sum(t.count(frags[0]) for t in texts)})
            ok = [e for e in ev if e["verdict"] == "ok"]
            with_block = [e for e in ok if e["block_pages"]]
            if not ok:
                gv = ("inconclusive_doc_unresolved"
                      if any(e["verdict"] == "doc_unresolvable" for e in ev) else "no_citation")
            elif len(frags) > 1:
                # near-dup: the print must carry BOTH variants for attestation;
                # one variant printing once = stored drift beyond print
                if any(min(e["per_frag_scoped"]) >= 1 for e in with_block):
                    gv = "attested_print_duplication"
                elif any(e["count_scoped"] >= 1 for e in with_block):
                    gv = "drafting_side_duplication_review"
                else:
                    gv = ("attested_in_doc_fallback_review"
                          if any(e["count_whole"] >= 2 for e in ok)
                          else "book_print_unverified")
            elif with_block:
                b = max(e["count_scoped"] for e in with_block)
                gv = ("attested_print_duplication" if b >= 2
                      else "drafting_side_duplication_review" if b == 1
                      else ("attested_in_doc_fallback_review"
                            if max(e["count_whole"] for e in ok) >= 2
                            else "book_print_unverified"))
            else:
                gv = ("attested_in_doc_fallback_review"
                      if max(e["count_whole"] for e in ok) >= 2
                      else "drafting_side_duplication_review"
                      if max(e["count_whole"] for e in ok) == 1
                      else "book_print_unverified")
            gout.append({"kind": g["kind"], "fragments": [f[:40] for f in frags],
                         "verdict": gv,
                         "best_scoped": max((e["count_scoped"] for e in ok), default=0),
                         "best_whole": max((e["count_whole"] for e in ok), default=0),
                         "page_evidence": ev})
        gvs = {g["verdict"] for g in gout}
        if "attested_print_duplication" in gvs and not (gvs & {
                "drafting_side_duplication_review", "attested_in_doc_fallback_review"}):
            rv = "attested_print_duplication"
        elif "drafting_side_duplication_review" in gvs:
            rv = "drafting_side_duplication_review"
        elif "attested_in_doc_fallback_review" in gvs:
            rv = "attested_in_doc_fallback_review"
        elif "book_print_unverified" in gvs:
            rv = "book_print_unverified"
        elif "inconclusive_doc_unresolved" in gvs:
            rv = "inconclusive_doc_unresolved"
        else:
            rv = "no_citation"
        cands.append({"sid": r["subject_id"], "course": r["course_name"],
                      "primary_code": r["primary_code"],
                      "subject_name": r["subject_name"][:90],
                      "effective_session_latest": r["effective_session_latest"],
                      "n_groups": len(gout), "row_verdict": rv, "groups": gout})

    led = {
        "run_id": RUN_ID,
        "test": "T9 book-entry identity within row",
        "policy": "LEDGER-ONLY stage-1+2; no CSV/quality_flags change; print wins per 6b/B76",
        "rule": {
            "stage1": "exact repeat within TB/RB; identical entry across TB&RB (cross_list); near-dup = token-Jaccard>=0.85, not exact",
            "stage2": "title-fragment occurrence count in CITED pages of own docs (longest quoted segment else first ~6 words, squashed); whole-doc count = fallback context (year-wide books legit print per-course)",
        },
        "counts": {
            "subject_rows": len(rows),
            "rows_with_books": n_tb + n_rb,
            "flagged_rows": len(stage1),
            "groups_by_kind": dict(kclass),
        },
        "candidates_stage2": cands,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    out = os.path.join(PROBE_DIR, "t9_probe_ledger.json")
    json.dump(led, open(out, "w"), indent=1)

    rv = Counter(c["row_verdict"] for c in cands)
    gv = Counter(g["verdict"] for c in cands for g in c["groups"])
    print("row verdicts:", dict(rv))
    print("group verdicts:", dict(gv))
    for c in cands:
        if c["row_verdict"] not in ("attested_print_duplication",):
            print(f"  - {c['sid']} {c['primary_code']} [{c['course']}] {c['row_verdict']} :: "
                  + "; ".join(f"{g['kind']}:{g['verdict']}(s{g['best_scoped']}/w{g['best_whole']})"
                              for g in c["groups"]))


if __name__ == "__main__":
    main()
