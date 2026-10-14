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
# with this progsram; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# ---------------------------------------------------------------------
"""Manage manually selected source layers in the profile table."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qgis.core import Qgis, QgsMapLayer, QgsProject, QgsRasterLayer, QgsVectorLayer
from qgis.PyQt.QtCore import QModelIndex, QObject, Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor, QStandardItem, QStandardItemModel
from qgis.PyQt.QtWidgets import QColorDialog, QInputDialog, QMessageBox

if TYPE_CHECKING:
    from qgis.gui import QgisInterface

    from ..ui.ptdockwidget import PTDockWidget

# plugin import
from .plottingtool import PlottingTool
from .utils import isProfilable


def layer_from_model(model: QStandardItemModel, row: int) -> QgsMapLayer | None:
    """Resolve a source ID through the project, avoiding deleted Qt wrappers."""
    item = model.item(row, 5)
    layer_id = item.data(Qt.ItemDataRole.EditRole) if item else None
    project = QgsProject.instance()
    return project.mapLayer(layer_id) if project is not None and isinstance(layer_id, str) else None


def _model_item(model: QStandardItemModel, row: int, column: int) -> QStandardItem:
    """Return an item after its value has been populated in the layer table."""
    item = model.item(row, column)
    if item is None:
        msg = "Profile layer table item was not created"
        raise RuntimeError(msg)
    return item


class TableViewTool(QObject):
    """Manage source-layer selection and edits in the profile table."""

    layerAddedOrRemoved = pyqtSignal()  # Established Qt signal API; naming exempted in ruff.toml.

    def addLayer(self, iface: QgisInterface, mdl: QStandardItemModel, layer1: QgsMapLayer | None = None) -> int | None:
        """Select a profilable source and band or field, then append its table row."""
        if layer1 is None:
            canvas = iface.mapCanvas()
            if canvas is None:
                return None
            templist: list[tuple[QgsMapLayer, str]] = []
            j = 0
            # Ask the layer by a input dialog
            for i in range(canvas.layerCount()):
                donothing = False
                layer = canvas.layer(i)
                if layer is None:
                    continue
                if isProfilable(layer):
                    for j in range(mdl.rowCount()):
                        existing_item = mdl.item(j, 5)
                        existing_id = (
                            existing_item.data(Qt.ItemDataRole.EditRole) if existing_item is not None else None
                        )
                        if existing_id == layer.id():
                            donothing = True
                else:
                    donothing = True

                if donothing is False:
                    templist.append((layer, layer.name()))

            if len(templist) == 0:
                QMessageBox.warning(iface.mainWindow(), "Profile tool", "No raster to add")
                return None
            # Identically named layers are allowed in QGIS. Disambiguate
            # display names but continue tracking them by stable layer ID.
            names = [entry[1] for entry in templist]
            labels = [name if names.count(name) == 1 else f"{name} [{layer.id()[-8:]}]" for layer, name in templist]
            selected_name, ok = QInputDialog.getItem(
                iface.mainWindow(),
                "Layer selector",
                "Choose layer",
                labels,
                0,
                False,  # noqa: FBT003 -- Qt's getItem binding requires positional arguments.
            )
            if not ok:
                return None
            layer2 = templist[labels.index(selected_name)][0]
        else:
            if isProfilable(layer1):
                layer2 = layer1
            else:
                text = "Active layer is not a profilable layer."
                if layer1.type() == Qgis.LayerType.Mesh:
                    text += "\n(MeshLayer support requires QGis version 3.6 or newer.)"
                QMessageBox.warning(iface.mainWindow(), "Profile tool", text)
                return None

        # Ask the Band by a input dialog
        # First, if isProfilable, considerate the real band number (instead of band + 1 for raster)
        if (layer2.type() == Qgis.LayerType.Plugin and isProfilable(layer2)) or layer2.type() == Qgis.LayerType.Mesh:
            self.bandoffset = 0
            typename = "parameter"
        elif layer2.type() == Qgis.LayerType.Raster:
            self.bandoffset = 1
            typename = "band"
        elif layer2.type() == Qgis.LayerType.Vector:
            self.bandoffset = 0
            typename = "field"
        else:
            return None

        if isinstance(layer2, QgsRasterLayer) and layer2.bandCount() != 1:
            listband = [str(i + self.bandoffset) for i in range(layer2.bandCount())]
            testqt, ok = QInputDialog.getItem(
                iface.mainWindow(),
                typename.capitalize() + " selector",
                "Choose the " + typename,
                listband,
                False,
            )
            if ok:
                choosenBand = int(testqt) - self.bandoffset
            else:
                return 2
        elif isinstance(layer2, QgsVectorLayer):
            fieldstemp = [field.name() for field in layer2.fields()]
            fields = [field.name() for field in layer2.fields() if field.isNumeric()]
            if len(fields) == 0:
                QMessageBox.warning(iface.mainWindow(), "Profile tool", "Active layer is not a profilable layer")
                return None
            if len(fields) == 1:
                choosenBand = fieldstemp.index(fields[0])

            else:
                defaultfield = fields.index("z") if "z" in fields else 0
                testqt, ok = QInputDialog.getItem(
                    iface.mainWindow(),
                    typename.capitalize() + " selector",
                    "Choose the " + typename,
                    fields,
                    defaultfield,
                )
                if ok:
                    choosenBand = fieldstemp.index(testqt)
                else:
                    return defaultfield
        elif layer2.type() == Qgis.LayerType.Plugin and isProfilable(layer2) and layer2.LAYER_TYPE == "selafin_viewer":
            listparameterband = []
            listparametername = []
            for i in range(layer2.bandCount()):
                listparameterband.append(layer2.hydrauparser.parametres[i][0])
                listparametername.append(layer2.hydrauparser.parametres[i][1])
            defaultparam = 3
            testqt, ok = QInputDialog.getItem(
                iface.mainWindow(),
                typename.capitalize() + " selector",
                "Choose the " + typename,
                listparametername,
                defaultparam,
            )
            if ok:
                choosenBand = listparameterband[listparametername.index(testqt)]
            else:
                return defaultparam

        else:
            choosenBand = 0

        # Complete the tableview
        row = mdl.rowCount()
        mdl.insertRow(row)
        mdl.setData(mdl.index(row, 0, QModelIndex()), True, Qt.ItemDataRole.CheckStateRole)
        _model_item(mdl, row, 0).setFlags(Qt.ItemFlag.ItemIsSelectable)
        lineColour = Qt.GlobalColor.red
        # QGis2
        if (
            (layer2.type() == Qgis.LayerType.Plugin and layer2.LAYER_TYPE == "crayfish_viewer")
            or (layer2.type() == Qgis.LayerType.Plugin and layer2.LAYER_TYPE == "selafin_viewer")
            or layer2.type() == Qgis.LayerType.Mesh
        ):
            lineColour = Qt.GlobalColor.blue
        mdl.setData(mdl.index(row, 1, QModelIndex()), QColor(lineColour), Qt.ItemDataRole.BackgroundRole)
        _model_item(mdl, row, 1).setFlags(Qt.ItemFlag.NoItemFlags)
        mdl.setData(mdl.index(row, 2, QModelIndex()), layer2.name())
        _model_item(mdl, row, 2).setFlags(Qt.ItemFlag.NoItemFlags)
        if layer2.type() == Qgis.LayerType.Plugin and layer2.LAYER_TYPE == "selafin_viewer":
            mdl.setData(mdl.index(row, 3, QModelIndex()), choosenBand + self.bandoffset)
        else:
            mdl.setData(mdl.index(row, 3, QModelIndex()), choosenBand + self.bandoffset)
            _model_item(mdl, row, 3).setFlags(Qt.ItemFlag.NoItemFlags)

        if layer2.type() == Qgis.LayerType.Vector:
            # Buffer distance is expressed in project CRS units: degrees in
            # geographic projects, linear units in projected projects.
            project = QgsProject.instance()
            default_buffer = 0.001 if project is not None and project.crs().isGeographic() else 100.0
            mdl.setData(mdl.index(row, 4, QModelIndex()), default_buffer)
        else:
            mdl.setData(mdl.index(row, 4, QModelIndex()), "")
            _model_item(mdl, row, 4).setFlags(Qt.ItemFlag.NoItemFlags)

        mdl.setData(mdl.index(row, 5, QModelIndex()), layer2.id())
        _model_item(mdl, row, 5).setFlags(Qt.ItemFlag.NoItemFlags)
        self.layerAddedOrRemoved.emit()
        return None

    def removeLayer(self, mdl: QStandardItemModel, index: int) -> None:
        """Remove a source row and notify listeners to refresh sampled profiles."""
        try:
            mdl.removeRow(index)
            self.layerAddedOrRemoved.emit()
        except RuntimeError:  # A Qt model can be deleted during dock shutdown.
            return

    def chooseLayerForRemoval(self, iface: QgisInterface, mdl: QStandardItemModel) -> int | None:
        """Return the chosen source-row index, or None when selection is canceled."""
        if mdl.rowCount() < 2:
            if mdl.rowCount() == 1:
                return 0
            return None

        list1 = []
        rows: list[int] = []
        for i in range(mdl.rowCount()):
            item = mdl.item(i, 2)
            if item is not None:
                list1.append(f"{i + 1} : {item.data(Qt.ItemDataRole.EditRole)}")
                rows.append(i)
        testqt, ok = QInputDialog.getItem(iface.mainWindow(), "Layer selector", "Choose the Layer", list1, 0)
        if ok:
            return rows[list1.index(testqt)]
        return None

    def onClick(
        self,
        iface: QgisInterface,
        wdg: PTDockWidget,
        mdl: QStandardItemModel,
        plotlibrary: str | None,
        index1: QModelIndex,
    ) -> None:  # action when clicking the tableview
        """Apply source-table color, visibility or plugin-parameter edits."""
        layer = layer_from_model(mdl, index1.row())
        if layer is None:
            return
        temp = mdl.itemFromIndex(index1)
        band_item = mdl.item(index1.row(), 3)
        if temp is None or band_item is None:
            return
        if index1.column() == 1:  # modifying color
            name = PlottingTool.curveName(
                layer,
                band_item.data(Qt.ItemDataRole.EditRole),
                mdl,
            )
            color = QColorDialog().getColor(temp.data(Qt.ItemDataRole.BackgroundRole))
            mdl.setData(mdl.index(temp.row(), 1, QModelIndex()), color, Qt.ItemDataRole.BackgroundRole)
            PlottingTool().changeColor(wdg, plotlibrary, color, name)
        elif index1.column() == 0:  # modifying checkbox
            name = PlottingTool.curveName(
                layer,
                band_item.data(Qt.ItemDataRole.EditRole),
                mdl,
            )
            booltemp = temp.data(Qt.ItemDataRole.CheckStateRole)
            booltemp = booltemp is not True
            mdl.setData(mdl.index(temp.row(), 0, QModelIndex()), booltemp, Qt.ItemDataRole.CheckStateRole)
            PlottingTool().changeAttachCurve(wdg, plotlibrary, booltemp, name)
        elif (
            index1.column() == 3 and layer.type() == Qgis.LayerType.Plugin and layer.LAYER_TYPE == "selafin_viewer"
        ):  # modifying selafin_viewer parameter
            listparameterband = []
            listparametername = []
            for i in range(layer.bandCount()):
                listparameterband.append(layer.hydrauparser.parametres[i][0])
                listparametername.append(layer.hydrauparser.parametres[i][1])
            previousparam = int(band_item.data(Qt.ItemDataRole.EditRole))
            testqt, ok = QInputDialog.getItem(
                iface.mainWindow(),
                "Parameter selector",
                "Choose the parameter",
                listparametername,
                previousparam,
            )
            choosenBand = listparameterband[listparametername.index(testqt)] if ok else previousparam
            mdl.setData(mdl.index(temp.row(), 3, QModelIndex()), choosenBand)
            self.layerAddedOrRemoved.emit()

        else:
            return
