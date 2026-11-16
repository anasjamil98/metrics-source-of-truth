"""The metric contracts.

One entry per metric: what it means in plain words, what counts, what doesn't,
and which gold column holds it. The documentation is generated from this file
and a test checks every column named here exists, so the definition people
read and the number they get can't drift apart.
"""

from collections import namedtuple

Metric = namedtuple(
    "Metric",
    "key name table column grain unit additive definition counts excludes watch_out",
)

METRICS = [
    Metric(
        key="dau",
        name="Daily active users (DAU)",
        table="gold_daily_metrics",
        column="dau",
        grain="local calendar day",
        unit="customers",
        additive=False,
        definition="Customers who completed at least one transaction they started themselves, on that local date.",
        counts="Any successful transaction of any type, initiated by the customer.",
        excludes="Failed and reversed transactions. Receiving a transfer. Internal test accounts.",
        watch_out="Opening the app isn't activity here. If Product means sessions, that's a different metric and needs a different name.",
    ),
    Metric(
        key="mau",
        name="Monthly active users (MAU)",
        table="gold_monthly_metrics",
        column="mau",
        grain="local calendar month",
        unit="customers",
        additive=False,
        definition="Customers who completed at least one transaction they started themselves, in that local calendar month.",
        counts="Same rule as DAU, over the month.",
        excludes="Same exclusions as DAU.",
        watch_out="Not the sum of DAU, and not a rolling 30 days. A customer active on ten days is one MAU.",
    ),
    Metric(
        key="tpv",
        name="Total payment value (TPV)",
        table="gold_daily_metrics",
        column="tpv_minor",
        grain="local calendar day (sums to month)",
        unit="minor units (divide by 100 for MRD)",
        additive=True,
        definition="The value of successful payments: transfers between people, merchant payments, card payments and bill payments.",
        counts="The transaction amount.",
        excludes="Fees. Failed and reversed transactions. Cash in and cash out, which are funding and reported separately.",
        watch_out="Finance may want cash in and cash out included. That number is TPV plus funding_minor, and it should be asked for by that name.",
    ),
    Metric(
        key="funding",
        name="Funding value",
        table="gold_daily_metrics",
        column="funding_minor",
        grain="local calendar day (sums to month)",
        unit="minor units (divide by 100 for MRD)",
        additive=True,
        definition="The value of successful cash in and cash out transactions.",
        counts="The transaction amount, both directions added together.",
        excludes="Fees. Failed and reversed transactions.",
        watch_out="This is gross movement, not net. Net funding is cash in minus cash out and isn't stored here.",
    ),
    Metric(
        key="successful_txn_count",
        name="Successful transactions",
        table="gold_daily_metrics",
        column="successful_txn_count",
        grain="local calendar day (sums to month)",
        unit="transactions",
        additive=True,
        definition="The number of transactions that completed.",
        counts="All six transaction types.",
        excludes="Failed and reversed transactions. Internal test accounts.",
        watch_out="Includes cash in and cash out, so it's wider than the set of transactions behind TPV.",
    ),
    Metric(
        key="success_rate",
        name="Success rate",
        table="gold_daily_metrics",
        column="success_rate",
        grain="local calendar day (recomputed for month)",
        unit="ratio, 0 to 1",
        additive=False,
        definition="Successful transactions divided by all attempts.",
        counts="Attempts are every row: successful, failed and reversed.",
        excludes="Internal test accounts.",
        watch_out="A reversed transaction counts as an attempt that didn't succeed. The monthly rate is recomputed from monthly totals, never averaged from daily rates.",
    ),
    Metric(
        key="new_customers",
        name="New customers",
        table="gold_daily_metrics",
        column="new_customers",
        grain="local calendar day (sums to month)",
        unit="customers",
        additive=True,
        definition="Customers whose signup date is that day.",
        counts="Every registration, whether or not the customer has transacted.",
        excludes="Internal test accounts.",
        watch_out="A new customer isn't an active customer. Many sign up and never transact.",
    ),
]

BY_KEY = {metric.key: metric for metric in METRICS}
