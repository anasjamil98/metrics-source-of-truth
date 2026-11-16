-- gold_monthly_metrics: one row per local calendar month.
--
-- Additive metrics are rolled up FROM the daily gold table, so the monthly
-- figure and the sum of the daily figures can never disagree.
--
-- MAU is the exception. A customer active on ten days is one monthly active
-- user, not ten, so MAU is counted again from staging. Summing DAU to get MAU
-- is the most common way this number goes wrong.

DROP TABLE IF EXISTS gold_monthly_metrics;

CREATE TABLE gold_monthly_metrics AS
WITH monthly_active AS (
    SELECT local_month AS month, COUNT(DISTINCT customer_id) AS mau
    FROM stg_transactions
    WHERE status = 'success'
    GROUP BY local_month
),
rolled_up AS (
    SELECT
        substr(local_date, 1, 7)  AS month,
        SUM(new_customers)        AS new_customers,
        SUM(successful_txn_count) AS successful_txn_count,
        SUM(attempt_count)        AS attempt_count,
        SUM(tpv_minor)            AS tpv_minor,
        SUM(funding_minor)        AS funding_minor,
        AVG(dau)                  AS avg_dau
    FROM gold_daily_metrics
    GROUP BY substr(local_date, 1, 7)
)
SELECT
    rolled_up.month,
    COALESCE(monthly_active.mau, 0) AS mau,
    rolled_up.new_customers,
    rolled_up.successful_txn_count,
    rolled_up.attempt_count,
    CASE WHEN rolled_up.attempt_count > 0
         THEN ROUND(1.0 * rolled_up.successful_txn_count / rolled_up.attempt_count, 4)
    END                             AS success_rate,
    rolled_up.tpv_minor,
    rolled_up.funding_minor,
    ROUND(rolled_up.avg_dau, 1)     AS avg_dau,
    CASE WHEN monthly_active.mau > 0
         THEN ROUND(rolled_up.avg_dau / monthly_active.mau, 4)
    END                             AS stickiness
FROM rolled_up
LEFT JOIN monthly_active ON monthly_active.month = rolled_up.month
ORDER BY rolled_up.month;
