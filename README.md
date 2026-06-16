# cc-status

Claude Code status line with **accurate full cost tracking** and throughput efficiency metrics.

```
c15x 🟢13%  |  7d:~$3795 @$140/M · td:~$525.1 @$137/M  |  ↑w42% ↺4d10h
```

If a Pomodoro session is active, a `🍅 P1 14m  |  ` prefix is added.

### Fields

| Field | Meaning |
|---|---|
| `c15x` | Cache reuse ratio: cache reads ÷ cache writes. Higher = more input cost amortized. Near 1x = cache not warming. |
| `🟢13%` | Current session context window %. Color-coded: 🟢 <50% · 🟡 50–60% · 🟠 60–70% · 🔴 ≥70%. Hidden when no CC stdin. |
| `7d:~$3795` | 7-day full cost — output + input + cache writes + cache reads, all at correct per-model rates. |
| `@$140/M` | **Throughput KPI**: 7d cost ÷ 7d output tokens (per million). Lower = more efficient. Watch this trend down over time. |
| `td:~$525.1` | Today's full cost (hidden if < $0.05). |
| `@$137/M` | Today's throughput efficiency. Compare to 7d rate: lower today = running hot; higher today = cache/model mix less efficient. |
| `⚪↑w42% ↺4d10h 🚀` | Weekly token budget remaining (free, not used). Color-coded: ⚪ ≥30% · 🟡 20–29% · 🔴 <20%. Pace emoji: 🚀 ahead of pace · ✅ on pace · 🔥 burning faster than the week is moving, likely to run out before reset · 💀 critical, more than half the week left but more than half the budget gone. Hidden when CC rate limits aren't injected. |
| `↺4d10h` | Time until weekly token reset. |

If a trading bot state file is fresh (`/tmp/trading.state.json` < 5 min old), a trailing `  |  $9,999 +1.2%` block is appended.

### vs. cc-statusline

The original [cc-statusline](https://github.com/silkyrex/cc-statusline) tracks output tokens only as a burn-rate proxy. This repo tracks the full API bill and surfaces throughput efficiency.

| Metric | cc-statusline | cc-status |
|---|---|---|
| Cost | Output tokens only | Input + output + cache_write + cache_read |
| Efficiency | Not shown | `@$/M` — cost per M output tokens |
| Cache ratio | reads / output tokens | reads / writes (true reuse) |
| Weekly budget | Used % | Free % (↑w%) |

Use cc-statusline for a lightweight proxy. Use this if you want numbers that match your invoice and a KPI you can improve.

### Pricing used

Claude 4.x rates, verified 2026-05-17. Rates live in `claude_rates.py` (imported from the agent-ops repo) — update there and both scripts pick it up automatically.

| Model | Input | Output | Cache write 5m | Cache write 1h | Cache read |
|---|---|---|---|---|---|
| Opus 4.7 | $5/M | $25/M | $6.25/M | $10/M | $0.50/M |
| Sonnet 4.6 | $3/M | $15/M | $3.75/M | $6/M | $0.30/M |
| Haiku 4.5 | $1/M | $5/M | $1.25/M | $2/M | $0.10/M |

## Install

```bash
git clone https://github.com/silkyrex/cc-status.git
cd cc-status
bash install.sh
```

**Requirements:** `python3 >= 3.9`, macOS or Linux, Claude Code installed and run at least once.

The installer backs up your existing `~/.claude/settings.json`, copies `cc-weekly-status.py` to `~/.local/bin/`, and sets the `statusLine` entry. Nothing else in `settings.json` is touched.

Restart Claude Code.

### Verify it worked

```bash
echo '{"context_window":{"used_percentage":13},"rate_limits":{"seven_day":{"used_percentage":58}}}' \
  | python3 ~/.local/bin/cc-weekly-status.py
# c15x 🟢13%  |  7d:~$3795 @$140/M · td:~$525.1 @$137/M  |  ↑w42% ↺4d10h
```

## Weekly KPI trend (`cc-kpi`)

The status line writes a daily snapshot to `~/.claude/cc-kpi.db` on every run. View the weekly trend:

```bash
cc-kpi
# Week            eff/M   cache    7d cost  days
# ----------------------------------------------
# 2026-05-19       $142     14x     $3,793     2
# 2026-05-12       $164     16x     $4,652     7  ↑
# 2026-05-05       $218     18x     $4,955     6  ↑
```

`eff/M` is the same `@$/M` from the status line, aggregated weekly. Lower = more efficient. The trend direction is the signal — not the absolute number.

`cc-kpi --weeks N` to show more history.

### Backfill from existing history

If you have an existing `~/.claude/cc-status-history.jsonl`, backfill it into the DB:

```bash
cd /path/to/cc-status
python backfill_kpi.py
```

## Configuring the weekly reset

The reset countdown is anchored to a hardcoded timestamp in `cc-weekly-status.py`:

```python
anchor = datetime.datetime(2026, 5, 4, 7, 59, tzinfo=pt)
```

Your Claude Code `/usage` dialog shows the reset time. Set `anchor` to any past occurrence of that time — the script takes the delta modulo 7 days and auto-rolls forward each week.

## How token counting works

- Recursively reads every `.jsonl` under `~/.claude/projects/` whose mtime is within the last 8 days.
- For each assistant message, reads `usage.output_tokens`, `usage.input_tokens`, `usage.cache_creation_input_tokens`, and `usage.cache_read_input_tokens`.
- Model detected by substring match on `message.model` (`opus`, `sonnet`, `haiku`).
- Cached to `~/.claude/cc-burn-cache.json` with a 90s TTL.

## Pomodoro integration (optional)

If `~/.claude/pomo-state.json` exists with `{"start": <epoch-seconds>}`, the status line prepends a Pomodoro badge. Silent no-op if absent.

## Known limitations

- `cc-burn-cache.json` has no locking. Under heavy concurrent refresh it could theoretically be truncated; Claude Code's cadence is too slow for this in practice.
- `@$/M` today requires at least one completed turn with output tokens. At session start it's hidden until the first turn lands.

## Uninstall

```bash
bash uninstall.sh
```

## Troubleshooting

**Status line shows `cc-status err: ...`** — run the verify snippet to see the full trace.

**Countdown shows the wrong time** — `anchor` isn't aligned with your plan's reset. See [Configuring the weekly reset](#configuring-the-weekly-reset).

**7d and today are 0** — no `.jsonl` files in `~/.claude/projects/` within the last 8 days.

**Stale numbers** — delete `~/.claude/cc-burn-cache.json` to force a rescan.

**`@$/M` not showing** — today's output token count is 0 (first turn of the day) or today's cost is < $0.05.

## License

MIT.
