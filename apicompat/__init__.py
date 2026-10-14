"""Legacy compatibility imports for older QGIS APIs."""

import qgis.utils

# Based on qgis2compat plugin from opengis.ch

# Dealing with a QGIS 2 version, monkey patch some things
# also guard with initialized so monkeypatching happens only once
initialized = False
if not initialized and hasattr(qgis.utils, "QGis"):
    initialized = True

    # Here import all the compatibility fixes modules
    import qgiscoreqgis
    import qgisutilsqgis
    import qgsgeometry
    import qgsmaplayer
    import qgspointxy
    import qgsproject
    import qgswkbtypes
