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
"""Render and export Profile Tool plots."""

from __future__ import annotations

from collections.abc import Sequence
from math import sqrt
from pathlib import Path
from typing import TYPE_CHECKING, cast

import numpy as np
from qgis.core import QgsMapLayer, QgsProject, QgsUnitTypes
from qgis.PyQt.QtCore import QSettings, Qt
from qgis.PyQt.QtGui import QBrush, QColor, QPainter, QPen, QStandardItemModel
from qgis.PyQt.QtSvg import QSvgGenerator
from qgis.PyQt.QtWidgets import QFileDialog, QGraphicsView, QSizePolicy, QWidget

from .. import pyqtgraph as pg
from ..dxfwrite import (
    DXFEngine as dxf,  # noqa: N813 -- Preserve the established writer alias.
)
from ..pyqtgraph import exporters
from .csv_export import write_plot_csv
from .dataReaderTool import DataReaderTool
from .profile_types import Profile
from .profilers import ProfileSeries

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as MatplotlibCanvas
    from qgis.gui import QgisInterface

    from ..ui.ptdockwidget import PTDockWidget
    from .plot_types import (
        CurvePen,
        DrawableCanvas,
        DxfEngine,
        ExportFigure,
        ImageExport,
        MatplotlibAxes,
        MatplotlibFigure,
        PlotConfig,
        PlotItem,
        PlotViewBox,
        PlotWidget,
    )

cast("PlotConfig", pg).setConfigOption("background", "w")


try:
    import matplotlib as mpl

    has_mpl = bool(mpl.__version__)
except ImportError:
    has_mpl = False


def getSaveFileName(parent: QWidget | None, caption: str, directory: str, filter: str) -> str:  # noqa: A002 -- Legacy keyword.
    """Return the selected output path from the Qt file dialog."""
    fileName, _selected_filter = QFileDialog.getSaveFileName(
        parent=parent, caption=caption, directory=directory, filter=filter
    )
    return fileName


def _valid_elevation(value: float | None) -> bool:
    """Accept finite numeric elevations while treating None and NaN as gaps."""
    return value is not None and bool(np.isfinite(value))


def pyqtgraph_plot_item(widget: QWidget | None) -> PlotItem | None:
    """Resolve the concrete plot item only for a PyQtGraph widget."""
    if isinstance(widget, pg.PlotWidget):
        return cast("PlotWidget", widget).getPlotItem()
    return None


def plot_data_items(plot_item: PlotItem) -> list[pg.PlotDataItem]:
    """Read profile curves created by PlotWidget.plot as PlotDataItem instances."""
    return cast("list[pg.PlotDataItem]", plot_item.listDataItems())


def plot_view_box(plot_item: PlotItem) -> PlotViewBox | None:
    """Return the plot's view box, allowing for an already closed plot."""
    return plot_item.getViewBox()


def _cosmetic_pen(color: QColor, width: int) -> QPen:
    """Keep plot strokes at their configured pixel width when the view scales."""
    pen = QPen(color)
    pen.setWidthF(width)
    pen.setCosmetic(True)
    return pen


class PlottingTool:
    """This class manages profile plotting.

    A call to changePlotWidget creates the widget where profiles will be
    plotted.
    Subsequent calls to functions on this class pass along the wdg object
    where profiles are to be plotted.
    Input data is the "profiles" vector, and the ["plot_x"] and ["plot_y"] values
    are used as the data series x and y values respectively.
    """

    @staticmethod
    def _chainage_unit() -> str:
        """Return the display unit from the active project's geographic status."""
        project = QgsProject.instance()
        if project is None:
            msg = "Profile plots require an active QGIS project"
            raise RuntimeError(msg)
        return QgsUnitTypes.toAbbreviatedString(project.crs().mapUnits()) or "unknown units"

    @staticmethod
    def curveName(layer: QgsMapLayer, band: int, model: QStandardItemModel) -> str:
        """Unique plot key; disambiguate layers with identical names."""
        name = layer.name()
        same_name = sum(
            item.data(Qt.ItemDataRole.EditRole) == name
            for i in range(model.rowCount())
            if (item := model.item(i, 2)) is not None
        )
        if same_name > 1:
            name += f" [{layer.id()[-8:]}]"
        return f"{name}#{band}"

    def changePlotWidget(
        self,
        library: str,
        frame_for_plot: QWidget,  # noqa: ARG002 -- Legacy widget factory signature.
    ) -> PlotWidget | MatplotlibCanvas | None:
        """Construct the selected plotting backend and configure its axes and cursors."""
        if library == "PyQtGraph":
            plotWdg = cast("PlotWidget", pg.PlotWidget())
            unit = self._chainage_unit()
            plotWdg.setLabel("bottom", f"Chainage ({unit})")
            plotWdg.showGrid(x=True, y=True, alpha=0.5)
            datavline = pg.InfiniteLine(
                0, angle=90, pen=_cosmetic_pen(QColor(Qt.GlobalColor.red), 1), name="cross_vertical"
            )
            datahline = pg.InfiniteLine(
                0, angle=0, pen=_cosmetic_pen(QColor(Qt.GlobalColor.red), 1), name="cross_horizontal"
            )
            plotWdg.addItem(datavline)
            plotWdg.addItem(datahline)
            # cursor
            xtextitem = pg.TextItem(
                "X : /",
                color=(0, 0, 0),
                border=_cosmetic_pen(QColor(Qt.GlobalColor.black), 1),
                fill=QBrush(Qt.GlobalColor.white),
                anchor=(0, 1),
            )
            ytextitem = pg.TextItem(
                "Y : / ",
                color=(0, 0, 0),
                border=_cosmetic_pen(QColor(Qt.GlobalColor.black), 1),
                fill=QBrush(Qt.GlobalColor.white),
                anchor=(0, 0),
            )
            plotWdg.addItem(xtextitem)
            plotWdg.addItem(ytextitem)

            plotWdg.getViewBox().autoRange(items=[])
            plotWdg.getViewBox().disableAutoRange()
            plotWdg.getViewBox().border = _cosmetic_pen(QColor(Qt.GlobalColor.black), 1)

            return plotWdg

        if library == "Matplotlib" and has_mpl:
            if TYPE_CHECKING:
                from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            else:
                try:
                    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
                except ImportError:
                    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
            from matplotlib import rcParams
            from matplotlib.figure import Figure, SubplotParams

            fig = Figure(
                (1.0, 1.0),
                linewidth=0.0,
                subplotpars=SubplotParams(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0),
            )

            rcParams["font.family"] = "arial"
            rcParams["font.weight"] = "normal"
            rcParams["font.size"] = 12

            rect = fig.patch
            rect.set_facecolor((0.9, 0.9, 0.9))

            self.subplot = cast("MatplotlibFigure", fig).add_axes((0.05, 0.15, 0.92, 0.82))
            unit = self._chainage_unit()
            cast("MatplotlibAxes", self.subplot).set_xlabel(f"Chainage ({unit})")
            self.subplot.set_xbound(0, 1000)
            self.subplot.set_ybound(0, 1000)
            self.manageMatplotlibAxe(self.subplot)
            canvas = FigureCanvasQTAgg(fig)
            sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            cast("QWidget", canvas).setSizePolicy(sizePolicy)
            return canvas
        return None

    def drawVertLine(self, wdg: PTDockWidget, pointstoDraw: Sequence[Sequence[float]], library: str | None) -> None:
        """Mark internal path vertices on the Matplotlib chainage axis."""
        if wdg.plotWdg is None:
            return
        if library == "PyQtGraph":
            pass
        elif library == "Matplotlib" and has_mpl:
            profileLen = 0
            for i in range(len(pointstoDraw) - 1):
                x1 = float(pointstoDraw[i][0])
                y1 = float(pointstoDraw[i][1])
                x2 = float(pointstoDraw[i + 1][0])
                y2 = float(pointstoDraw[i + 1][1])
                profileLen += sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                cast("MatplotlibAxes", wdg.plotWdg.figure.get_axes()[0]).axvline(
                    profileLen * DataReaderTool.project_distance_scale(), linewidth=1
                )
            profileLen = 0

    def attachCurves(
        self, wdg: PTDockWidget, profiles: Sequence[Profile], model1: QStandardItemModel, library: str | None
    ) -> None:
        """Draw profile series with their source-table colors and visibility settings."""
        if wdg.plotWdg is None:
            return

        if library == "PyQtGraph":
            plot_item = pyqtgraph_plot_item(wdg.plotWdg)
            if plot_item is None:
                return
            # cretae graph
            for i, profile in enumerate(profiles):
                color_item = model1.item(i, 1)
                visibility_item = model1.item(i, 0)
                if color_item is None or visibility_item is None:
                    continue
                tmp_name = self.curveName(profile["layer"], profile["band"], model1)
                # case line outside the raster
                y = np.array(profile["plot_y"], dtype=float)  # replace None value by np.nan
                x = np.array(profile["plot_x"])
                cast("PlotWidget", wdg.plotWdg).plot(
                    x,
                    y,
                    pen=_cosmetic_pen(color_item.data(Qt.ItemDataRole.BackgroundRole), 2),
                    name=tmp_name,
                )
                # set it visible or not
                for item in plot_data_items(plot_item):
                    if item.name() == tmp_name:
                        item.setVisible(visibility_item.data(Qt.ItemDataRole.CheckStateRole))

        elif library == "Matplotlib" and has_mpl:
            for i, profile in enumerate(profiles):
                color_item = model1.item(i, 1)
                visibility_item = model1.item(i, 0)
                if color_item is None or visibility_item is None:
                    continue
                tmp_name = self.curveName(profile["layer"], profile["band"], model1)
                if visibility_item.data(Qt.ItemDataRole.CheckStateRole):
                    cast("MatplotlibAxes", wdg.plotWdg.figure.get_axes()[0]).plot(
                        profile["plot_x"],
                        profile["plot_y"],
                        gid=tmp_name,
                        linewidth=3,
                        visible=True,
                    )
                else:
                    cast("MatplotlibAxes", wdg.plotWdg.figure.get_axes()[0]).plot(
                        profile["plot_x"],
                        profile["plot_y"],
                        gid=tmp_name,
                        linewidth=3,
                        visible=False,
                    )
                self.changeColor(
                    wdg,
                    "Matplotlib",
                    color_item.data(Qt.ItemDataRole.BackgroundRole),
                    tmp_name,
                )
            if profiles and len(profiles[-1]["plot_x"]) > 0:
                self.reScalePlot(wdg, profiles, library)
                wdg.plotWdg.figure.get_axes()[0].set_xbound(0, max(profiles[-1]["plot_x"]))
            wdg.plotWdg.figure.get_axes()[0].redraw_in_frame()
            wdg.plotWdg.draw()

    def findMin(self, values: ProfileSeries) -> float:
        """Return the smallest finite value from a nonempty sample series."""
        return min(float(z) for z in values if z is not None and np.isfinite(z))

    def findMax(self, values: ProfileSeries) -> float:
        """Return the largest finite value from a nonempty sample series."""
        return max(float(z) for z in values if z is not None and np.isfinite(z))

    def plotRangechanged(self, wdg: PTDockWidget, library: str | None) -> None:
        """Synchronize vertical bounds with the PyQtGraph view range."""
        if wdg.plotWdg is None:
            return

        if library == "PyQtGraph":
            plot_item = pyqtgraph_plot_item(wdg.plotWdg)
            if plot_item is None or (view_box := plot_view_box(plot_item)) is None:
                return
            view_range = cast("list[list[float]]", view_box.viewRange())
            wdg.disconnectYSpinbox()
            wdg.sbMaxVal.setValue(view_range[1][1])
            wdg.sbMinVal.setValue(view_range[1][0])
            wdg.connectYSpinbox()

    def reScalePlot(
        self,
        wdg: PTDockWidget,
        profiles: Sequence[Profile] | None,
        library: str | None,
        auto: bool = False,  # noqa: FBT001, FBT002 -- Preserve positional calls to the legacy API.
    ) -> None:  # called when spinbox value changed
        """Apply requested vertical bounds or automatically fit visible profile data."""
        if profiles is None or wdg.plotWdg is None:
            return
        minimumValue = wdg.sbMinVal.value()
        maximumValue = wdg.sbMaxVal.value()

        y_vals = [p["plot_y"] for p in profiles]

        if minimumValue == maximumValue:
            # Automatic mode
            minimumValue = 1000000000
            maximumValue = -1000000000
            for i in range(len(y_vals)):
                if any(z is not None and np.isfinite(z) for z in y_vals[i]):
                    minimumValue = min(self.findMin(y_vals[i]), minimumValue)
                    maximumValue = max(self.findMax(y_vals[i]) + 1, maximumValue)
                    wdg.sbMaxVal.setValue(maximumValue)
                    wdg.sbMinVal.setValue(minimumValue)
                    wdg.sbMaxVal.setEnabled(True)
                    wdg.sbMinVal.setEnabled(True)

        if minimumValue < maximumValue:
            if library == "PyQtGraph":
                plot_item = pyqtgraph_plot_item(wdg.plotWdg)
                if plot_item is None or (view_box := plot_view_box(plot_item)) is None:
                    return
                wdg.disconnectPlotRangechanged()
                if auto:
                    view_box.autoRange(items=plot_data_items(plot_item))
                    wdg.plotRangechanged()
                else:
                    view_box.setYRange(minimumValue, maximumValue, padding=0)
                wdg.connectPlotRangechanged()

            elif library == "Matplotlib" and has_mpl:
                if auto:
                    wdg.sbMaxVal.setValue(wdg.sbMinVal.value())
                    self.reScalePlot(wdg, profiles, library)
                else:
                    wdg.plotWdg.figure.get_axes()[0].set_ybound(minimumValue, maximumValue)
                    wdg.plotWdg.figure.get_axes()[0].redraw_in_frame()
                    wdg.plotWdg.draw()

    def clearData(self, wdg: PTDockWidget, profiles: Sequence[Profile] | None, library: str | None) -> None:
        """Remove plotted curves and reset the vertical-bound controls."""
        if not profiles or wdg.plotWdg is None:
            return

        if library == "PyQtGraph":
            plot_item = pyqtgraph_plot_item(wdg.plotWdg)
            if plot_item is None:
                return
            pitems = plot_data_items(plot_item)
            for item in pitems:
                plot_item.removeItem(item)
            # Mouse callbacks belong to ProfileToolCore, which manages them.

        elif library == "Matplotlib" and has_mpl:
            wdg.plotWdg.figure.get_axes()[0].cla()
            self.manageMatplotlibAxe(wdg.plotWdg.figure.get_axes()[0])
        wdg.sbMaxVal.setEnabled(False)
        wdg.sbMinVal.setEnabled(False)
        wdg.sbMaxVal.setValue(0)
        wdg.sbMinVal.setValue(0)

    def changeColor(self, wdg: PTDockWidget, library: str | None, color1: QColor, name: str) -> None:
        """Apply a source-table color to the curve identified by its plot key."""
        if wdg.plotWdg is None:
            return

        if library == "PyQtGraph":
            pitems = pyqtgraph_plot_item(wdg.plotWdg)
            if pitems is None:
                return
            for item in plot_data_items(pitems):
                if item.name() == name:
                    cast("CurvePen", item).setPen(color1, width=2)

        elif library == "Matplotlib":
            temp1 = wdg.plotWdg.figure.get_axes()[0].get_lines()
            for i in range(len(temp1)):
                if name == str(temp1[i].get_gid()):
                    temp1[i].set_color(
                        (
                            color1.red() / 255.0,
                            color1.green() / 255.0,
                            color1.blue() / 255.0,
                            color1.alpha() / 255.0,
                        )
                    )
                    wdg.plotWdg.figure.get_axes()[0].redraw_in_frame()
                    cast("DrawableCanvas", wdg.plotWdg.figure.canvas).draw()
                    wdg.plotWdg.draw()
                    break

    def changeAttachCurve(self, wdg: PTDockWidget, library: str | None, bool: int | Qt.CheckState, name: str) -> None:  # noqa: A002 -- Preserve the legacy keyword argument.
        """Update a named curve's visibility from its source-table check state."""
        if wdg.plotWdg is None:
            return

        if library == "PyQtGraph":
            pitems = pyqtgraph_plot_item(wdg.plotWdg)
            if pitems is None:
                return
            for item in plot_data_items(pitems):
                if item.name() == name:
                    if bool:
                        item.setVisible(True)
                    else:
                        item.setVisible(False)

        elif library == "Matplotlib":
            temp1 = wdg.plotWdg.figure.get_axes()[0].get_lines()
            for i in range(len(temp1)):
                if name == str(temp1[i].get_gid()):
                    if bool:
                        temp1[i].set_visible(True)
                    else:
                        temp1[i].set_visible(False)
                    wdg.plotWdg.figure.get_axes()[0].redraw_in_frame()
                    cast("DrawableCanvas", wdg.plotWdg.figure.canvas).draw()
                    wdg.plotWdg.draw()

                    break

    def manageMatplotlibAxe(self, axe1: Axes) -> None:
        """Configure chainage units, grid lines and ticks on a Matplotlib axis."""
        unit = self._chainage_unit()
        ax = cast("MatplotlibAxes", axe1)
        ax.set_xlabel(f"Chainage ({unit})")
        ax.grid()
        ax.tick_params(
            axis="both",
            which="major",
            direction="out",
            length=10,
            width=1,
            bottom=True,
            top=False,
            left=True,
            right=False,
        )
        axe1.minorticks_on()
        ax.tick_params(
            axis="both",
            which="minor",
            direction="out",
            length=5,
            width=1,
            bottom=True,
            top=False,
            left=True,
            right=False,
        )

    def outPrint(self, iface: QgisInterface, wdg: PTDockWidget, mdl: QStandardItemModel, library: str | None) -> None:
        """Save the Matplotlib plot as PostScript after selecting an output path."""
        if wdg.plotWdg is None:
            return
        name = "Profile"
        # Postscript file rendering doesn't work properly yet.
        for i in range(mdl.rowCount()):
            checked_item = mdl.item(i, 0)
            name_item = mdl.item(i, 2)
            if checked_item is not None and name_item is not None and checked_item.data(Qt.ItemDataRole.CheckStateRole):
                name = str(name_item.data(Qt.ItemDataRole.EditRole))
        fileName = getSaveFileName(
            iface.mainWindow(), "Save As", "Profile of " + name + ".ps", "PostScript Format (*.ps)"
        )
        if fileName and library == "Matplotlib" and has_mpl:
            cast("ExportFigure", wdg.plotWdg.figure).savefig(str(fileName), bbox_inches="tight")

    def outPDF(self, iface: QgisInterface, wdg: PTDockWidget, mdl: QStandardItemModel, library: str | None) -> None:
        """Save the Matplotlib plot as PDF after selecting an output path."""
        if wdg.plotWdg is None:
            return
        name = "Profile"
        for i in range(mdl.rowCount()):
            checked_item = mdl.item(i, 0)
            name_item = mdl.item(i, 2)
            if checked_item is not None and name_item is not None and checked_item.data(Qt.ItemDataRole.CheckStateRole):
                name = str(name_item.data(Qt.ItemDataRole.EditRole))
                break
        fileName = getSaveFileName(
            iface.mainWindow(),
            "Save As",
            "Profile of " + name + ".pdf",
            "Portable Document Format (*.pdf)",
        )
        if fileName and library == "Matplotlib" and has_mpl:
            cast("ExportFigure", wdg.plotWdg.figure).savefig(str(fileName), bbox_inches="tight")

    def outSVG(self, iface: QgisInterface, wdg: PTDockWidget, mdl: QStandardItemModel, library: str | None) -> None:  # noqa: ARG002 -- Common export signature.
        """Export the current plot as SVG using the selected backend."""
        if wdg.plotWdg is None:
            return
        fileName = getSaveFileName(
            parent=iface.mainWindow(),
            caption="Save As",
            directory=wdg.profiletoolcore.loaddirectory,
            filter="Scalable Vector Graphics (*.svg)",
        )

        if fileName:
            wdg.profiletoolcore.loaddirectory = str(Path(fileName).parent)
            QSettings().setValue("profiletool/lastdirectory", wdg.profiletoolcore.loaddirectory)

            if library == "PyQtGraph":
                # Qt 6 SVG paths are not compatible with the bundled
                # pyqtgraph exporter's coordinate parser. Render through Qt
                # directly so paths, including NoData gaps, remain vector data.
                if not isinstance(wdg.plotWdg, pg.PlotWidget):
                    return
                view = cast("QGraphicsView", wdg.plotWdg)
                generator = QSvgGenerator()
                generator.setFileName(fileName)
                generator.setSize(view.size())
                generator.setViewBox(view.rect())
                painter = QPainter()
                if not painter.begin(generator):
                    message = "Could not open SVG export for painting."
                    raise OSError(message)
                try:
                    view.render(painter)
                finally:
                    painter.end()
            elif library == "Matplotlib" and has_mpl:
                cast("ExportFigure", wdg.plotWdg.figure).savefig(str(fileName), bbox_inches="tight")

    def outPNG(self, iface: QgisInterface, wdg: PTDockWidget, mdl: QStandardItemModel, library: str | None) -> None:  # noqa: ARG002 -- Common export signature.
        """Export the current plot as PNG using the selected backend."""
        if wdg.plotWdg is None:
            return
        fileName = getSaveFileName(
            parent=iface.mainWindow(),
            caption="Save As",
            directory=wdg.profiletoolcore.loaddirectory,
            filter="Portable Network Graphics (*.png)",
        )

        if fileName:
            wdg.profiletoolcore.loaddirectory = str(Path(fileName).parent)
            QSettings().setValue("profiletool/lastdirectory", wdg.profiletoolcore.loaddirectory)

            if library == "PyQtGraph":
                plot_item = pyqtgraph_plot_item(wdg.plotWdg)
                if plot_item is None:
                    return
                exporter = exporters.ImageExporter(plot_item)
                cast("ImageExport", exporter).export(fileName)
            elif library == "Matplotlib" and has_mpl:
                cast("ExportFigure", wdg.plotWdg.figure).savefig(str(fileName), bbox_inches="tight")

    def outCSV(self, iface: QgisInterface, wdg: PTDockWidget, mdl: QStandardItemModel, library: str | None) -> None:  # noqa: ARG002 -- Common export signature.
        """Export plotted source curves as CSV, regardless of graph backend."""
        profiles = wdg.profiletoolcore.profiles
        if not profiles:
            return
        fileName = getSaveFileName(
            parent=iface.mainWindow(),
            caption="Save As",
            directory=wdg.profiletoolcore.loaddirectory,
            filter="Comma-separated values (*.csv)",
        )
        if not fileName:
            return
        series = [
            (
                self.curveName(profile["layer"], profile["band"], mdl),
                profile["plot_x"],
                profile["plot_y"],
            )
            for profile in profiles
        ]
        write_plot_csv(
            fileName,
            series,
            chainage_label=f"Chainage ({self._chainage_unit()})",
            value_label=wdg.plotComboBox.currentText(),
        )
        wdg.profiletoolcore.loaddirectory = str(Path(fileName).parent)
        QSettings().setValue("profiletool/lastdirectory", wdg.profiletoolcore.loaddirectory)

    def outDXF(
        self,
        iface: QgisInterface,
        wdg: PTDockWidget,
        mdl: QStandardItemModel,  # noqa: ARG002 -- Common export signature.
        library: str | None,  # noqa: ARG002 -- Common export signature.
        profiles: Sequence[Profile],
        type: str = "3D",  # noqa: A002 -- Preserve the legacy keyword argument.
    ) -> None:
        """Export 2D or source-coordinate 3D polylines, splitting at missing elevations."""
        fileName = getSaveFileName(
            parent=iface.mainWindow(),
            caption="Save As",
            directory=wdg.profiletoolcore.loaddirectory,
            filter="dxf (*.dxf)",
        )
        if not fileName:
            return
        wdg.profiletoolcore.loaddirectory = str(Path(fileName).parent)
        QSettings().setValue("profiletool/lastdirectory", wdg.profiletoolcore.loaddirectory)
        dxf_engine = cast("DxfEngine", dxf)
        drawing = dxf_engine.drawing(fileName)
        for profile in profiles:
            name = profile["layer"].name()
            drawing.add_layer(name)
            if type == "2D":
                vertices = [
                    (length, elevation, 0) if _valid_elevation(elevation) else None
                    for length, elevation in zip(profile["l"], profile["z"])
                ]
            else:
                vertices = [
                    (x, y, elevation) if _valid_elevation(elevation) else None
                    for x, y, elevation in zip(profile["x"], profile["y"], profile["z"])
                ]
            # NoData gaps must not become fictitious connecting lines.
            part: list[tuple[float, float, float]] = []
            for vertex in [*vertices, None]:
                if vertex is None:
                    if len(part) >= 2:
                        drawing.add(dxf_engine.polyline(part, color=7, layer=name))
                    part = []
                else:
                    part.append(vertex)
        drawing.save()
