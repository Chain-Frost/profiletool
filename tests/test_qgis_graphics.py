"""Real Qt regression for scene attachment and bounds invalidation."""

from __future__ import annotations

import sys
from pathlib import Path
from types import TracebackType
from typing import cast

import pytest

pytest.importorskip("qgis.core", reason="Requires the QGIS environment")

from qgis.PyQt.QtGui import QTransform
from qgis.PyQt.QtWidgets import QGraphicsItem
from qgis.testing import start_app

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from profiletool import pyqtgraph as pg


def test_graphics_parent_scene_and_bounds_notifications_are_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    """QGIS 3.44/PyQt5 must not lose parent attachment or plot auto-range updates."""
    callback_errors: list[BaseException] = []

    def capture_callback_error(
        _kind: type[BaseException], value: BaseException, _traceback: TracebackType | None
    ) -> None:
        callback_errors.append(value)

    monkeypatch.setattr(sys, "excepthook", capture_callback_error)
    start_app()
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
        cast("QGraphicsItem", curve).setPos(12.0, 4.0)
        assert curve.pos().x() == 12.0
        assert curve.pos().y() == 4.0
        assert curve in bounds_changed

        # QGIS 3/PyQt5 must invalidate bounds for explicit transforms, too.
        bounds_changed.clear()
        cast("QGraphicsItem", curve).setTransform(QTransform.fromScale(2.0, 1.5))
        assert curve in bounds_changed
        bounds_changed.clear()
        curve.resetTransform()
        assert curve in bounds_changed

        plot.removeItem(curve)
        assert curve.scene() is None
        assert not callback_errors, [str(error) for error in callback_errors]
    finally:
        plot.close()

def test_parentless_curve_tracks_scene_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Direct scene attachment, transfer and removal update view registration."""
    start_app()
    first = pg.GraphicsView()
    second = pg.GraphicsView()
    curve = pg.PlotCurveItem([0.0, 1.0], [2.0, 3.0])
    notifications: list[None] = []
    previous_transform_changed = curve.viewTransformChanged

    def transform_changed() -> None:
        notifications.append(None)
        previous_transform_changed()

    monkeypatch.setattr(curve, "viewTransformChanged", transform_changed)
    try:
        first.addItem(curve)
        assert curve.parentItem() is None
        assert curve.getViewBox() is first
        notifications.clear()
        first.sigDeviceTransformChanged.emit(first)
        assert notifications == [None]

        second.addItem(curve)
        assert curve.parentItem() is None
        assert curve.getViewBox() is second
        notifications.clear()
        first.sigDeviceTransformChanged.emit(first)
        assert not notifications
        second.sigDeviceTransformChanged.emit(second)
        assert notifications == [None]

        second.removeItem(curve)
        assert curve.scene() is None
        assert curve.getViewBox() is None
        notifications.clear()
        second.sigDeviceTransformChanged.emit(second)
        assert not notifications
    finally:
        if curve.scene() is not None:
            curve.scene().removeItem(curve)
        first.close()
        second.close()
