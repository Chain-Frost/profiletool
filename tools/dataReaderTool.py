# -*- coding: utf-8 -*-
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
import platform
from math import sqrt

import numpy as np
import qgis
from qgis.core import *
from qgis.PyQt.QtCore import QCoreApplication

from .utils import isProfilable


class DataReaderTool:
    """def __init__(self):
    self.profiles = None"""

    def dataRasterReaderTool(self, iface1, tool1, profile1, pointstoDraw1, resolution_mode):
        """Sample a raster/mesh along a line drawn in the project CRS.

        Chainage uses project-CRS angular units for geographic projects, and
        metres for projected projects (including projected CRSs in feet).
        Sample coordinates are stored in the source layer CRS.
        """
        self.tool = tool1
        self.profiles = profile1
        self.pointstoDraw = pointstoDraw1
        self.iface = iface1

        lengths, sample_x, sample_y, project_samples = [], [], [], []
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
            elif layer.type() == layer.RasterLayer:
                pixel_x = abs(layer.rasterUnitsPerPixelX())
                pixel_y = abs(layer.rasterUnitsPerPixelY())
                if not pixel_x or not pixel_y:
                    steps = 1
                else:
                    steps = max(
                        1,
                        int(np.ceil(max(
                            abs(end_layer.x() - start_layer.x()) / pixel_x,
                            abs(end_layer.y() - start_layer.y()) / pixel_y,
                        ))),
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

        profile1.update({
            "l": lengths,
            "l_slope": self._slope_distances(project_samples, lengths),
            "z": self._extractZValues(sample_x, sample_y),
            "x": sample_x,
            "y": sample_y,
            "crs": layer.crs(),
        })
        iface1.mainWindow().statusBar().showMessage("")
        return profile1

    @staticmethod
    def _project_distance_scale():
        """Conversion from project map units to plotted chainage units."""
        project_crs = QgsProject.instance().crs()
        if project_crs.isGeographic():
            return 1.0  # degrees, matching the geographic project CRS
        return QgsUnitTypes.fromUnitToUnitFactor(
            project_crs.mapUnits(), Qgis.DistanceUnit.Meters
        )

    @staticmethod
    def _slope_distances(project_points, chainages):
        """Slope distance in metres, even when displayed chainage is degrees.

        A geographic project's displayed chainage remains angular. Geodesic
        segment lengths are used only for grades, which must have linear units.
        """
        if not project_points:
            return []
        project = QgsProject.instance()
        if not project.crs().isGeographic():
            return chainages
        distance = QgsDistanceArea()
        distance.setSourceCrs(project.crs(), project.transformContext())
        ellipsoid = project.ellipsoid()
        distance.setEllipsoid(
            ellipsoid if ellipsoid and ellipsoid != "NONE" else "WGS84"
        )
        result = [0.0]
        for start, end in zip(project_points[:-1], project_points[1:]):
            result.append(result[-1] + distance.measureLine(start, end))
        return result

    @staticmethod
    def _project_chainage_tolerance():
        """Tolerance in native project map units (not always metres)."""
        project_crs = QgsProject.instance().crs()
        if project_crs.isGeographic():
            return 1e-8  # Avoid treating separate locations as duplicates.
        return 0.01 / DataReaderTool._project_distance_scale()

    def _status_update(self, advancement_pct):
        """Send a progress message to status bar.

        advancement_pct is the advancemente in percentage (from 0 to 100).
        """
        if advancement_pct % 10 == 0:
            progress = "Creating profile: " + "|" * (advancement_pct // 10)
            self.iface.mainWindow().statusBar().showMessage(progress)

    def _extractZValues(self, x, y):
        layer = self.profiles["layer"]
        band = self.profiles["band"]
        values = []
        if not x:
            return values

        is_plugin = layer.type() == layer.PluginLayer and isProfilable(layer)
        is_mesh = layer.type() == layer.MeshLayer
        identifier = qgis.gui.QgsMapToolIdentify(qgis.utils.iface.mapCanvas()) if is_mesh else None
        mesh_field = QCoreApplication.translate("QgsMapToolIdentify", "Scalar Value")
        provider = layer.dataProvider() if not (is_plugin or is_mesh) else None

        for n, (x_coord, y_coord) in enumerate(zip(x, y)):
            point = QgsPointXY(x_coord, y_coord)
            value = np.nan
            try:
                if is_plugin:
                    result = layer.identify(point)
                    value = float(list(result[1].values())[band])
                elif is_mesh:
                    matches = identifier.identify(
                        QgsGeometry.fromPointXY(point),
                        qgis.gui.QgsMapToolIdentify.DefaultQgsSetting,
                        [layer],
                        qgis.gui.QgsMapToolIdentify.MeshLayer,
                    )
                    if matches:
                        value = float(matches[0].mAttributes[mesh_field])
                else:
                    # Single-band sampling avoids expensive multi-band identify().
                    sampled, valid = provider.sample(point, band)
                    if valid and sampled is not None:
                        value = float(sampled)
            except (AttributeError, IndexError, KeyError, TypeError, ValueError):
                pass  # Unavailable/out-of-range samples are gaps, never 0 m.
            values.append(value if np.isfinite(value) else np.nan)
            self._status_update((100 * n) // max(1, len(x) - 1))
        return values

    def dataVectorReaderTool(self, iface1, tool1, profile1, pointstoDraw1, valbuf1):
        """Sample point features near a profile line in the project CRS.

        Buffer and exact distance checks are both performed in project units,
        irrespective of the source point layer's CRS.
        """
        layer = profile1["layer"]
        profile = {"layer": layer, "band": profile1["band"], "l": [], "z": [],
                   "x": [], "y": [], "crs": QgsProject.instance().crs()}
        if len(pointstoDraw1) < 2:
            return profile, None, None

        geom = QgsGeometry.fromPolylineXY([QgsPointXY(*p) for p in pointstoDraw1])
        if geom.isEmpty() or geom.length() == 0:
            return profile, None, None

        buffer_distance = max(0.0, float(valbuf1))
        buffer_geom = geom.buffer(buffer_distance, 12)
        project_crs = QgsProject.instance().crs()
        layer_crs = layer.crs()
        to_layer = QgsCoordinateTransform(project_crs, layer_crs, QgsProject.instance())
        to_project = QgsCoordinateTransform(layer_crs, project_crs, QgsProject.instance())
        search_geom = QgsGeometry(buffer_geom)
        search_geom.transform(to_layer)
        candidates = layer.getFeatures(
            QgsFeatureRequest().setFilterRect(search_geom.boundingBox())
        )

        projected = []
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
            projected.append([
                distance_along, projected_point.x(), projected_point.y(),
                distance_from_line, 0, elevation, original.x(), original.y(),
                feature,
            ])

        if not projected:
            return profile, buffer_geom, QgsGeometry.fromMultiPolylineXY([])
        projected = np.array(projected, dtype=object)
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
            [QgsPointXY(float(p[1]), float(p[2])),
             QgsPointXY(float(p[6]), float(p[7]))]
            for p in projected if p[6] is not None and p[7] is not None
        ]
        multipoly = QgsGeometry.fromMultiPolylineXY(guides)
        return profile, buffer_geom, multipoly

    def removeDuplicateLenght(self, projectedpoints):
        """Keep the point closest to the line for each 0.01-unit chainage group.

        Sort and group once, rather than scanning the full array for each point.
        """
        if len(projectedpoints) < 2:
            return projectedpoints
        ordered = sorted(projectedpoints, key=lambda p: float(p[0]))
        tolerance = self._project_chainage_tolerance()
        retained = []
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
    def interpolateNodeofPolyline(self, geom, projectedpoints):
        """
        projectedpoints : array [[lenght, xprojected ,yprojected ,dist from origignal point, segment of polyline on witch it's projected, atribute (z), xoriginal point, yoriginal point ,original point feature], ... ]
        """
        PRECISION = self._project_chainage_tolerance()
        polyline = geom.asPolyline()
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

        projectedpointsinterp = []

        for i, point in enumerate(polyline):
            if i == 0:
                continue
            elif i == len(polyline) - 1:
                break
            else:
                vertexpoint_xy = QgsPointXY(geom.vertexAt(i))
                # vertexpoint_xy = QgsPointXY(vertexpoint.x(), vertexpoint.y())
                lenpoly = geom.lineLocatePoint(qgis.core.QgsGeometry.fromPointXY(vertexpoint_xy))

                if min(abs(projectedpoints[:, 0] - lenpoly)) < PRECISION:
                    continue
                else:
                    temp1 = self.interpolatePoint(vertexpoint_xy, geom, projectedpoints)
                    if temp1 != None:
                        projectedpointsinterp.append(temp1)

        temp = projectedpoints.tolist() + projectedpointsinterp
        projectedpoints = np.array(temp)

        projectedpoints = projectedpoints[projectedpoints[:, 0].argsort()]

        return projectedpoints

    def interpolatePoint(self, vertexpoint, geom, projectedpoints):

        lenpoly = geom.lineLocatePoint(qgis.core.QgsGeometry.fromPointXY(vertexpoint))

        previouspointindex = np.max(np.where(projectedpoints[:, 0] <= lenpoly)[0])
        nextpointindex = np.min(np.where(projectedpoints[:, 0] >= lenpoly)[0])

        lentot = projectedpoints[nextpointindex][0] - projectedpoints[previouspointindex][0]
        if lentot > 0:
            lentemp = lenpoly - projectedpoints[previouspointindex][0]
            z = (
                projectedpoints[previouspointindex][5]
                + (projectedpoints[nextpointindex][5] - projectedpoints[previouspointindex][5])
                / lentot
                * lentemp
            )
            # return [lenpoly, point[0], point[1], -1, None ,z,point[0], point[1], None ]
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
        else:
            return None
