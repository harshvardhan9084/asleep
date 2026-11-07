#!/usr/bin/env python3
"""w3_kls_rex.py — W3 phase 2: mercury-3 REX for rows where the deterministic
scan found only partial K-levels in the cited docs' text layers.
Owner directives applied: tiny test call FIRST; <=5 concurrent; all T2T via
mercury_call.py (5-key round-robin, cooldown-rest, exit-3 => skip row for
this run, NO subagent fallback needed for extraction leftovers); incremental
results file (crash-safe); per-key stats land in mercury_stats.json."""
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

BASE = "/home/z/my-project/work/pipeline_v2"
CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
MC = "/home/z/my-project/scripts/pipeline_v2/mercury_call.py"
PROMPT = "/home/z/my-project/scripts/pipeline_v2/w3_rex_prompt.md"
RESULTS = f"{BASE}/w3_rex_results.json"

rows = {r["subject_id"]: r for r in csv.DictReader(open(CSV, newline="", encoding="utf-8"))}
queue = json.load(open(f"{BASE}/w3_rex_queue.json"))
done = {}
if os.path.exists(RESULTS):
    done = json.load(open(RESULTS))
todo = [q for q in queue if q["sid"] not in done]
print(f"W3-REX|queue={len(queue)} done={len(done)} todo={len(todo)}")

import fitz, hashlib
corpus = {}
for root in ("/home/z/my-project/work/repo_asleep/PDFs", "/home/z/my-project/upload",
             "/home/z/my-project/work/artd_v3/sources"):
    for dp, _d, fs in os.walk(root):
        for fn in fs:
            if fn.lower().endswith(".pdf"):
                p = os.path.join(dp, fn)
                try:
                    h = hashlib.md5()
                    with open(p, "rb") as fh:
                        for chunk in iter(lambda: fh.read(1 << 20), b""):
                            h.update(chunk)
                    corpus.setdefault(h.hexdigest()[:16], p)
                except Exception:
                    pass

def context_pages(shas, cap=4200):
    """Verbatim text of cited-doc pages that print CO/K content."""
    out = []
    for sha in shas:
        p = corpus.get(sha)
        if not p:
            continue
        try:
            d = fitz.open(p)
            pages = [pg.get_text() for pg in d]
            d.close()
        except Exception:
            continue
        for pi, t in enumerate(pages):
            if t and ("CO" in t) and re.search(r"\bK[1-6]\b", t):
                out.append(f"[{os.path.basename(p)} p.{pi+1}]\n{t.strip()[:2200]}")
            if sum(len(x) for x in out) > cap:
                break
        if sum(len(x) for x in out) > cap:
            break
    return "\n---\n".join(out)[:cap]

def build_payload(q):
    r = rows[q["sid"]]
    n = q["co_count"]
    cos = "\n".join(f"CO-{i}: {(r.get(f'co{i}_text') or '').strip()[:400]}" for i in range(1, n + 1))
    pages = context_pages(q.get("shas", []))
    return (f"Course outcomes (n={n}):\n{cos}\n\n"
            f"Verbatim printed CO-table text from the cited source document(s):\n{pages or '(no K-bearing text layer found)'}\n\n"
            f"Extract the printed K-level for each of the {n} outcomes. JSON only.")

def call_mercury(payload):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tf:
        tf.write(payload)
        uf = tf.name
    try:
        p = subprocess.run([sys.executable, MC, "--prompt-file", PROMPT, "--user-file", uf,
                            "--max-tokens", "900", "--temperature", "0.0", "--timeout", "180"],
                           capture_output=True, text=True, timeout=240)
        return p.returncode, p.stdout.strip()
    finally:
        os.unlink(uf)

def parse_kls(txt, n):
    if not txt:
        return None
    m = re.search(r"\[.*\]", txt, re.S)
    if not m:
        return None
    try:
        arr = json.loads(m.group(0))
    except Exception:
        return None
    kls = {}
    for o in arr:
        if isinstance(o, dict) and isinstance(o.get("no"), int) and 1 <= o["no"] <= n:
            kl = o.get("kl")
            if isinstance(kl, str) and re.fullmatch(r"K[1-6]", kl.strip().upper()):
                kls[o["no"]] = kl.strip().upper()
            else:
                kls[o["no"]] = None
    return [kls.get(i) for i in range(1, n + 1)] if len(kls) == n else None

# ---- tiny test call (owner directive: confirm API BEFORE batch drafting)
rc, out = call_mercury("Reply with the single word: OK")
print(f"W3-REX|tiny_test rc={rc} out={out[:40]!r}")
if rc != 0:
    print("W3-REX|API unavailable (exit 3) — REX phase deferred; no fallback needed")
    sys.exit(3)

stats = {"ok": 0, "parse_fail": 0, "api_fail": 0, "partial": 0}
lock_free = RESULTS

def work(q):
    sid = q["sid"]
    n = q["co_count"]
    payload = build_payload(q)
    rc, out = call_mercury(payload)
    if rc != 0:
        return sid, {"status": "api_fail", "kls": None}
    kls = parse_kls(out, n)
    if kls is None:
        rc2, out2 = call_mercury(payload + "\n\nIMPORTANT: return ONLY the JSON array, nothing else.")
        if rc2 == 0:
            kls = parse_kls(out2, n)
    if kls is None:
        return sid, {"status": "parse_fail", "kls": None}
    if any(k is None for k in kls):
        return sid, {"status": "partial", "kls": kls}
    return sid, {"status": "ok", "kls": kls}

with ThreadPoolExecutor(max_workers=5) as ex:
    futures = [ex.submit(work, q) for q in todo]
    for i, fut in enumerate(futures, 1):
        sid, res = fut.result()
        done[sid] = res
        stats[res["status"]] = stats.get(res["status"], 0) + 1
        if i % 10 == 0 or i == len(futures):
            json.dump(done, open(RESULTS, "w"), indent=1)
            print(f"W3-REX|progress {i}/{len(futures)} {stats}", flush=True)

json.dump(done, open(RESULTS, "w"), indent=1)
print(f"W3-REX|COMPLETE {stats}")
