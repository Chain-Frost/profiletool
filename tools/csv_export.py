"""Write independent plot series to a portable CSV file."""

from __future__ import annotations

import csv
from collections.abc import Iterable, Sequence
from itertools import zip_longest
from math import isfinite
from pathlib import Path


def write_plot_csv(
    path: str | Path,
    series: Sequence[tuple[str, Iterable[float], Iterable[float]]],
    *,
    chainage_label: str,
    value_label: str,
) -> None:
    """Export x/y pairs, retaining unequal sample counts and missing-data gaps."""
    columns: list[Iterable[float]] = []
    headers: list[str] = []
    for name, chainages, values in series:
        headers.extend((f"{name} {chainage_label}", f"{name} {value_label}"))
        columns.extend((chainages, values))

    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        for row in zip_longest(*columns, fillvalue=None):
            writer.writerow([value if value is not None and isfinite(value) else "" for value in row])
