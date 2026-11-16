-- Staging view over the source database (attached read-only as "src").
-- Local reporting date, test accounts excluded, and the payment / funding
-- split that TPV depends on. Defined once, used by every gold table.

CREATE TEMP VIEW stg_transactions AS
SELECT
    t.txn_id,
    date(t.txn_ts, '+3 hours')              AS local_date,
    strftime('%Y-%m', t.txn_ts, '+3 hours') AS local_month,
    t.customer_id,
    t.txn_type,
    t.amount_minor,
    t.status,
    -- Cash in and cash out move money between the wallet and the outside
    -- world. They're funding, not payments, and they don't count towards TPV.
    t.txn_type IN ('p2p_transfer', 'merchant_payment', 'card_payment', 'bill_payment') AS is_payment
FROM src.transactions AS t
JOIN src.customers    AS c ON c.customer_id = t.customer_id
WHERE c.is_test_account = 0;
