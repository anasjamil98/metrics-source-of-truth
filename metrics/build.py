"""Builds the gold tables into their own database, reading the source read-only."""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = ROOT / "sql"
DEFAULT_SOURCE = ROOT / "data" / "zaffre.db"
DEFAULT_GOLD = ROOT / "data" / "gold.db"

GOLD_SQL = ["gold_daily_metrics.sql", "gold_monthly_metrics.sql"]


def connect(source_db=DEFAULT_SOURCE, gold_db=DEFAULT_GOLD):
    """Gold database as main, source attached read-only as src, staging view ready."""
    Path(gold_db).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(Path(gold_db).resolve().as_uri(), uri=True)
    con.execute("ATTACH DATABASE ? AS src", (Path(source_db).resolve().as_uri() + "?mode=ro",))
    con.executescript((SQL_DIR / "stg_transactions.sql").read_text(encoding="utf-8"))
    return con


def build(source_db=DEFAULT_SOURCE, gold_db=DEFAULT_GOLD):
    """Full refresh of both gold tables. Returns (daily rows, monthly rows)."""
    con = connect(source_db, gold_db)
    try:
        for name in GOLD_SQL:
            con.executescript((SQL_DIR / name).read_text(encoding="utf-8"))
        con.commit()
        daily = con.execute("SELECT COUNT(*) FROM gold_daily_metrics").fetchone()[0]
        monthly = con.execute("SELECT COUNT(*) FROM gold_monthly_metrics").fetchone()[0]
    finally:
        con.close()
    return daily, monthly
