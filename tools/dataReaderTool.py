# -----------------------------------------------------------
#
# Profile
# Copyright (C) 2008  Borys Jurgiel
# Copyright (C) 2012  Patrice Verchere
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
"""Sample raster and vector elevations along profile paths."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, cast

import numpy as np
from qgis.core import (
    Qgis,
    QgsCoordinateTransform,
    QgsDistanceArea,
    QgsFeatureRequest,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsUnitTypes,
)
from qgis.PyQt.QtCore import QCoreApplication

from .utils import isProfilable

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Protocol

    from numpy.typing import NDArray
    from qgis.core import (
        QgsFeature,
        QgsRasterDataProvider,
        QgsRasterLayer,
        QgsVectorLayer,
    )
    from qgis.gui import QgisInterface, QgsMapTool
    from qgis.PyQt.QtWidgets import QMainWindow

    from .profile_types import ReaderProfile

    class _LineGeometry(Protocol):
        """QGIS geometry with its native line-vertex return contract."""

        def asPolyline(self) -> list[QgsPointXY]:
            """Return vertices of the single-part geometry."""
            ...

    class _PluginIdentifier(Protocol):
        """Optional third-party QGIS plugin-layer identification interface."""

        def identify(self, point: QgsPointXY) -> tuple[object, Mapping[str, float | str]]:
            """Return source-band values for the requested coordinate."""
            ...


class DataReaderTool:
    """Read elevations and construct source-aware profile arrays."""

    @staticmethod
    def _project() -> QgsProject:
        """Return the active project required for coordinate transformations."""
        project = QgsProject.instance()
        if project is None:
            msg = "Profile sampling requires an active QGIS project"
            raise RuntimeError(msg)
        return project

    def dataRasterReaderTool(
        self,
        iface1: QgisInterface,
        tool1: QgsMapTool,
        profile1: ReaderProfile,
        pointstoDraw1: Sequence[Sequence[float]],
        resolution_mode: str,
    ) -> ReaderProfile:
        """Sample a raster/mesh along a line drawn in the project CRS.

        Chainage uses the project CRS's native angular or linear units.
        Sample coordinates are stored in the source layer CRS.
        """
        self.tool = tool1
        self.profiles = profile1
        self.pointstoDraw = pointstoDraw1
        self.iface = iface1

        lengths: list[float] = []
        sample_x: list[float] = []
        sample_y: list[float] = []
        project_samples: list[QgsPointXY] = []
        previous_length = 0.0
        project_scale = self._project_distance_scale()
        first_segment = True
        layer = profile1["layer"]

        for start, end in zip(pointstoDraw1[:-1], pointstoDraw1[1:]):
            start_map, end_map = QgsPointXY(*start), QgsPointXY(*end)
            start_layer = tool1.toLayerCoordinates(layer, start_map)
            end_layer = tool1.toLayerCoordinates(layer, end_map)
            dx = end[0] - start[0]
            dy = end[1] - start[1]

            if resolution_mode == "samples":
                steps = 1
            elif layer.type() == Qgis.LayerType.Raster:
                raster_layer = cast("QgsRasterLayer", layer)
                pixel_x = abs(raster_layer.rasterUnitsPerPixelX())
                pixel_y = abs(raster_layer.rasterUnitsPerPixelY())
                if not pixel_x or not pixel_y:
                    steps = 1
                else:
                    steps = max(
                        1,
                        int(
                            np.ceil(
                                max(
                                    abs(end_layer.x() - start_layer.x()) / pixel_x,
                                    abs(end_layer.y() - start_layer.y()) / pixel_y,
                                )
                            )
                        ),
                    )
            else:
                steps = max(1, int(np.ceil(np.hypot(dx, dy))))
            if resolution_mode == "limited":
                steps = min(steps, 1000)

            segment_length = float(np.hypot(dx, dy)) * project_scale
            for n in range(0 if first_segment else 1, steps + 1):
                fraction = n / steps
                point_map = QgsPointXY(start[0] + fraction * dx, start[1] + fraction * dy)
                # Transform each point; projecting only the endpoints and
                # interpolating in layer CRS distorts long/mixed-CRS lines.
                point_layer = tool1.toLayerCoordinates(layer, point_map)
                project_samples.append(point_map)
                sample_x.append(point_layer.x())
                sample_y.append(point_layer.y())
                lengths.append(previous_length + fraction * segment_length)
            previous_length += segment_length
            first_segment = False

        profile1.update(
            {
                "l": lengths,
                "l_slope": self._slope_distances(project_samples, lengths),
                "z": self._extractZValues(sample_x, sample_y),
                "x": sample_x,
                "y": sample_y,
                "crs": layer.crs(),
            }
        )
        self._status_message("")
        return profile1

    @staticmethod
    def project_distance_scale() -> float:
        """Return the shared conversion from project units to plot chainage units."""
        return DataReaderTool._project_distance_scale()

    @staticmethod
    def _project_distance_scale() -> float:
        """Keep displayed chainage in native project map units."""
        return 1.0

    @staticmethod
    def _slope_distances(project_points: Sequence[QgsPointXY], chainages: list[float]) -> list[float]:
        """Slope distance in metres, independently of displayed CRS units.

        A geographic project's displayed chainage remains angular. Geodesic
        segment lengths are used only for grades, which must have linear units.
        """
        if not project_points:
            return []
        project = DataReaderTool._project()
        if not project.crs().isGeographic():
            factor = QgsUnitTypes.fromUnitToUnitFactor(project.crs().mapUnits(), Qgis.DistanceUnit.Meters)
            return [chainage * factor for chainage in chainages]
        distance = QgsDistanceArea()
        distance.setSourceCrs(project.crs(), project.transformContext())
        ellipsoid = project.ellipsoid()
        distance.setEllipsoid(ellipsoid if ellipsoid and ellipsoid != "NONE" else "WGS84")
        result = [0.0]
        for start, end in zip(project_points[:-1], project_points[1:]):
            result.append(result[-1] + distance.measureLine(start, end))
        return result

    @staticmethod
    def _project_chainage_tolerance() -> float:
        """Tolerance in native project map units (not always metres)."""
        project_crs = DataReaderTool._project().crs()
        if project_crs.isGeographic():
            return 1e-8  # Avoid treating separate locations as duplicates.
        metres_per_unit = QgsUnitTypes.fromUnitToUnitFactor(project_crs.mapUnits(), Qgis.DistanceUnit.Meters)
        return 0.01 / metres_per_unit

    def _status_update(self, advancement_pct: int) -> None:
        """Send a progress message to status bar.

        advancement_pct is the advancemente in percentage (from 0 to 100).
        """
        if advancement_pct % 10 == 0:
            progress = "Creating profile: " + "|" * (advancement_pct // 10)
            self._status_message(progress)

    def _status_message(self, message: str) -> None:
        """Update progress only when the desktop window and status bar exist."""
        window = cast("QMainWindow | None", self.iface.mainWindow())
        if window is not None:
            status_bar = window.statusBar()
            if status_bar is not None:
                status_bar.showMessage(message)

    def _extractZValues(self, x: Sequence[float], y: Sequence[float]) -> list[float]:
        layer = self.profiles["layer"]
        band = self.profiles["band"]
        values: list[float] = []
        if not x:
            return values

        is_plugin = layer.type() == Qgis.LayerType.Plugin and isProfilable(layer)
        is_mesh = layer.type() == Qgis.LayerType.Mesh
        identifier = None
        if is_mesh:
            from qgis.gui import QgsMapToolIdentify

            canvas = self.iface.mapCanvas()
            if canvas is not None:
                identifier = QgsMapToolIdentify(canvas)
        mesh_field = QCoreApplication.translate("QgsMapToolIdentify", "Scalar Value")
        # Non-plugin/non-mesh sources reach this method through the raster path.
        provider = cast("QgsRasterDataProvider | None", layer.dataProvider()) if not (is_plugin or is_mesh) else None

        for n, (x_coord, y_coord) in enumerate(zip(x, y)):
            point = QgsPointXY(x_coord, y_coord)
            value = np.nan
            try:
                if is_plugin:
                    # Only plugin layers provide identify(); it is not on QgsMapLayer.
                    plugin_source = cast("_PluginIdentifier", layer)
                    result = plugin_source.identify(point)
                    value = float(list(result[1].values())[band])
                elif is_mesh and identifier is not None:
                    matches = identifier.identify(
                        QgsGeometry.fromPointXY(point),
                        identifier.IdentifyMode.DefaultQgsSetting,
                        [layer],
                        identifier.Type.MeshLayer,
                    )
                    if matches:
                        scalar = matches[0].mAttributes.get(mesh_field)
                        if scalar is not None:
                            value = float(scalar)
                elif provider is not None:
                    # Single-band sampling avoids expensive multi-band identify().
                    sampled, valid = provider.sample(point, band)
                    if valid:
                        value = float(sampled)
            except (AttributeError, IndexError, KeyError, TypeError, ValueError):
                pass  # Unavailable/out-of-range samples are gaps, never 0 m.
            values.append(value if np.isfinite(value) else np.nan)
            self._status_update((100 * n) // max(1, len(x) - 1))
        return values

    def dataVectorReaderTool(
        self,
        iface1: QgisInterface,  # noqa: ARG002 -- Preserve the legacy vector-reader call signature.
        tool1: QgsMapTool,  # noqa: ARG002 -- Preserve the legacy vector-reader call signature.
        profile1: ReaderProfile,
        pointstoDraw1: Sequence[Sequence[float]],
        valbuf1: float,
    ) -> tuple[ReaderProfile, QgsGeometry | None, QgsGeometry | None]:
        """Sample point features near a profile line in the project CRS.

        Buffer and exact distance checks are both performed in project units,
        irrespective of the source point layer's CRS.
        """
        # The vector reader is dispatched only for vector layers by the core.
        layer = cast("QgsVectorLayer", profile1["layer"])
        profile: ReaderProfile = {
            "layer": layer,
            "band": profile1["band"],
            "l": [],
            "z": [],
            "x": [],
            "y": [],
            "crs": DataReaderTool._project().crs(),
        }
        if len(pointstoDraw1) < 2:
            return profile, None, None

        geom = QgsGeometry.fromPolylineXY([QgsPointXY(*p) for p in pointstoDraw1])
        if geom.isEmpty() or geom.length() == 0:
            return profile, None, None

        buffer_distance = max(0.0, float(valbuf1))
        buffer_geom = geom.buffer(buffer_distance, 12)
        project_crs = DataReaderTool._project().crs()
        layer_crs = layer.crs()
        to_layer = QgsCoordinateTransform(project_crs, layer_crs, DataReaderTool._project())
        to_project = QgsCoordinateTransform(layer_crs, project_crs, DataReaderTool._project())
        search_geom = QgsGeometry(buffer_geom)
        search_geom.transform(to_layer)
        # QGIS's feature iterator is iterable at runtime; its bundled stub marks
        # __iter__ as optional, so document the actual iteration contract here.
        candidates = cast(
            "Iterable[QgsFeature]", layer.getFeatures(QgsFeatureRequest().setFilterRect(search_geom.boundingBox()))
        )

        projected_rows: list[list[float | QgsFeature]] = []
        for feature in candidates:
            point_geom = QgsGeometry(feature.geometry())
            if point_geom.isNull() or point_geom.isEmpty():
                continue
            point_geom.transform(to_project)
            distance_from_line = geom.distance(point_geom)
            if distance_from_line > buffer_distance:
                continue
            distance_along = geom.lineLocatePoint(point_geom)
            projected_point = geom.interpolate(distance_along).asPoint()
            try:
                elevation = float(feature[profile1["band"]])
            except (ValueError, TypeError, KeyError):
                continue
            if not np.isfinite(elevation):
                continue
            original = point_geom.asPoint()
            projected_rows.append(
                [
                    distance_along,
                    projected_point.x(),
                    projected_point.y(),
                    distance_from_line,
                    0,
                    elevation,
                    original.x(),
                    original.y(),
                    feature,
                ]
            )

        if not projected_rows:
            return profile, buffer_geom, QgsGeometry.fromMultiPolylineXY([])
        projected: NDArray[np.object_] = np.array(projected_rows, dtype=object)
        projected = self.removeDuplicateLenght(projected)
        projected = self.interpolateNodeofPolyline(geom, projected)

        distance_scale = self._project_distance_scale()
        profile["l"] = [float(p[0]) * distance_scale for p in projected]
        profile["l_slope"] = self._slope_distances(
            [QgsPointXY(float(p[1]), float(p[2])) for p in projected],
            profile["l"],
        )
        profile["z"] = [float(p[5]) if p[5] is not None else np.nan for p in projected]
        profile["x"] = [float(p[1]) for p in projected]
        profile["y"] = [float(p[2]) for p in projected]
        guides = [
            [QgsPointXY(float(p[1]), float(p[2])), QgsPointXY(float(p[6]), float(p[7]))]
            for p in projected
            if p[6] is not None and p[7] is not None
        ]
        multipoly = QgsGeometry.fromMultiPolylineXY(guides)
        return profile, buffer_geom, multipoly

    def removeDuplicateLenght(self, projectedpoints: NDArray[np.object_]) -> NDArray[np.object_]:
        """Keep the point closest to the line for each 0.01-unit chainage group.

        Sort and group once, rather than scanning the full array for each point.
        """
        if len(projectedpoints) < 2:
            return projectedpoints
        ordered = sorted(projectedpoints, key=lambda p: float(p[0]))
        tolerance = self._project_chainage_tolerance()
        retained: list[NDArray[np.object_]] = []
        group = [ordered[0]]
        anchor = float(ordered[0][0])
        for point in ordered[1:]:
            if float(point[0]) - anchor < tolerance:
                group.append(point)
            else:
                retained.append(min(group, key=lambda p: float(p[3])))
                group = [point]
                anchor = float(point[0])
        retained.append(min(group, key=lambda p: float(p[3])))
        return np.array(retained, dtype=object)

    # def interpolateNodeofPolyline(self,geom):
    def interpolateNodeofPolyline(self, geom: QgsGeometry, projectedpoints: NDArray[np.object_]) -> NDArray[np.object_]:
        """Interpolate source elevations at unsampled path vertices.

        Records include chainage, projected coordinates, distance from the
        source point, elevation, original coordinates, and source feature.
        """
        PRECISION = self._project_chainage_tolerance()
        # SIP omits the QgsPolylineXY alias from the generated return stub.
        polyline = cast("_LineGeometry", geom).asPolyline()
        projectedpoints = projectedpoints[projectedpoints[:, 0].argsort()]

        lenpoly = 0

        # Write fist and last element if no value
        if projectedpoints[0][0] != 0:
            projectedpoints = np.append(
                projectedpoints,
                [
                    [
                        0,
                        polyline[0].x(),
                        polyline[0].y(),
                        -1,
                        0,
                        projectedpoints[0][5],
                        polyline[0].x(),
                        polyline[0].y(),
                        projectedpoints[0][8],
                    ]
                ],
                axis=0,
            )
            projectedpoints = projectedpoints[projectedpoints[:, 0].argsort()]
        if projectedpoints[-1][0] != geom.length():
            projectedpoints = np.append(
                projectedpoints,
                [
                    [
                        geom.length(),
                        polyline[-1].x(),
                        polyline[-1].y(),
                        -1,
                        len(polyline) - 2,
                        projectedpoints[-1][5],
                        polyline[-1].x(),
                        polyline[-1].y(),
                        projectedpoints[0][8],
                    ]
                ],
                axis=0,
            )
            projectedpoints = projectedpoints[projectedpoints[:, 0].argsort()]

        projectedpointsinterp: list[list[object]] = []

        for i, _point in enumerate(polyline):
            if i == 0:
                continue
            if i == len(polyline) - 1:
                break
            vertexpoint_xy = QgsPointXY(geom.vertexAt(i))
            lenpoly = geom.lineLocatePoint(QgsGeometry.fromPointXY(vertexpoint_xy))

            if min(abs(projectedpoints[:, 0] - lenpoly)) < PRECISION:
                continue
            temp1 = self.interpolatePoint(vertexpoint_xy, geom, projectedpoints)
            if temp1 is not None:
                projectedpointsinterp.append(temp1)

        temp = projectedpoints.tolist() + projectedpointsinterp
        projectedpoints = np.array(temp)

        return projectedpoints[projectedpoints[:, 0].argsort()]

    def interpolatePoint(
        self, vertexpoint: QgsPointXY, geom: QgsGeometry, projectedpoints: NDArray[np.object_]
    ) -> list[object] | None:
        """Interpolate elevation at a path vertex between neighboring source samples."""
        lenpoly = geom.lineLocatePoint(QgsGeometry.fromPointXY(vertexpoint))

        previouspointindex = np.max(np.where(projectedpoints[:, 0] <= lenpoly)[0])
        nextpointindex = np.min(np.where(projectedpoints[:, 0] >= lenpoly)[0])

        lentot = projectedpoints[nextpointindex][0] - projectedpoints[previouspointindex][0]
        if lentot > 0:
            lentemp = lenpoly - projectedpoints[previouspointindex][0]
            z = (
                projectedpoints[previouspointindex][5]
                + (projectedpoints[nextpointindex][5] - projectedpoints[previouspointindex][5]) / lentot * lentemp
            )
            return [
                lenpoly,
                vertexpoint.x(),
                vertexpoint.y(),
                -1,
                None,
                z,
                vertexpoint.x(),
                vertexpoint.y(),
                None,
            ]
        return None
