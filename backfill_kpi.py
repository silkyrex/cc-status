#!/usr/bin/env python3
"""One-time backfill: read cc-status-history.jsonl, insert one row per day into DB.

t_cost is not in historical rows -- eff_td will be NULL for those.
Run once; safe to re-run (INSERT OR REPLACE by date).
"""
import json
from pathlib import Path
import kpi_db

JSONL = Path.home() / '.claude' / 'cc-status-history.jsonl'


def main():
    kpi_db.init_db()

    by_date: dict[str, dict] = {}
    skipped = 0
    with open(JSONL) as f:
        for line in f:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            date = row.get('ts', '')[:10]
            if not date:
                skipped += 1
                continue
            by_date[date] = row  # last row per day wins

    inserted = 0
    for date, row in sorted(by_date.items()):
        kpi_db.upsert_today({
            'w_cost':     row.get('w_cost'),
            'w_out':      row.get('w_out'),
            't_cost':     row.get('t_cost'),   # NULL in historical rows
            't_out':      row.get('t_out'),
            'cache_x':    row.get('cache_x'),
            'w_opus_pct': row.get('w_opus_pct'),
        }, date=date)
        inserted += 1

    print(f'Backfill complete: {inserted} days inserted, {skipped} lines skipped.')
    print(f'DB: {kpi_db.DB_PATH}')


if __name__ == '__main__':
    main()
