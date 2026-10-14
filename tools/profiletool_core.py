# -----------------------------------------------------------
#
# Profile
# Copyright (C) 2008  Borys Jurgiel
# Copyright (C) 2012  Patrice Verchere
# -----------------------------------------------------------
#
# licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, print to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# ---------------------------------------------------------------------

"""Coordinate layer sampling, profile plotting and map tools."""

from __future__ import annotations

import os
from collections.abc import Sequence
from contextlib import suppress
from typing import TYPE_CHECKING, cast

import numpy as np

# qgis import
from qgis.core import (
    Qgis,
    QgsFeature,
    QgsGeometry,
    QgsMapLayer,
    QgsPointXY,
    QgsProject,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.gui import QgisInterface, QgsMapTool
from qgis.PyQt.QtCore import QSettings, QSignalBlocker, Qt
from qgis.PyQt.QtGui import QStandardItemModel
from qgis.PyQt.QtWidgets import QWidget

from ..ui.ptdockwidget import PTDockWidget
from . import profilers

# plugin import
from .dataReaderTool import DataReaderTool
from .plottingtool import PlottingTool
from .profile_types import Profile, ReaderProfile
from .ptmaptool import ProfiletoolMapToolRenderer
from .selectlinetool import SelectLineTool
from .tableviewtool import layer_from_model

if TYPE_CHECKING:
    from matplotlib.backend_bases import MouseEvent

    from ..profileplugin import ProfilePlugin


class ProfileToolCore(QWidget):
    def __init__(self, iface: QgisInterface, plugincore: ProfilePlugin, parent: QWidget | None = None) -> None:
        QWidget.__init__(self, parent)
        self.iface = iface
        self.plugincore = plugincore
        self.instance = QgsProject.instance()

        # remimber repository for saving
        if QSettings().value("profiletool/lastdirectory") != "":
            self.loaddirectory = QSettings().value("profiletool/lastdirectory")
        else:
            self.loaddirectory = ""

        # mouse tracking
        self.doTracking = False
        self.liveUpdate = True
        # the datas / results
        # dictionary where is saved the plotting data {"l":[l],"z":[z], "layer":layer1, "curve":curve1}
        self.profiles: list[Profile] = []
        # The line information
        self.pointstoDraw: list[Sequence[float]] = []
        # he renderer for temporary polyline
        self.toolrenderer = None
        # the maptool previously loaded
        self.saveTool: QgsMapTool | None = None  # Save the standard map tool for restoring it at the end.
        # Used to remove highlighting from previously active layer.
        self.previousLayerId = None
        self.pointLayer: QgsVectorLayer | None = None
        self._layers_signal_connected = False
        self.x_cursor: float | None = None  # Keep track of last x position of cursor
        self.distancesPicked: list[float] = []
        # the dockwidget
        self.dockwidget = PTDockWidget(self.iface, self)
        # Initialize the dockwidget combo box with the list of available profiles.
        # (Use sorted list to be sure that Height is always on top and
        # the combobox order is consistent)
        for profile in sorted(profilers.PLOT_PROFILERS):
            self.dockwidget.plotComboBox.addItem(profile)
        self.dockwidget.plotComboBox.setCurrentIndex(0)
        self.dockwidget.plotComboBox.currentIndexChanged.connect(lambda _index: self.plotProfil())
        # dockwidget graph zone
        self.dockwidget.changePlotLibrary(self.dockwidget.cboLibrary.currentIndex())

    def activateProfileMapTool(self) -> None:
        canvas = self.iface.mapCanvas()
        if canvas is None:
            return
        if self.toolrenderer is not None:
            if canvas.mapTool() != self.toolrenderer.tool:
                self.saveTool = canvas.mapTool()
                self.toolrenderer.connectTool()
                canvas.setMapTool(self.toolrenderer.tool)
            return
        self.saveTool = canvas.mapTool()
        self.toolrenderer = ProfiletoolMapToolRenderer(self)
        self.toolrenderer.connectTool()
        self.toolrenderer.setSelectionMethod(self.dockwidget.comboBox.currentIndex())
        canvas.setMapTool(self.toolrenderer.tool)
        if not self._layers_signal_connected:
            self.instance.layersRemoved.connect(self.onLayersRemoved)
            self._layers_signal_connected = True

    # ******************************************************************************************
    # **************************** function part *************************************************
    # ******************************************************************************************

    def clearProfil(self) -> None:
        self.updateProfilFromFeatures(None, [])

    def updateProfilFromFeatures(
        self, layer: QgsVectorLayer | None, features: Sequence[QgsFeature], plotProfil: bool = True
    ) -> None:
        """Read only the selected polyline part; preserve existing QGIS selection."""
        points: list[list[float]] = []
        if layer and features and self.toolrenderer is not None:
            if SelectLineTool.checkIsPointLayer(layer):
                for feature in features:
                    geom = feature.geometry()
                    if not geom.isNull() and not geom.isEmpty():
                        point = self.toolrenderer.tool.toMapCoordinates(layer, QgsPointXY(geom.asPoint()))
                        points.append([point.x(), point.y()])
            else:
                # The feature-selection tool narrows multipart geometries to
                # the clicked part. For layer-wide mode, use the first part
                # rather than silently stitching disconnected parts together.
                for feature in features:
                    geometry = feature.geometry()
                    if geometry.isNull() or geometry.isEmpty():
                        continue
                    parts = geometry.asMultiPolyline() if geometry.isMultipart() else [geometry.asPolyline()]
                    if not parts or not parts[0]:
                        continue
                    part_points = [self.toolrenderer.tool.toMapCoordinates(layer, p) for p in parts[0]]
                    converted = [[p.x(), p.y()] for p in part_points]
                    if points and converted and points[-1] != converted[0]:
                        # Do not join distinct/disconnected lines with a
                        # fabricated profile segment.
                        break
                    points.extend(converted if not points else converted[1:])
        if self.toolrenderer:
            self.toolrenderer.pointstoDraw = points.copy()
            self.toolrenderer.updateRubberBand()
        self.updateProfil(points, False, plotProfil)

    def updateProfil(
        self, points1: Sequence[Sequence[float]], removeSelection: bool = True, plotProfil: bool = True
    ) -> None:
        """Sample selected, manually added layers without changing feature selections."""
        self.pointstoDraw = list(points1)
        self.profiles = []
        self.distancesPicked = []
        self.removeClosedLayers(self.dockwidget.mdl)

        for i in range(self.dockwidget.mdl.rowCount()):
            layer = layer_from_model(self.dockwidget.mdl, i)
            if layer is None:
                continue
            band = self.dockwidget.mdl.item(i, 3).data(Qt.ItemDataRole.EditRole)
            profile: ReaderProfile = {"layer": layer, "band": band}
            if layer.type() == QgsMapLayer.VectorLayer:
                profile, buffer_geom, guide_geom = DataReaderTool().dataVectorReaderTool(
                    self.iface,
                    self.toolrenderer.tool,
                    profile,
                    self.pointstoDraw,
                    float(self.dockwidget.mdl.item(i, 4).data(Qt.ItemDataRole.EditRole)),
                )
                profile["_buffer_geometry"] = buffer_geom
                profile["_guide_geometry"] = guide_geom
            else:
                if not self.dockwidget.profileInterpolationCheckBox.isChecked():
                    resolution_mode = "samples"
                else:
                    resolution_mode = "full" if self.dockwidget.fullResolutionCheckBox.isChecked() else "limited"
                profile = DataReaderTool().dataRasterReaderTool(
                    self.iface,
                    self.toolrenderer.tool,
                    profile,
                    self.pointstoDraw,
                    resolution_mode,
                )
            profile["plot_x"] = []
            profile["plot_y"] = []
            # Both reader paths populate source coordinates, samples and CRS;
            # plot series are populated immediately above before storage.
            self.profiles.append(cast(Profile, profile))
        if plotProfil:
            self.plotProfil()

    def plotProfil(self, vertline: bool = True) -> None:
        self.disableMouseCoordonates()
        if self.removeClosedLayers(self.dockwidget.mdl):
            self.updateProfil(self.pointstoDraw, False, True)
            return
        plotting = PlottingTool()
        plotting.clearData(self.dockwidget, self.profiles, self.dockwidget.plotlibrary)
        if vertline:
            plotting.drawVertLine(self.dockwidget, self.pointstoDraw, self.dockwidget.plotlibrary)

        geoms = []
        for profile in self.profiles:
            for name in ("_buffer_geometry", "_guide_geometry"):
                geometry = profile.get(name)
                if geometry is not None and not geometry.isNull() and not geometry.isEmpty():
                    geoms.append(geometry)
        if self.toolrenderer:
            self.toolrenderer.setBufferGeometry(geoms)

        profile_func = profilers.PLOT_PROFILERS[self.dockwidget.plotComboBox.currentText()]
        for profile in self.profiles:
            profile["plot_x"], profile["plot_y"] = profile_func(profile)

        plotting.attachCurves(self.dockwidget, self.profiles, self.dockwidget.mdl, self.dockwidget.plotlibrary)
        plotting.reScalePlot(self.dockwidget, self.profiles, self.dockwidget.plotlibrary)
        self.dockwidget.updateCoordinateTab()
        self.updateCursorOnMap(self.x_cursor)
        self.enableMouseCoordonates(self.dockwidget.plotlibrary)

    def setPointOnMap(self, x: float | None, y: float) -> None:
        """Store the actual sampled elevation, even on a slope-profile plot."""
        elevation = y  # Preserve the legacy keyword argument while naming its meaning locally.
        self.x_cursor = x
        if not self.pointstoDraw or not self.doTracking or x is None:
            return
        points = [QgsPointXY(*p) for p in self.pointstoDraw]
        geom = QgsGeometry.fromPolylineXY(points)
        try:
            scale = DataReaderTool._project_distance_scale()
            map_distance = float(x) / scale
            point_projected = geom.interpolate(map_distance).asPoint()
        except (AttributeError, TypeError, ValueError, ZeroDivisionError):
            return
        if not np.isfinite(elevation):
            return

        if self.pointLayer is None or not QgsProject.instance().mapLayer(self.pointLayer.id()):
            self.pointLayer = None
            for layer in QgsProject.instance().mapLayersByName("profile_points"):
                if not isinstance(layer, QgsVectorLayer):
                    continue
                fields = {field.name() for field in layer.fields()}
                if (
                    layer.geometryType() == QgsWkbTypes.PointGeometry
                    and {"d", "z"} <= fields
                    and layer.crs() == QgsProject.instance().crs()
                ):
                    self.pointLayer = layer
                    break

        if self.pointLayer is None:
            self.pointLayer = QgsVectorLayer(
                "Point?field=z:double&field=d:double&index=yes&crs=" + QgsProject.instance().crs().authid(),
                "profile_points",
                "memory",
            )
            QgsProject.instance().addMapLayer(self.pointLayer)
            qml_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "profile_points",
                "profile_points.qml",
            )
            self.pointLayer.loadNamedStyle(qml_path)

        feature = QgsFeature(self.pointLayer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(point_projected))
        feature["d"] = float(x)
        feature["z"] = float(elevation)
        self.pointLayer.dataProvider().addFeatures([feature])
        self.pointLayer.updateExtents()
        self.pointLayer.triggerRepaint()
        self.iface.messageBar().pushMessage(
            "Profile Tool",
            'Point added to layer "profile_points"',
            level=Qgis.Info,
        )

    def updateCursorOnMap(self, x: float | None) -> None:
        self.x_cursor = x
        if self.toolrenderer is None:
            return
        if self.pointstoDraw and self.doTracking:
            if x is not None:
                points = [QgsPointXY(*p) for p in self.pointstoDraw]
                geom = QgsGeometry.fromPolylineXY(points)
                try:
                    if len(points) > 1:
                        pointprojected = geom.interpolate(float(x) / DataReaderTool._project_distance_scale()).asPoint()
                    else:
                        pointprojected = points[0]
                except (IndexError, AttributeError, ValueError):
                    pointprojected = None

                if pointprojected:
                    self.toolrenderer.rubberbandpoint.setCenter(pointprojected)
            self.toolrenderer.rubberbandpoint.show()
        else:
            self.toolrenderer.rubberbandpoint.hide()

    # remove layers which were removed from QGIS
    def onLayersRemoved(self, *args):
        self.updateProfil(self.pointstoDraw, False, True)

    def removeClosedLayers(self, model1: QStandardItemModel) -> bool:
        """Remove missing layers by stable ID, not by non-unique layer name."""
        removed = False
        blocker = QSignalBlocker(self.dockwidget.tableViewTool)
        try:
            for i in range(model1.rowCount() - 1, -1, -1):
                if layer_from_model(model1, i) is None:
                    self.dockwidget.removeLayer(i)
                    removed = True
        finally:
            blocker.unblock()
        return removed

    def cleaning(self) -> None:
        self.profiles = []
        self.pointstoDraw = []
        if self.toolrenderer:
            self.toolrenderer.cleaning()
        if self._layers_signal_connected:
            with suppress(AttributeError, RuntimeError, TypeError):
                self.instance.layersRemoved.disconnect(self.onLayersRemoved)
            self._layers_signal_connected = False

    # ******************************************************************************************
    # **************************** mouse interaction *******************************************
    # ******************************************************************************************

    def activateMouseTracking(self, int1: int) -> None:
        if self.dockwidget.TYPE == "PyQtGraph":
            if int1 == 2:
                self.doTracking = True
            elif int1 == 0:
                self.doTracking = False

        elif self.dockwidget.TYPE == "Matplotlib":
            if int1 == 2:
                self.doTracking = True
                self.cid = self.dockwidget.plotWdg.mpl_connect("motion_notify_event", self.mouseevent_mpl)
            elif int1 == 0:
                self.doTracking = False
                with suppress(AttributeError, RuntimeError, TypeError):
                    self.dockwidget.plotWdg.mpl_disconnect(self.cid)
                try:
                    if self.vline:
                        self.dockwidget.plotWdg.figure.get_axes()[0].lines.remove(self.vline)
                        self.dockwidget.plotWdg.draw()
                except Exception as e:
                    print(str(e))

    def mouseevent_mpl(self, event: MouseEvent) -> None:
        """Handle interactive mouse movement in the Matplotlib view."""
        if event.xdata:
            try:
                if self.vline:
                    self.dockwidget.plotWdg.figure.get_axes()[0].lines.remove(self.vline)
            except Exception:
                pass
            xdata = float(event.xdata)
            self.vline = self.dockwidget.plotWdg.figure.get_axes()[0].axvline(xdata, linewidth=2, color="k")
            self.dockwidget.plotWdg.draw()
            self.updateCursorOnMap(xdata)

    def enableMouseCoordonates(self, library: str | None) -> None:
        if library == "PyQtGraph":
            self.dockwidget.plotWdg.scene().sigMouseMoved.connect(self.mouseMovedPyQtGraph)
            self.dockwidget.plotWdg.scene().sigMouseClicked.connect(self.mouseClickedPyQtGraph)
            self.dockwidget.plotWdg.getViewBox().autoRange(items=self.dockwidget.plotWdg.getPlotItem().listDataItems())
            self.dockwidget.connectPlotRangechanged()

    def mouseClickedPyQtGraph(self, event):
        if not self.dockwidget.cbAddPoint.isChecked():
            return
        pos = event.scenePos()
        if not self.dockwidget.showcursor or not self.dockwidget.plotWdg.sceneBoundingRect().contains(pos):
            return
        mouse = self.dockwidget.plotWdg.getViewBox().mapSceneToView(pos)
        best = None
        for profile, item in zip(self.profiles, self.dockwidget.plotWdg.getPlotItem().listDataItems()):
            if not item.isVisible():
                continue
            x, y = item.getData()
            x_values = np.asarray(x, dtype=float)
            y_values = np.asarray(y, dtype=float)
            if not len(x_values):
                continue
            valid = np.isfinite(x_values) & np.isfinite(y_values)
            if not valid.any():
                continue
            indices = np.flatnonzero(valid)
            index = indices[np.argmin(np.abs(x_values[indices] - mouse.x()))]
            score = abs(y_values[index] - mouse.y())
            if best is None or score < best[0]:
                # Store source z, never the plotted slope percentage or degrees.
                source_z = profile["z"][index]
                best = (score, float(x_values[index]), float(source_z))
        if best is None or not np.isfinite(best[2]):
            return
        x, z = best[1:]
        if x not in self.distancesPicked:
            self.setPointOnMap(x, z)
            self.distancesPicked.append(x)

    def disableMouseCoordonates(self) -> None:
        with suppress(AttributeError, RuntimeError, TypeError):
            self.dockwidget.plotWdg.scene().sigMouseMoved.disconnect(self.mouseMovedPyQtGraph)
        with suppress(AttributeError, RuntimeError, TypeError):
            self.dockwidget.plotWdg.scene().sigMouseClicked.disconnect(self.mouseClickedPyQtGraph)
        self.dockwidget.disconnectPlotRangechanged()

    def mouseMovedPyQtGraph(self, pos):
        # si connexion directe du signal "mouseMoved" : la fonction reçoit le point courant
        # si le point est dans la zone courante
        if self.dockwidget.plotWdg.sceneBoundingRect().contains(pos) and self.dockwidget.showcursor:
            range = self.dockwidget.plotWdg.getViewBox().viewRange()
            # récupère le point souris à partir ViewBox
            mousePoint = self.dockwidget.plotWdg.getViewBox().mapSceneToView(pos)

            pitems = self.dockwidget.plotWdg.getPlotItem()
            ytoplot = None
            xtoplot = None

            if len(pitems.listDataItems()) > 0:
                # get data and nearest xy from cursor
                compt = 0
                try:
                    for item in pitems.listDataItems():
                        if item.isVisible():
                            x, y = item.getData()
                            nearestindex = np.argmin(abs(np.array(x, dtype=float) - mousePoint.x()))
                            if compt == 0:
                                xtoplot = np.array(x, dtype=float)[nearestindex]
                                ytoplot = np.array(y)[nearestindex]
                            else:
                                if abs(np.array(y)[nearestindex] - mousePoint.y()) < abs(ytoplot - mousePoint.y()):
                                    ytoplot = np.array(y)[nearestindex]
                                    xtoplot = np.array(x)[nearestindex]
                            compt += 1
                except (IndexError, ValueError):
                    ytoplot = None
                    xtoplot = None
                # plot xy label and cursor
                if xtoplot is not None and ytoplot is not None:
                    for item in self.dockwidget.plotWdg.allChildItems():
                        if str(type(item)) == "<class 'profiletool.pyqtgraph.graphicsItems.InfiniteLine.InfiniteLine'>":
                            if item.name() == "cross_vertical":
                                item.show()
                                item.setPos(xtoplot)
                            elif item.name() == "cross_horizontal":
                                item.show()
                                item.setPos(ytoplot)
                        elif str(type(item)) == "<class 'profiletool.pyqtgraph.graphicsItems.TextItem.TextItem'>":
                            if item.textItem.toPlainText()[0] == "X":
                                item.show()
                                item.setText("X : " + str(round(xtoplot, 3)))
                                item.setPos(xtoplot, range[1][0])
                            elif item.textItem.toPlainText()[0] == "Y":
                                item.show()
                                item.setText("Y : " + str(round(ytoplot, 3)))
                                item.setPos(range[0][0], ytoplot)
            # tracking part
            self.updateCursorOnMap(xtoplot)
