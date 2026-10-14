# -----------------------------------------------------------
#
# Profile
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
# with this progsram; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# ---------------------------------------------------------------------
"""Select line features and clicked multipart geometry components."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, cast

from qgis.core import (
    Qgis,
    QgsFeature,
    QgsFeatureRequest,
    QgsGeometry,
    QgsMapLayer,
    QgsPointXY,
    QgsRectangle,
    QgsSpatialIndex,
    QgsVectorLayer,
)
from qgis.PyQt.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from qgis.gui import QgisInterface, QgsMapTool


class SelectLineTool:
    def __init__(self, selectionMethod: str = "feature") -> None:
        """Selection mode can be feature or layer."""
        self.selectionMethod = selectionMethod

    def getPointTableFromSelectedLine(
        self, iface: QgisInterface, tool: QgsMapTool, newPoints: Sequence[Sequence[float]]
    ) -> tuple[QgsVectorLayer | None, list[QgsFeature]]:
        closestFeatures: list[QgsFeature] = []
        layer = iface.activeLayer()
        if not isinstance(layer, QgsVectorLayer) or not self.checkIsLineLayer(layer):
            QMessageBox.warning(iface.mainWindow(), "Closest Feature Finder", "No line layer selected")
            return None, closestFeatures

        if self.selectionMethod == "feature":
            # get the point coordinates in the layer's CRS
            point = tool.toLayerCoordinates(layer, QgsPointXY(newPoints[0][0], newPoints[0][1]))
            closestFeatures = self.select_closest_feature(iface, layer, point)
            if closestFeatures:
                closestFeatures = [self.select_closest_part(closestFeatures[0], point)]
        elif self.selectionMethod == "layer":
            closestFeatures = self.select_layer_features(iface, layer, None)

        return layer, closestFeatures

    @staticmethod
    def select_closest_part(feature: QgsFeature, clicked_point: QgsPointXY) -> QgsFeature:
        """Return a feature copy containing only the clicked multipart line."""
        geometry = feature.geometry()
        if not geometry.isMultipart():
            return feature
        parts = cast(list[list[QgsPointXY]], geometry.asMultiPolyline())
        if not parts:
            return feature
        click_geometry = QgsGeometry.fromPointXY(clicked_point)
        best_part = min(
            parts,
            key=lambda part: QgsGeometry.fromPolylineXY(part).distance(click_geometry),
        )
        selected = QgsFeature(feature)
        selected.setGeometry(QgsGeometry.fromPolylineXY(best_part))
        return selected

    @staticmethod
    def checkIsLineLayer(layer: QgsMapLayer | None) -> bool:
        return isinstance(layer, QgsVectorLayer) and layer.geometryType() == Qgis.GeometryType.Line

    @staticmethod
    def checkIsPointLayer(layer: QgsMapLayer | None) -> bool:
        return isinstance(layer, QgsVectorLayer) and layer.geometryType() == Qgis.GeometryType.Point

    @staticmethod
    def select_closest_feature(iface: QgisInterface, layer: QgsVectorLayer, point: QgsPointXY) -> list[QgsFeature]:
        """Returns a list with the closest feature in given layer."""
        # Create the index with the layers features
        layerindex = QgsSpatialIndex()
        # rajout
        f = QgsFeature()
        #
        iter = layer.getFeatures()
        while iter.nextFeature(f):
            layerindex.addFeature(f)

        # get the feature which has the closest bounding box using the spatial index
        nearest = layerindex.nearestNeighbor(point, 1)
        featureId = nearest[0] if len(nearest) > 0 else None
        closestFeature: QgsFeature | None = QgsFeature()

        f = QgsFeature()
        if featureId is None or layer.getFeatures(QgsFeatureRequest(featureId)).nextFeature(f) is False:
            closestFeature = None

        booltemp = layer.geometryType() != Qgis.GeometryType.Point

        if booltemp and closestFeature is not None:
            # find the furthest bounding box borders
            f = QgsFeature()
            layer.getFeatures(QgsFeatureRequest(featureId)).nextFeature(f)
            rect = f.geometry().boundingBox()

            dist_pX_rXmax = abs(point.x() - rect.xMaximum())
            dist_pX_rXmin = abs(point.x() - rect.xMinimum())
            if dist_pX_rXmax > dist_pX_rXmin:
                width = dist_pX_rXmax
            else:
                width = dist_pX_rXmin

            dist_pY_rYmax = abs(point.y() - rect.yMaximum())
            dist_pY_rYmin = abs(point.y() - rect.yMinimum())
            if dist_pY_rYmax > dist_pY_rYmin:
                height = dist_pY_rYmax
            else:
                height = dist_pY_rYmin

            # create the search rectangle
            rect = QgsRectangle()
            rect.setXMinimum(point.x() - width)
            rect.setXMaximum(point.x() + width)
            rect.setYMinimum(point.y() - height)
            rect.setYMaximum(point.y() + height)

            # retrieve all geometries into the search rectangle

            iter2 = layer.getFeatures(QgsFeatureRequest(rect))
            # find the nearest feature
            minDist = -1
            featureId = None
            point_geometry = QgsGeometry.fromPointXY(point)
            f = QgsFeature()
            while iter2.nextFeature(f):
                geom = f.geometry()
                distance = geom.distance(point_geometry)
                if minDist < 0 or distance < minDist:
                    minDist = distance
                    featureId = f.id()
            # get the closest feature
            f = QgsFeature()
            # closestFeature = layer.getFeatures(QgsFeatureRequest(featureId)).next()
            layer.getFeatures(QgsFeatureRequest(featureId)).nextFeature(f)
            closestFeature = f
            if featureId is None or layer.getFeatures(QgsFeatureRequest(featureId)).nextFeature(f) is False:
                closestFeature = None

        return [closestFeature] if closestFeature else []

    @staticmethod
    def select_layer_features(
        iface: QgisInterface | None, layer: QgsVectorLayer | None, point: QgsPointXY | None
    ) -> list[QgsFeature]:
        """Returns a list with all the features in layer.

        iface, point are unused, kept to use
        the same function interface as select_closest_feature.
        """
        if layer is not None:
            return list(cast(Iterator[QgsFeature], layer.getFeatures()))
        return []
