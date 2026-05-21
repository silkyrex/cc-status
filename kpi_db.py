"""SQLite KPI store for cc-status throughput metrics.

DB path: ~/.claude/cc-kpi.db
One row per calendar day (upsert by date).
"""
import datetime
import sqlite3
from pathlib import Path

DB_PATH = Path.home() / '.claude' / 'cc-kpi.db'

DDL = """
CREATE TABLE IF NOT EXISTS daily_snapshots (
    date        TEXT PRIMARY KEY,
    w_cost      REAL,
    w_out       INTEGER,
    eff_per_m   REAL,
    t_cost      REAL,
    t_out       INTEGER,
    eff_td      REAL,
    cache_x     INTEGER,
    w_opus_pct  REAL,
    ts          TEXT
);
"""

WEEKLY_QUERY = """
SELECT
    date(date, 'weekday 1', '-6 days') AS week_start,
    ROUND(AVG(eff_per_m), 1)           AS avg_eff_per_m,
    ROUND(AVG(cache_x), 1)             AS avg_cache_x,
    ROUND(MAX(w_cost), 0)              AS week_cost,
    COUNT(*)                           AS days
FROM daily_snapshots
GROUP BY week_start
ORDER BY week_start DESC
LIMIT ?;
"""


def _conn(path: Path = DB_PATH) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def init_db(path: Path = DB_PATH) -> None:
    with _conn(path) as con:
        con.executescript(DDL)


def upsert_today(data: dict, path: Path = DB_PATH, date: str | None = None) -> None:
    """Upsert a daily snapshot. date defaults to today (YYYY-MM-DD)."""
    today = date or datetime.date.today().isoformat()
    w_out = data.get('w_out') or 0
    w_cost = data.get('w_cost') or 0.0
    t_out = data.get('t_out') or 0
    t_cost = data.get('t_cost')

    eff_per_m = round(w_cost / (w_out / 1_000_000), 2) if w_out else None
    eff_td = round(t_cost / (t_out / 1_000_000), 2) if (t_cost and t_out) else None

    row = (
        today,
        round(w_cost, 2),
        w_out,
        eff_per_m,
        round(t_cost, 2) if t_cost is not None else None,
        t_out,
        eff_td,
        data.get('cache_x'),
        data.get('w_opus_pct'),
        datetime.datetime.now().isoformat(),
    )
    with _conn(path) as con:
        con.execute(
            "INSERT OR REPLACE INTO daily_snapshots "
            "(date, w_cost, w_out, eff_per_m, t_cost, t_out, eff_td, cache_x, w_opus_pct, ts) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            row,
        )


def weekly_report(n_weeks: int = 12, path: Path = DB_PATH) -> list[dict]:
    """Return list of weekly aggregates, newest first."""
    with _conn(path) as con:
        rows = con.execute(WEEKLY_QUERY, (n_weeks,)).fetchall()
    return [dict(r) for r in rows]
