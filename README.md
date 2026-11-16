# metrics-source-of-truth

One written definition per metric, gold tables built from those definitions, and a daily alert that reads the same tables everyone else does.

## The problem

Two teams ask for "active users" and mean two different things. Whichever one you answer first becomes the number everybody quotes for the next year.

Nobody's being careless. Each reading is reasonable on its own. On the synthetic data in this repo, the same question for October 2025 has 6 defensible answers:

```
Monthly active users, 2025-10: one question, 6 answers

     2,716  Contract definition (gold_monthly_metrics.mau)
     2,748  Counting failed and reversed attempts as activity  +32 (+1.2%)
     2,765  Leaving internal test accounts in  +49 (+1.8%)
     3,649  Counting people who only received a transfer  +933 (+34.4%)
     2,701  Rolling 30 days to month end instead of the calendar month  -15 (-0.6%)
    15,194  Adding up the daily active users  +12,478 (+459.4%)
```

Look at the small ones. A figure that's 459% out gets caught in the meeting, because 15,194 active users out of 4,000 customers is plainly impossible. A figure that's 1.8% out, 2,765 against 2,716, gets published. Then it doesn't match Finance, and you spend a week finding 49 test accounts.

When definitions live in 2 people's heads, you fix that by asking a senior or digging through old queries. It works until that person's on leave. So I write each definition down once, build the tables from it, and have everything read those tables.

## What's in here

| Piece | What it does |
|---|---|
| [`metrics/registry.py`](metrics/registry.py) | The contracts. One entry per metric: what it means in plain words, what counts, what doesn't, the trap people fall into, and the gold column that holds it |
| [`docs/metric_contracts.md`](docs/metric_contracts.md) | The readable version, generated from the registry. A test fails if the two fall out of step |
| [`sql/stg_transactions.sql`](sql/stg_transactions.sql) | Local reporting date, test accounts out, and the payment / funding split. Defined once |
| [`sql/gold_daily_metrics.sql`](sql/gold_daily_metrics.sql) | One row per day, no gaps. A day with nothing gets zeros, so "nothing happened" is never confused with "nothing loaded" |
| [`sql/gold_monthly_metrics.sql`](sql/gold_monthly_metrics.sql) | Additive metrics rolled up from the daily table. MAU recounted, because it isn't additive |
| [`metrics/compare.py`](metrics/compare.py) | The six-answers table above |
| [`metrics/alert.py`](metrics/alert.py) | The daily alert |

I defined 7 metrics: DAU, MAU, TPV, funding value, successful transactions, success rate and new customers. They land in 2 gold tables, 365 daily rows and 12 monthly ones.

## Run it

You need Python 3.9 or later.

```bash
pip install -r requirements.txt
```

```bash
python data/generate.py
```

```bash
python -m metrics build
```

```bash
python -m metrics compare --month 2025-10
```

```bash
python -m metrics alert --date 2025-09-17
```

```bash
python -m pytest
```

## The daily alert

The alert reads `gold_daily_metrics` and nothing else, so it can't disagree with a report built on the same table. Here's what you get for 17 September 2025, the outage day in the synthetic data:

```
Daily performance: Wed 17 Sep 2025

  Active users (DAU)                     313   LOW  (usual 380 to 513)
  Successful transactions                347   LOW  (usual 462 to 626)
  Payment value (TPV)          MRD 13,205.00   LOW  (usual MRD 14,991.64 to MRD 25,663.49)
  Success rate                         64.7%   LOW  (usual 89.8% to 96.0%)
  New customers                            2

4 figures are outside the usual range for a Wednesday. Worth a look before the day's reports go out.
```

A success rate of 64.7% on a day that's usually above 89.8%. All 4 watched figures are low at once, which is what a real incident looks like.

It writes a text file. I left out posting to a chat channel on purpose, so the repo makes no network calls.

## The messy part: my alert was wrong twice

My first 2 versions of "usual" were the obvious ones. Both were bad.

| Version | How "usual" was worked out | Days flagged |
|---|---|---|
| 1 | Same weekday, previous 8 weeks | 77, March to December |
| 2 | Same weekday and same side of payday | 55, March to December |
| 3 | Today relative to the last 28 days, compared with that same ratio on comparable days | 8 in the whole year |

Version 1 flagged 77 days in 10 months. Nearly all of them sat between the 25th and the 3rd, because volumes really do go up when salaries land.

Version 2 compared payday with payday. Down to 55, and still useless: almost every flag said HIGH. The business in this dataset nearly doubles over the year, from 11,479 transactions in January to 21,531 in December, so any baseline built from weeks ago sits too low.

Version 3 expresses each day as a ratio to the 28 days before it, then compares that ratio with the same weekday over the previous 13 weeks. Growth cancels out. The payday lift is expected. That left 8 flagged days in 365, and 17 September is the only one where all 4 figures move together. The other 7 are single-figure flags, about the noise you'd expect from bands this wide.

Why spend more time here than on the SQL? An alert that fires every week gets muted. Then it's no use on the day something's actually wrong.

## Decisions worth explaining

**TPV excludes cash in and cash out.** They move money between the wallet and the outside world. I call that funding and store it separately as `funding_minor`. Finance may well want the two added together. Fine, as long as they ask for it by a different name.

**MAU is recounted, never summed.** A customer active on 10 days is 1 monthly active user. Sum the daily figures for October and you get 15,194. Count properly and it's 2,716.

**Rates are recomputed from totals.** The monthly success rate is monthly successes over monthly attempts. Average 30 daily rates and you get a different number, and a wrong one.

**The docs can't drift from the tables.** One test checks that every column named in a contract exists. Another checks the committed documentation is exactly what the registry generates.

**I recount gold the slow way in tests.** MAU and TPV for September are recomputed row by row in plain Python and have to match exactly. That's 1 of 16 tests.

## What I'd change

- The gold tables are a full refresh. At real volume I'd make them incremental and rebuild only the days that changed.
- The payday window is a hard-coded rule, the 25th to the 3rd. It belongs in a calendar table next to public holidays, which this alert knows nothing about.
- The first 9 weeks of data have no baseline. The alert says so and flags nothing until 4 March. That's honest, but it means a new metric goes unwatched for 2 months.

## About the data

Every row is generated by [`data/generate.py`](data/generate.py) from a fixed seed: 4,000 customers and 194,707 transactions across 2025. Zaffre Wallet is invented, and so are its customers, merchants and currency. None of the code or definitions come from an employer's systems.

## Licence

MIT
