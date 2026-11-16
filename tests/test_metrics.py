import datetime as dt
import sqlite3

from metrics import alert, compare, docs
from metrics.registry import METRICS


def scalar(con, sql, params=()):
    return con.execute(sql, params).fetchone()[0]


# ---- the contract and the tables can't drift --------------------------------

def test_every_metric_points_at_a_real_column(con):
    for metric in METRICS:
        columns = {row[1] for row in con.execute(f"PRAGMA table_info({metric.table})")}
        assert metric.column in columns, f"{metric.key} -> {metric.table}.{metric.column} doesn't exist"


def test_committed_docs_match_the_registry():
    assert docs.DOC_PATH.read_text(encoding="utf-8") == docs.render()


def test_metric_keys_are_unique():
    keys = [m.key for m in METRICS]
    assert len(keys) == len(set(keys))


# ---- shape of the gold tables ----------------------------------------------

def test_daily_table_has_one_row_per_day_and_no_gaps(con):
    first, last, rows, distinct = con.execute(
        "SELECT MIN(local_date), MAX(local_date), COUNT(*), COUNT(DISTINCT local_date) FROM gold_daily_metrics"
    ).fetchone()
    span = (dt.date.fromisoformat(last) - dt.date.fromisoformat(first)).days + 1
    assert rows == distinct == span == 365


def test_no_negative_or_impossible_values(con):
    bad = scalar(
        con,
        "SELECT COUNT(*) FROM gold_daily_metrics WHERE dau < 0 OR tpv_minor < 0 OR funding_minor < 0 "
        "OR successful_txn_count > attempt_count OR success_rate < 0 OR success_rate > 1 "
        "OR dau > successful_txn_count",
    )
    assert bad == 0


# ---- additive metrics roll up exactly; MAU doesn't --------------------------

def test_monthly_additive_metrics_equal_the_sum_of_daily(con):
    for column in ("tpv_minor", "funding_minor", "successful_txn_count", "attempt_count", "new_customers"):
        mismatches = scalar(
            con,
            f"SELECT COUNT(*) FROM gold_monthly_metrics m WHERE m.{column} <> "
            f"(SELECT SUM(d.{column}) FROM gold_daily_metrics d WHERE substr(d.local_date, 1, 7) = m.month)",
        )
        assert mismatches == 0, column


def test_mau_sits_between_peak_dau_and_summed_dau(con):
    rows = con.execute(
        "SELECT m.month, m.mau, MAX(d.dau), SUM(d.dau) FROM gold_monthly_metrics m "
        "JOIN gold_daily_metrics d ON substr(d.local_date, 1, 7) = m.month GROUP BY m.month"
    ).fetchall()
    assert len(rows) == 12
    for month, mau, peak_dau, summed_dau in rows:
        assert peak_dau <= mau < summed_dau, month


def test_monthly_success_rate_is_recomputed_not_averaged(con):
    for month, rate, successes, attempts in con.execute(
        "SELECT month, success_rate, successful_txn_count, attempt_count FROM gold_monthly_metrics"
    ):
        assert rate == round(successes / attempts, 4), month


# ---- the numbers agree with a slow, obvious recount --------------------------

def test_mau_and_tpv_match_a_row_by_row_recount(dbs, con):
    source, _ = dbs
    raw = sqlite3.connect(str(source))
    test_accounts = {r[0] for r in raw.execute("SELECT customer_id FROM customers WHERE is_test_account = 1")}
    payments = {"p2p_transfer", "merchant_payment", "card_payment", "bill_payment"}
    active, tpv = set(), 0
    for ts, customer_id, txn_type, amount, status in raw.execute(
        "SELECT txn_ts, customer_id, txn_type, amount_minor, status FROM transactions"
    ):
        local = dt.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") + dt.timedelta(hours=3)
        if (local.year, local.month) != (2025, 9) or status != "success" or customer_id in test_accounts:
            continue
        active.add(customer_id)
        if txn_type in payments:
            tpv += amount
    raw.close()
    mau, tpv_gold = con.execute("SELECT mau, tpv_minor FROM gold_monthly_metrics WHERE month = '2025-09'").fetchone()
    assert (mau, tpv_gold) == (len(active), tpv)


def test_test_accounts_never_reach_gold(con):
    with_test_accounts = scalar(
        con,
        "SELECT COUNT(DISTINCT customer_id) FROM src.transactions "
        "WHERE status = 'success' AND strftime('%Y-%m', txn_ts, '+3 hours') = '2025-09'",
    )
    assert scalar(con, "SELECT mau FROM gold_monthly_metrics WHERE month = '2025-09'") < with_test_accounts


# ---- one question, several answers ------------------------------------------

def test_every_looser_definition_gives_a_different_number(dbs):
    rows = compare.compare("2025-09", *dbs)
    assert rows[0][2] == 0
    by_label = {label: diff for label, _, diff in rows}
    assert by_label["Counting failed and reversed attempts as activity"] >= 0
    assert by_label["Leaving internal test accounts in"] > 0
    assert by_label["Counting people who only received a transfer"] > 0
    assert by_label["Adding up the daily active users"] > 0
    assert by_label["Rolling 30 days to month end instead of the calendar month"] == 0  # September has 30 days
    assert compare.compare("2025-10", *dbs)[4][2] != 0  # October doesn't


# ---- the alert ---------------------------------------------------------------

def test_outage_day_is_flagged_on_success_rate(dbs, tmp_path):
    _, gold = dbs
    message, flagged, path = alert.run("2025-09-17", gold, tmp_path)
    assert "success_rate" in flagged
    assert "LOW" in message
    assert path.read_text(encoding="utf-8").strip() == message


def test_ordinary_day_does_not_flag_success_rate(dbs, tmp_path):
    _, gold = dbs
    _, flagged, _ = alert.run("2025-06-11", gold, tmp_path)
    assert "success_rate" not in flagged


def test_first_week_has_no_baseline(dbs, tmp_path):
    _, gold = dbs
    message, flagged, _ = alert.run("2025-01-05", gold, tmp_path)
    assert flagged == []
    assert "no baseline yet" in message


def test_usual_range_ignores_one_bad_week():
    steady = [100, 102, 98, 101, 99, 100, 103, 20]  # one outage in the history
    low, high = alert.usual_range(steady, 0.15)
    assert low < 100 < high
    assert 20 < low  # the outage is still outside the band it helped to build


def test_unknown_date_raises(dbs, tmp_path):
    _, gold = dbs
    try:
        alert.run("2030-01-01", gold, tmp_path)
    except LookupError:
        return
    raise AssertionError("expected LookupError")
