"""Generates docs/metric_contracts.md from the registry."""

from pathlib import Path

from .registry import METRICS

ROOT = Path(__file__).resolve().parent.parent
DOC_PATH = ROOT / "docs" / "metric_contracts.md"


def render():
    out = [
        "# Metric contracts",
        "",
        "Generated from `metrics/registry.py` by `python -m metrics docs`. Don't edit this file by hand:",
        "change the registry and regenerate, and a test will fail if the two fall out of step.",
        "",
        "Every metric uses the **local** reporting date (UTC+3) and excludes internal test accounts.",
        "",
        "| Metric | Where | Grain | Sums across days? |",
        "|---|---|---|---|",
    ]
    for m in METRICS:
        out.append(f"| [{m.name}](#{m.key}) | `{m.table}.{m.column}` | {m.grain} | {'Yes' if m.additive else 'No'} |")
    for m in METRICS:
        out += [
            "",
            f'<a id="{m.key}"></a>',
            f"## {m.name}",
            "",
            m.definition,
            "",
            f"- **Counts:** {m.counts}",
            f"- **Doesn't count:** {m.excludes}",
            f"- **Unit:** {m.unit}",
            f"- **Stored in:** `{m.table}.{m.column}`",
            f"- **Watch out:** {m.watch_out}",
        ]
    return "\n".join(out) + "\n"


def write():
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(str(DOC_PATH), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(render())
    return DOC_PATH
