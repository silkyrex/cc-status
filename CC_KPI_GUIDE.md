# How to Read `cc-kpi`

## Running it

```bash
cc-kpi              # last 12 weeks (default)
cc-kpi --weeks 4    # last 4 weeks
```

## Output

```
Week            eff/M   cache    7d cost  days
----------------------------------------------
2026-05-19       $142     14x     $3,793     2
2026-05-12       $164     16x     $4,652     7  ↑
2026-05-05       $218     18x     $4,955     6  ↑
2026-04-21        $20    132x       $425     1  ↓
```

| Column | What it is |
|--------|-----------|
| **Week** | Monday starting the 7-day window |
| **eff/M** | 7d cost ÷ 7d output tokens (per million). The KPI. Lower = more efficient. |
| **cache** | Avg cache reads ÷ cache writes for the week (tokens). Higher = more input cost reused at read price instead of full input price. |
| **7d cost** | Total dollars that rolling 7-day window. |
| **days** | Daily snapshots captured. Less than 3 = ignore the row, not enough data. |
| **↑ / ↓** | That week vs the newer week above it. ↑ = less efficient, ↓ = more efficient. |

## What moves eff/M

One lever matters: **cache ratio**. Higher cache ratio means more tokens are served at read price (cheap) instead of input price (expensive). When cache drops, eff/M rises. Everything else is secondary.

Rates live in `claude_rates.py` — check there for current model prices.

## When to act

| Signal | Action |
|--------|--------|
| eff/M rising 2 weeks in a row | Compare status line `@$/M` today vs 7d. If today is high: check whether warm sessions are running. |
| cache dropping week over week | Warm skills aren't being loaded at session start. Run `/warm-plan` or `/warm-trading` before sessions. |
| Single-week spike, days < 3 | Ignore. Not enough snapshots for a valid average. |

## Status line connection

`cc-kpi` is the weekly rollup of the `@$/M` field in the status line. The 7d `@$/M` in the status line matches this week's eff/M in real time.
