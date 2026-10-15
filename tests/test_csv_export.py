"""CSV export regressions without a QGIS desktop dependency."""

from __future__ import annotations

import csv
from pathlib import Path

from tools.csv_export import write_plot_csv


def test_export_keeps_separate_chainages_and_nodata(tmp_path: Path) -> None:
    """Each source retains its original sampling and invalid values become blanks."""
    output = tmp_path / "profile.csv"
    write_plot_csv(
        output,
        [
            ("DEM#1", [0.0, 1.0, 2.0], [0.0, float("nan"), 2.5]),
            ("Survey#2", [0.0, 5.0], [10.0, 20.0]),
        ],
        chainage_label="Chainage (ft)",
        value_label="Slope (%)",
    )
    with output.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream))
    assert rows == [
        ["DEM#1 Chainage (ft)", "DEM#1 Slope (%)", "Survey#2 Chainage (ft)", "Survey#2 Slope (%)"],
        ["0.0", "0.0", "0.0", "10.0"],
        ["1.0", "", "5.0", "20.0"],
        ["2.0", "2.5", "", ""],
    ]


def test_csv_quotes_source_names_and_retains_zero(tmp_path: Path) -> None:
    """Delimited layer names are quoted and legitimate zero remains a zero."""
    output = tmp_path / "quoted.csv"
    write_plot_csv(
        output,
        [('Mine, "north"', [0.0], [0.0])],
        chainage_label="Chainage (m)",
        value_label="Height",
    )
    with output.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream))
    assert rows == [
        ['Mine, "north" Chainage (m)', 'Mine, "north" Height'],
        ["0.0", "0.0"],
    ]
