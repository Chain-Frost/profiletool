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
"""Render and manage interactive profile selection on the map canvas."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, cast

from qgis.core import Qgis, QgsGeometry, QgsMapLayer, QgsPointXY, QgsVectorLayer
from qgis.gui import (
    QgsMapCanvas,
    QgsMapMouseEvent,
    QgsMapTool,
    QgsRubberBand,
    QgsVertexMarker,
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor, QCursor
from qgis.PyQt.QtWidgets import QAction, QMainWindow

from .selectlinetool import SelectLineTool

if TYPE_CHECKING:
    from .profiletool_core import ProfileToolCore


class ProfiletoolMapToolRenderer:
    """Manage map-selection events and temporary profile geometry overlays."""

    def __init__(self, profiletool: ProfileToolCore) -> None:
        self.profiletool = profiletool
        self.iface = self.profiletool.iface
        canvas = self.profiletool.iface.mapCanvas()
        if canvas is None:
            msg = "Profile Tool requires an active map canvas"
            raise RuntimeError(msg)
        self.canvas = canvas
        # The plugin creates its action before constructing the map renderer.
        self.tool = ProfiletoolMapTool(self.canvas, self.profiletool.plugincore.action)
        self.pointstoDraw: list[Sequence[float]] = []  # Polyline being drawn in freehand mode
        self.dblclktemp = None  # enable disctinction between leftclick and doubleclick
        self.isPlotting = False
        self._signals_connected = False
        # the rubberband
        self.rubberband = QgsRubberBand(self.canvas, Qgis.GeometryType.Line)
        self.rubberband.setWidth(2)
        self.rubberband.setColor(QColor(Qt.GlobalColor.red))

        self.rubberbandpoint = QgsVertexMarker(self.iface.mapCanvas())
        self.rubberbandpoint.setColor(QColor(Qt.GlobalColor.red))
        self.rubberbandpoint.setIconSize(5)
        self.rubberbandpoint.setIconType(QgsVertexMarker.IconType.ICON_BOX)
        self.rubberbandpoint.setPenWidth(3)

        self.rubberbandbuf = QgsRubberBand(self.iface.mapCanvas())
        self.rubberbandbuf.setWidth(1)
        self.rubberbandbuf.setColor(QColor(Qt.GlobalColor.blue))

        self.textquit0 = "Left click for polyline and right click to end (Right click to clear)"
        self.textquit1 = "Select the polyline feature in a vector layer (Right click to quit)"
        self.textquit2 = "Select the polyline vector layer (Right click to quit)"

        self.setSelectionMethod(0)

    def resetRubberBand(self) -> None:
        """Clear the temporary line overlay while retaining its geometry type."""
        self.rubberband.reset(Qgis.GeometryType.Line)

    def _status_message(self, message: str) -> None:
        """Display map-tool instructions when the desktop status bar exists."""
        window = cast(QMainWindow | None, self.iface.mainWindow())
        if window is not None:
            status_bar = window.statusBar()
            if status_bar is not None:
                status_bar.showMessage(message)

    def updateRubberBand(self) -> None:
        """Redraw the temporary line from the currently collected path points."""
        self.resetRubberBand()
        for i in range(len(self.pointstoDraw)):
            self.rubberband.addPoint(QgsPointXY(self.pointstoDraw[i][0], self.pointstoDraw[i][1]))

    def moved(self, position: Mapping[str, int]) -> None:  # draw the polyline on the temp layer (rubberband)
        """Extend the freehand preview to the mouse's current map position."""
        if self.selectionmethod == 0 and len(self.pointstoDraw) > 0:
            # Get mouse coords
            transform = self.canvas.getCoordinateTransform()
            if transform is None:
                return
            mapPos = transform.toMapCoordinates(position["x"], position["y"])
            # Draw on temp layer
            self.updateRubberBand()
            self.rubberband.addPoint(QgsPointXY(mapPos.x(), mapPos.y()))
        if self.selectionmethod in (1, 2):
            return

    def rightClicked(self, position: Mapping[str, int]) -> None:  # noqa: ARG002 -- Keep the signal callback signature.
        """Finish a drawn profile or clear an idle freehand selection."""
        if self.selectionmethod == 0:
            if self.isPlotting:
                self.updateRubberBand()
                self.isPlotting = False
                # launch analyses
                self._status_message(str(self.pointstoDraw))
                self.profiletool.updateProfil(self.pointstoDraw)
                # Reset
                self.pointstoDraw = []
            else:
                self.profiletool.clearProfil()
                self.cleaning()
        if self.selectionmethod in (1, 2):
            return

    def leftClicked(self, position: Mapping[str, int]) -> None:  # Add point to analyse
        """Collect a freehand vertex or select source features at the clicked position."""
        transform = self.canvas.getCoordinateTransform()
        if transform is None:
            return
        mapPos = transform.toMapCoordinates(position["x"], position["y"])
        newPoints = [[mapPos.x(), mapPos.y()]]
        if self.profiletool.doTracking:
            self.rubberbandpoint.hide()

        if self.selectionmethod == 0:
            if not self.isPlotting:
                self.profiletool.clearProfil()
                self.cleaning()
                self.isPlotting = True
            self.pointstoDraw += newPoints
            if self.profiletool.liveUpdate:
                self.profiletool.updateProfil(self.pointstoDraw)
            self._status_message(self.textquit0)
        if self.selectionmethod in (1, 2):
            if self.selectionmethod == 1:
                method = "feature"
                message = self.textquit1
            else:
                method = "layer"
                message = self.textquit2
            result = SelectLineTool(selectionMethod=method).getPointTableFromSelectedLine(
                self.iface, self.tool, newPoints
            )
            self.profiletool.updateProfilFromFeatures(result[0], result[1])

            self._status_message(message)

    def currentLayerChanged(self, layer: QgsMapLayer | None) -> None:
        """Refresh whole-layer selection when the active source layer changes."""
        if self.selectionmethod == 2:
            if isinstance(layer, QgsVectorLayer) and (
                SelectLineTool.checkIsLineLayer(layer) or SelectLineTool.checkIsPointLayer(layer)
            ):
                self.profiletool.updateProfilFromFeatures(
                    layer, SelectLineTool.select_layer_features(None, layer, None)
                )
            else:
                self.profiletool.clearProfil()

    def setSelectionMethod(self, method: int) -> None:
        """Set freehand, feature or whole-layer selection and update instructions."""
        self.cleaning()
        self.selectionmethod = method
        if method == 0:
            self.tool.setCursor(Qt.CursorShape.CrossCursor)
            self._status_message(self.textquit0)
        elif method == 1:
            self.tool.setCursor(Qt.CursorShape.PointingHandCursor)
            self._status_message(self.textquit1)
        elif method == 2:
            self.tool.setCursor(Qt.CursorShape.PointingHandCursor)
            self._status_message(self.textquit2)
        self.currentLayerChanged(self.iface.activeLayer())

    def setBufferGeometry(self, geoms: Sequence[QgsGeometry | None]) -> None:
        """Draw the valid buffer geometries used for point-source sampling."""
        self.rubberbandbuf.reset()
        for geom in geoms:
            if geom is not None and not geom.isNull() and not geom.isEmpty():
                self.rubberbandbuf.addGeometry(geom, None)

    def cleaning(self) -> None:  # used on right click
        """Clear temporary path geometry and map-selection instructions."""
        self.pointstoDraw = []
        self.rubberbandpoint.hide()
        self.resetRubberBand()
        self.rubberbandbuf.reset()
        self._status_message("")

    def connectTool(self) -> None:
        """Connect the renderer's map and layer callbacks once."""
        if self._signals_connected:
            return
        self._signals_connected = True
        self.tool.moved.connect(self.moved)
        self.tool.rightClicked.connect(self.rightClicked)
        self.tool.leftClicked.connect(self.leftClicked)
        self.tool.desactivate.connect(self.deactivate)
        self.iface.currentLayerChanged.connect(self.currentLayerChanged)

    def deactivate(self) -> None:
        """Disconnect only our callbacks; let QGIS switch map tools normally."""
        self.cleaning()
        if not self._signals_connected:
            return
        self._signals_connected = False
        self.tool.moved.disconnect(self.moved)
        self.tool.rightClicked.disconnect(self.rightClicked)
        self.tool.leftClicked.disconnect(self.leftClicked)
        self.tool.desactivate.disconnect(self.deactivate)
        self.iface.currentLayerChanged.disconnect(self.currentLayerChanged)


class ProfiletoolMapTool(QgsMapTool):
    """Emit profile-selection signals from QGIS canvas mouse events."""

    moved = pyqtSignal(dict)
    rightClicked = pyqtSignal(dict)
    leftClicked = pyqtSignal(dict)
    doubleClicked = pyqtSignal(dict)
    desactivate = pyqtSignal()

    def __init__(self, canvas: QgsMapCanvas, button: QAction) -> None:
        QgsMapTool.__init__(self, canvas)
        self._canvas = canvas
        self.cursor = QCursor(Qt.CursorShape.CrossCursor)
        self._action = button

    def canvasMoveEvent(self, e: QgsMapMouseEvent | None) -> None:
        """Emit the current viewport position when a mouse event is available."""
        if e is not None:
            self.moved.emit({"x": e.pos().x(), "y": e.pos().y()})

    def canvasReleaseEvent(self, e: QgsMapMouseEvent | None) -> None:
        """Emit a left- or right-click position from the released mouse button."""
        if e is None:
            return
        if e.button() == Qt.MouseButton.RightButton:
            self.rightClicked.emit({"x": e.pos().x(), "y": e.pos().y()})
        else:
            self.leftClicked.emit({"x": e.pos().x(), "y": e.pos().y()})

    def canvasDoubleClickEvent(self, e: QgsMapMouseEvent | None) -> None:
        """Emit the viewport position of a double-click event."""
        if e is not None:
            self.doubleClicked.emit({"x": e.pos().x(), "y": e.pos().y()})

    def activate(self) -> None:
        """Activate the canvas cursor and check the plugin toolbar action."""
        QgsMapTool.activate(self)
        self._canvas.setCursor(self.cursor)
        self._action.setCheckable(True)
        self._action.setChecked(True)

    def deactivate(self) -> None:
        """Notify the renderer and release the checked toolbar action."""
        self.desactivate.emit()
        self._action.setCheckable(False)
        QgsMapTool.deactivate(self)

    def isZoomTool(self) -> bool:
        """Report that this tool selects profile paths rather than changing zoom."""
        return False

    def setCursor(self, cursor: QCursor | Qt.CursorShape) -> None:
        """Store the cursor to apply when the profile map tool is activated."""
        self.cursor = QCursor(cursor)
