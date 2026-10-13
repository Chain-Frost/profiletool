"""Extend live desktop validation with Qt mouse events, dialogs and exports.

Invoke with runpy.run_path in the connected QGIS desktop. QtTest sends events
through the real widgets; it does not simulate human hardware input.
"""

from __future__ import annotations

# ruff: noqa: INP001, SLF001 -- Standalone integration checks inspect signal state.
import csv
import hashlib
import importlib
import io
import json
import math
import runpy
import sys
import traceback
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from osgeo import gdal, osr
from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsRasterLayer, QgsRectangle, QgsVectorLayer
from qgis.PyQt.QtCore import QMimeData, QPoint, QSize, Qt, QTimer
from qgis.PyQt.QtTest import QTest
from qgis.PyQt.QtWidgets import QApplication, QComboBox, QDialogButtonBox, QInputDialog
from qgis.utils import iface

ROOT = Path(__file__).resolve().parents[1]
baseline = runpy.run_path(str(ROOT / "scripts" / "validate_qgis_desktop.py"))
require = baseline["require"]
show_profile = baseline["show_profile"]
make_raster = baseline["make_raster"]
set_crs = baseline["set_crs"]
clear_rows = baseline["clear_rows"]
core = baseline["core"]
dock = baseline["dock"]
OUTPUT = baseline["OUTPUT"]
project = QgsProject.instance()
canvas = iface.mapCanvas()
initial_ids = set(project.mapLayers())
initial_crs = project.crs()
initial_canvas_crs = canvas.mapSettings().destinationCrs()
initial_extent = QgsRectangle(canvas.extent())
initial_tool = canvas.mapTool()
initial_dirty = project.isDirty()
initial_render_flag = canvas.renderFlag()
initial_clipboard = QMimeData()
clipboard_data = QApplication.clipboard().mimeData()
if clipboard_data is not None:
    for mime_type in clipboard_data.formats():
        initial_clipboard.setData(mime_type, clipboard_data.data(mime_type))
initial_hook = sys.excepthook
sys.excepthook = baseline["event_hook"]
run_case = baseline["run_case"]
metre_points = baseline["metre_points"]


def canvas_clicks() -> dict[str, object]:
    """Send canvas mouse press/release events through the real active map tool."""
    raster = make_raster("interaction-metres", 28350, (400000, 6500000), 1)
    show_profile(raster, metre_points, 28350)
    layer = QgsVectorLayer("MultiLineString?crs=EPSG:28350", "interaction-lines", "memory")
    feature = QgsFeature()
    feature.setGeometry(
        QgsGeometry.fromWkt("MULTILINESTRING((400000 6499998,400019 6499998),(400000 6499989.5,400019 6499989.5))")
    )
    layer.dataProvider().addFeatures([feature])
    project.addMapLayer(layer)
    ids = [feature.id() for feature in layer.getFeatures()]
    layer.selectByIds(ids)
    iface.setActiveLayer(layer)
    dock.comboBox.setCurrentIndex(1)
    core.activateProfileMapTool()
    canvas.setExtent(QgsRectangle(399990, 6499980, 400030, 6500010))
    canvas.refresh()
    QTest.qWait(150)
    clicked_parts = []
    for y in [6499998, 6499989.5]:
        pixel = canvas.mapSettings().mapToPixel().transform(400005, y)
        QTest.mouseClick(
            canvas.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(round(pixel.x()), round(pixel.y())),
        )
        QTest.qWait(50)
        require(len(core.pointstoDraw) == 2, "Canvas click did not select one line part")
        require(
            all(math.isclose(point[1], y, abs_tol=1e-7) for point in core.pointstoDraw),
            "Canvas selected the wrong multipart line",
        )
        require(layer.selectedFeatureIds() == ids, "Canvas click changed existing feature selections")
        clicked_parts.append(y)
    for _ in range(3):
        iface.actionPan().trigger()
        require(not core.toolrenderer._signals_connected, "Callbacks persist after switching to pan")
        core.activateProfileMapTool()
        require(core.toolrenderer._signals_connected, "Callbacks not restored on reactivation")
    dock.comboBox.setCurrentIndex(0)
    return {
        "input": "QtTest mouse press/release to canvas viewport",
        "multipart_parts_y": clicked_parts,
        "pan_cycles": 3,
        "selections_preserved": True,
    }


def plot_clicks() -> dict[str, object]:
    """Send a viewport click through pyqtgraph's actual mouse-event dispatch."""
    raster = make_raster("interaction-plot", 28350, (400000, 6500000), 1)
    show_profile(raster, metre_points, 28350)
    dock.plotComboBox.setCurrentIndex(dock.plotComboBox.findText("Slope (%)"))
    dock.cbAddPoint.setChecked(True)
    dock.checkBox_mpl_tracking.setChecked(True)
    core.doTracking = True
    core.distancesPicked = []
    dock.showcursor = True
    view = dock.plotWdg.getViewBox()
    view.setRange(xRange=(0, 19), yRange=(0, 110), padding=0)
    QTest.qWait(50)
    point = view.mapViewToScene(QgsPointXY(3, 100).toQPointF())
    pixel = dock.plotWdg.mapFromScene(point)
    QTest.mouseClick(dock.plotWdg.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pixel)
    QTest.qWait(50)
    require(core.pointLayer is not None, "Viewport click saved no point")
    feature = list(core.pointLayer.getFeatures())[-1]
    require(
        feature["z"] == 3 and math.isclose(feature["d"], 3, abs_tol=1e-8),
        "Viewport click saved incorrect source elevation or chainage",
    )
    dock.plotWdg.grab().save(str(OUTPUT / "plot-click.png"))
    return {
        "input": "QtTest mouse press/release to plot viewport",
        "source_z": feature["z"],
        "displayed_grade": 100,
        "chainage": feature["d"],
    }


def interact_dialogs(action: Callable[[], object], choices: list[tuple[str, str]]) -> list[dict[str, object]]:
    """Use keyboard and button mouse events inside actual modal input dialogs."""
    pending = choices.copy()
    observed = []
    errors = []
    attempts = 0
    timer = QTimer()

    def choose() -> None:
        """Accept each expected dialog or reject on a bounded timeout."""
        nonlocal attempts
        attempts += 1
        dialog = QApplication.activeModalWidget()
        if isinstance(dialog, QInputDialog) and pending:
            expected_title, text = pending[0]
            if dialog.windowTitle() != expected_title:
                errors.append("Unexpected dialog: " + dialog.windowTitle())
                dialog.reject()
                timer.stop()
                return
            combos = dialog.findChildren(QComboBox)
            require(combos, "Dialog has no choices")
            combo = combos[0]
            labels = [combo.itemText(index) for index in range(combo.count())]
            matches = [index for index, label in enumerate(labels) if text in label]
            if len(matches) != 1:
                errors.append("Ambiguous choices: " + repr(labels))
                dialog.reject()
                timer.stop()
                return
            QTest.keyClick(combo, Qt.Key.Key_Home)
            for _ in range(matches[0]):
                QTest.keyClick(combo, Qt.Key.Key_Down)
            observed.append({"title": dialog.windowTitle(), "choices": labels, "selected": combo.currentText()})
            pending.pop(0)
            buttons = dialog.findChild(QDialogButtonBox)
            QTest.mouseClick(buttons.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton)
            if not pending:
                timer.stop()
        elif attempts > 60:
            errors.append("Timed out waiting for expected dialog")
            if dialog is not None:
                dialog.reject()
            timer.stop()

    timer.timeout.connect(choose)
    timer.start(100)
    try:
        action()
    finally:
        timer.stop()
    require(not errors and not pending, repr(errors or pending))
    return observed


def selection_dialogs() -> dict[str, object]:
    """Open real layer, band and removal dialogs with known distinct band data."""
    clear_rows()
    core.pointstoDraw = []
    set_crs(28350)
    path = OUTPUT / "interaction-multiband.tif"
    dataset = gdal.GetDriverByName("GTiff").Create(str(path), 20, 20, 2, gdal.GDT_Float64)
    dataset.SetGeoTransform((400000, 1, 0, 6500000, 0, -1))
    reference = osr.SpatialReference()
    reference.ImportFromEPSG(28350)
    dataset.SetProjection(reference.ExportToWkt())
    data = np.tile(np.arange(20, dtype=float), (20, 1))
    for band, offset in [(1, 0), (2, 100)]:
        dataset.GetRasterBand(band).WriteArray(data + offset)
    dataset = None
    layer = QgsRasterLayer(str(path), "interaction-multiband")
    layer.setCrs(baseline["crs"](28350))
    project.addMapLayer(layer)
    QTest.qWait(100)
    observed = interact_dialogs(dock.addLayer, [("Layer selector", "interaction-multiband"), ("Band selector", "2")])
    core.updateProfil(metre_points, removeSelection=False, plotProfil=True)
    require(
        core.profiles[0]["band"] == 2 and core.profiles[0]["z"][0] == 100 and core.profiles[0]["z"][-1] == 119,
        "Selected band 2 did not reach the plotted profile",
    )
    other = make_raster("interaction-removal", 28350, (400000, 6500000), 1)
    dock.addLayer(other)
    observed.extend(interact_dialogs(dock.pushButton.click, [("Layer selector", "interaction-removal")]))
    require(
        dock.mdl.rowCount() == 1 and dock.mdl.item(0, 5).data(Qt.ItemDataRole.EditRole) == layer.id(),
        "Removal dialog removed the wrong source",
    )
    return {"dialogs": observed, "band_2_endpoints": [100, 119], "remaining_source": layer.name()}


def broader_rasters() -> dict[str, object]:
    """Check another hemisphere, Web Mercator, ASCII grid and a rotated slope."""
    clear_rows()
    core.pointstoDraw = []
    for layer_id in list(project.mapLayers()):
        if layer_id not in initial_ids:
            project.removeMapLayer(layer_id)
    canvas.setRenderFlag(False)
    set_crs(3857)
    utm = make_raster("interaction-north-utm", 32632, (500000, 6000000), 1)
    source_points = [[500000.5, 5999989.5], [500019.5, 5999989.5]]
    converted = baseline["transformed_points"](source_points, 32632, 3857)
    mercator = baseline["check_raster"](utm, converted, 3857, math.dist(*converted))
    ascii_path = OUTPUT / "interaction-grid.asc"
    dataset = gdal.Open(utm.source())
    ascii_dataset = gdal.GetDriverByName("AAIGrid").CreateCopy(str(ascii_path), dataset)
    ascii_dataset.FlushCache()
    ascii_dataset = None
    dataset = None
    ascii_layer = QgsRasterLayer(str(ascii_path), "interaction-ascii-grid")
    require(ascii_layer.isValid(), "Invalid ASCII-grid fixture")
    ascii_layer.setCrs(baseline["crs"](32632))
    project.addMapLayer(ascii_layer)
    ascii_result = baseline["check_raster"](ascii_layer, source_points, 32632, 19)
    path = OUTPUT / "interaction-rotated.tif"
    transform = (15000000, 2, 0.5, -3500000, 0.3, -5)
    dataset = gdal.GetDriverByName("GTiff").Create(str(path), 20, 20, 1, gdal.GDT_Float64)
    dataset.SetGeoTransform(transform)
    reference = osr.SpatialReference()
    reference.ImportFromEPSG(3857)
    dataset.SetProjection(reference.ExportToWkt())
    data = np.tile(19 - np.arange(20, dtype=float), (20, 1))
    data[:, 10] = -9999
    dataset.GetRasterBand(1).SetNoDataValue(-9999)
    dataset.GetRasterBand(1).WriteArray(data)
    dataset = None
    rotated = QgsRasterLayer(str(path), "interaction-rotated-negative-grade")
    require(rotated.isValid(), "Invalid rotated fixture")
    rotated.setCrs(baseline["crs"](3857))
    project.addMapLayer(rotated)
    points = [
        [
            transform[0] + column * transform[1] + 10.5 * transform[2],
            transform[3] + column * transform[4] + 10.5 * transform[5],
        ]
        for column in [0.5, 19.5]
    ]
    profile = show_profile(rotated, points, 3857)
    require(profile["z"][0] == 19 and profile["z"][-1] == 0, "Wrong rotated-raster endpoint samples")
    dock.plotComboBox.setCurrentIndex(dock.plotComboBox.findText("Slope (%)"))
    grades = np.asarray(core.profiles[0]["plot_y"])
    provider_values = []
    for x, y in zip(profile["x"], profile["y"]):
        value, valid = rotated.dataProvider().sample(QgsPointXY(x, y), 1)
        provider_values.append(value if valid else np.nan)
    require(
        np.allclose(profile["z"], provider_values, equal_nan=True),
        "Plugin samples differ from QGIS's rotated-raster provider",
    )
    require(np.all(grades[np.isfinite(grades)] < 0), "Rotated-raster negative grade was lost")
    thin_gap_missing_samples = int(np.isnan(profile["z"]).sum())
    # QGIS exposes rotated GeoTIFFs through a square-pixel warped provider.
    # Its coarse nearest-neighbour grid can omit a single source-column gap.
    # Preserve that evidence and separately verify a gap visible to the provider.
    wide_path = OUTPUT / "interaction-rotated-wide-gap.tif"
    dataset = gdal.Open(str(path))
    wide_dataset = gdal.GetDriverByName("GTiff").CreateCopy(str(wide_path), dataset)
    data[:, 9:12] = -9999
    wide_dataset.GetRasterBand(1).WriteArray(data)
    wide_dataset.FlushCache()
    wide_dataset = None
    dataset = None
    wide_layer = QgsRasterLayer(str(wide_path), "interaction-rotated-wide-gap")
    wide_layer.setCrs(baseline["crs"](3857))
    project.addMapLayer(wide_layer)
    wide_profile = show_profile(wide_layer, points, 3857)
    dock.plotComboBox.setCurrentIndex(dock.plotComboBox.findText("Slope (%)"))
    wide_grades = np.asarray(core.profiles[0]["plot_y"])
    require(
        np.isnan(wide_profile["z"]).any()
        and np.isnan(wide_grades).any()
        and np.all(wide_grades[np.isfinite(wide_grades)] < 0),
        "Provider-visible rotated-raster gap or negative grade was lost",
    )
    return {
        "northern_utm_to_web_mercator": mercator,
        "ascii_grid": ascii_result,
        "rotated_unequal_pixels": {
            "geotransform": transform,
            "endpoints_z": [19, 0],
            "negative_grades": True,
            "provider_sample_parity": True,
            "thin_gap_missing_samples": thin_gap_missing_samples,
            "wide_gap_missing_samples": int(np.isnan(wide_profile["z"]).sum()),
            "limitation": "QGIS's warped provider omits this single-column raw-source gap before the plugin samples it.",
        },
    }


def pdf_and_tables() -> dict[str, object]:
    """Exercise Matplotlib PDF output and the supported tabular clipboard paths."""
    clear_rows()
    core.pointstoDraw = []
    for layer_id in list(project.mapLayers()):
        if layer_id not in initial_ids:
            project.removeMapLayer(layer_id)
    set_crs(28350)
    raster = make_raster("interaction-exports", 28350, (400000, 6500000), 1)
    profile = show_profile(raster, metre_points, 28350)
    menus = {}
    for library in ["PyQtGraph", "Matplotlib"]:
        index = dock.cboLibrary.findText(library)
        require(index >= 0, library + " is unavailable")
        dock.cboLibrary.setCurrentIndex(index)
        dock.refreshPlot()
        QTest.qWait(50)
        menus[library] = [dock.cbxSaveAs.itemText(index) for index in range(dock.cbxSaveAs.count())]
    plotting = importlib.import_module("profiletool.tools.plottingtool")
    pdf = OUTPUT / "interaction-matplotlib.pdf"
    original_dialog = plotting.getSaveFileName
    try:
        plotting.getSaveFileName = lambda *_args, **_kwargs: str(pdf)
        dock.cbxSaveAs.setCurrentIndex(dock.cbxSaveAs.findText("Graph - PDF"))
        dock.butSaveAs.click()
    finally:
        plotting.getSaveFileName = original_dialog
    require(
        pdf.exists() and pdf.stat().st_size > 1000 and pdf.read_bytes().startswith(b"%PDF-"),
        "Matplotlib PDF export failed",
    )
    pdf_pages = None
    if importlib.util.find_spec("PyQt6") and importlib.util.find_spec("PyQt6.QtPdf"):
        pdf_module = importlib.import_module("PyQt6.QtPdf")
        document = pdf_module.QPdfDocument(None)
        document.load(str(pdf))
        pdf_pages = document.pageCount()
        require(pdf_pages == 1, "Exported PDF cannot be reopened as one page")
        size = document.pagePointSize(0)
        preview = document.render(0, QSize(800, round(800 * size.height() / size.width())))
        require(not preview.isNull(), "Exported PDF cannot be rendered")
        preview.save(str(OUTPUT / "pdf-preview.png"))
    dock.cboLibrary.setCurrentIndex(dock.cboLibrary.findText("PyQtGraph"))
    dock.refreshPlot()
    tables = []
    for button, columns, filename in [
        (dock.profilePushButton[0], 2, "interaction-profile.tsv"),
        (dock.coordsPushButton[0], 4, "interaction-coordinates.tsv"),
    ]:
        button.click()
        text = QApplication.clipboard().text()
        rows = list(csv.reader(io.StringIO(text), delimiter="\t"))
        require(
            len(rows) == len(profile["l"]) and all(len(row) == columns for row in rows), "Wrong clipboard table shape"
        )
        data = np.asarray([[float(value) for value in row] for row in rows])
        require(np.allclose(data[:, 0], profile["l"], equal_nan=True), "Wrong clipboard chainage")
        require(np.allclose(data[:, -1], profile["z"], equal_nan=True), "Wrong clipboard source elevation/NoData")
        if columns == 4:
            require(
                np.allclose(data[:, 1], profile["x"]) and np.allclose(data[:, 2], profile["y"]),
                "Wrong clipboard source coordinates",
            )
        (OUTPUT / filename).write_text(text, encoding="utf-8")
        tables.append({"path": filename, "rows": len(rows), "columns": columns})
    return {
        "pdf": str(pdf),
        "pdf_reopened_pages": pdf_pages,
        "export_menus": menus,
        "clipboard_tables": tables,
        "csv": "No native CSV action; clipboard is tab-separated text for spreadsheet import. No CSV file export claimed.",
    }


try:
    run_case(13, "canvas viewport mouse clicks and map-tool transitions", canvas_clicks)
    run_case(14, "plot viewport mouse click stores source elevation", plot_clicks)
    run_case(15, "actual modal layer/band/removal dialog interactions", selection_dialogs)
    run_case(16, "broader raster format, CRS and rotated negative-grade fixtures", broader_rasters)
    run_case(17, "Matplotlib PDF and clipboard table workflows", pdf_and_tables)
finally:
    cleanup_errors = []
    try:
        clear_rows()
        for layer_id in list(project.mapLayers()):
            if layer_id not in initial_ids:
                project.removeMapLayer(layer_id)
        project.setCrs(initial_crs)
        canvas.setDestinationCrs(initial_canvas_crs)
        canvas.setExtent(initial_extent)
        canvas.setRenderFlag(initial_render_flag)
        if initial_tool is not None:
            canvas.setMapTool(initial_tool)
        project.setDirty(initial_dirty)
        QApplication.clipboard().setMimeData(initial_clipboard)
    except Exception:  # noqa: BLE001 -- Record cleanup failures as evidence.
        cleanup_errors.append(traceback.format_exc())
    sys.excepthook = initial_hook
    report = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "qgis": baseline["Qgis"].QGIS_VERSION,
        "results": baseline["results"],
        "qt_callback_errors": baseline["event_errors"],
        "cleanup_errors": cleanup_errors,
        "restored_layer_ids": set(project.mapLayers()) == initial_ids,
        "restored_crs": project.crs() == initial_crs,
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for directory in ["tools", "ui", "scripts"]
            for path in (ROOT / directory).glob("*.py")
        },
        "limits": "QtTest-generated widget events, not human hardware clicks. Synthetic fixtures only. QGIS 3.44 unavailable. Single-column raw-source NoData gap in the rotated raster is omitted by QGIS's warped provider; the plugin matches that provider.",
    }
    (OUTPUT / "interaction-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "report": str(OUTPUT / "interaction-report.json"),
                "results": [{"item": item["item"], "status": item["status"]} for item in report["results"]],
                "cleanup_errors": cleanup_errors,
            }
        )
    )
