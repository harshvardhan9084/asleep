#!/usr/bin/env python3
"""mark_done.py <rel1> [<rel2> ...]   — set status=done on exact queue rels
   mark_done.py --failed <reason> <rel> — set status=failed(reason)
Prints MARK|<rel>|OK. Appends queue meta.history.
"""
import json, os, sys
from datetime import datetime

QUEUE = "/home/z/my-project/work/pipeline_v2/queue.json"


def main():
    args = sys.argv[1:]
    failed = None
    if args and args[0] == "--failed":
        failed = args[1]
        args = args[2:]
    if not args:
        print("usage: mark_done.py [--failed reason] rel...")
        return 1
    q = json.load(open(QUEUE))
    by_rel = {e["rel"]: e for e in q["entries"]}
    missing = []
    for rel in args:
        e = by_rel.get(rel)
        if not e:
            missing.append(rel)
            print(f"MARK|{rel}|MISS")
            continue
        e["status"] = f"failed({failed})" if failed else "done"
        e["done_ts"] = datetime.now().astimezone().isoformat(timespec="seconds")
        print(f"MARK|{rel}|{'FAILED(' + failed + ')' if failed else 'OK'}")
    if missing:
        print("MISSING_RELS|" + ",".join(missing))
        return 1
    q["meta"].setdefault("history", []).append(
        {"ts": datetime.now().astimezone().isoformat(timespec="seconds"),
         "event": ("failed " if failed else "done ") + ",".join(args) + (f" reason={failed}" if failed else "")})
    with open(QUEUE, "w") as f:
        json.dump(q, f, indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
