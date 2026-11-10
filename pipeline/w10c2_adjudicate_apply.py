#!/usr/bin/env python3
"""w10c2_adjudicate_apply.py — B76 wave: (A) re-audit B74's 31 corrected_W10C
writes under the B76 discriminators (wrap-fragment / table-column-header /
semester-break / differing-intervening-header), reverting false positives;
(B) write the 1 tightened print_category verdict; (C) durable notes.
Zero-guess: every revert/keep/write carries a page-cited printed reason."""
import json
import re
import sys
from collections import Counter

import fitz

sys.path.insert(0, "/home/z/my-project/scripts/pipeline_v2")
import wave_commit as WC
from w10c2_fulldoc_probe import (corpus_map_load, governing_header_tight,
                                 code_variants, HEADERS, HONOR_RE, MARK)

BASE = WC.BASE
REA_MARK = "W10c2 reaudit:"

COL_TOKENS = re.compile(r"^(s\.?\s*no\.?|sr\.?\s*no\.?|subject|code|subject\s+code|"
                        r"subject\s+name|name|periods?|sessional|evaluation\s+scheme|"
                        r"scheme|credit|ct|ta|te|pe|ps|ese|total|l|t|p)$", re.I)
SEM_BREAK = re.compile(r"\bsemeste?r\b", re.I)


def header_cats_between(text, hpos, cpos):
    out = []
    for ln in text[hpos:cpos].splitlines():
        s = ln.strip()
        for hre, cat in HEADERS:
            if hre.match(s) and not HONOR_RE.match(s):
                out.append((s, cat))
    return out


def col_header_between(text, hpos, cpos):
    """true if a scheme-table column header row block starts between the
    claimed section header and the code hit (>=3 distinct column tokens)"""
    toks = set()
    for ln in text[hpos:cpos].splitlines():
        s = ln.strip()
        if s and COL_TOKENS.match(s):
            toks.add(s.lower())
    return len(toks) >= 3, sorted(toks)[:6]


def sem_break_between(text, hpos, cpos):
    return bool(SEM_BREAK.search(text[hpos:cpos]))


def main():
    rows = WC.load_rows()
    by_id = {r["subject_id"]: r for r in rows}
    corpus = corpus_map_load()
    fl = json.load(open(f"{BASE}/audit_flags.json"))["rows"]
    ck2 = json.load(open(f"{BASE}/w10c2_ckpt.json"))["results"]

    # ---------- Phase A: re-audit the 31 ----------
    b74 = [r for r in rows if "corrected_W10C_CATEGORY" in (r.get("quality_flags") or "")]
    verdicts = {}
    for r in b74:
        sid = r["subject_id"]
        pc = (r.get("primary_code") or "").strip().upper()
        stored = (r.get("subject_type") or "").strip()
        ev = ""
        try:
            for e in json.loads(r.get("corrections_json") or "[]"):
                if e.get("rule") == "TYPE_EMPTY" and e.get("evidence"):
                    ev = e["evidence"]
        except Exception:
            pass
        m = re.search(r"(\S+)#([0-9a-f]{12,16})\s*p\.(\d+)", ev)
        if not m or not pc:
            verdicts[sid] = {"verdict": "keep", "reason": "evidence cite missing — no basis to revert committed value",
                             "evidence": ev[:80]}
            continue
        base, sha, pno = m.group(1), m.group(2), int(m.group(3))
        path = corpus.get(sha) or next((corpus[k] for k in corpus if k.startswith(sha)), None)
        if not path:
            verdicts[sid] = {"verdict": "keep", "reason": "sha unresolved — no basis to revert", "evidence": sha}
            continue
        d = fitz.open(path)
        t = d[pno - 1].get_text() or ""
        d.close()
        variants = code_variants(pc)
        pat = re.compile(r"\b(" + "|".join(re.escape(v) for v in variants) + r")\b", re.I)
        hit = pat.search(t)
        if not hit:
            verdicts[sid] = {"verdict": "keep", "reason": "code not on cited page — no basis to revert",
                             "evidence": f"{base}#{sha} p.{pno}"}
            continue
        # loose header = last HEADERS match above the hit (B74's rule)
        hpos, hcat = -1, None
        acc = 0
        for ln in t[:hit.start()].splitlines():
            s = ln.strip()
            for hre, cat in HEADERS:
                if hre.match(s) and not HONOR_RE.match(s):
                    hpos, hcat = t[:hit.start()].rfind(s) + s.find(s), cat
            acc += len(ln) + 1
        if hpos < 0:
            verdicts[sid] = {"verdict": "revert", "reason": "no section header above code on cited page",
                             "evidence": f"{base}#{sha} p.{pno}"}
            continue
        between = t[hpos:hit.start()]
        has_col, toks = col_header_between(t, hpos, hit.start())
        inter = header_cats_between(t, hpos, hit.start())
        sem = sem_break_between(t, hpos, hit.start())
        why = []
        if has_col:
            why.append(f"table column-header starts between header and code ({','.join(toks)})")
        if sem:
            why.append("semester break between header and code")
        diff = [(s, c) for (s, c) in inter if c != hcat]
        if diff:
            why.append(f"differing intervening header {diff[0][0]!r}->{diff[0][1]}")
        # wrap-continuation of the claimed header line
        up_lines = t[:hpos].splitlines()
        prev = next((l.strip() for l in reversed(up_lines) if l.strip()), "")
        lastw = re.split(r"[^A-Za-z]+", prev)[-1].lower() if re.search(r"[A-Za-z]", prev) else ""
        WRAP_WORDS = {"science", "based", "open", "deptt", "departmental", "department",
                      "elective", "electives", "professional", "value", "added",
                      "mandatory", "practical", "core", "cores", "lab", "labs"}
        if lastw in WRAP_WORDS:
            why.append(f"wrap-continuation (prev line ends '{lastw}')")
        if why:
            verdicts[sid] = {"verdict": "revert", "reason": "; ".join(why),
                             "evidence": f"{base}#{sha} p.{pno}", "stored": stored}
        else:
            verdicts[sid] = {"verdict": "keep",
                             "reason": f"sub-header {hcat} governs inside one table (no column-header/semester break/intervening header between header and code)",
                             "evidence": f"{base}#{sha} p.{pno}", "stored": stored}
    dist = Counter(v["verdict"] for v in verdicts.values())
    print(f"REAUDIT|{len(verdicts)}|{dict(dist)}")
    for sid, v in sorted(verdicts.items()):
        if v["verdict"] == "revert":
            print(f"  REVERT {sid} (stored={v.get('stored')}): {v['reason']} [{v['evidence']}]")

    # ---------- Phase B: the 1 tightened W10c2 write ----------
    writes = {}
    for sid, v in ck2.items():
        if v.get("status") == "print_category" and v.get("category") in (
                "open-elective", "departmental-elective", "elective"):
            r = by_id[sid]
            if (r.get("subject_type") or "").strip():
                continue
            writes[sid] = v
    print(f"W10C2_WRITES|{sorted(writes)}")

    # ---------- apply ----------
    touched = {}
    n_rev = n_write = n_notes = 0
    for sid, v in verdicts.items():
        r = by_id[sid]
        seg = (f"{REA_MARK} {v['verdict'].upper()} ({v.get('stored')}) {v['reason']} at {v['evidence']}"
               if v["verdict"] == "keep"
               else f"{REA_MARK} REVERT (was {v.get('stored')}) {v['reason']} at {v['evidence']}")
        old = r.get("notes", "") or ""
        if seg[:80] not in old:
            r["notes"] = (old + " | " if old else "") + seg
            n_notes += 1
        if v["verdict"] == "revert":
            cjson = json.loads(r.get("corrections_json") or "[]")
            cjson.append({"field": "subject_type", "before": v.get("stored", ""),
                          "after": "", "rule": "TYPE_EMPTY_REVERT",
                          "evidence": f"{v['evidence']} — {v['reason']}", "wave": "W10c2"})
            r["corrections_json"] = json.dumps(cjson, ensure_ascii=False)
            r["subject_type"] = ""
            r["subject_type_norm"] = ""
            r["verification_status"] = "needs_review"
            qf = [f for f in (r.get("quality_flags", "") or "").split(";") if f.strip()]
            r["quality_flags"] = ";".join(
                ("reverted_W10C_B76" if f == "corrected_W10C_CATEGORY" else f) for f in qf)
            note = ("W10c2 reaudit(TYPE_EMPTY): B74 subject_type write reverted — governing-header claim "
                    "fails the B76 discriminators (elective bullet-list header above an unrelated scheme "
                    "table); page-cited reason in corrections_json")
            prev_cn = r.get("change_note_vs_previous", "") or ""
            r["change_note_vs_previous"] = (prev_cn + "; " if prev_cn else "") + note
            touched[sid] = r
            n_rev += 1
    for sid, v in writes.items():
        r = by_id[sid]
        cat = v["category"]
        r["subject_type"] = cat
        r["subject_type_norm"] = cat
        cjson = json.loads(r.get("corrections_json") or "[]")
        cjson.append({"field": "subject_type", "before": "", "after": cat,
                      "rule": "TYPE_EMPTY", "evidence": v.get("evidence", ""),
                      "wave": "W10c2"})
        r["corrections_json"] = json.dumps(cjson, ensure_ascii=False)
        r["verification_status"] = "corrected"
        qf = [f for f in (r.get("quality_flags", "") or "").split(";") if f.strip()]
        if "corrected_W10C_CATEGORY" not in qf:
            qf.append("corrected_W10C_CATEGORY")
        r["quality_flags"] = ";".join(qf)
        note = ("W10c2(TYPE_EMPTY): subject_type set from printed scheme section header per RULES §6b — "
                "full-document re-probe, tight same-page grammar, page-cited in corrections_json")
        prev_cn = r.get("change_note_vs_previous", "") or ""
        r["change_note_vs_previous"] = (prev_cn + "; " if prev_cn else "") + note
        touched[sid] = r
        n_write += 1

    # ---------- Phase C: durable W10c2 probe notes for all probed targets ----------
    def seg_for(sid, v):
        st = v.get("status", "?")
        ev = (v.get("evidence") or "").strip()
        cat = f" -> {v.get('category')}" if v.get("category") else ""
        core = f"{MARK} {st}{cat}"
        if st == "no_code_print_found":
            core += f" ({v.get('pages_probed') or 'full text layer'} probed)"
        rej = v.get("rejected_headers")
        if rej:
            core += f" [rejected: {'; '.join(rej[:2])}]"
        return f"{core} at {ev}" if ev else core

    for sid, v in ck2.items():
        r = by_id[sid]
        if sid in touched and v.get("status") == "print_category":
            seg = seg_for(sid, v)
        else:
            seg = seg_for(sid, v)
            if sid in touched:
                continue
        old = r.get("notes", "") or ""
        if seg[:80] not in old:
            r["notes"] = (old + " | " if old else "") + seg
            if sid not in touched:
                touched[sid] = r
            n_notes += 1

    print(f"APPLY|reverts={n_rev} writes={n_write} note_rows={n_notes} touched={len(touched)}")
    json.dump({"reaudit": verdicts}, open(f"{BASE}/w10c2_reaudit.json", "w"), indent=1)

    if not touched:
        print("APPLY|nothing to commit")
        return 0
    # gates probe ONLY field-changed rows (B74/B75 convention: notes-only rows
    # are not registry-content changes and never enter the G6 spot-check set)
    changed = [sid for sid, v in verdicts.items() if v["verdict"] == "revert"] \
        + list(writes)
    pre = {r["subject_id"]: dict(r) for r in rows}
    gates = WC.run_gates(rows, sorted(changed), pre)
    print("GATES|g1:", gates["g1"], "|g2:", gates["g2"], f"codes={gates['g2_codes']}",
          "|g3:", gates["g3"], "|g6:", gates["g6"], "|pre_hits:", gates.get("g6_pre_edit_hits"))
    ok = all(gates[k] in (True, None) for k in ("g1", "g2", "g3", "g6"))
    if not ok:
        print("WAVE_ABORT|gates failed")
        return 2
    WC.commit(rows, "W10c2", sorted(changed), gates,
              {"reaudit_keep": dist.get("keep", 0), "reaudit_revert": dist.get("revert", 0),
               "writes": n_write, "probe_notes": n_notes})
    print("COMMIT_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
