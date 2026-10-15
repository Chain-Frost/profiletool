# -----------------------------------------------------------
#
# Profile
# Copyright (C) 2013  Peter Wells
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

"""Check whether QGIS layers support profile sampling."""

from qgis.core import Qgis, QgsMapLayer, QgsVectorLayer


def isProfilable(layer: QgsMapLayer) -> bool:
    """Return whether a layer supports raster, mesh or point profiling."""
    layer_type = layer.type()
    if layer_type in (Qgis.LayerType.Raster, Qgis.LayerType.Mesh):
        return True
    if layer_type == Qgis.LayerType.Plugin:
        return getattr(layer, "LAYER_TYPE", None) == "selafin_viewer"
    return isinstance(layer, QgsVectorLayer) and layer.geometryType() == Qgis.GeometryType.Point
