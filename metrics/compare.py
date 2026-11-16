"""Shows how far "monthly active users" moves depending on who you ask.

Each variant below is a reasonable thing for somebody to mean. None of them is
stupid. That's the problem: without a written contract, whichever one gets
answered first becomes the number everybody quotes.
"""

import datetime as dt

from .build import connect

# (label, SQL returning one number). :month is 'YYYY-MM'; :first/:next are local dates.
VARIANTS = [
    (
        "Contract definition (gold_monthly_metrics.mau)",
        "SELECT mau FROM gold_monthly_metrics WHERE month = :month",
    ),
    (
        "Counting failed and reversed attempts as activity",
        "SELECT COUNT(DISTINCT customer_id) FROM stg_transactions WHERE local_month = :month",
    ),
    (
        "Leaving internal test accounts in",
        "SELECT COUNT(DISTINCT customer_id) FROM src.transactions "
        "WHERE status = 'success' AND strftime('%Y-%m', txn_ts, '+3 hours') = :month",
    ),
    (
        "Counting people who only received a transfer",
        "SELECT COUNT(*) FROM ("
        " SELECT t.customer_id FROM src.transactions t"
        " WHERE t.status = 'success' AND strftime('%Y-%m', t.txn_ts, '+3 hours') = :month"
        " UNION"
        " SELECT t.counterparty_customer_id FROM src.transactions t"
        " WHERE t.status = 'success' AND t.counterparty_customer_id IS NOT NULL"
        " AND strftime('%Y-%m', t.txn_ts, '+3 hours') = :month"
        ") AS u JOIN src.customers c ON c.customer_id = u.customer_id WHERE c.is_test_account = 0",
    ),
    (
        "Rolling 30 days to month end instead of the calendar month",
        "SELECT COUNT(DISTINCT customer_id) FROM stg_transactions "
        "WHERE status = 'success' AND local_date >= date(:next, '-30 days') AND local_date < :next",
    ),
    (
        "Adding up the daily active users",
        "SELECT SUM(dau) FROM gold_daily_metrics WHERE local_date >= :first AND local_date < :next",
    ),
]


def _bounds(month):
    year, mon = (int(part) for part in month.split("-"))
    first = dt.date(year, mon, 1)
    following = dt.date(year + (mon == 12), mon % 12 + 1, 1)
    return {"month": month, "first": first.isoformat(), "next": following.isoformat()}


def compare(month, source_db=None, gold_db=None):
    """Returns [(label, value, difference from contract)]."""
    kwargs = {k: v for k, v in (("source_db", source_db), ("gold_db", gold_db)) if v}
    con = connect(**kwargs)
    try:
        params = _bounds(month)
        values = []
        for label, sql in VARIANTS:
            used = {name: params[name] for name in params if f":{name}" in sql}
            values.append((label, con.execute(sql, used).fetchone()[0] or 0))
    finally:
        con.close()
    contract = values[0][1]
    return [(label, value, value - contract) for label, value in values]


def render(month, rows):
    contract = rows[0][1]
    lines = [f"Monthly active users, {month}: one question, {len(rows)} answers", ""]
    for label, value, diff in rows:
        change = "" if diff == 0 else f"  {diff:+,} ({diff / contract:+.1%})" if contract else f"  {diff:+,}"
        lines.append(f"  {value:>8,}  {label}{change}")
    return "\n".join(lines)
