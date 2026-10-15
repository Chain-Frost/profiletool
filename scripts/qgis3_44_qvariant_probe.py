"""Diagnostic: test Qt5 without the bundled GraphicsObject.itemChange override.

Do not use this as a production fix; parent/scene lifecycle notifications and
view-range invalidation must be preserved and verified separately.
"""

from __future__ import annotations

import sys

import pytest

from profiletool.pyqtgraph.graphicsItems.GraphicsObject import GraphicsObject

if __name__ == "__main__":
    saved_override = GraphicsObject.itemChange
    del GraphicsObject.itemChange
    print("Diagnostic only: temporarily removed GraphicsObject.itemChange override", flush=True)
    try:
        result = pytest.main([
            "-s",
            "-q",
            "/tests_directory/profiletool/tests/test_qgis_layer_lifecycle.py",
        ])
    finally:
        GraphicsObject.itemChange = saved_override
    sys.exit(int(result))
