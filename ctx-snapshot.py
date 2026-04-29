#!/usr/bin/env python3
"""Daily snapshot: peak ctx% from cc-status-history (measured) or session files (estimated) → ctx-peak-log.jsonl"""

import json
import os
from datetime import datetime, date
from pathlib import Path

STATUS_HISTORY = Path.home() / ".claude/cc-status-history.jsonl"
CTX_LOG = Path.home() / ".claude/ctx-peak-log.jsonl"
PROJECTS_DIR = Path.home() / ".claude/projects/-Users-rzhu"

# Rough calibration: session file bytes → estimated ctx% peak
# 120 KB JSONL ≈ ~1% of 1M ctx window (tuned against 04/21 measured 95% @ 11MB)
BYTES_PER_PCT = 120_000


def measured_snapshot(target_date: date):
    ctx_vals, opus_vals, cache_vals = [], [], []
    if STATUS_HISTORY.exists():
        with open(STATUS_HISTORY) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    ts = datetime.fromisoformat(r["ts"])
                    if ts.date() != target_date:
                        continue
                    if r.get("ctx_pct") is not None:
                        ctx_vals.append(r["ctx_pct"])
                    if r.get("w_opus_pct") is not None:
                        opus_vals.append(r["w_opus_pct"])
                    if r.get("cache_x") is not None:
                        cache_vals.append(r["cache_x"])
                except Exception:
                    pass
    return ctx_vals, opus_vals, cache_vals


def estimated_peak(target_date: date):
    """Estimate peak ctx% from largest session file modified on target_date."""
    max_bytes = 0
    if PROJECTS_DIR.exists():
        for f in PROJECTS_DIR.glob("*.jsonl"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime).date()
                if mtime == target_date:
                    max_bytes = max(max_bytes, f.stat().st_size)
            except Exception:
                pass
    if max_bytes == 0:
        return None
    return min(95, max_bytes // BYTES_PER_PCT)


def snapshot(target_date: date = None):
    if target_date is None:
        target_date = date.today()
    day_str = target_date.isoformat()

    ctx_vals, opus_vals, cache_vals = measured_snapshot(target_date)

    if ctx_vals:
        source = "measured"
        peak_ctx = max(ctx_vals)
        avg_ctx = round(sum(ctx_vals) / len(ctx_vals), 1)
    else:
        est = estimated_peak(target_date)
        if est is None:
            print(f"No data for {day_str} — nothing logged.")
            return
        source = "estimated"
        peak_ctx = est
        avg_ctx = None

    record = {
        "date": day_str,
        "source": source,
        "peak_ctx_pct": peak_ctx,
        "avg_ctx_pct": avg_ctx,
        "avg_opus_pct": round(sum(opus_vals) / len(opus_vals), 1) if opus_vals else None,
        "avg_cache_x": round(sum(cache_vals) / len(cache_vals), 0) if cache_vals else None,
        "samples": len(ctx_vals) if ctx_vals else None,
        "wall_hit": peak_ctx >= 90,
    }

    # Skip if already logged today
    existing_dates = set()
    if CTX_LOG.exists():
        with open(CTX_LOG) as f:
            for line in f:
                try:
                    existing_dates.add(json.loads(line)["date"])
                except Exception:
                    pass

    if day_str in existing_dates:
        print(f"Entry for {day_str} already exists — skipping.")
        return

    with open(CTX_LOG, "a") as f:
        f.write(json.dumps(record) + "\n")

    wall = " ← WALL HIT" if record["wall_hit"] else ""
    avg_str = f"  avg={avg_ctx}%" if avg_ctx else ""
    print(
        f"[{source}] {day_str}: peak={peak_ctx}%{avg_str}  "
        f"opus={record['avg_opus_pct']}%  cache={record['avg_cache_x']}x{wall}"
    )


if __name__ == "__main__":
    snapshot()
