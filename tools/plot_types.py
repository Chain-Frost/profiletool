"""Qt contracts for the additional scene signals exposed by PyQtGraph."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.axes import Axes
    from qgis.PyQt.QtCore import QPointF, pyqtBoundSignal
    from qgis.PyQt.QtGui import QColor, QPen
    from qgis.PyQt.QtWidgets import QGraphicsItem, QGraphicsScene

    from .. import pyqtgraph as pg
    from .profilers import ProfileSeries

    class ExportFigure(Protocol):
        """Matplotlib figure operations consumed by the file exporters."""

        def savefig(self, fname: str, *, bbox_inches: str) -> None:
            """Write a figure to the chosen filename with the requested bounds."""
            ...

        def get_axes(self) -> list[Axes]:
            """Return the figure's axes in their existing order."""
            ...

    class CursorLine(pg.InfiniteLine):
        """Numeric cursor positioning consumed by the profile callbacks."""

        def setPos(self, pos: float | QPointF | Sequence[float]) -> None:  # noqa: N802 -- Existing PyQtGraph API.
            """Place a cursor at a scalar chainage/elevation or a point."""
            ...

    class CursorLabel(pg.TextItem):
        """Text-label update method consumed by the profile callbacks."""

        def setText(self, text: str, color: QColor | tuple[int, int, int] | str | None = None) -> None:  # noqa: N802 -- Existing PyQtGraph API.
            """Replace cursor text, optionally updating its color."""
            ...

    class PlotViewBox(pg.ViewBox):
        """View box with the bound range signal used by the dock controls."""

        sigRangeChanged: pyqtBoundSignal  # noqa: N815 -- Existing PyQtGraph signal API.

        def mapSceneToView(self, obj: QPointF) -> QPointF:  # noqa: N802 -- Existing PyQtGraph API.
            """Map a scene point into the plot's data coordinates."""
            ...

        def autoRange(  # noqa: N802 -- Existing PyQtGraph API.
            self,
            padding: float | None = None,
            items: Sequence[QGraphicsItem] | None = None,
            item: QGraphicsItem | None = None,
        ) -> None:
            """Fit the view to the specified graphics items."""
            ...

        def setYRange(  # noqa: N802 -- Existing PyQtGraph API.
            self,
            min: float,  # noqa: A002 -- External keyword argument.
            max: float,  # noqa: A002 -- External keyword argument.
            padding: float | None = None,
            update: bool = True,  # noqa: FBT001, FBT002 -- Preserve the external method signature.
        ) -> None:
            """Apply numeric vertical bounds and optional relative padding."""
            ...

    class PlotItem(pg.PlotItem):
        """Concrete graphics-item methods used by the plugin's profile plot."""

        def getViewBox(self) -> PlotViewBox | None:  # noqa: N802 -- Existing PyQtGraph API.
            """Return the view that maps scene and data coordinates."""
            ...

        def allChildItems(self, root: QGraphicsItem | None = None) -> list[QGraphicsItem]:  # noqa: N802 -- Existing PyQtGraph API.
            """Return descendant graphics items under the selected root."""
            ...

        def addItem(self, item: QGraphicsItem, *args: object, **kwargs: object) -> None:  # noqa: N802 -- Existing PyQtGraph API.
            """Attach a graphics item and forward its supported view options."""
            ...

        def removeItem(self, item: QGraphicsItem) -> None:  # noqa: N802 -- Existing PyQtGraph API.
            """Remove a graphics item from this plot."""
            ...

    class PlotWidget(pg.PlotWidget):
        """PlotWidget methods otherwise exposed through dynamic forwarding."""

        def getPlotItem(self) -> PlotItem | None:  # noqa: N802 -- Existing PyQtGraph API.
            """Return the owned plot item unless the widget was closed."""
            ...

        def scene(self) -> PlotScene | None:
            """Return the graphics scene containing this plot."""
            ...

        def addItem(self, *args: QGraphicsItem) -> None:  # noqa: N802 -- Existing PyQtGraph API.
            """Forward graphics-item insertion to the owned plot."""
            ...

        def plot(self, x: ProfileSeries, y: ProfileSeries, *, pen: QPen, name: str) -> pg.PlotDataItem:
            """Create a named profile curve with explicit sample arrays and pen."""
            ...

    class DockPlotItem(Protocol):
        """Plot-item methods forwarded by PlotWidget and used by dock controls."""

        def getViewBox(self) -> PlotViewBox | None:  # noqa: N802 -- Existing PyQtGraph API.
            """Return the plot's view box, if it is still available."""
            ...

        def allChildItems(self) -> list[QGraphicsItem]:  # noqa: N802 -- Existing PyQtGraph API.
            """Return all descendant graphics items in the plot."""
            ...

    class PlotScene(QGraphicsScene):
        """Graphics scene with the actual bound signals used for plot tracking."""

        sigMouseMoved: pyqtBoundSignal  # noqa: N815 -- Existing PyQtGraph signal API.
        sigMouseClicked: pyqtBoundSignal  # noqa: N815 -- Existing PyQtGraph signal API.
