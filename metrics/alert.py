"""Daily performance alert.

Reads the gold table and says whether each of today's figures is unusual. It
only reads gold: the alert and every report quoting the same metrics are
looking at the same stored numbers.

Getting "unusual" right took three attempts, and the first two are worth
knowing about because they're the obvious ones.

1. Compare with the same weekday over recent weeks. This flagged nearly every
   month-end, because volumes really do rise when salaries land.
2. Compare only with days on the same side of payday. Better, but it still
   flagged dozens of days as HIGH. The business is growing, so any baseline
   built from weeks ago sits too low.
3. What's here now. Each day is first expressed relative to the level of the
   28 days before it ("today is 1.12x the recent level"). That ratio is then
   compared with the same ratio on comparable days: same weekday, same side of
   payday, previous thirteen weeks. Growth cancels out, the payday lift is
   expected, and what's left is the genuinely odd days.

Medians throughout, because one bad Wednesday shouldn't change what a normal
Wednesday looks like. The success rate doesn't trend, so it's compared
directly.

An alert that fires every week gets muted, and then it's no use on the day
something is actually wrong. That's the whole reason for the care above.

The message is written to a text file. Posting it to a chat channel is one
function call away and deliberately left out, so this repo makes no network
calls.
"""

import datetime as dt
import sqlite3
import statistics
from pathlib import Path

from .build import DEFAULT_GOLD, ROOT

WEEKS_OF_HISTORY = 13
LEVEL_DAYS = 28
MIN_HISTORY = 3

# column, label, kind, minimum band (relative for counts and money, absolute for the rate)
ALERT_METRICS = [
    ("dau", "Active users (DAU)", "count", 0.15),
    ("successful_txn_count", "Successful transactions", "count", 0.15),
    ("tpv_minor", "Payment value (TPV)", "money", 0.20),
    ("success_rate", "Success rate", "rate", 0.03),
]
INFO_METRICS = [("new_customers", "New customers", "count")]


def _format(value, kind):
    if value is None:
        return "n/a"
    if kind == "money":
        return f"MRD {value / 100:,.2f}"
    if kind == "rate":
        return f"{value:.1%}"
    return f"{int(round(value)):,}"


def usual_range(history, minimum_band, relative=True):
    """(low, high) around the median of history, or None when there isn't enough of it.

    The band is three scaled median absolute deviations, but never narrower
    than minimum_band (a share of the median when relative, else absolute).
    """
    history = [v for v in history if v is not None]
    if len(history) < MIN_HISTORY:
        return None
    median = statistics.median(history)
    mad = statistics.median(abs(v - median) for v in history)
    floor = minimum_band * median if relative else minimum_band
    spread = max(3 * 1.4826 * mad, floor)
    return median - spread, median + spread


def _load(gold_db):
    con = sqlite3.connect(Path(gold_db).resolve().as_uri() + "?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        return {row["local_date"]: row for row in con.execute("SELECT * FROM gold_daily_metrics")}
    finally:
        con.close()


def _recent_level(days, day, column):
    """Median of the 28 days before `day`, or None if any of them is missing."""
    values = []
    for back in range(1, LEVEL_DAYS + 1):
        row = days.get((day - dt.timedelta(days=back)).isoformat())
        if row is None:
            return None
        values.append(row[column])
    return statistics.median(values) or None


def _band(days, day, column, kind, minimum_band):
    """The usual range for `day`, in the metric's own units."""
    today = days[day.isoformat()]
    comparable = []
    for week in range(1, WEEKS_OF_HISTORY + 1):
        past = day - dt.timedelta(weeks=week)
        row = days.get(past.isoformat())
        if row is not None and row["is_payday_window"] == today["is_payday_window"]:
            comparable.append((past, row[column]))

    if kind == "rate":
        return usual_range([value for _, value in comparable], minimum_band, relative=False)

    level_today = _recent_level(days, day, column)
    if level_today is None:
        return None
    ratios = []
    for past, value in comparable:
        level = _recent_level(days, past, column)
        if level is not None:
            ratios.append(value / level)
    band = usual_range(ratios, minimum_band)
    if band is None:
        return None
    return band[0] * level_today, band[1] * level_today


def evaluate(date_text, gold_db=DEFAULT_GOLD):
    """Returns (rows, flagged) for one local date. Raises LookupError for an unknown date."""
    days = _load(gold_db)
    if date_text not in days:
        raise LookupError(f"{date_text} isn't in gold_daily_metrics")
    day = dt.date.fromisoformat(date_text)
    today = days[date_text]

    rows, flagged = [], []
    for column, label, kind, minimum_band in ALERT_METRICS:
        value = today[column]
        band = _band(days, day, column, kind, minimum_band)
        if band is None or value is None:
            state = "no baseline yet"
        elif value < band[0]:
            state = "LOW"
        elif value > band[1]:
            state = "HIGH"
        else:
            state = "normal"
        if state in ("LOW", "HIGH"):
            flagged.append(column)
        usual = "" if band is None else f"usual {_format(max(band[0], 0), kind)} to {_format(band[1], kind)}"
        rows.append((label, _format(value, kind), state, usual))
    for column, label, kind in INFO_METRICS:
        rows.append((label, _format(today[column], kind), "", ""))
    return rows, flagged


def render(date_text, rows, flagged):
    day = dt.date.fromisoformat(date_text)
    kind_of_day = day.strftime("%A")
    lines = [f"Daily performance: {day.strftime('%a %d %b %Y')}", ""]
    for label, value, state, usual in rows:
        note = f"{state}  ({usual})" if usual else state
        lines.append(f"  {label:<26}{value:>16}   {note}".rstrip())
    lines.append("")
    if flagged:
        noun = "figure is" if len(flagged) == 1 else "figures are"
        lines.append(
            f"{len(flagged)} {noun} outside the usual range for a {kind_of_day}. "
            "Worth a look before the day's reports go out."
        )
    else:
        lines.append(f"Everything is inside the usual range for a {kind_of_day}.")
    return "\n".join(lines)


def run(date_text, gold_db=DEFAULT_GOLD, out_dir=ROOT / "output"):
    rows, flagged = evaluate(date_text, gold_db)
    message = render(date_text, rows, flagged)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"alert_{date_text}.txt"
    path.write_text(message + "\n", encoding="utf-8")
    return message, flagged, path
