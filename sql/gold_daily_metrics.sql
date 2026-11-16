-- gold_daily_metrics: one row per local calendar day, no gaps.
-- A day with no activity gets a row of zeros, not a missing row, so a chart
-- or an alert never mistakes "nothing happened" for "nothing loaded".

DROP TABLE IF EXISTS gold_daily_metrics;

CREATE TABLE gold_daily_metrics AS
WITH RECURSIVE
bounds AS (
    SELECT MIN(local_date) AS first_date, MAX(local_date) AS last_date
    FROM stg_transactions
),
calendar (local_date) AS (
    SELECT first_date FROM bounds
    UNION ALL
    SELECT date(calendar.local_date, '+1 day')
    FROM calendar, bounds
    WHERE calendar.local_date < bounds.last_date
),
activity AS (
    SELECT
        local_date,
        COUNT(DISTINCT CASE WHEN status = 'success' THEN customer_id END)             AS dau,
        SUM(status = 'success')                                                       AS successful_txn_count,
        COUNT(*)                                                                      AS attempt_count,
        SUM(CASE WHEN status = 'success' AND is_payment     THEN amount_minor ELSE 0 END) AS tpv_minor,
        SUM(CASE WHEN status = 'success' AND NOT is_payment THEN amount_minor ELSE 0 END) AS funding_minor
    FROM stg_transactions
    GROUP BY local_date
),
signups AS (
    SELECT signup_date AS local_date, COUNT(*) AS new_customers
    FROM src.customers
    WHERE is_test_account = 0
    GROUP BY signup_date
)
SELECT
    calendar.local_date,
    -- Salaries land around month end, and volumes rise with them. It's a
    -- calendar fact, stored here so nothing downstream has to rediscover it.
    CAST(strftime('%d', calendar.local_date) AS INTEGER) >= 25
        OR CAST(strftime('%d', calendar.local_date) AS INTEGER) <= 3 AS is_payday_window,
    COALESCE(activity.dau, 0)                  AS dau,
    COALESCE(signups.new_customers, 0)         AS new_customers,
    COALESCE(activity.successful_txn_count, 0) AS successful_txn_count,
    COALESCE(activity.attempt_count, 0)        AS attempt_count,
    CASE WHEN activity.attempt_count > 0
         THEN ROUND(1.0 * activity.successful_txn_count / activity.attempt_count, 4)
    END                                        AS success_rate,
    COALESCE(activity.tpv_minor, 0)            AS tpv_minor,
    COALESCE(activity.funding_minor, 0)        AS funding_minor
FROM calendar
LEFT JOIN activity ON activity.local_date = calendar.local_date
LEFT JOIN signups  ON signups.local_date  = calendar.local_date
ORDER BY calendar.local_date;
