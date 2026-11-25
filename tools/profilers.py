# -----------------------------------------------------------
#
# Profilers
# Copyright (C) 2017  Javier Becerra
# -----------------------------------------------------------
#
# licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, print to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# ---------------------------------------------------------------------

"""Height and grade transformations for sampled profiles."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypedDict

import numpy as np
from numpy.typing import NDArray

# Python 3.10+ supports PEP 604 unions at runtime.
ProfileSeries = Sequence[float] | NDArray[np.float64]


class ProfileSamples(TypedDict):
    """Required displayed chainage and elevation samples."""

    l: ProfileSeries  # noqa: E741 -- Existing profile dictionary key for chainage.
    z: ProfileSeries


class ProfileData(ProfileSamples, total=False):
    """Profile samples with optional physical chainage for grade calculations."""

    l_slope: ProfileSeries


def height(p: ProfileData) -> tuple[ProfileSeries, ProfileSeries]:
    """Return the height profile for given track p.

    Returns the x (distance from origin) and y (height)
    coordinates for the plot.
    """
    return p["l"], p["z"]


def slopes_pct(p: ProfileData) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Return grade at each sample; invalid or absent data remain gaps."""
    x = np.asarray(p["l"], dtype=float)
    y = np.asarray(p["z"], dtype=float)
    if len(x) == 0:
        return x, np.empty(0, dtype=float)
    if len(x) == 1:
        return x, np.array([np.nan])

    # Geographic projects display angular chainage, but grades use geodesic
    # metre distances. Projected projects use native linear units, assuming
    # that the elevation samples use those same units.
    physical_x = np.asarray(p.get("l_slope", p["l"]), dtype=float)
    dx = np.diff(physical_x)
    dz = np.diff(y)
    grades = np.full(len(dx), np.nan)
    valid = np.isfinite(dx) & np.isfinite(dz) & (dx != 0)
    np.divide(100 * dz, dx, out=grades, where=valid)

    result = np.full(len(x), np.nan)
    result[0], result[-1] = grades[0], grades[-1]
    if len(x) > 2:
        adjacent = np.isfinite(grades[:-1]) & np.isfinite(grades[1:])
        result[1:-1] = np.where(adjacent, (grades[:-1] + grades[1:]) / 2, np.nan)
    return x, result


def slopes_deg(p: ProfileData) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Return a profile's slope in degrees.

    Returns the x (distance from origin) and y (slope in degrees)
    coordinates for the plot.
    """
    x, slope_pct = slopes_pct(p)
    slope_deg = np.degrees(np.arctan(slope_pct / 100.0))
    return x, slope_deg


def max_finite_plot_chainage(series: Sequence[tuple[ProfileSeries, ProfileSeries]]) -> float | None:
    """Find the furthest finite chainage that has a finite plotted value.

    All plotted sources are considered, regardless of their order. A missing
    final source or NoData-only curve must not suppress valid earlier curves.
    """
    maximum: float | None = None
    for x, y in series:
        x_values = np.asarray(x, dtype=float)
        y_values = np.asarray(y, dtype=float)
        if not len(x_values) or len(x_values) != len(y_values):
            continue
        valid = np.isfinite(x_values) & np.isfinite(y_values)
        if valid.any():
            source_max = float(np.max(x_values[valid]))
            maximum = source_max if maximum is None else max(maximum, source_max)
    return maximum


PLOT_PROFILERS: dict[str, Callable[[ProfileData], tuple[ProfileSeries, ProfileSeries]]] = {
    "Height": height,
    "Slope (%)": slopes_pct,
    "Slope (°)": slopes_deg,
}
