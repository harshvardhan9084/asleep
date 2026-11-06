#!/usr/bin/env python3
"""mercury_call.py — mercury-3 (inceptionlabs) T2T client: 5-key round-robin + rest-cooldown.

Owner directives (2026-11-06, updated):
  * Key pool from /home/z/my-project/.env:
      INCEPTIONLABS_API_KEY (#1) .. INCEPTIONLABS_API_KEY_5 (#5)
      (uncommented, non-PENDING, len>=20). Keys are NEVER discarded: none has a
      hard quota — 429 AND 402 are transient server-load codes per the owner.
  * Round-robin: each call atomically claims a starting index under flock (so
    <=5 concurrent calls spread across the pool). Within one call: try the
    eligible keys in rotation, one attempt per key, ~2s pause between attempts.
  * Rest-cooldown ("let them rest for some short time if constantly crying"):
    a key that fails (HTTP 429 / 402 / other 4xx-5xx / network / empty-after-
    retry) rests INCEPTIONLABS_COOLDOWN_SECONDS (.env, default 300) and then
    rejoins rotation automatically. A successful key's cooldown is cleared.
    If EVERY key is currently resting -> exit 3 immediately (no hammering).
  * 'response is empty' -> ONE retry on the same key before resting it.
  * Cumulative stats in work/pipeline_v2/mercury_stats.json (per-key
    calls/ok/http_429/empty/key_fail/network_fail/cooldown_count/cooldown_until
    + totals) for the mandatory owner transparency report.
  * Exit codes: 0 = ok; 3 = every eligible key failed OR all keys resting
    (caller may then use the general-subagent fallback per RULES and MUST log
    it); 4 = config error. NEVER prints key material — key INDEX only.

Usage:
  python3 mercury_call.py --prompt-file P [--user-file U | --stdin]
      [--max-tokens 4000] [--temperature 0.2] [--timeout 600]
      [--stats-file /home/z/my-project/work/pipeline_v2/mercury_stats.json]
stdout: the model's text content.  stderr: one-line status summary.
"""
import argparse
import fcntl
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ENV_PATH = '/home/z/my-project/.env'
DEF_URL = 'https://api.inceptionlabs.ai/v1/chat/completions'
DEF_MODEL = 'mercury-3'
KEY_SLOTS = ('INCEPTIONLABS_API_KEY', 'INCEPTIONLABS_API_KEY_2',
             'INCEPTIONLABS_API_KEY_3', 'INCEPTIONLABS_API_KEY_4',
             'INCEPTIONLABS_API_KEY_5')
ATTEMPT_PAUSE_S = 2


def load_env(path):
    env = {}
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return env


def fresh_key_stats():
    return {"calls": 0, "ok": 0, "http_429": 0, "empty": 0, "key_fail": 0,
            "network_fail": 0, "cooldown_count": 0, "cooldown_until": 0}


def load_stats(path):
    st = {"updated_at": None, "keys_active": 0, "rotation_index": 0,
          "totals": {"ok": 0, "http_429": 0, "empty": 0, "key_fail": 0,
                     "network_fail": 0, "exhausted_calls": 0,
                     "all_resting_calls": 0},
          "per_key": {}}
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            disk = json.load(fh)
        if isinstance(disk.get('rotation_index'), int):
            st['rotation_index'] = disk['rotation_index']
        if isinstance(disk.get('totals'), dict):
            st['totals'].update({k: v for k, v in disk['totals'].items()
                                 if isinstance(v, int)})
        if isinstance(disk.get('per_key'), dict):
            st['per_key'] = disk['per_key']
    except (OSError, ValueError):
        pass
    for k in st['totals']:
        st['totals'].setdefault(k, 0)
    return st


def save_stats(path, st):
    st['updated_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    d = os.path.dirname(path) or '.'
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix='.mercury_stats_', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            json.dump(st, fh, indent=1, sort_keys=True)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def http_post(url, key, model, content, max_tokens, temperature, timeout):
    body = json.dumps({"model": model,
                       "messages": [{"role": "user", "content": content}],
                       "max_tokens": int(max_tokens),
                       "temperature": float(temperature),
                       "stream": False}).encode('utf-8')
    req = urllib.request.Request(url, data=body, method='POST', headers={
        'Authorization': 'Bearer ' + key,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'mercury_call/1.1 (+aktu-catalog-pipeline)'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read().decode('utf-8', 'replace')
        except Exception:
            return e.code, ''
    except Exception as e:  # URLError, timeout, TLS, ...
        return -1, type(e).__name__ + ': ' + str(e)[:200]


def extract_text(raw):
    try:
        data = json.loads(raw)
        ch = data.get('choices') or []
        if not ch:
            return ''
        msg = ch[0].get('message') or {}
        return (msg.get('content') or '').strip()
    except Exception:
        return ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prompt-file', required=True)
    ap.add_argument('--user-file')
    ap.add_argument('--stdin', action='store_true')
    ap.add_argument('--max-tokens', type=int, default=4000)
    ap.add_argument('--temperature', type=float, default=0.2)
    ap.add_argument('--timeout', type=int, default=600)
    ap.add_argument('--stats-file',
                    default='/home/z/my-project/work/pipeline_v2/mercury_stats.json')
    args = ap.parse_args()

    env = load_env(ENV_PATH)
    keys = []
    for slot in KEY_SLOTS:
        v = env.get(slot, '')
        if v and not v.upper().startswith('PENDING') and len(v) >= 20:
            keys.append(v)
    if not keys:
        print('MERCURY status=config_error reason=no_active_keys_in_env', file=sys.stderr)
        return 4
    n = len(keys)
    try:
        cooldown_s = int(env.get('INCEPTIONLABS_COOLDOWN_SECONDS', '') or 300)
    except ValueError:
        cooldown_s = 300

    base = env.get('INCEPTIONLABS_BASE_URL', '').strip() or DEF_URL
    if '/chat/completions' not in base:
        base = base.rstrip('/') + '/chat/completions'
    model = env.get('INCEPTIONLABS_MODEL', '').strip() or DEF_MODEL

    with open(args.prompt_file, 'r', encoding='utf-8', errors='replace') as fh:
        prompt = fh.read()
    user = ''
    if args.user_file:
        with open(args.user_file, 'r', encoding='utf-8', errors='replace') as fh:
            user = fh.read()
    elif args.stdin:
        user = sys.stdin.read()
    content = prompt + (('\n\n' + user) if user else '')

    lock_path = args.stats_file + '.lock'
    os.makedirs(os.path.dirname(lock_path) or '.', exist_ok=True)

    # Phase 1: atomically claim the starting key (fast — no HTTP under lock).
    with open(lock_path, 'w') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        st = load_stats(args.stats_file)
        rot = int(st.get('rotation_index', 0)) % n
        st['rotation_index'] = (rot + 1) % n
        st['keys_active'] = n
        save_stats(args.stats_file, st)
        fcntl.flock(lf, fcntl.LOCK_UN)

    order = [(rot + j) % n for j in range(n)]
    now = time.time()
    eligible = [i for i in order
                if float(st['per_key'].get(str(i + 1), {}).get('cooldown_until', 0)) <= now]
    resting = n - len(eligible)

    def merge_deltas(deltas, cried, ok_key):
        with open(lock_path, 'w') as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            stx = load_stats(args.stats_file)
            stx['keys_active'] = n
            for klabel, fields in deltas.items():
                pk = stx['per_key'].setdefault(klabel, fresh_key_stats())
                for f, c in fields.items():
                    pk[f] = pk.get(f, 0) + c
                    stx['totals'][f] = stx['totals'].get(f, 0) + c
            for klabel in cried:
                pk = stx['per_key'].setdefault(klabel, fresh_key_stats())
                pk['cooldown_until'] = time.time() + cooldown_s
                pk['cooldown_count'] = pk.get('cooldown_count', 0) + 1
            if ok_key is not None:
                pk = stx['per_key'].setdefault(ok_key, fresh_key_stats())
                pk['cooldown_until'] = 0
            save_stats(args.stats_file, stx)
            fcntl.flock(lf, fcntl.LOCK_UN)

    if not eligible:
        with open(lock_path, 'w') as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            stx = load_stats(args.stats_file)
            stx['totals']['all_resting_calls'] = stx['totals'].get('all_resting_calls', 0) + 1
            stx['keys_active'] = n
            save_stats(args.stats_file, stx)
            fcntl.flock(lf, fcntl.LOCK_UN)
        earliest = min(float(st['per_key'].get(str(i + 1), {}).get('cooldown_until', 0))
                       for i in range(n))
        print('MERCURY status=all_resting keys=%d resting=%d earliest_retry_in=%ds '
              '-> subagent fallback permitted per RULES (log the fallback)'
              % (n, resting, max(0, int(earliest - time.time()))), file=sys.stderr)
        return 3

    deltas = {}
    attempts = []

    def bump(klabel, field):
        deltas.setdefault(klabel, {})
        deltas[klabel][field] = deltas[klabel].get(field, 0) + 1

    t0 = time.time()
    out_text = ''
    ok_klabel = None

    for idx, ki in enumerate(eligible):
        if idx:
            time.sleep(ATTEMPT_PAUSE_S)
        klabel = str(ki + 1)
        code, raw = http_post(base, keys[ki], model, content,
                              args.max_tokens, args.temperature, args.timeout)
        bump(klabel, 'calls')
        if code == 429:
            bump(klabel, 'http_429'); attempts.append('k%d:429' % (ki + 1)); continue
        if code == -1:
            bump(klabel, 'network_fail'); attempts.append('k%d:net' % (ki + 1)); continue
        if code != 200:
            bump(klabel, 'key_fail'); attempts.append('k%d:http%d' % (ki + 1, code)); continue
        text = extract_text(raw)
        if text:
            bump(klabel, 'ok'); attempts.append('k%d:ok' % (ki + 1))
            out_text = text; ok_klabel = klabel
            break
        # HTTP 200 but empty -> ONE retry on the same key (owner rule).
        time.sleep(ATTEMPT_PAUSE_S)
        code2, raw2 = http_post(base, keys[ki], model, content,
                                args.max_tokens, args.temperature, args.timeout)
        bump(klabel, 'calls')
        if code2 == 200:
            text2 = extract_text(raw2)
            if text2:
                bump(klabel, 'ok'); attempts.append('k%d:ok(2)' % (ki + 1))
                out_text = text2; ok_klabel = klabel
                break
            bump(klabel, 'empty'); attempts.append('k%d:empty' % (ki + 1)); continue
        if code2 == 429:
            bump(klabel, 'http_429'); attempts.append('k%d:429(2)' % (ki + 1)); continue
        if code2 == -1:
            bump(klabel, 'network_fail'); attempts.append('k%d:net(2)' % (ki + 1)); continue
        bump(klabel, 'key_fail'); attempts.append('k%d:http%d(2)' % (ki + 1, code2))

    if out_text:
        print(out_text)

    cried = sorted({kl for kl, fs in deltas.items()
                    if any(fs.get(f) for f in
                           ('http_429', 'empty', 'key_fail', 'network_fail'))})
    exhausted = ok_klabel is None
    merge_deltas(deltas, cried, ok_klabel)

    elapsed = round(time.time() - t0, 1)
    if not exhausted:
        print('MERCURY status=ok key=%s/%d keys_active=%d resting=%d attempts=%s elapsed=%ss'
              % (ok_klabel, n, n, resting, ','.join(attempts) or '-', elapsed),
              file=sys.stderr)
        return 0
    merge_deltas({}, [], None)  # exhausted_calls bookkeeping below
    with open(lock_path, 'w') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        stx = load_stats(args.stats_file)
        stx['totals']['exhausted_calls'] = stx['totals'].get('exhausted_calls', 0) + 1
        save_stats(args.stats_file, stx)
        fcntl.flock(lf, fcntl.LOCK_UN)
    print('MERCURY status=exhausted keys_active=%d resting_now=%d attempts=%s elapsed=%ss '
          '-> crying keys sent to %ds rest; subagent fallback permitted per RULES '
          '(MUST be logged in the worklog)'
          % (n, resting, ','.join(attempts) or '-', elapsed, cooldown_s), file=sys.stderr)
    return 3


if __name__ == '__main__':
    sys.exit(main())
