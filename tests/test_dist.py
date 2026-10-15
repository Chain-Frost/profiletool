"""Inspect layer/project distance conversions from a running QGIS console."""

from typing import cast

from qgis.core import QgsDistanceArea, QgsProject
from qgis.gui import QgisInterface
from qgis.utils import iface

desktop_iface = cast("QgisInterface | None", iface)
if desktop_iface is None:
    message = "Run this script from the QGIS desktop Python console"
    raise RuntimeError(message)
vl = desktop_iface.activeLayer()
canvas = desktop_iface.mapCanvas()
project = QgsProject.instance()
if vl is None or canvas is None or project is None:
    message = "Distance inspection requires an active layer, canvas and project"
    raise RuntimeError(message)

crs1 = vl.crs()
crs2 = canvas.mapSettings().destinationCrs()

dist = QgsDistanceArea()
dist.setSourceCrs(crs2, project.transformContext())

dist2 = QgsDistanceArea()
dist2.setSourceCrs(crs1, project.transformContext())

print(dist.convertLengthMeasurement(1.0, crs1.mapUnits()))
print(dist2.convertLengthMeasurement(1.0, crs2.mapUnits()))
