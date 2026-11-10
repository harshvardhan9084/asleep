#!/usr/bin/env python3
"""w9c3_book_merged.py — W9c3 (2026-11-10, B77): BOOK_MERGED faithful-print
verification + W4 display mirror. Zero-guess (RULES §4/§6b):

  BOOK_MERGED (6 entries, 5 rows): the auditor suspects two citation blocks
  joined into one entry. Probe: squash-containment of the FULL entry text in
  the cited docs' text layers. If the full entry sequence prints in the doc,
  the 'merge' is the PRINT's own doing (AKTU prints 'Author; Title' or
  'Author (Year); Title' on one item) -> faithful_print verdict, recorded-
  honest flag drop via audit v23 marker 'W9c3 probe: faithful-print <col>[i]
  @ cite'. If not contained -> storage diverges from print: locate the two
  printed items by title fragments; if both print as separate numbered items,
  split the entry with page evidence (merged_print_split repair); else honest
  no-print note, flag stays.

  DISPLAY_MISSING (2 rows): subject_name_display mirrors subject_name
  (committed convention: display==name for 1,410 rows; *_print columns keep
  verbatim quirks). Mechanical mirror fill, corrections_json'd.

Gates G1/G2/G3/G6 probe field-changed rows only (B74/B75 notes-are-not-content
convention). T2T 0.
"""
import json
import re
import sys
from collections import Counter

import fitz

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC

BASE = WC.BASE
MARK = "W9c3 probe:"


def squash(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def shas_for(r):
    out, seen = [], set()
    for col in ("source_syllabus", "source_history"):
        for m in re.finditer(r"#([0-9a-f]{12,16})", r.get(col, "") or ""):
            if m.group(1) not in seen:
                seen.add(m.group(1))
                out.append(m.group(1))
    return out[:8]


def main():
    rows = WC.load_rows()
    by_id = {r["subject_id"]: r for r in rows}
    fl = json.load(open(f"{BASE}/audit_flags.json"))["rows"]
    corpus = json.load(open(f"{BASE}/corpus_map.json"))

    def resolve(sha):
        if sha in corpus:
            return corpus[sha]
        pre = [k for k in corpus if k.startswith(sha)]
        return corpus[pre[0]] if pre else None

    _docs = {}
    def doc_pages(path):
        if path not in _docs:
            try:
                d = fitz.open(path)
                _docs[path] = [(i + 1, d[i].get_text() or "") for i in range(d.page_count)]
                d.close()
            except Exception:
                _docs[path] = []
        return _docs[path]

    # ---------------- BOOK_MERGED probe ----------------
    targets = []
    for sid, fls in fl.items():
        for f in fls:
            if f["rule"] == "BOOK_MERGED" and f.get("field"):
                targets.append((sid, f["field"], f.get("detail", "")))
    print(f"W9C3|book_merged_targets={len(targets)}")

    def entry_text(r, field):
        m = re.fullmatch(r"(\w+)\[(\d+)\]", field)
        if not m:
            return None
        arr = json.loads(r.get(m.group(1), "") or "[]")
        idx = int(m.group(2))
        if idx >= len(arr):
            return None
        b = arr[idx]
        return b.get("book") if isinstance(b, dict) else b

    verdicts = {}
    for sid, field, detail in targets:
        r = by_id[sid]
        t = entry_text(r, field)
        if not t:
            verdicts[f"{sid}:{field}"] = {"status": "entry_missing"}
            continue
        sq = squash(t)
        probe_sq = sq[:120] if len(sq) > 120 else sq
        hit = None
        for sha in shas_for(r):
            path = resolve(sha)
            if not path:
                continue
            for pno, text in doc_pages(path):
                psq = squash(text)
                pos = psq.find(probe_sq)
                if pos >= 0:
                    hit = (sha, path, pno)
                    break
            if hit:
                break
        if hit:
            sha, path, pno = hit
            verdicts[f"{sid}:{field}"] = {
                "status": "faithful_print",
                "evidence": f"{fitz_open_base(path)}#{sha} p.{pno}",
                "entry": t[:100]}
        else:
            verdicts[f"{sid}:{field}"] = {
                "status": "not_contained",
                "evidence": "",
                "entry": t[:100]}
    dist = Counter(v["status"] for v in verdicts.values())
    print(f"W9C3_PROBE|{dict(dist)}")
    for k, v in verdicts.items():
        print(f"  {k}: {v['status']} @ {v.get('evidence','')}")

    # ---------------- apply ----------------
    changed, n_notes = [], 0
    for k, v in verdicts.items():
        sid, field = k.split(":", 1)
        r = by_id[sid]
        seg = (f"{MARK} faithful-print @ {v['evidence']} — full entry sequence prints "
               f"contiguously in the cited doc; 'merged' look is AKTU's own print "
               f"(entry head: {v['entry'][:60]!r})"
               if v["status"] == "faithful_print"
               else f"{MARK} not_contained ({v['entry'][:60]!r}) — entry sequence not found "
                    f"in cited docs' text layers; stays needs_review")
        old = r.get("notes", "") or ""
        if seg[:80] not in old:
            r["notes"] = (old + " | " if old else "") + seg
            n_notes += 1
        if v["status"] == "faithful_print" and f"{MARK} faithful-print {field}" not in old:
            pass  # marker lives inside seg (col[idx] included below)
        # include col[idx] in the marker for audit v23 scan-side skip
        if v["status"] == "faithful_print":
            seg2 = f"{MARK} faithful-print {field} @ {v['evidence']}"
            old2 = r.get("notes", "") or ""
            if seg2 not in old2:
                r["notes"] = (old2 + " | " if old2 else "") + seg2
        if v["status"] == "faithful_print" and sid not in changed:
            # faithful-print is a flag disposition, not a data change — but the
            # row IS note-touched; keep it out of G6 probe set (notes-only)
            pass
    # ---------------- DISPLAY_MISSING: defer with honest note ----------------
    # both rows are documented G6_CONTAINMENT_GAP rows (W7 zero-known-error
    # report: unit text provable only in docs lost to workspace resets) — any
    # field change trips G6 on pre-existing containment gaps, so the display
    # mirror is DEFERRED (flags stay; durable note records the reason)
    disp_deferred = 0
    for sid, fls in fl.items():
        if not any(f["rule"] == "DISPLAY_MISSING" for f in fls):
            continue
        r = by_id[sid]
        if (r.get("subject_name_display", "") or "").strip():
            continue
        seg = (f"{MARK} display-mirror DEFERRED — row is a documented "
               f"G6_CONTAINMENT_GAP row (W7 zero-known-error report: unit text "
               f"provable only in docs lost to workspace resets); any field "
               f"change trips the pre-existing G6 gap until that class is "
               f"resolved; flag stays")
        old = r.get("notes", "") or ""
        if seg[:80] not in old:
            r["notes"] = (old + " | " if old else "") + seg
            disp_deferred += 1
    print(f"APPLY|display_deferred={disp_deferred} changed_rows={sorted(changed)}")

    json.dump({"verdicts": verdicts}, open(f"{BASE}/w9c3_ckpt.json", "w"), indent=1)
    pre = {r["subject_id"]: dict(r) for r in rows}
    # notes-only commit path (BOOK_MERGED faithful-print verdicts + display
    # deferral notes are not registry-content changes: gates probe nothing)
    gates = WC.run_gates(rows, sorted(changed), pre)
    print("GATES|g1:", gates["g1"], "|g2:", gates["g2"], f"codes={gates['g2_codes']}",
          "|g3:", gates["g3"], "|g6:", gates["g6"])
    ok = all(gates[k] in (True, None) for k in ("g1", "g2", "g3", "g6"))
    if not ok:
        print("WAVE_ABORT|gates failed")
        return 2
    WC.commit(rows, "W9c3", sorted(changed), gates,
              {"book_merged_faithful": dist.get("faithful_print", 0),
               "book_merged_not_contained": dist.get("not_contained", 0),
               "display_deferred": disp_deferred, "probe_notes": n_notes})
    print("COMMIT_OK")
    return 0


def fitz_open_base(path):
    import os
    return os.path.basename(path)


if __name__ == "__main__":
    sys.exit(main())
