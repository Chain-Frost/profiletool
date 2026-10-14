"""Qt contracts for the additional scene signals exposed by PyQtGraph."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from qgis.PyQt.QtCore import pyqtBoundSignal
    from qgis.PyQt.QtWidgets import QGraphicsItem, QGraphicsScene

    from .. import pyqtgraph as pg

    class PlotViewBox(pg.ViewBox):
        """View box with the bound range signal used by the dock controls."""

        sigRangeChanged: pyqtBoundSignal  # noqa: N815 -- Existing PyQtGraph signal API.

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
