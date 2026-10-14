"""Real QGIS regression for deleted source wrappers; run in an isolated process."""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path
from types import TracebackType
from typing import cast

import pytest

pytest.importorskip("qgis.core", reason="Requires the OSGeo4W QGIS environment")

from qgis.core import QgsFeature, QgsGeometry, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QApplication, QGroupBox, QVBoxLayout
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
        # Coordinate-tab rebuilding must preserve the Designer widget fields.
        assert isinstance(dock.groupBox, QGroupBox)
        assert isinstance(dock.verticalLayout, QVBoxLayout)
        # Exercise coordinate-tab actions through their real Qt signal senders.
        profile = core.profiles[0]
        clipboard = QApplication.clipboard()
        assert clipboard is not None
        dock.profilePushButton[0].click()
        expected = "".join(f"{length}\t{height}\n" for length, height in zip(profile["l"], profile["z"]))
        assert clipboard.text() == expected
        dock.coordsPushButton[0].click()
        assert all(len(row.split("\t")) == 4 for row in clipboard.text().splitlines())
        before_ids = set(project.mapLayers())
        dock.tolayerPushButton[0].click()
        added_ids = set(project.mapLayers()) - before_ids
        assert len(added_ids) == 1
        temporary_layer = project.mapLayer(added_ids.pop())
        assert isinstance(temporary_layer, QgsVectorLayer)
        assert temporary_layer.featureCount() == len(profile["z"])
        assert temporary_layer.crs() == profile["crs"]
        exported_features = cast(Iterable[QgsFeature], temporary_layer.getFeatures())
        assert [feature["Value"] for feature in exported_features] == list(profile["z"])
        project.removeMapLayer(temporary_layer.id())
        assert not callback_errors
        tracking_connections = dock.checkBox_mpl_tracking.receivers(dock.checkBox_mpl_tracking.stateChanged)
        for _ in range(2):
            for index in range(dock.cboLibrary.count()):
                dock.cboLibrary.setCurrentIndex(index)
                dock.refreshPlot()
                if dock.cboLibrary.currentText() == "Matplotlib":
                    from matplotlib.backend_bases import MouseEvent

                    plot = dock.plotWdg
                    assert plot is not None
                    axes = plot.figure.get_axes()[0]
                    before_lines = len(axes.lines)
                    event = MouseEvent("motion_notify_event", plot, 0, 0)
                    event.xdata = 0.0
                    core.mouseevent_mpl(event)
                    assert core.x_cursor == 0.0
                    assert len(axes.lines) == before_lines + 1
                    event.xdata = 1.0
                    core.mouseevent_mpl(event)
                    assert len(axes.lines) == before_lines + 1
                    core.activateMouseTracking(0)
                    assert core.vline is None
                    assert len(axes.lines) == before_lines
                    core.activateMouseTracking(2)
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
