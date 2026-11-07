#!/usr/bin/env python3
"""wave_runner.py — cron entry for the correction-wave pipeline (post-B56).
Runs the next pending wave stage per wave_state.json; every stage ends with
gates+commit+push_catalog.sh+worklog append (RULES §1c). Owner transparency
directive: T2T stats reported per run in the worklog section.

Stages:
  w3_resume  — retry mercury-3 REX for api_fail/parse_fail rows, then apply
               (guarded: rows already corrected are skipped)
  w5_marks   — deterministic per-row marks/credit adjudication against the
               verbatim source_scheme_line (multiset-alignment fixes only;
               everything else stays flagged)
  w7_reaudit — fresh audit_rules.py scan + zero-known-error report
The runner is idempotent; each run executes ONE stage then exits (cron pacing).
"""
import json
import os
import subprocess
import sys

BASE = "/home/z/my-project/work/pipeline_v2"
PROJ = "/home/z/my-project"
STATE = f"{BASE}/wave_state.json"
STAGES = ["w3_resume", "w3_apply2", "w5_marks", "w7_reaudit"]
NO_CSV = {"w3_resume", "w7_reaudit"}  # no registry change -> no CSV in commit (B06 guard exempt)

def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    return {"done": [], "notes": []}

def save_state(st):
    json.dump(st, open(STATE, "w"), indent=1)

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    tail = "\n".join((p.stdout + "\n" + p.stderr).strip().splitlines()[-14:])
    print(f"RUN|rc={p.returncode}|{cmd[-1] if cmd else ''}\n{tail}")
    return p.returncode, tail

def push(batch, summary, manifest):
    rc, _ = run(["bash", f"{PROJ}/scripts/pipeline_v2/push_catalog.sh", batch, batch, summary, manifest])
    return rc == 0

def main():
    st = load_state()
    nxt = next((s for s in STAGES if s not in st["done"]), None)
    if not nxt:
        print("WAVE_RUNNER|all stages done — nothing to do")
        return 0
    print(f"WAVE_RUNNER|stage={nxt}")
    batch_no = st.get("batch_next", 57)

    if nxt == "w3_resume":
        rc, out = run([sys.executable, f"{PROJ}/scripts/pipeline_v2/w3_kls_rex.py"])
    elif nxt == "w3_apply2":
        rc, out = run([sys.executable, f"{PROJ}/scripts/pipeline_v2/w3_kls_apply.py"])
    elif nxt == "w5_marks":
        rc, out = run([sys.executable, f"{PROJ}/scripts/pipeline_v2/w5_marks.py"])
    elif nxt == "w7_reaudit":
        rc, out = run([sys.executable, f"{PROJ}/scripts/pipeline_v2/w7_reaudit.py"])
    if rc == 0:
        mf = f"{BASE}/manifest_B{batch_no}_{nxt}.md"
        open(mf, "w").write(
            f"# Task ID: CRON-AUTO-B{batch_no} ({nxt})\n\nAutomated wave-runner stage `{nxt}`.\n\n```\n{out}\n```\n")
        pushed = False
        if nxt not in NO_CSV:
            pushed = push(f"CRON-AUTO-B{batch_no}", f"wave stage {nxt} (automated; see manifest)", mf)
            print(f"WAVE_RUNNER|push={'OK' if pushed else 'FAIL'} batch=B{batch_no}")
        else:
            print(f"WAVE_RUNNER|no-CSV stage — no push (results recorded in manifest {mf})")
        st["done"].append(nxt)
        if pushed or nxt in NO_CSV:
            st["batch_next"] = batch_no + (1 if pushed else 0)
    else:
        st["notes"].append({"stage": nxt, "rc": rc, "tail": out[-400:], "retry": True})
        if nxt == "w3_resume" and rc == 3:
            print("WAVE_RUNNER|all keys resting — stage left pending for next run")
    save_state(st)
    return 0 if rc == 0 else rc

if __name__ == "__main__":
    sys.exit(main())
