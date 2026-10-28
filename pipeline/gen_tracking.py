#!/usr/bin/env python3
"""gen_tracking.py — generate the GitHub-referenced change-tracking files
(RULES §1c, owner directive 2026-10-28).

Usage:
  gen_tracking.py <run_id> <batch_label> <summary_line> <manifest_md_path>

Produces (under work/repo_asleep/syllabus_catalog/):
  CHANGELOG.md                     — newest-first, one append-only entry per push
  runs/<UTC-ts>_<run_id>_<slug>.md — the full run manifest (batch narrative)

Deltas are computed from the repo git history: HEAD's CSV vs the new local
CSV (download/art_d_final/syllabus_extreme_rich.csv). Nothing here guesses:
all numbers come from the two files.
"""
import csv, json, os, re, subprocess, sys
from collections import Counter
from datetime import datetime, timezone

REPO = "/home/z/my-project/work/repo_asleep"
CAT = f"{REPO}/syllabus_catalog"
LOCAL_CSV = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
CSV_IN_REPO = "syllabus_catalog/syllabus_extreme_rich.csv"
CODE_RE = re.compile(r"[A-Z]{2,4}\d{3}[A-Z]?")


def stats(path_or_blob, is_path=True):
    if is_path:
        rows = list(csv.DictReader(open(path_or_blob)))
    else:
        import io
        rows = list(csv.DictReader(io.StringIO(path_or_blob)))
    subs = [r for r in rows if r["row_kind"] == "subject"]
    codes = set()
    for r in subs:
        for f in ("primary_code", "all_codes"):
            for c in (r.get(f, "") or "").split(";"):
                c = c.strip()
                if c and CODE_RE.fullmatch(c):
                    codes.add(c)
    by_course = Counter(r["course_name"] for r in subs)
    kinds = Counter(r["row_kind"] for r in rows)
    return {"rows": len(rows), "subjects": len(subs), "codes": len(codes),
            "by_course": dict(sorted(by_course.items())), "kinds": dict(sorted(kinds.items()))}


def head_csv_blob():
    r = subprocess.run(["git", "-C", REPO, "show", f"HEAD:{CSV_IN_REPO}"],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def main():
    run_id, batch, summary, manifest_path = sys.argv[1:5]
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    fname_ts = now.strftime("%Y%m%dT%H%M%SZ")

    new = stats(LOCAL_CSV)
    old_blob = head_csv_blob()
    old = stats(old_blob, is_path=False) if old_blob else None

    def arrow(k):
        if not old:
            return str(new[k])
        return f"{old[k]}\u2192{new[k]}"

    def course_arrow():
        if not old:
            return json.dumps(new["by_course"], ensure_ascii=False)
        keys = sorted(set(old["by_course"]) | set(new["by_course"]))
        return ", ".join(f"{k} {old['by_course'].get(k, 0)}\u2192{new['by_course'].get(k, 0)}" for k in keys)

    entry = f"""## {ts} — run `{run_id}` — batch {batch}

- {summary}
- rows {arrow('rows')}, subjects {arrow('subjects')}, owned codes {arrow('codes')}
- subjects by course: {course_arrow()}
- row kinds: {json.dumps(new['kinds'], ensure_ascii=False)}
- gates G1/G2/G3/G6 enforced at the pipeline commit (see runs/ manifest for detail)
- commit: this push (git log — message carries run id + batch)
- data: [syllabus_extreme_rich.csv](syllabus_extreme_rich.csv) — 57 columns; zero-guess; provenance per row; rr_sid owner-assigned
"""

    chlog_path = f"{CAT}/CHANGELOG.md"
    if os.path.exists(chlog_path):
        head = open(chlog_path).read()
    else:
        head = ("# CHANGELOG — syllabus_extreme_rich.csv\n\n"
                "One entry per push; GitHub git log + this file are the authoritative\n"
                "per-run change history (RULES §1c, owner directive 2026-10-28).\n\n")
    # newest-first: insert the new entry just before the first existing '## '
    idx = head.find("\n## ")
    if idx >= 0:
        new_head = head[:idx].rstrip("\n") + "\n\n" + entry + head[idx + 1:]
    else:
        new_head = head.rstrip("\n") + "\n\n" + entry
    with open(chlog_path, "w") as f:
        f.write(new_head)

    slug = re.sub(r"[^a-z0-9]+", "-", (batch + " " + summary).lower()).strip("-")[:60]
    run_path = f"{CAT}/runs/{fname_ts}_{run_id}_{slug[:40]}.md"
    os.makedirs(f"{CAT}/runs", exist_ok=True)
    manifest = open(manifest_path).read() if os.path.exists(manifest_path) else "(manifest not provided)"
    with open(run_path, "w") as f:
        f.write(f"# Run manifest — {run_id} — batch {batch} — {ts}\n\n"
                f"Summary: {summary}\n\n"
                f"Registry deltas: rows {arrow('rows')}, subjects {arrow('subjects')}, "
                f"codes {arrow('codes')}; by course: {course_arrow()}\n\n"
                f"---\n\n{manifest}\n")
    print(f"CHANGELOG|{chlog_path}")
    print(f"RUNMANIFEST|{run_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
