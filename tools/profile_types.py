"""Shared contracts for sampled profiles and plot-ready profile records."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .profilers import ProfileData, ProfileSeries

if TYPE_CHECKING:
    from qgis.core import QgsCoordinateReferenceSystem, QgsGeometry, QgsMapLayer


class SampledProfile(ProfileData):
    """Source identity and source-coordinate samples returned by the readers."""

    layer: QgsMapLayer
    band: int
    x: list[float]
    y: list[float]
    crs: QgsCoordinateReferenceSystem


class PlotSamples(SampledProfile):
    """Sampled profile with the selected height or grade plot series."""

    plot_x: ProfileSeries
    plot_y: ProfileSeries


class Profile(PlotSamples, total=False):
    """Plot-ready profile with optional point-source buffer/guide geometry."""

    _buffer_geometry: QgsGeometry | None
    _guide_geometry: QgsGeometry | None
