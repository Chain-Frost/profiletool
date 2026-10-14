"""Run fixture-based checks in the live QGIS desktop through its Python console.

Run with runpy.run_path from QGIS or MCP, never as a standalone interpreter.
Generated fixtures, exports and the evidence report stay under validation_artifacts.
"""

from __future__ import annotations

# ruff: noqa: SLF001 -- Standalone integration checks intentionally inspect callback state.
import hashlib
import importlib
import json
import math
import runpy
import sys
import traceback
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import Any

import numpy as np
from osgeo import gdal, osr
from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsSettings,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QPointF, Qt
from qgis.PyQt.QtWidgets import QApplication
from qgis.utils import iface

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "validation_artifacts" / "qgis-desktop"
OUTPUT.mkdir(parents=True, exist_ok=True)
project = QgsProject.instance()
canvas = iface.mapCanvas()
initial_ids = set(project.mapLayers())
initial_crs = project.crs()
initial_canvas_crs = canvas.mapSettings().destinationCrs()
initial_extent = QgsRectangle(canvas.extent())
initial_tool = canvas.mapTool()
initial_active = iface.activeLayer()
initial_dirty = project.isDirty()
settings = QgsSettings()
initial_directory = settings.value("profiletool/lastdirectory")
initial_directory_exists = settings.contains("profiletool/lastdirectory")
initial_hook = sys.excepthook
event_errors = []


def event_hook(kind: type[BaseException], value: BaseException, tb: TracebackType | None) -> None:
    """Record Qt callback exceptions as validation failures."""
    event_errors.append("".join(traceback.format_exception(kind, value, tb)))


sys.excepthook = event_hook
results = []


def require(condition: object, message: str) -> None:
    """Raise an explicit failure for an unmet acceptance criterion."""
    if not condition:
        raise RuntimeError(message)


def run_case(number: int, name: str, function: Callable[[], dict[str, object]]) -> None:
    """Record each independent desktop scenario and its callback errors."""
    before = len(event_errors)
    try:
        detail = function()
        QApplication.processEvents()
        require(len(event_errors) == before, "Qt callback error: " + "\n".join(event_errors[before:]))
        results.append({"item": number, "name": name, "status": "passed", "detail": detail})
    except Exception:  # noqa: BLE001 -- Record failures and continue independent cases.
        results.append({"item": number, "name": name, "status": "failed", "traceback": traceback.format_exc()})
    (OUTPUT / "progress.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


def make_raster(name: str, epsg: int, origin: tuple[float, float], pixel: float) -> QgsRasterLayer:
    """Create a georeferenced ramp with a known zero and internal gap."""
    path = OUTPUT / f"{name}.tif"
    data = np.tile(np.arange(20, dtype=np.float64), (20, 1))
    data[:, 10] = -9999
    ds = gdal.GetDriverByName("GTiff").Create(str(path), 20, 20, 1, gdal.GDT_Float64)
    ds.SetGeoTransform((origin[0], pixel, 0, origin[1], 0, -pixel))
    spatial = osr.SpatialReference()
    spatial.ImportFromEPSG(epsg)
    ds.SetProjection(spatial.ExportToWkt())
    ds.GetRasterBand(1).SetNoDataValue(-9999)
    ds.GetRasterBand(1).WriteArray(data)
    ds = None
    layer = QgsRasterLayer(str(path), name)
    require(layer.isValid(), f"Invalid fixture {name}")
    layer.setCrs(crs(epsg))
    project.addMapLayer(layer)
    return layer


def crs(epsg: int) -> QgsCoordinateReferenceSystem:
    """Resolve an explicit EPSG reference for a fixture."""
    return QgsCoordinateReferenceSystem(f"EPSG:{epsg}")


def set_crs(epsg: int) -> None:
    """Set matching project and canvas references."""
    project.setCrs(crs(epsg))
    canvas.setDestinationCrs(project.crs())


def clear_rows() -> None:
    """Remove validation sources from the profile table."""
    while dock.mdl.rowCount():
        dock.removeLayer(0)


def show_profile(layer: QgsRasterLayer | QgsVectorLayer, points: list[list[float]], epsg: int) -> dict[str, Any]:
    """Sample and plot a fixture through the live profile dock."""
    clear_rows()
    core.pointstoDraw = []
    set_crs(epsg)
    dock.plotComboBox.setCurrentIndex(dock.plotComboBox.findText("Height"))
    dock.profileInterpolationCheckBox.setChecked(True)
    dock.fullResolutionCheckBox.setChecked(True)
    dock.addLayer(layer)
    core.updateProfil(points, removeSelection=False, plotProfil=True)
    require(len(core.profiles) == 1, "Expected one displayed profile")
    return core.profiles[0]


def transformed_points(points: list[list[float]], source: int, destination: int) -> list[list[float]]:
    """Transform reference endpoints using QGIS coordinate operations."""
    transform = QgsCoordinateTransform(crs(source), crs(destination), project)
    return [[p.x(), p.y()] for p in (transform.transform(QgsPointXY(*p)) for p in points)]


def check_raster(
    layer: QgsRasterLayer, points: list[list[float]], project_epsg: int, expected_length: float
) -> dict[str, object]:
    """Verify plotted units and transformed samples against the known ramp."""
    profile = show_profile(layer, points, project_epsg)
    require(math.isclose(profile["l"][-1], expected_length, rel_tol=1e-7, abs_tol=1e-9), "Wrong chainage units")
    require(profile["z"][0] == 0 and profile["z"][-1] == 19, "Incorrect transformed endpoint sampling")
    require(profile["crs"] == layer.crs(), "Wrong sample-coordinate CRS")
    require(np.isnan(profile["z"]).any(), "NoData gap disappeared")
    return {
        "length": profile["l"][-1],
        "samples": len(profile["l"]),
        "endpoints_z": [profile["z"][0], profile["z"][-1]],
    }


def nodata() -> dict[str, object]:
    """Verify internal and external gaps remain distinct from a valid zero."""
    points = [[399998.5, 6499989.5], [400021.5, 6499989.5]]
    profile = show_profile(metre_raster, points, 28350)
    require(np.isnan(profile["z"][0]) and np.isnan(profile["z"][-1]), "Outside raster samples should be missing")
    require(0 in profile["z"], "Valid zero was lost")
    dock.plotComboBox.setCurrentIndex(dock.plotComboBox.findText("Slope (%)"))
    require(np.isnan(core.profiles[0]["plot_y"]).any(), "Grade filled NoData")
    return {"missing_samples": int(np.isnan(profile["z"]).sum()), "grade_gaps": True}


def multipart() -> dict[str, object]:
    """Exercise real multipart selection without changing existing selections."""
    selection = importlib.import_module("profiletool.tools.selectlinetool")

    layer = QgsVectorLayer("MultiLineString?crs=EPSG:28350", "desktop-multipart", "memory")
    feature = QgsFeature()
    feature.setGeometry(
        QgsGeometry.fromWkt("MULTILINESTRING((400000 6500000,400019 6500000),(400000 6499989.5,400019 6499989.5))")
    )
    layer.dataProvider().addFeatures([feature])
    project.addMapLayer(layer)
    ids = [f.id() for f in layer.getFeatures()]
    layer.selectByIds(ids)
    set_crs(28350)
    iface.setActiveLayer(layer)
    selections = layer.selectedFeatureIds()
    _, chosen = selection.SelectLineTool().getPointTableFromSelectedLine(
        iface, core.toolrenderer.tool, [[400000, 6499989.6]]
    )
    require(len(chosen) == 1, "Selection failed")
    require(not chosen[0].geometry().isMultipart(), "Selected all multipart parts")
    require(chosen[0].geometry().asPolyline()[0].y() == 6499989.5, "Wrong multipart part")
    require(layer.selectedFeatureIds() == selections, "Changed existing QGIS selections")
    return {"feature_selection_handler": "passed", "physical_mouse_click": "not tested", "selection_preserved": True}


def refreshes() -> dict[str, object]:
    """Check source edits and repeated refresh/library-switch callbacks."""
    show_profile(metre_raster, metre_points, 28350)
    dock.addLayer(geo_raster)
    core.updateProfil(metre_points, removeSelection=False, plotProfil=True)
    for _ in range(4):
        dock.refreshPlot()
    require(dock.mdl.rowCount() == 2, "Unexpected source rows")
    require(len(dock.plotWdg.getPlotItem().listDataItems()) == 2, "Duplicate plot curves")
    dock.removeLayer(1)
    require(dock.mdl.rowCount() == 1, "Source removal failed")
    dock.updateCoordinateTab()
    libraries = [dock.cboLibrary.itemText(i) for i in range(dock.cboLibrary.count())]
    initial_receivers = dock.checkBox_mpl_tracking.receivers(dock.checkBox_mpl_tracking.stateChanged)
    for _ in range(2):
        for library in libraries:
            dock.cboLibrary.setCurrentIndex(dock.cboLibrary.findText(library))
            dock.refreshPlot()
            QApplication.processEvents()
    dock.cboLibrary.setCurrentIndex(dock.cboLibrary.findText("PyQtGraph"))
    dock.refreshPlot()
    require(
        dock.checkBox_mpl_tracking.receivers(dock.checkBox_mpl_tracking.stateChanged) == initial_receivers,
        "Tracking signal callbacks accumulate when switching plot libraries",
    )
    return {
        "repeated_refreshes": 4,
        "curve_count": 2,
        "libraries": libraries,
        "library_switch_cycles": 2,
    }


def vector_sampling() -> dict[str, object]:
    """Check metre buffers and output coordinates from geographic point data."""
    set_crs(28350)
    layer = QgsVectorLayer("Point?crs=EPSG:4326&field=z:double", "desktop-mixed-crs-points", "memory")
    to_source = QgsCoordinateTransform(crs(28350), crs(4326), project)
    for x, offset, z in [(400002, 0.5, 12), (400015, 0.5, 25), (400010, 5, 999)]:
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(to_source.transform(QgsPointXY(x, 6499989.5 + offset))))
        feature["z"] = z
        layer.dataProvider().addFeatures([feature])
    project.addMapLayer(layer)
    show_profile(layer, metre_points, 28350)
    dock.mdl.setData(dock.mdl.index(0, 4), 1.0, Qt.ItemDataRole.EditRole)
    core.updateProfil(metre_points, removeSelection=False, plotProfil=True)
    profile = core.profiles[0]
    require(
        999 not in profile["z"] and 12 in profile["z"] and 25 in profile["z"],
        "Buffer is not measured in project metres",
    )
    require(profile["crs"] == crs(28350), "Vector coordinates have wrong CRS")
    dock.tolayerPushButton[0].click()
    created = [
        layer
        for key, layer in project.mapLayers().items()
        if key not in initial_ids and layer.name().startswith("ProfileTool_")
    ]
    require(created and created[-1].crs() == crs(28350), "Temporary layer has wrong CRS")
    require(
        all(399999 < feature.geometry().asPoint().x() < 400020 for feature in created[-1].getFeatures()),
        "Temporary layer coordinates are not projected",
    )
    return {"buffer_metres": 1, "excluded_z": 999, "temporary_layer_crs": created[-1].crs().authid()}


def duplicate_names() -> dict[str, object]:
    """Keep identically named sources distinct during plotting and deletion."""
    other = QgsRasterLayer(metre_raster.source(), metre_raster.name())
    other.setCrs(metre_raster.crs())
    project.addMapLayer(other)
    show_profile(metre_raster, metre_points, 28350)
    dock.addLayer(other)
    core.updateProfil(metre_points, removeSelection=False, plotProfil=True)
    names = [curve.name() for curve in dock.plotWdg.getPlotItem().listDataItems()]
    require(len(names) == len(set(names)) == 2, "Duplicate names overwrite curves")
    project.removeMapLayer(other.id())
    require(dock.mdl.rowCount() == 1, "Removing one source removed the wrong row")
    require(dock.mdl.item(0, 5).data(Qt.ItemDataRole.EditRole) == metre_raster.id(), "Wrong source remains")
    return {"distinct_curve_names": names, "remaining_source_correct": True}


def save_source_elevation() -> dict[str, object]:
    """Invoke the plot-click handler and check the saved source elevation."""
    show_profile(metre_raster, metre_points, 28350)
    dock.plotComboBox.setCurrentIndex(dock.plotComboBox.findText("Slope (%)"))
    core.doTracking = True
    dock.cbAddPoint.setChecked(True)
    dock.showcursor = True
    core.distancesPicked = []
    index = 3
    x = core.profiles[0]["plot_x"][index]
    y = core.profiles[0]["plot_y"][index]
    QApplication.processEvents()
    scene = dock.plotWdg.getViewBox().mapViewToScene(QPointF(float(x), float(y)))

    class Click:
        """Minimal plot event carrying a QGraphicsScene coordinate."""

        def scenePos(self) -> QPointF:  # noqa: N802 -- Match the Qt event interface.
            """Provide the selected plot position to the real click handler."""
            return scene

    core.mouseClickedPyQtGraph(Click())
    require(core.pointLayer is not None, "No profile point saved")
    point = list(core.pointLayer.getFeatures())[-1]
    require(point["z"] == core.profiles[0]["z"][index], "Stored slope instead of source elevation")
    require(point["z"] != y, "Fixture must distinguish slope and elevation")
    return {"source_elevation": point["z"], "plotted_grade": float(y)}


def export_checks() -> dict[str, object]:
    """Reopen exports and inspect actual geometry across the NoData gap."""
    plotting = importlib.import_module("profiletool.tools.plottingtool")

    show_profile(metre_raster, metre_points, 28350)
    paths = {}
    original = plotting.getSaveFileName
    try:
        for kind in ["PNG", "SVG", "DXF2D", "DXF3D"]:
            path = OUTPUT / (kind.lower() + (".dxf" if kind.startswith("DXF") else "." + kind.lower()))
            plotting.getSaveFileName = lambda _path=path, **_kwargs: str(_path)
            if kind.startswith("DXF"):
                plotting.PlottingTool().outDXF(
                    iface, dock, dock.mdl, dock.plotlibrary, core.profiles, "2D" if kind == "DXF2D" else "3D"
                )
                # Read the actual exported DXF with GDAL's DXF driver.
                ds = gdal.OpenEx(str(path), gdal.OF_VECTOR)
                require(ds is not None, "Cannot reopen exported DXF")
                geometries = [feature.GetGeometryRef().Clone() for feature in ds.GetLayer(0)]
                require(len(geometries) == 2, "DXF bridges the internal NoData gap")
                require(all(geometry.GetPointCount() >= 2 for geometry in geometries), "Empty exported line")
                elevations = (
                    [
                        (geometry.GetPoint(0)[1], geometry.GetPoint(geometry.GetPointCount() - 1)[1])
                        for geometry in geometries
                    ]
                    if kind == "DXF2D"
                    else [
                        (geometry.GetPoint(0)[2], geometry.GetPoint(geometry.GetPointCount() - 1)[2])
                        for geometry in geometries
                    ]
                )
                require(elevations == [(0, 9), (11, 19)], "Wrong DXF elevation coordinates or gap endpoints")
                ds = None
            else:
                getattr(plotting.PlottingTool(), "out" + kind)(iface, dock, dock.mdl, dock.plotlibrary)
            require(path.exists() and path.stat().st_size > 100, "Empty export")
            if kind == "PNG":
                require(path.read_bytes().startswith(b"\x89PNG"), "Invalid PNG")
            if kind == "SVG":
                svg = ET.parse(path)  # noqa: S314 -- Parse only our own freshly generated fixture export.
                require(svg.getroot().tag.endswith("svg"), "Invalid SVG")
            paths[kind] = str(path)
    finally:
        plotting.getSaveFileName = original
    return {"artifacts": paths, "dxf_gap_parts": 2, "pdf_csv": "not available in the PyQtGraph export menu"}


def lifecycle() -> dict[str, object]:
    """Check repeated dock close/reopen and plugin unload signal cleanup."""
    global core, dock  # noqa: PLW0603 -- Refresh handles after reloading the live plugin.

    plugin = iface.profiletool_dev
    renderer = core.toolrenderer
    dock.close()
    require(not renderer._signals_connected, "Map tool callbacks remain after dock close")
    require(not core._layers_signal_connected, "Layer callbacks remain after dock close")
    for _ in range(3):
        plugin.run()
        renderer = plugin.profiletool.toolrenderer
        plugin.profiletool.dockwidget.close()
        require(not renderer._signals_connected, "Callbacks remain after repeated reopen/close")
    plugin.run()
    plugin.unload()
    require(not plugin.profiletool._layers_signal_connected, "Callbacks remain after unload")
    runpy.run_path(str(ROOT / "scripts" / "qgis_dev.py"), init_globals={"PROFILETOOL_DEV_ROOT": str(ROOT)})
    core = iface.profiletool_dev.profiletool
    dock = core.dockwidget
    return {"reopen_close_cycles": 3, "unload": "passed", "map_tool_restoration": "checked in final cleanup"}


try:
    runpy.run_path(str(ROOT / "scripts" / "qgis_dev.py"), init_globals={"PROFILETOOL_DEV_ROOT": str(ROOT)})
    core = iface.profiletool_dev.profiletool
    dock = core.dockwidget
    geo_raster = make_raster("desktop-geographic", 4326, (115, -31.99), 0.001)
    metre_raster = make_raster("desktop-metres", 28350, (400000, 6500000), 1)
    feet_raster = make_raster("desktop-feet", 2277, (3000000, 10000000), 1)
    geo_points = [[115.0005, -31.9995], [115.0195, -31.9995]]
    metre_points = [[400000.5, 6499989.5], [400019.5, 6499989.5]]
    metre_in_geo = transformed_points(metre_points, 28350, 4326)
    geo_in_metres = transformed_points(geo_points, 4326, 28350)
    run_case(1, "geographic project/geographic raster", lambda: check_raster(geo_raster, geo_points, 4326, 0.019))
    run_case(
        2,
        "geographic project/projected raster",
        lambda: check_raster(metre_raster, metre_in_geo, 4326, math.dist(*metre_in_geo)),
    )
    run_case(
        3,
        "projected project/geographic raster",
        lambda: check_raster(geo_raster, geo_in_metres, 28350, math.dist(*geo_in_metres)),
    )
    run_case(
        4,
        "feet project/feet raster",
        lambda: check_raster(feet_raster, [[3000000.5, 9999989.5], [3000019.5, 9999989.5]], 2277, 19 * 1200 / 3937),
    )
    run_case(5, "NoData, outside extent, valid zero and grade gaps", nodata)
    run_case(6, "multipart selection handler and preserved selections", multipart)
    run_case(7, "add/remove sources and repeated plot refreshes", refreshes)
    run_case(8, "mixed-CRS point vector buffer and temporary output", vector_sampling)
    run_case(9, "duplicate source names and individual source deletion", duplicate_names)
    run_case(10, "save source elevation while plotting slope", save_source_elevation)
    run_case(12, "PNG/SVG and split 2D/3D DXF exports", export_checks)
    run_case(11, "dock reopen and plugin unload callback cleanup", lifecycle)
finally:
    cleanup_errors = []
    try:
        for key in list(project.mapLayers()):
            if key not in initial_ids:
                project.removeMapLayer(key)
        project.setCrs(initial_crs)
        canvas.setDestinationCrs(initial_canvas_crs)
        canvas.setExtent(initial_extent)
        if initial_active is not None:
            iface.setActiveLayer(initial_active)
        if initial_tool is not None:
            canvas.setMapTool(initial_tool)
        else:
            canvas.unsetMapTool(canvas.mapTool())
        project.setDirty(initial_dirty)
        if initial_directory_exists:
            settings.setValue("profiletool/lastdirectory", initial_directory)
        else:
            settings.remove("profiletool/lastdirectory")
    except Exception:  # noqa: BLE001 -- Preserve cleanup failures in the evidence report.
        cleanup_errors.append(traceback.format_exc())
    sys.excepthook = initial_hook
    report = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "qgis": Qgis.QGIS_VERSION,
        "python": sys.version,
        "checkout": str(ROOT),
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for folder in ["tools", "ui"]
            for path in (ROOT / folder).glob("*.py")
        },
        "results": results,
        "qt_callback_errors": event_errors,
        "cleanup_errors": cleanup_errors,
        "restored_layer_ids": set(project.mapLayers()) == initial_ids,
        "restored_project_crs": project.crs() == initial_crs,
        "restored_map_tool": canvas.mapTool() == initial_tool,
        "manual_limits": "Handler/widget calls in live QGIS; physical mouse clicks and visual export inspection remain manual. QGIS 3.40/3.44 not tested.",
    }
    path = OUTPUT / "report.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "report": str(path),
                "results": [{"item": item["item"], "status": item["status"]} for item in results],
                "cleanup_errors": cleanup_errors,
            }
        )
    )
