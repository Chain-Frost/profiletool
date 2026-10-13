"""Real QGIS regression for deleted source wrappers; run in an isolated process."""

import sys
from pathlib import Path

import pytest

pytest.importorskip("qgis.core", reason="Requires the OSGeo4W QGIS environment")

from qgis.core import QgsFeature, QgsGeometry, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import Qt
from qgis.testing.mocked import get_iface

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from profiletool.profileplugin import ProfilePlugin


def test_deleting_profile_sources_refreshes_without_deleted_wrappers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deleting one or several sources must keep model and sampled profiles valid."""
    callback_errors = []
    monkeypatch.setattr(sys, "excepthook", lambda *error: callback_errors.append(error))
    iface = get_iface()
    project = QgsProject.instance()
    iface.activeLayer.return_value = None
    plugin = ProfilePlugin(iface)
    plugin.initGui()
    plugin.run()
    core = plugin.profiletool
    dock = core.dockwidget
    layers = []
    try:
        for _ in range(3):
            layer = QgsVectorLayer("Point?crs=EPSG:28350&field=z:double", "same-name", "memory")
            for x, z in [(400000, 1), (400019, 20)]:
                feature = QgsFeature(layer.fields())
                feature.setGeometry(QgsGeometry.fromWkt(f"POINT({x} 6500000)"))
                feature["z"] = z
                layer.dataProvider().addFeatures([feature])
            project.addMapLayer(layer)
            layers.append(layer)
            dock.addLayer(layer)
        core.updateProfil([[400000, 6500000], [400019, 6500000]], removeSelection=False, plotProfil=True)
        tracking_connections = dock.checkBox_mpl_tracking.receivers(dock.checkBox_mpl_tracking.stateChanged)
        for _ in range(2):
            for index in range(dock.cboLibrary.count()):
                dock.cboLibrary.setCurrentIndex(index)
                dock.refreshPlot()
        assert dock.checkBox_mpl_tracking.receivers(dock.checkBox_mpl_tracking.stateChanged) == tracking_connections
        ids = [layer.id() for layer in layers]
        assert dock.mdl.item(0, 5).data(Qt.ItemDataRole.EditRole) == ids[0]
        project.removeMapLayer(ids[1])
        assert dock.mdl.rowCount() == 2
        assert {profile["layer"].id() for profile in core.profiles} == {ids[0], ids[2]}
        core.updateProfil(core.pointstoDraw, removeSelection=False, plotProfil=True)
        project.removeMapLayers([ids[0], ids[2]])
        assert dock.mdl.rowCount() == 0
        assert core.profiles == []
        assert not callback_errors
    finally:
        plugin.unload()
        project.removeAllMapLayers()
