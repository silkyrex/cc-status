# cc-status

Claude Code status line with **accurate full cost tracking** — input, output, cache writes, and cache reads all priced correctly.

```
7d: 29.2M  ~$5332  opus 42%  |  td: 3.3M  opus 2.4M  snt 818K  ~$1079.7  ctx 37%  |  6d01h 13%  ~$39783/wk  cache 18x
```

If a Pomodoro session is active, a `🍅 P1 14m  |  ` prefix is added.

### Fields

| Field | Meaning |
|---|---|
| `7d: 29.2M` | Output tokens over the last 7 days. |
| `~$5332` | 7d **full cost** — output + input + cache writes + cache reads, all at correct per-model rates. |
| `opus 42%` | Opus share of 7d output. Lower = cheaper. |
| `td: 3.3M` | Output tokens today. |
| `opus 2.4M` | Today's Opus output. |
| `snt 818K` | Today's Sonnet output (hidden if zero). |
| `~$1079.7` | **Today's full cost** (hidden if < $0.05). |
| `ctx 37%` | Current session context usage. Compact near 100%. |
| `6d01h 13%` | Time until weekly reset and % of cycle elapsed. |
| `~$39783/wk` | Weekly spend at current pace. Hidden early in cycle. |
| `cache 18x` | Cache reads ÷ cache writes — true reuse ratio. Higher = better. Near 1x = cache not warming. |

### vs. cc-statusline

The original [cc-statusline](https://github.com/silkyrex/cc-statusline) tracks **output tokens only** as a deliberate burn-rate indicator. This repo tracks the full API bill.

| Metric | cc-statusline | cc-status |
|---|---|---|
| 7d cost | Output only | Input + output + cache_write + cache_read |
| Today's cost | Not shown | Shown |
| Cache ratio | `cache_reads / output_tokens` | `cache_reads / cache_writes` (true reuse) |

Use cc-statusline if you want a lightweight proxy. Use this if you want numbers that match your invoice.

### Pricing used

| Model | Input | Output | Cache write | Cache read |
|---|---|---|---|---|
| Opus | $15/M | $25/M | $18.75/M | $1.50/M |
| Sonnet | $3/M | $3/M | $3.75/M | $0.30/M |
| Haiku | $0.80/M | $0.80/M | $1.00/M | $0.08/M |

## Install

```bash
git clone https://github.com/silkyrex/cc-status.git
cd cc-status
bash install.sh
```

**Requirements:** `python3 >= 3.9`, `jq`, macOS or Linux, Claude Code installed and run at least once.

The installer backs up your existing `~/.claude/settings.json`, copies `cc-weekly-status.py` to `~/.local/bin/`, and sets the `statusLine` entry. Nothing else in `settings.json` is touched.

Restart Claude Code.

### Verify it worked

```bash
echo '{"session_id":"test","context_window":{"used_percentage":50}}' | python3 ~/.local/bin/cc-weekly-status.py
```

## Configuring the weekly reset

The reset countdown is anchored to a hardcoded timestamp in `cc-weekly-status.py`:

```python
def reset_countdown():
    pt = ZoneInfo('America/Los_Angeles')
    anchor = datetime.datetime(2026, 4, 23, 12, 0, tzinfo=pt)
```

Your Claude Code `/usage` dialog shows something like:

> Current week (all models)
> Resets Apr 23 at 12pm (America/Los_Angeles)

Set the `anchor` to that date/time and `ZoneInfo` to that timezone (line 88 in `cc-weekly-status.py`). Any single occurrence works — the script takes the delta modulo 7 days, so it auto-rolls forward each week.

## How token counting works

- Recursively reads every `.jsonl` under `~/.claude/projects/` whose mtime is within the last 8 days.
- For each assistant message, reads `usage.output_tokens`, `usage.input_tokens`, `usage.cache_creation_input_tokens`, and `usage.cache_read_input_tokens`.
- Model detected by substring match on `message.model` (`opus`, `sonnet`, `haiku`).
- Cached to `~/.claude/cc-burn-cache.json` with a 90s TTL.

## Pomodoro integration (optional)

If `~/.claude/pomo-state.json` exists with `{"start": <epoch-seconds>}`, the status line prepends a Pomodoro badge. If you don't use this, it's a silent no-op.

## Known limitations

- `cc-burn-cache.json` has no locking. Under heavy concurrent refresh it could theoretically be truncated; in practice Claude Code's 60s cadence is too slow for collisions.

## Uninstall

```bash
bash uninstall.sh
```

## Troubleshooting

**Status line shows `cc-status err: ...`** — run the verify snippet to see the full trace.

**Countdown shows the wrong time** — your `anchor` isn't aligned with your plan's reset. See [Configuring the weekly reset](#configuring-the-weekly-reset).

**7d and today are 0** — no `.jsonl` files in `~/.claude/projects/` within the last 8 days.

**Stale numbers** — delete `~/.claude/cc-burn-cache.json` to force a rescan.

## License

MIT.
