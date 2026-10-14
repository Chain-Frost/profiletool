from qgis.core import QgsDistanceArea, QgsProject
from qgis.utils import iface

vl = iface.activeLayer()

crs1 = vl.crs()
crs2 = iface.mapCanvas().mapSettings().destinationCrs()

dist = QgsDistanceArea()
dist.setSourceCrs(crs2, QgsProject.instance().transformContext())

dist2 = QgsDistanceArea()
dist2.setSourceCrs(crs1, QgsProject.instance().transformContext())

print(dist.convertLengthMeasurement(1.0, crs1.mapUnits()))
print(dist2.convertLengthMeasurement(1.0, crs2.mapUnits()))
