#!/usr/bin/env python3
"""Status line: gate-focused burn (7d + today, opus share on both).

Reads assistant-message usage from session JSONLs in ~/.claude/projects/.
Caches to ~/.claude/cc-burn-cache.json (TTL 90s) since full scan is ~2s.
"""
import json, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

CACHE = Path.home() / '.claude' / 'cc-burn-cache.json'
TTL = 90  # seconds

OUT_RATE  = {'opus': 25,    'sonnet': 3,    'haiku': 0.8}
IN_RATE   = {'opus': 15,    'sonnet': 3,    'haiku': 0.8}
CW_RATE   = {'opus': 18.75, 'sonnet': 3.75, 'haiku': 1.0}
CR_RATE   = {'opus': 1.5,   'sonnet': 0.3,  'haiku': 0.08}

def fmt(n):
    if n >= 1_000_000: return f'{n/1_000_000:.1f}M'
    if n >= 1_000: return f'{n/1_000:.0f}K'
    return str(n)

def fmt_cost(n):
    if n >= 10_000: return f'~${n/1000:.0f}K'
    if n >= 1_000:  return f'~${n:.0f}'
    return f'~${n:.1f}'

def model_key(model):
    if 'opus' in model: return 'opus'
    if 'sonnet' in model: return 'sonnet'
    if 'haiku' in model: return 'haiku'
    return None

def scan():
    base = Path.home() / '.claude' / 'projects'
    cutoff = time.time() - 8 * 86400
    by_day = {}
    for p in base.rglob('*.jsonl'):
        try:
            if p.stat().st_mtime < cutoff: continue
            with open(p) as f:
                for line in f:
                    try: e = json.loads(line)
                    except: continue
                    msg = e.get('message') or {}
                    u = msg.get('usage') or {}
                    out = u.get('output_tokens', 0)
                    if not out: continue
                    day = e.get('timestamp', '')[:10]
                    if not day: continue
                    mk = model_key(msg.get('model', ''))
                    bucket = by_day.setdefault(day, {
                        'out': 0, 'opus': 0, 'sonnet': 0, 'cost': 0.0,
                        'cache_r': 0, 'cache_w': 0,
                    })
                    inp     = u.get('input_tokens', 0)
                    cache_r = u.get('cache_read_input_tokens', 0)
                    cache_w = u.get('cache_creation_input_tokens', 0)
                    bucket['out']     += out
                    bucket['cache_r'] += cache_r
                    bucket['cache_w'] += cache_w
                    if mk == 'opus':   bucket['opus']   += out
                    if mk == 'sonnet': bucket['sonnet'] += out
                    if mk:
                        bucket['cost'] += (
                            out     * OUT_RATE[mk] / 1_000_000 +
                            inp     * IN_RATE[mk]  / 1_000_000 +
                            cache_w * CW_RATE[mk]  / 1_000_000 +
                            cache_r * CR_RATE[mk]  / 1_000_000
                        )
        except: pass
    return by_day

def load_cache():
    try:
        d = json.loads(CACHE.read_text())
        if time.time() - d['ts'] < TTL: return d['by_day']
    except: pass
    return None

def save_cache(by_day):
    try: CACHE.write_text(json.dumps({'ts': time.time(), 'by_day': by_day}))
    except: pass

def reset_countdown():
    pt = ZoneInfo('America/Los_Angeles')
    anchor = datetime.datetime(2026, 5, 4, 7, 59, tzinfo=pt)  # update if /usage shows a different reset time
    delta = (anchor - datetime.datetime.now(pt)).total_seconds()
    delta %= 7 * 86400
    pct_used = (1 - delta / (7 * 86400)) * 100
    return f'{int(delta // 86400)}d{int((delta % 86400) // 3600):02d}h', pct_used


def pomo_status():
    state_file = Path.home() / '.claude' / 'pomo-state.json'
    try:
        s = json.loads(state_file.read_text())
        elapsed = int(time.time()) - s['start']
        blocks = [
            (0,      25*60, 'P1'),
            (25*60,  30*60, 'brk'),
            (30*60,  55*60, 'P2'),
            (55*60,  60*60, 'brk'),
            (60*60,  85*60, 'P3'),
            (85*60,  90*60, 'done'),
        ]
        for start, end, label in blocks:
            if start <= elapsed < end:
                mins = (end - elapsed + 59) // 60
                return f'🍅 b {mins}m' if label == 'brk' else f'🍅 {label[0]} {mins}m'
    except:
        pass
    return None

try:
    import sys
    ctx_pct = None
    stdin_data = {}
    try:
        stdin_data = json.loads(sys.stdin.read())
        ctx_pct = stdin_data.get('context_window', {}).get('used_percentage')
    except Exception:
        pass

    by_day = load_cache()
    if by_day is None:
        by_day = scan()
        save_cache(by_day)

    today = datetime.date.today().isoformat()
    dates = sorted(by_day.keys())[-7:]
    w_out    = sum(by_day[d]['out']     for d in dates)
    w_opus   = sum(by_day[d]['opus']    for d in dates)
    w_cost   = sum(by_day[d]['cost']    for d in dates)
    w_cache_r = sum(by_day[d].get('cache_r', 0) for d in dates)
    w_cache_w = sum(by_day[d].get('cache_w', 0) for d in dates)

    t = by_day.get(today, {'out': 0, 'opus': 0, 'sonnet': 0, 'cost': 0.0})
    t_out, t_opus, t_cost = t['out'], t['opus'], t.get('cost', 0.0)

    w_pct      = (w_opus / w_out * 100) if w_out else 0
    t_opus_pct = int(t_opus / t_out * 100) if t_out else 0
    cache_ratio = int(w_cache_r / w_cache_w) if w_cache_w else 0

    td_cost_str = fmt_cost(t_cost) if t_cost >= 0.05 else ''
    td_mix_str  = f' o{t_opus_pct}%' if t_out else ''
    ctx_str     = f' ctx {ctx_pct:.0f}%' if ctx_pct is not None else ''
    if ctx_pct is not None:
        try: Path('/tmp/claude-ctx-pct.txt').write_text(str(ctx_pct))
        except: pass
    reset_str, pct_used = reset_countdown()

    # Bot equity slot: reads /tmp/trading.state.json synced from droplet every 60s.
    # Renders as its own block ('  |  $X +Y.Y%') when fresh; empty when stale
    # (>5min) or missing so the trailing pipe collapses cleanly.
    bot_block = ''
    try:
        sf = Path('/tmp/trading.state.json')
        if sf.exists():
            s = json.loads(sf.read_text())
            age = time.time() - s.get('ts', 0)
            if age < 300:
                eq = s['equity']
                pct = s['day_pct']
                sign = '+' if pct >= 0 else ''
                bot_block = f'  |  ${eq:,.0f} {sign}{pct:.1f}%'
    except Exception:
        pass
    cache_str = f'  c{cache_ratio}x' if cache_ratio else ''
    w_pct_q  = (stdin_data.get('rate_limits') or {}).get('seven_day', {}).get('used_percentage')
    week_str = f'  w{w_pct_q:.0f}%' if w_pct_q is not None else ''
    s_pct = (stdin_data.get('rate_limits') or {}).get('five_hour', {}).get('used_percentage')
    session_str = f'  s{s_pct:.0f}%' if s_pct is not None else ''

    token_line = (
        f'7d: {fmt_cost(w_cost)} ({fmt(w_out)}) o{w_pct:.0f}%'
        f'  |  td: {td_cost_str}{td_mix_str}{ctx_str}'
        f'  |  {reset_str}{week_str}{cache_str}{session_str}'
        f'{bot_block}'
    )
    pomo = pomo_status()
    print(f'{pomo}  |  {token_line}' if pomo else token_line)

    history = Path.home() / '.claude' / 'cc-status-history.jsonl'
    try:
        with open(history, 'a') as f:
            f.write(json.dumps({
                'ts': datetime.datetime.now().isoformat(),
                'w_out': w_out,
                'w_cost': round(w_cost, 2),
                'w_opus_pct': round(w_pct, 1),
                't_out': t_out,
                't_opus': t_opus,
                'cache_x': cache_ratio,
                'ctx_pct': round(ctx_pct, 1) if ctx_pct is not None else None,
            }) + '\n')
    except: pass
except Exception as e:
    print(f'cc-status err: {e}')
