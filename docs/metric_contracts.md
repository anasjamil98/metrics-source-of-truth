# Metric contracts

Generated from `metrics/registry.py` by `python -m metrics docs`. Don't edit this file by hand:
change the registry and regenerate, and a test will fail if the two fall out of step.

Every metric uses the **local** reporting date (UTC+3) and excludes internal test accounts.

| Metric | Where | Grain | Sums across days? |
|---|---|---|---|
| [Daily active users (DAU)](#dau) | `gold_daily_metrics.dau` | local calendar day | No |
| [Monthly active users (MAU)](#mau) | `gold_monthly_metrics.mau` | local calendar month | No |
| [Total payment value (TPV)](#tpv) | `gold_daily_metrics.tpv_minor` | local calendar day (sums to month) | Yes |
| [Funding value](#funding) | `gold_daily_metrics.funding_minor` | local calendar day (sums to month) | Yes |
| [Successful transactions](#successful_txn_count) | `gold_daily_metrics.successful_txn_count` | local calendar day (sums to month) | Yes |
| [Success rate](#success_rate) | `gold_daily_metrics.success_rate` | local calendar day (recomputed for month) | No |
| [New customers](#new_customers) | `gold_daily_metrics.new_customers` | local calendar day (sums to month) | Yes |

<a id="dau"></a>
## Daily active users (DAU)

Customers who completed at least one transaction they started themselves, on that local date.

- **Counts:** Any successful transaction of any type, initiated by the customer.
- **Doesn't count:** Failed and reversed transactions. Receiving a transfer. Internal test accounts.
- **Unit:** customers
- **Stored in:** `gold_daily_metrics.dau`
- **Watch out:** Opening the app isn't activity here. If Product means sessions, that's a different metric and needs a different name.

<a id="mau"></a>
## Monthly active users (MAU)

Customers who completed at least one transaction they started themselves, in that local calendar month.

- **Counts:** Same rule as DAU, over the month.
- **Doesn't count:** Same exclusions as DAU.
- **Unit:** customers
- **Stored in:** `gold_monthly_metrics.mau`
- **Watch out:** Not the sum of DAU, and not a rolling 30 days. A customer active on ten days is one MAU.

<a id="tpv"></a>
## Total payment value (TPV)

The value of successful payments: transfers between people, merchant payments, card payments and bill payments.

- **Counts:** The transaction amount.
- **Doesn't count:** Fees. Failed and reversed transactions. Cash in and cash out, which are funding and reported separately.
- **Unit:** minor units (divide by 100 for MRD)
- **Stored in:** `gold_daily_metrics.tpv_minor`
- **Watch out:** Finance may want cash in and cash out included. That number is TPV plus funding_minor, and it should be asked for by that name.

<a id="funding"></a>
## Funding value

The value of successful cash in and cash out transactions.

- **Counts:** The transaction amount, both directions added together.
- **Doesn't count:** Fees. Failed and reversed transactions.
- **Unit:** minor units (divide by 100 for MRD)
- **Stored in:** `gold_daily_metrics.funding_minor`
- **Watch out:** This is gross movement, not net. Net funding is cash in minus cash out and isn't stored here.

<a id="successful_txn_count"></a>
## Successful transactions

The number of transactions that completed.

- **Counts:** All six transaction types.
- **Doesn't count:** Failed and reversed transactions. Internal test accounts.
- **Unit:** transactions
- **Stored in:** `gold_daily_metrics.successful_txn_count`
- **Watch out:** Includes cash in and cash out, so it's wider than the set of transactions behind TPV.

<a id="success_rate"></a>
## Success rate

Successful transactions divided by all attempts.

- **Counts:** Attempts are every row: successful, failed and reversed.
- **Doesn't count:** Internal test accounts.
- **Unit:** ratio, 0 to 1
- **Stored in:** `gold_daily_metrics.success_rate`
- **Watch out:** A reversed transaction counts as an attempt that didn't succeed. The monthly rate is recomputed from monthly totals, never averaged from daily rates.

<a id="new_customers"></a>
## New customers

Customers whose signup date is that day.

- **Counts:** Every registration, whether or not the customer has transacted.
- **Doesn't count:** Internal test accounts.
- **Unit:** customers
- **Stored in:** `gold_daily_metrics.new_customers`
- **Watch out:** A new customer isn't an active customer. Many sign up and never transact.
