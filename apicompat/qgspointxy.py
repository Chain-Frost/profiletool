
"""Historical point API compatibility definitions."""

import qgis.core

# QgsPoint has been renamed to QgsPoint in QGis 3.0 api
qgis.core.QgsPointXY = qgis.core.QgsPoint
