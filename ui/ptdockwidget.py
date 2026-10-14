# -----------------------------------------------------------
#
# Profile
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

"""Implement the interactive Profile Tool dock widget."""

from __future__ import annotations

import os
from contextlib import suppress
from typing import TYPE_CHECKING

from qgis.core import (
    Qgis,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsMapLayer,
    QgsPointXY,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QMetaType, QModelIndex, Qt, pyqtSignal
from qgis.PyQt.QtGui import QCloseEvent, QStandardItem, QStandardItemModel
from qgis.PyQt.QtWidgets import (
    QApplication,
    QDockWidget,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)

# plugin import
from ..tools.plottingtool import PlottingTool
from ..tools.tableviewtool import TableViewTool, layer_from_model

try:
    import matplotlib as mpl

    # The dock needs only availability, not a star import into its namespace.
    matplotlib_loaded = bool(mpl.__version__)
except ImportError:
    matplotlib_loaded = False


uiFilePath = os.path.abspath(os.path.join(os.path.dirname(__file__), "profiletool.ui"))
if TYPE_CHECKING:
    from qgis.gui import QgisInterface

    from ..tools.profile_types import Profile
    from ..tools.profiletool_core import ProfileToolCore
    from .profiletool_form_types import Ui_ProfileTool as FormClass
else:
    FormClass = uic.loadUiType(uiFilePath)[0]


class PTDockWidget(QDockWidget, FormClass):
    """Present profile sources, plotting controls and coordinate export actions."""

    TITLE = "ProfileTool"
    TYPE: str | None = None

    closed = pyqtSignal()

    def __init__(self, iface1: QgisInterface, profiletoolcore: ProfileToolCore, parent: QWidget | None = None) -> None:
        QDockWidget.__init__(self, parent)
        self.setupUi(self)
        self.profiletoolcore = profiletoolcore
        self.iface = iface1
        # Apperance
        self.location = Qt.DockWidgetArea.BottomDockWidgetArea
        minsize = self.minimumSize()
        maxsize = self.maximumSize()
        self.setMinimumSize(minsize)
        self.setMaximumSize(maxsize)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # init scale widgets
        self.sbMaxVal.setValue(0)
        self.sbMinVal.setValue(0)
        self.sbMaxVal.setEnabled(False)
        self.sbMinVal.setEnabled(False)
        self.connectYSpinbox()

        # model
        self.mdl = QStandardItemModel(0, 6)  # the model whitch in are saved layers analysed caracteristics
        self.tableView.setModel(self.mdl)
        self.tableView.setColumnWidth(0, 20)
        self.tableView.setColumnWidth(1, 20)
        hh = self.tableView.horizontalHeader()
        if hh is not None:
            hh.setStretchLastSection(True)
        self.tableView.setColumnHidden(5, True)
        self.mdl.setHorizontalHeaderLabels(["", "", self.tr("Layer"), self.tr("Band/Field"), self.tr("Search buffer")])
        self.tableViewTool = TableViewTool()

        # other
        self.addOptionComboboxItems()
        self.selectionmethod = 0
        self.plotlibrary = None  # The plotting library to use
        self.showcursor = True

        # Signals
        self.butSaveAs.clicked.connect(self.saveAs)
        self.tableView.clicked.connect(self._onClick)
        self.mdl.itemChanged.connect(self._onChange)
        self.pushButton_2.clicked.connect(self.addLayer)
        self.pushButton.clicked.connect(self.removeLayer)
        self.comboBox.currentIndexChanged.connect(self.selectionMethod)
        self.cboLibrary.currentIndexChanged.connect(self.changePlotLibrary)
        self.tableViewTool.layerAddedOrRemoved.connect(self.refreshPlot)
        self.pushButton_reinitview.clicked.connect(self.reScalePlot)
        self.checkBox_showcursor.stateChanged.connect(self.showCursor)
        self.cbLiveUpdate.stateChanged.connect(self.liveUpdateChanged)
        self.fullResolutionCheckBox.stateChanged.connect(self.refreshPlot)
        self.profileInterpolationCheckBox.stateChanged.connect(self.refreshPlot)

        self.cbSameAxisScale.stateChanged.connect(self._onSameAxisScaleStateChanged)

    # ********************************************************************************
    # init things ****************************************************************
    # ********************************************************************************

    def addOptionComboboxItems(self) -> None:
        """Populate the plot-backend selector with installed libraries."""
        self.cboLibrary.addItem("PyQtGraph")
        if matplotlib_loaded:
            self.cboLibrary.addItem("Matplotlib")

    def selectionMethod(self, item: int) -> None:
        """Apply the chosen map-selection mode to the active profile renderer."""
        renderer = self.profiletoolcore.toolrenderer
        canvas = self.iface.mapCanvas()
        if renderer is None or canvas is None:
            return
        renderer.setSelectionMethod(item)

        if canvas.mapTool() == renderer.tool:
            canvas.setMapTool(renderer.tool)
            renderer.connectTool()

    def changePlotLibrary(self, item: int) -> None:
        # Each library switch replaces the plot, not the tracking checkbox.
        # Remove our previous connection before connecting the new plot once.
        """Switch plotting backends and reconnect tracking controls once."""
        with suppress(TypeError, RuntimeError):
            self.checkBox_mpl_tracking.stateChanged.disconnect(self.profiletoolcore.activateMouseTracking)
        self.plotlibrary = self.cboLibrary.itemText(item)
        self.addPlotWidget(self.plotlibrary)

        if self.plotlibrary == "PyQtGraph":
            self.checkBox_mpl_tracking.setEnabled(True)
            self.checkBox_showcursor.setEnabled(True)
            self.checkBox_mpl_tracking.setCheckState(Qt.CheckState.Checked)
            self.profiletoolcore.activateMouseTracking(2)
            self.checkBox_mpl_tracking.stateChanged.connect(self.profiletoolcore.activateMouseTracking)
            self._onSameAxisScaleStateChanged(self.cbSameAxisScale.checkState())

        elif self.plotlibrary == "Matplotlib":
            self.checkBox_mpl_tracking.setEnabled(True)
            self.checkBox_showcursor.setEnabled(False)
            self.checkBox_mpl_tracking.setCheckState(Qt.CheckState.Checked)
            self.profiletoolcore.activateMouseTracking(2)
            self.checkBox_mpl_tracking.stateChanged.connect(self.profiletoolcore.activateMouseTracking)
            self.cbSameAxisScale.setCheckState(Qt.CheckState.Unchecked)

        else:
            self.checkBox_mpl_tracking.setCheckState(Qt.CheckState.Unchecked)
            self.checkBox_mpl_tracking.setEnabled(False)
            self.cbSameAxisScale.setCheckState(Qt.CheckState.Unchecked)

        self.cbSameAxisScale.setEnabled(self.plotlibrary == "PyQtGraph")

    def addPlotWidget(self, library: str) -> None:
        """Replace the plot widget and populate its supported export options."""
        layout = self.frame_for_plot.layout()
        if layout is None:
            return

        while layout.count():
            child = layout.takeAt(0)
            if child is not None and (widget := child.widget()) is not None:
                widget.deleteLater()

        if library == "PyQtGraph":
            self.stackedWidget.setCurrentIndex(0)
            self.plotWdg = PlottingTool().changePlotWidget("PyQtGraph", self.frame_for_plot)
            layout.addWidget(self.plotWdg)
            self.TYPE = "PyQtGraph"
            self.cbxSaveAs.clear()
            self.cbxSaveAs.addItems(["Graph - PNG", "Graph - SVG", "3D line - DXF", "2D Profile - DXF"])

        elif library == "Matplotlib":
            self.stackedWidget.setCurrentIndex(0)
            self.plotWdg = PlottingTool().changePlotWidget("Matplotlib", self.frame_for_plot)
            layout.addWidget(self.plotWdg)
            self.TYPE = "Matplotlib"
            self.cbxSaveAs.clear()
            self.cbxSaveAs.addItems(
                [
                    "Graph - PDF",
                    "Graph - PNG",
                    "Graph - SVG",
                    "Graph - print (PS)",
                    "3D line - DXF",
                    "2D Profile - DXF",
                ]
            )

    # ********************************************************************************
    # graph things ****************************************************************
    # ********************************************************************************

    def connectYSpinbox(self) -> None:
        """Connect vertical-bound edits to plot rescaling."""
        self.sbMinVal.valueChanged.connect(self.reScalePlot)
        self.sbMaxVal.valueChanged.connect(self.reScalePlot)

    def disconnectYSpinbox(self) -> None:
        """Disconnect vertical-bound callbacks during programmatic updates."""
        with suppress(AttributeError, RuntimeError, TypeError):
            self.sbMinVal.valueChanged.disconnect(self.reScalePlot)
            self.sbMaxVal.valueChanged.disconnect(self.reScalePlot)

    def connectPlotRangechanged(self) -> None:
        """Connect PyQtGraph range changes to the bound-control update."""
        if self.plotWdg is None:
            return
        self.plotWdg.getViewBox().sigRangeChanged.connect(self.plotRangechanged)

    def disconnectPlotRangechanged(self) -> None:
        """Disconnect range updates while changing the plot programmatically."""
        if self.plotWdg is None:
            return
        with suppress(AttributeError, RuntimeError, TypeError):
            self.plotWdg.getViewBox().sigRangeChanged.disconnect(self.plotRangechanged)

    def plotRangechanged(self, param: object = None) -> None:  # called when pyqtgraph view changed
        """Refresh vertical-bound controls after the plot view range changes."""
        PlottingTool().plotRangechanged(self, self.cboLibrary.currentText())

    def liveUpdateChanged(self, state: int) -> None:
        """Apply the live-update checkbox state to the profile core."""
        self.profiletoolcore.liveUpdate = bool(state)

    def reScalePlot(self, param: float | bool) -> None:  # called when a spinbox value changed
        """Rescale profiles after a bound edit or the automatic-fit button."""
        if isinstance(param, bool):  # comes from button
            PlottingTool().reScalePlot(self, self.profiletoolcore.profiles, self.cboLibrary.currentText(), True)

        else:  # spinboxchanged
            if self.sbMinVal.value() == self.sbMaxVal.value() == 0:
                # don't execute it on init
                pass
            else:
                PlottingTool().reScalePlot(self, self.profiletoolcore.profiles, self.cboLibrary.currentText())

    def showCursor(self, int1: int) -> None:
        """Toggle PyQtGraph cursor visibility and map-tracking controls."""
        if self.plotWdg is None:
            return
        # For pyqtgraph mode
        if self.plotlibrary == "PyQtGraph":
            if int1 == 2:
                self.showcursor = True
                self.profiletoolcore.doTracking = bool(self.checkBox_mpl_tracking.checkState())
                self.checkBox_mpl_tracking.setEnabled(True)
                for item in self.plotWdg.allChildItems():
                    if str(type(item)) == "<class 'profiletool.pyqtgraph.graphicsItems.InfiniteLine.InfiniteLine'>":
                        if item.name() == "cross_vertical" or item.name() == "cross_horizontal":
                            item.show()
                    elif str(type(item)) == "<class 'profiletool.pyqtgraph.graphicsItems.TextItem.TextItem'>":
                        if item.textItem.toPlainText()[0] == "X" or item.textItem.toPlainText()[0] == "Y":
                            item.show()
            elif int1 == 0:
                self.showcursor = False
                self.profiletoolcore.doTracking = False
                self.checkBox_mpl_tracking.setEnabled(False)

                for item in self.plotWdg.allChildItems():
                    if str(type(item)) == "<class 'profiletool.pyqtgraph.graphicsItems.InfiniteLine.InfiniteLine'>":
                        if item.name() == "cross_vertical" or item.name() == "cross_horizontal":
                            item.hide()
                    elif str(type(item)) == "<class 'profiletool.pyqtgraph.graphicsItems.TextItem.TextItem'>":
                        if item.textItem.toPlainText()[0] == "X" or item.textItem.toPlainText()[0] == "Y":
                            item.hide()
            self.profiletoolcore.plotProfil()

    # ********************************************************************************
    # tablebiew things ****************************************************************
    # ********************************************************************************

    def addLayer(self, layer1: QgsMapLayer | bool | None = None) -> None:
        """Add a selected source and connect its data-change refresh callback."""
        if isinstance(layer1, bool):  # comes from click
            layer1 = self.iface.activeLayer()

        before = self.mdl.rowCount()
        self.tableViewTool.addLayer(self.iface, self.mdl, layer1)
        if self.mdl.rowCount() > before:
            selected_layer = layer_from_model(self.mdl, self.mdl.rowCount() - 1)
            if selected_layer is not None:
                selected_layer.dataChanged.connect(self.refreshPlot)

    def removeLayer(self, index: int | None = None) -> None:
        """Disconnect a source callback and remove its profile-table row."""
        if isinstance(index, bool):  # come from button
            index = self.tableViewTool.chooseLayerForRemoval(self.iface, self.mdl)

        if index is not None:
            layer = layer_from_model(self.mdl, index)
            if layer is not None:
                with suppress(AttributeError, RuntimeError, TypeError):
                    layer.dataChanged.disconnect(self.refreshPlot)
            self.tableViewTool.removeLayer(self.mdl, index)

    def refreshPlot(self) -> None:
        #
        #    Refreshes/updates the plot without requiring the user to
        #    redraw the plot line (rubberband)
        #
        """Resample the existing path after source or interpolation settings change."""
        self.profiletoolcore.updateProfil(self.profiletoolcore.pointstoDraw, False, True)

    def _onClick(self, index1: QModelIndex) -> None:  # action when clicking the tableview
        self.tableViewTool.onClick(self.iface, self, self.mdl, self.plotlibrary, index1)

    def _onChange(self, item: QStandardItem) -> None:
        layer = layer_from_model(self.mdl, item.row())
        if layer is not None and item.column() == 4 and layer.type() == Qgis.LayerType.Vector:
            self.refreshPlot()

    def _onSameAxisScaleStateChanged(self, state: int | Qt.CheckState) -> None:
        """Keep both plot axes at the same scale when requested.

        Aspect-ratio locking is supported only by PyQtGraph.
        """
        if self.plotlibrary == "PyQtGraph" and self.plotWdg is not None:
            self.plotWdg.getViewBox().setAspectLocked(state == Qt.CheckState.Checked)

    # ********************************************************************************
    # coordinate tab ****************************************************************
    # ********************************************************************************
    @staticmethod
    def _profile_name(profile: Profile) -> str:
        groupTitle = profile["layer"].name()
        band = profile["band"]
        if band is not None and band > -1:
            groupTitle += f"_band_{band}"
        return groupTitle.replace(" ", "_")

    def updateCoordinateTab(self) -> None:
        # Reinitialize the coordinate tab while retaining its existing layout.
        """Rebuild per-source sample tables and their copy and layer-export buttons."""
        self.VLayout = self.scrollAreaWidgetContents.layout()
        if self.VLayout is None:
            self.VLayout = QVBoxLayout(self.scrollAreaWidgetContents)
            self.VLayout.setContentsMargins(9, -1, -1, -1)
        while (child := self.VLayout.takeAt(0)) is not None:
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()
        # Setup the table tab
        self.coordinateGroups: list[QGroupBox] = []
        self.profilePushButton: list[QPushButton] = []
        self.coordsPushButton: list[QPushButton] = []
        self.tolayerPushButton: list[QPushButton] = []
        self.profileTableViews: list[QTableView] = []
        self.profileModels: list[QStandardItemModel] = []
        self.coordinateLayouts: list[QVBoxLayout] = []
        if self.mdl.rowCount() != len(self.profiletoolcore.profiles or []):
            return
        for i in range(self.mdl.rowCount()):
            self.coordinateGroups.append(QGroupBox(self.scrollAreaWidgetContents))
            sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.coordinateGroups[i].setSizePolicy(sizePolicy)
            profileTitle = self._profile_name(self.profiletoolcore.profiles[i])

            self.coordinateGroups[i].setTitle(QApplication.translate("GroupBox" + str(i), profileTitle))
            self.coordinateGroups[i].setObjectName("groupBox" + str(i))

            self.coordinateLayouts.append(QVBoxLayout(self.coordinateGroups[i]))
            self.coordinateLayouts[i].setObjectName("verticalLayout")
            # The table
            self.profileTableViews.append(QTableView(self.coordinateGroups[i]))
            sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.profileTableViews[i].setSizePolicy(sizePolicy)
            self.profileTableViews[i].setObjectName("tableView" + str(i))
            column = len(self.profiletoolcore.profiles[i]["l"])
            self.mdl2 = QStandardItemModel(2, column)
            self.profileModels.append(self.mdl2)
            for j in range(len(self.profiletoolcore.profiles[i]["l"])):
                self.mdl2.setData(self.mdl2.index(0, j, QModelIndex()), self.profiletoolcore.profiles[i]["l"][j])
                self.mdl2.setData(self.mdl2.index(1, j, QModelIndex()), self.profiletoolcore.profiles[i]["z"][j])
            vertical_header = self.profileTableViews[i].verticalHeader()
            horizontal_header = self.profileTableViews[i].horizontalHeader()
            if vertical_header is not None:
                vertical_header.setDefaultSectionSize(18)
            if horizontal_header is not None:
                horizontal_header.setDefaultSectionSize(60)
            self.profileTableViews[i].setModel(self.mdl2)
            # 2 * header (1 header + 1 horz slider) + nrows + a small margin
            minTableHeight = (
                2 * (horizontal_header.height() if horizontal_header is not None else 0)
                + sum(self.profileTableViews[i].rowHeight(j) for j in range(self.mdl2.rowCount()))
                + 6
            )  # extra safety margin
            self.profileTableViews[i].setMinimumHeight(minTableHeight)

            self.coordinateLayouts[i].addWidget(self.profileTableViews[i])

            self.horizontalLayout = QHBoxLayout()

            # the copy to clipboard button
            self.profilePushButton.append(QPushButton(self.coordinateGroups[i]))
            sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
            self.profilePushButton[i].setSizePolicy(sizePolicy)
            self.profilePushButton[i].setText(QApplication.translate("GroupBox", "Copy to clipboard"))
            self.profilePushButton[i].setObjectName(str(i))
            self.horizontalLayout.addWidget(self.profilePushButton[i])

            # button to copy to clipboard with coordinates
            self.coordsPushButton.append(QPushButton(self.coordinateGroups[i]))
            sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
            self.coordsPushButton[i].setSizePolicy(sizePolicy)
            self.coordsPushButton[i].setText(QApplication.translate("GroupBox", "Copy to clipboard (with coordinates)"))

            # button to copy to clipboard with coordinates
            self.tolayerPushButton.append(QPushButton(self.coordinateGroups[i]))
            sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
            self.tolayerPushButton[i].setSizePolicy(sizePolicy)
            self.tolayerPushButton[i].setText(QApplication.translate("GroupBox", "Create Temporary layer"))

            self.coordsPushButton[i].setObjectName(str(i))
            self.horizontalLayout.addWidget(self.coordsPushButton[i])

            self.tolayerPushButton[i].setObjectName(str(i))
            self.horizontalLayout.addWidget(self.tolayerPushButton[i])

            self.horizontalLayout.addStretch(0)
            self.coordinateLayouts[i].addLayout(self.horizontalLayout)

            self.VLayout.addWidget(self.coordinateGroups[i])

            self.profilePushButton[i].clicked.connect(self.copyTable)
            self.coordsPushButton[i].clicked.connect(self.copyTableAndCoords)
            self.tolayerPushButton[i].clicked.connect(self.createTemporaryLayer)

    def copyTable(self) -> None:  # Writing the table to clipboard in excel form
        """Copy the button's source chainage and elevation samples as tab-separated text."""
        sender = self.sender()
        if sender is None:
            return
        nr = int(sender.objectName())
        self.clipboard = QApplication.clipboard()
        if self.clipboard is None:
            return
        text = ""
        for i in range(len(self.profiletoolcore.profiles[nr]["l"])):
            text += (
                str(self.profiletoolcore.profiles[nr]["l"][i])
                + "\t"
                + str(self.profiletoolcore.profiles[nr]["z"][i])
                + "\n"
            )
        self.clipboard.setText(text)

    def copyTableAndCoords(self) -> None:  # Writing the table with coordinates to clipboard in excel form
        """Copy source chainage, coordinates and elevations as tab-separated text."""
        sender = self.sender()
        if sender is None:
            return
        nr = int(sender.objectName())
        self.clipboard = QApplication.clipboard()
        if self.clipboard is None:
            return
        text = ""
        for i in range(len(self.profiletoolcore.profiles[nr]["l"])):
            text += (
                str(self.profiletoolcore.profiles[nr]["l"][i])
                + "\t"
                + str(self.profiletoolcore.profiles[nr]["x"][i])
                + "\t"
                + str(self.profiletoolcore.profiles[nr]["y"][i])
                + "\t"
                + str(self.profiletoolcore.profiles[nr]["z"][i])
                + "\n"
            )
        self.clipboard.setText(text)

    def createTemporaryLayer(self) -> None:
        """Create a point layer from the button's source coordinates and elevations."""
        sender = self.sender()
        if sender is None:
            return
        nr = int(sender.objectName())
        type = "Point?crs=" + str(self.profiletoolcore.profiles[nr]["crs"].authid())
        name = f"ProfileTool_{self._profile_name(self.profiletoolcore.profiles[nr])}"
        vl = QgsVectorLayer(type, name, "memory")
        pr = vl.dataProvider()
        if pr is None:
            return
        vl.startEditing()
        # add fields
        pr.addAttributes([QgsField("Value", QMetaType.Type.Double)])
        vl.updateFields()
        # Add features to layer
        for i in range(len(self.profiletoolcore.profiles[nr]["l"])):
            fet = QgsFeature(vl.fields())
            # set geometry
            fet.setGeometry(
                QgsGeometry.fromPointXY(
                    QgsPointXY(
                        self.profiletoolcore.profiles[nr]["x"][i],
                        self.profiletoolcore.profiles[nr]["y"][i],
                    )
                )
            )
            # set attributes
            fet.setAttributes([self.profiletoolcore.profiles[nr]["z"][i]])
            pr.addFeatures([fet])
        vl.commitChanges()
        # labeling/enabled
        if False:
            labelsettings = vl.labeling().settings()
            labelsettings.enabled = True

        # show layer
        project = QgsProject.instance()
        if project is not None:
            project.addMapLayer(vl)

    # ********************************************************************************
    # other things ****************************************************************
    # ********************************************************************************

    def closeEvent(self, event: QCloseEvent | None) -> None:
        """Emit the dock-close signal and clear owned profile state."""
        self.closed.emit()
        self.profiletoolcore.cleaning()

    # generic save as button
    def saveAs(self) -> None:
        """Dispatch the selected graph or DXF export workflow."""
        idx = self.cbxSaveAs.currentText()
        if idx == "Graph - PDF":
            self.outPDF()
        elif idx == "Graph - PNG":
            self.outPNG()
        elif idx == "Graph - SVG":
            self.outSVG()
        elif idx == "Graph - print (PS)":
            self.outPrint()
        elif idx == "3D line - DXF":
            self.outDXF("3D")
        elif idx == "2D Profile - DXF":
            self.outDXF("2D")
        else:
            print("plottingtool: invalid index " + str(idx))

    def outPrint(self) -> None:  # Postscript file rendering doesn't work properly yet.
        """Delegate PostScript export to the current plotting backend."""
        PlottingTool().outPrint(self.iface, self, self.mdl, self.cboLibrary.currentText())

    def outPDF(self) -> None:
        """Delegate PDF export to the current plotting backend."""
        PlottingTool().outPDF(self.iface, self, self.mdl, self.cboLibrary.currentText())

    def outSVG(self) -> None:
        """Delegate SVG export to the current plotting backend."""
        PlottingTool().outSVG(self.iface, self, self.mdl, self.cboLibrary.currentText())

    def outPNG(self) -> None:
        """Delegate PNG export to the current plotting backend."""
        PlottingTool().outPNG(self.iface, self, self.mdl, self.cboLibrary.currentText())

    def outDXF(self, type: str) -> None:
        """Delegate the requested 2D or 3D profile export to the DXF writer."""
        PlottingTool().outDXF(
            self.iface,
            self,
            self.mdl,
            self.cboLibrary.currentText(),
            self.profiletoolcore.profiles,
            type,
        )
