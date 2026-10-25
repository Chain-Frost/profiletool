"""Real QGIS regression for deleted source wrappers; run in an isolated process."""

from __future__ import annotations

import csv
import sys
from collections.abc import Iterable
from pathlib import Path
from traceback import format_exception
from types import TracebackType
from typing import cast

import pytest

pytest.importorskip("qgis.core", reason="Requires the OSGeo4W QGIS environment")

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QPointF, Qt, pyqtBoundSignal
from qgis.PyQt.QtGui import QTransform
from qgis.PyQt.QtWidgets import QApplication, QGroupBox, QVBoxLayout
from qgis.testing.mocked import get_iface

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from profiletool import pyqtgraph as pg
from profiletool.profileplugin import ProfilePlugin
from profiletool.tools import plottingtool as plottingtool_module
from profiletool.tools.plottingtool import PlottingTool, pyqtgraph_plot_item


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


def test_graphics_parent_scene_and_bounds_notifications_are_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    """QGIS 3.44/PyQt5 must not lose parent attachment or plot auto-range updates."""
    callback_errors: list[BaseException] = []

    def capture_callback_error(
        _kind: type[BaseException], value: BaseException, _traceback: TracebackType | None
    ) -> None:
        callback_errors.append(value)

    monkeypatch.setattr(sys, "excepthook", capture_callback_error)
    plot = pg.PlotWidget()
    curve = pg.PlotDataItem([0.0, 1.0], [3.0, 6.0])
    try:
        assert curve.scene() is None
        plot.addItem(curve)
        assert curve.scene() is plot.scene()
        assert curve.parentItem() is not None
        view_box = plot.getViewBox()
        assert curve.getViewBox() is view_box

        # Bounds notification is required for PyQtGraph's auto-range behaviour.
        bounds_changed: list[object] = []
        previous_bounds_changed = view_box.itemBoundsChanged

        def capture_bounds_changed(item: object) -> None:
            bounds_changed.append(item)
            previous_bounds_changed(item)

        monkeypatch.setattr(view_box, "itemBoundsChanged", capture_bounds_changed)
        curve.setPos(12.0, 4.0)
        assert curve.pos().x() == 12.0
        assert curve.pos().y() == 4.0
        assert curve in bounds_changed

        # QGIS 3/PyQt5 must invalidate bounds for explicit transforms, too.
        bounds_changed.clear()
        curve.setTransform(QTransform.fromScale(2.0, 1.5))
        assert curve in bounds_changed
        bounds_changed.clear()
        curve.resetTransform()
        assert curve in bounds_changed

        plot.removeItem(curve)
        assert curve.scene() is None
        assert not callback_errors, [str(error) for error in callback_errors]
    finally:
        plot.close()


def test_plot_cursor_hides_nodata_and_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mouse tracking must not snap across missing raster samples."""
    iface = get_iface()
    iface.activeLayer.return_value = None
    plugin = ProfilePlugin(iface)
    plugin.initGui()
    try:
        plugin.run()
        core = plugin.profiletool
        assert core is not None
        assert core.toolrenderer is not None
        plot = core.dockwidget.plotWdg
        assert isinstance(plot, pg.PlotWidget)
        plot_item = plot.getPlotItem()
        gap_curve = plot.plot([0.0, 1.0, 2.0], [3.0, float("nan"), 5.0], name="gap")
        assert core._nearest_plot_sample(plot_item, QPointF(0.0, 3.0)) == (0.0, 3.0)
        assert core._nearest_plot_sample(plot_item, QPointF(1.0, 4.0)) == (None, None)
        other = plot.plot([0.0, 1.0, 2.0], [float("nan"), 7.0, float("nan")], name="other")
        assert core._nearest_plot_sample(plot_item, QPointF(1.0, 6.0)) == (1.0, 7.0)
        other.hide()
        assert core._nearest_plot_sample(plot_item, QPointF(1.0, 4.0)) == (None, None)
        gap_curve.hide()
        assert core._nearest_plot_sample(plot_item, QPointF(0.0, 3.0)) == (None, None)
        gap_curve.show()

        core.pointstoDraw = [[0.0, 0.0], [2.0, 0.0]]
        core.doTracking = True
        core.updateCursorOnMap(0.0)
        marker = core.toolrenderer.rubberbandpoint
        assert marker.isVisible()
        monkeypatch.setattr(core, "_nearest_plot_sample", lambda *args: (None, None))
        core.dockwidget.showcursor = True
        core.mouseMovedPyQtGraph(plot_item.sceneBoundingRect().center())
        assert core.x_cursor is None
        assert not marker.isVisible()
        cursor_items = [
            item for item in plot_item.allChildItems()
            if isinstance(item, pg.InfiniteLine) and item.name() in ("cross_vertical", "cross_horizontal")
        ]
        assert len(cursor_items) == 2
        assert all(not item.isVisible() for item in cursor_items)
    finally:
        plugin.unload()


def test_chainage_label_refreshes_for_project_crs_changes() -> None:
    """Resampling in an existing dock updates the units on both graph backends."""
    iface = get_iface()
    iface.activeLayer.return_value = None
    project = QgsProject.instance()
    assert project is not None
    old_crs = project.crs()
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:28350"))
    plugin = ProfilePlugin(iface)
    plugin.initGui()
    try:
        plugin.run()
        core = plugin.profiletool
        assert core is not None
        dock = core.dockwidget
        plot = dock.plotWdg
        assert isinstance(plot, pg.PlotWidget)
        assert "m" in plot.getPlotItem().getAxis("bottom").labelText
        project.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        core.plotProfil()
        assert PlottingTool._chainage_unit() in plot.getPlotItem().getAxis("bottom").labelText
        if dock.cboLibrary.findText("Matplotlib") >= 0:
            dock.cboLibrary.setCurrentIndex(dock.cboLibrary.findText("Matplotlib"))
            core.plotProfil()
            assert PlottingTool._chainage_unit() in dock.plotWdg.figure.get_axes()[0].get_xlabel()
    finally:
        plugin.unload()
        project.setCrs(old_crs)



def test_active_profile_preserves_geometry_and_elevations_across_project_crs_change() -> None:
    """Reproject the active path, then resample it without misinterpreting stored coordinates."""
    iface = get_iface()
    iface.activeLayer.return_value = None
    project = QgsProject.instance()
    assert project is not None
    original_crs = QgsCoordinateReferenceSystem(project.crs())
    source_crs = QgsCoordinateReferenceSystem("EPSG:28350")
    destination_crs = QgsCoordinateReferenceSystem("EPSG:4326")
    project.setCrs(source_crs)
    layer = QgsVectorLayer("Point?crs=EPSG:28350&field=z:double", "crs-change-points", "memory")
    provider = layer.dataProvider()
    assert provider is not None
    for x, z in ((400000.0, 10.0), (400020.0, 20.0)):
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, 6500000.0)))
        feature["z"] = z
        assert provider.addFeatures([feature])[0]
    project.addMapLayer(layer)
    plugin = ProfilePlugin(iface)
    plugin.initGui()
    try:
        plugin.run()
        core = plugin.profiletool
        assert core is not None
        assert core.toolrenderer is not None
        dock = core.dockwidget
        dock.addLayer(layer)
        old_points = [[400000.0, 6500000.0], [400020.0, 6500000.0]]
        core.toolrenderer.pointstoDraw = list(old_points)
        core.toolrenderer.updateRubberBand()
        core.updateProfil(old_points, removeSelection=False)
        assert len(core.profiles) == 1
        assert core.profiles[0]["z"] == pytest.approx([10.0, 20.0])
        assert core.profiles[0]["l"][-1] == pytest.approx(20.0)

        transform = QgsCoordinateTransform(source_crs, destination_crs, project)
        expected = [transform.transform(QgsPointXY(*coords)) for coords in old_points]
        project.setCrs(destination_crs)
        assert len(core.pointstoDraw) == 2
        for point, reference in zip(core.pointstoDraw, expected):
            assert point == pytest.approx([reference.x(), reference.y()], abs=1e-7)
        assert core.toolrenderer.pointstoDraw == core.pointstoDraw
        assert core.profiles[0]["z"] == pytest.approx([10.0, 20.0])
        assert core.profiles[0]["l"][-1] == pytest.approx(
            QgsGeometry.fromPolylineXY(expected).length(), rel=1e-5
        )
        assert core.profiles[0]["crs"] == destination_crs
        assert core.pointLayer is None

        # Repeated changes must use the immediately preceding CRS, not the initial one.
        project.setCrs(source_crs)
        for point, reference in zip(core.pointstoDraw, old_points):
            assert point == pytest.approx(reference, abs=0.01)
        assert core.profiles[0]["z"] == pytest.approx([10.0, 20.0])

        # Unloading removes our project CRS signal and leaves no stale callbacks.
        assert core._crs_signal_connected
    finally:
        plugin.unload()
        assert not plugin.profiletool or not plugin.profiletool._crs_signal_connected
        project.removeMapLayer(layer.id())
        project.setCrs(original_crs)


def test_matplotlib_autoscales_when_final_profile_is_empty() -> None:
    """A final source without samples must not suppress earlier plotted data."""
    iface = get_iface()
    iface.activeLayer.return_value = None
    project = QgsProject.instance()
    assert project is not None
    old_crs = project.crs()
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:28350"))
    plugin = ProfilePlugin(iface)
    plugin.initGui()
    layers: list[QgsVectorLayer] = []
    try:
        plugin.run()
        core = plugin.profiletool
        assert core is not None
        dock = core.dockwidget
        if dock.cboLibrary.findText("Matplotlib") < 0:
            pytest.skip("Matplotlib is not installed in this QGIS environment")
        for name, has_samples in [("with-elevation", True), ("empty", False)]:
            layer = QgsVectorLayer("Point?crs=EPSG:28350&field=z:double", name, "memory")
            if has_samples:
                provider = layer.dataProvider()
                assert provider is not None
                for x, z in ((400000, 200.0), (400020, 220.0)):
                    feature = QgsFeature(layer.fields())
                    feature.setGeometry(QgsGeometry.fromWkt(f"POINT({x} 6500000)"))
                    feature["z"] = z
                    provider.addFeatures([feature])
            project.addMapLayer(layer)
            layers.append(layer)
            dock.addLayer(layer)
        dock.cboLibrary.setCurrentIndex(dock.cboLibrary.findText("Matplotlib"))
        core.updateProfil([[400000, 6500000], [400020, 6500000]], removeSelection=False, plotProfil=True)
        assert len(core.profiles) == 2
        assert len(core.profiles[0]["plot_y"]) > 0
        assert not core.profiles[-1]["plot_x"]
        axes = dock.plotWdg.figure.get_axes()[0]
        assert 19.0 <= axes.get_xlim()[1] < 100.0
        assert axes.get_ylim()[1] >= 220.0
        assert axes.get_ylim()[1] < 250.0
    finally:
        plugin.unload()
        for layer in layers:
            project.removeMapLayer(layer.id())
        project.setCrs(old_crs)


def test_whole_layer_selection_keeps_all_disconnected_features() -> None:
    """Whole-layer mode must not silently discard subsequent line features."""
    iface = get_iface()
    iface.activeLayer.return_value = None
    project = QgsProject.instance()
    assert project is not None
    original_crs = project.crs()
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:28350"))
    plugin = ProfilePlugin(iface)
    plugin.initGui()
    layer = QgsVectorLayer("LineString?crs=EPSG:28350", "disconnected", "memory")
    try:
        provider = layer.dataProvider()
        assert provider is not None
        for coords in (((0.0, 0.0), (2.0, 0.0)), ((10.0, 0.0), (12.0, 0.0))):
            feature = QgsFeature(layer.fields())
            feature.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(*point) for point in coords]))
            provider.addFeatures([feature])
        project.addMapLayer(layer)
        plugin.run()
        core = plugin.profiletool
        assert core is not None
        features = list(cast(Iterable[QgsFeature], layer.getFeatures()))
        core.updateProfilFromFeatures(layer, features)
        # The upstream code concatenated all source lines, dropping the first
        # point of each subsequent feature. Preserve that observable behaviour.
        assert core.pointstoDraw == [[0.0, 0.0], [2.0, 0.0], [12.0, 0.0]]

        # A single multipart feature must also preserve all of its vertices.
        multipart = QgsFeature(layer.fields())
        multipart.setGeometry(
            QgsGeometry.fromMultiPolylineXY(
                [
                    [QgsPointXY(1, 1), QgsPointXY(2, 1)],
                    [QgsPointXY(10, 1), QgsPointXY(11, 1)],
                ]
            )
        )
        core.updateProfilFromFeatures(layer, [multipart])
        assert core.pointstoDraw == [[1.0, 1.0], [2.0, 1.0], [10.0, 1.0], [11.0, 1.0]]
    finally:
        plugin.unload()
        project.removeMapLayer(layer.id())
        project.setCrs(original_crs)


def test_deleting_profile_sources_refreshes_without_deleted_wrappers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Deleting one or several sources must keep model and sampled profiles valid."""
    callback_errors: list[tuple[type[BaseException], BaseException, TracebackType | None]] = []

    def capture_callback_error(
        kind: type[BaseException], value: BaseException, traceback: TracebackType | None
    ) -> None:
        callback_errors.append((kind, value, traceback))
        # Expose native Qt callback failures in headless QGIS CI logs.
        print("QGIS callback exception:\\n" + "".join(format_exception(kind, value, traceback)), file=sys.stderr)

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
        assert not callback_errors, [
            "".join(format_exception(kind, value, traceback)) for kind, value, traceback in callback_errors
        ]
        tracking_connections = dock.checkBox_mpl_tracking.receivers(dock.checkBox_mpl_tracking.stateChanged)
        for _ in range(2):
            for index in range(dock.cboLibrary.count()):
                dock.cboLibrary.setCurrentIndex(index)
                dock.refreshPlot()
                # Exercise the actual Save As menu on every installed backend.
                output = tmp_path / f"profile_{index}.csv"
                monkeypatch.setattr(
                    plottingtool_module,
                    "getSaveFileName",
                    lambda *args, output_path=output, **kwargs: str(output_path),
                )
                assert dock.cbxSaveAs.findText("Graph - CSV") >= 0
                dock.cbxSaveAs.setCurrentText("Graph - CSV")
                dock.butSaveAs.click()
                with output.open(newline="", encoding="utf-8") as stream:
                    csv_rows = list(csv.reader(stream))
                assert len(csv_rows) > 1
                assert len(csv_rows[0]) == 2 * len(core.profiles)
                assert csv_rows[1][1] != ""
                if dock.cboLibrary.currentText() == "PyQtGraph":
                    plot = dock.plotWdg
                    assert isinstance(plot, pg.PlotWidget)
                    plot_item = pyqtgraph_plot_item(plot)
                    assert plot_item is not None
                    view_box = plot_item.getViewBox()
                    assert view_box is not None
                    assert isinstance(view_box.sigRangeChanged, pyqtBoundSignal)
                    empty_label = pg.TextItem("")
                    plot_item.addItem(empty_label)
                    cursor_items = [
                        item
                        for item in plot_item.allChildItems()
                        if isinstance(item, pg.InfiniteLine) and item.name() in ("cross_vertical", "cross_horizontal")
                    ]
                    assert len(cursor_items) == 2
                    dock.showCursor(0)
                    assert all(not item.isVisible() for item in cursor_items)
                    dock.showCursor(2)
                    assert all(item.isVisible() for item in cursor_items)
                    plot_item.removeItem(empty_label)
                    before_connections = view_box.receivers(view_box.sigRangeChanged)
                    dock.disconnectPlotRangechanged()
                    assert view_box.receivers(view_box.sigRangeChanged) == before_connections - 1
                    dock.connectPlotRangechanged()
                    assert view_box.receivers(view_box.sigRangeChanged) == before_connections
                    dock.cbSameAxisScale.setCheckState(Qt.CheckState.Checked)
                    assert view_box.state["aspectLocked"] == 1
                    dock.cbSameAxisScale.setCheckState(Qt.CheckState.Unchecked)
                    assert view_box.state["aspectLocked"] is False
                elif dock.cboLibrary.currentText() == "Matplotlib":
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
                    assert core.vline is not None
                    core.vline.remove()
                    event.xdata = 2.0
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
