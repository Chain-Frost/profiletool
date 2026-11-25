"""Shared contracts for sampled profiles and plot-ready profile records."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from .profilers import ProfileData, ProfileSeries

if TYPE_CHECKING:
    from qgis.core import QgsCoordinateReferenceSystem, QgsGeometry, QgsMapLayer


class SourceProfile(TypedDict):
    """Layer and band/field identity available before sampling."""

    layer: QgsMapLayer
    band: int


class ReaderProfile(SourceProfile, total=False):
    """Mutable reader record, populated as sampling and plotting proceed."""

    l: ProfileSeries  # noqa: E741 -- Established profile dictionary key for chainage.
    l_slope: ProfileSeries
    z: ProfileSeries
    x: list[float]
    y: list[float]
    crs: QgsCoordinateReferenceSystem
    plot_x: ProfileSeries
    plot_y: ProfileSeries
    _buffer_geometry: QgsGeometry | None
    _guide_geometry: QgsGeometry | None


class SampledProfile(ProfileData, SourceProfile):
    """Source identity and source-coordinate samples returned by the readers."""

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
