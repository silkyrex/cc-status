#!/usr/bin/env python3
"""Status line: real numbers only (2026-09-26 rewrite).

Limit % comes from Claude Code's statusline stdin (`rate_limits`), which is the
same source /usage reads. Token counts come from session JSONLs, deduped per
message id (streaming writes partial usage lines first). No dollar math: Ray is
on a flat subscription, so list-price x tokens is fiction.
Old version: cc-weekly-status.py.bak-2026-09-26
"""
import json, datetime, sys, time
from pathlib import Path

CACHE = Path.home() / '.claude' / 'cc-burn-cache.json'
HISTORY = Path.home() / '.claude' / 'cc-status-history.jsonl'
TTL = 90  # seconds; full scan is ~2s


def fmt(n):
    if n >= 1_000_000: return f'{n/1_000_000:.1f}M'
    if n >= 1_000: return f'{n/1_000:.0f}K'
    return str(n)


def scan():
    """Output tokens + cache read/write per local day, one count per message id."""
    cutoff = time.time() - 8 * 86400
    best = {}  # message id -> (day, usage) with the largest output_tokens
    for p in (Path.home() / '.claude' / 'projects').rglob('*.jsonl'):
        try:
            if p.stat().st_mtime < cutoff: continue
            with open(p, errors='ignore') as f:
                for line in f:
                    if '"usage"' not in line: continue
                    try: e = json.loads(line)
                    except Exception: continue
                    msg = e.get('message') or {}
                    u = msg.get('usage')
                    key = msg.get('id') or e.get('requestId')
                    ts = e.get('timestamp')
                    if not u or not key or not ts or msg.get('model') == '<synthetic>': continue
                    prev = best.get(key)
                    if prev is None or u.get('output_tokens', 0) >= prev[1].get('output_tokens', 0):
                        when = datetime.datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone()
                        best[key] = (when.date().isoformat(), u)
        except Exception:
            pass
    by_day = {}
    for day, u in best.values():
        b = by_day.setdefault(day, {'out': 0, 'cache_r': 0, 'cache_w': 0, 'req': 0})
        b['out'] += u.get('output_tokens', 0)
        b['cache_r'] += u.get('cache_read_input_tokens', 0)
        b['cache_w'] += u.get('cache_creation_input_tokens', 0)
        b['req'] += 1
    return by_day


def load_cache():
    try:
        d = json.loads(CACHE.read_text())
        if time.time() - d['ts'] < TTL and d.get('v') == 2: return d['by_day']
    except Exception: pass
    return None


def save_cache(by_day):
    try: CACHE.write_text(json.dumps({'v': 2, 'ts': time.time(), 'by_day': by_day}))
    except Exception: pass


def countdown(resets_at):
    """resets_at may be epoch seconds or ISO; returns ('1d20h', seconds_left) or (None, None)."""
    try:
        if isinstance(resets_at, (int, float)):
            target = resets_at
        else:
            target = datetime.datetime.fromisoformat(str(resets_at).replace('Z', '+00:00')).timestamp()
        left = max(0, target - time.time())
        if left >= 86400: return f'{int(left // 86400)}d{int(left % 86400 // 3600):02d}h', left
        return f'{int(left // 3600)}h{int(left % 3600 // 60):02d}m', left
    except Exception:
        return None, None


def pomo_status():
    try:
        s = json.loads((Path.home() / '.claude' / 'pomo-state.json').read_text())
        elapsed = int(time.time()) - s['start']
        for start, end, label in [(0, 1500, 'P1'), (1500, 1800, 'brk'), (1800, 3300, 'P2'),
                                  (3300, 3600, 'brk'), (3600, 5100, 'P3'), (5100, 5400, 'done')]:
            if start <= elapsed < end:
                mins = (end - elapsed + 59) // 60
                return f'🍅 b {mins}m' if label == 'brk' else f'🍅 {label[0]} {mins}m'
    except Exception:
        pass
    return None


def bot_block():
    """Droplet bot equity from /tmp/trading.state.json; empty when stale (>5 min) or missing."""
    try:
        s = json.loads(Path('/tmp/trading.state.json').read_text())
        if time.time() - s.get('ts', 0) < 300:
            pct = s['day_pct']
            return f'  |  ${s["equity"]:,.0f} {"+" if pct >= 0 else ""}{pct:.1f}%'
    except Exception:
        pass
    return ''


LABELS = {'five_hour': '5h', 'seven_day': 'wk'}

try:
    stdin_data = {}
    try: stdin_data = json.loads(sys.stdin.read())
    except Exception: pass
    ctx_pct = (stdin_data.get('context_window') or {}).get('used_percentage')
    limits = stdin_data.get('rate_limits') or {}

    by_day = load_cache()
    if by_day is None:
        by_day = scan()
        save_cache(by_day)
    today = datetime.date.today()
    week = [(today - datetime.timedelta(days=i)).isoformat() for i in range(7)]
    w_out = sum(by_day.get(d, {}).get('out', 0) for d in week)
    t_out = by_day.get(today.isoformat(), {}).get('out', 0)
    w_cr = sum(by_day.get(d, {}).get('cache_r', 0) for d in week)
    w_cw = sum(by_day.get(d, {}).get('cache_w', 0) for d in week)
    cache_x = int(w_cr / w_cw) if w_cw else 0

    parts = []
    if ctx_pct is not None:
        e = '🔴' if ctx_pct >= 70 else '🟠' if ctx_pct >= 60 else '🟡' if ctx_pct >= 50 else '🟢'
        parts.append(f'{e}ctx{ctx_pct:.0f}%')

    # Plan limits: every bucket Claude Code reports, e.g. five_hour, seven_day, and any model-specific week.
    limit_bits, week_reset = [], None
    for key, v in limits.items():
        if not isinstance(v, dict) or v.get('used_percentage') is None: continue
        used = v['used_percentage']
        label = LABELS.get(key, key.replace('seven_day_', 'wk-').replace('_', ''))
        dot = '🔴' if used >= 80 else '🟡' if used >= 70 else ''
        limit_bits.append(f'{dot}{label} {used:.0f}%')
        if key == 'seven_day': week_reset = v.get('resets_at')
    if limit_bits:
        rs, _ = countdown(week_reset) if week_reset is not None else (None, None)
        parts.append(' · '.join(limit_bits) + (f' ↺{rs}' if rs else ''))
    else:
        parts.append('limits: n/a')

    parts.append(f'out td {fmt(t_out)} · 7d {fmt(w_out)}' + (f' · c{cache_x}x' if cache_x else ''))
    line = '  |  '.join(parts) + bot_block()
    pomo = pomo_status()
    print(f'{pomo}  |  {line}' if pomo else line)

    try:
        with open(HISTORY, 'a') as f:
            f.write(json.dumps({
                'ts': datetime.datetime.now().isoformat(timespec='seconds'),
                'rate_limits': limits or None,
                'ctx_pct': round(ctx_pct, 1) if ctx_pct is not None else None,
                'w_out': w_out, 't_out': t_out, 'cache_x': cache_x,
            }) + '\n')
    except Exception:
        pass
except Exception as e:
    print(f'cc-status err: {e}')
