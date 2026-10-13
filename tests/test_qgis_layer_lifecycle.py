"""Real QGIS regression for deleted source wrappers; run in an isolated process."""

from __future__ import annotations

import sys
from pathlib import Path
from types import TracebackType

import pytest

pytest.importorskip("qgis.core", reason="Requires the OSGeo4W QGIS environment")

from qgis.core import QgsFeature, QgsGeometry, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import Qt
from qgis.testing.mocked import get_iface

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from profiletool.profileplugin import ProfilePlugin


def test_unload_before_opening_dock_disconnects_map_tool_callback() -> None:
    """Disabling an unopened plugin must release its canvas signal connection."""
    iface = get_iface()
    canvas = iface.mapCanvas()
    before = canvas.receivers(canvas.mapToolSet)
    plugin = ProfilePlugin(iface)
    plugin.initGui()
    assert canvas.receivers(canvas.mapToolSet) == before + 1
    plugin.unload()
    assert canvas.receivers(canvas.mapToolSet) == before


def test_deleting_profile_sources_refreshes_without_deleted_wrappers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deleting one or several sources must keep model and sampled profiles valid."""
    callback_errors: list[tuple[type[BaseException], BaseException, TracebackType | None]] = []

    def capture_callback_error(
        kind: type[BaseException], value: BaseException, traceback: TracebackType | None
    ) -> None:
        callback_errors.append((kind, value, traceback))

    monkeypatch.setattr(sys, "excepthook", capture_callback_error)
    iface = get_iface()
    project = QgsProject.instance()
    assert project is not None
    iface.activeLayer.return_value = None
    plugin = ProfilePlugin(iface)
    plugin.initGui()
    plugin.run()
    core = plugin.profiletool
    assert core is not None
    assert core.toolrenderer is not None
    assert core.toolrenderer.tool.canvas() is iface.mapCanvas()
    assert callable(core.toolrenderer.tool.button)
    dock = core.dockwidget
    layers: list[QgsVectorLayer] = []
    try:
        for _ in range(3):
            layer = QgsVectorLayer("Point?crs=EPSG:28350&field=z:double", "same-name", "memory")
            for x, z in [(400000, 1), (400019, 20)]:
                feature = QgsFeature(layer.fields())
                feature.setGeometry(QgsGeometry.fromWkt(f"POINT({x} 6500000)"))
                feature["z"] = z
                provider = layer.dataProvider()
                assert provider is not None
                provider.addFeatures([feature])
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
        first_source = dock.mdl.item(0, 5)
        assert first_source is not None
        assert first_source.data(Qt.ItemDataRole.EditRole) == ids[0]
        project.removeMapLayer(ids[1])
        assert dock.mdl.rowCount() == 2
        assert core.profiles is not None
        assert {profile["layer"].id() for profile in core.profiles} == {ids[0], ids[2]}
        core.updateProfil(core.pointstoDraw, removeSelection=False, plotProfil=True)
        project.removeMapLayers([ids[0], ids[2]])
        assert dock.mdl.rowCount() == 0
        assert core.profiles == []
        assert not callback_errors
    finally:
        plugin.unload()
        project.removeAllMapLayers()
