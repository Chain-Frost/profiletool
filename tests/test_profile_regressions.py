"""Focused regression tests without requiring a desktop QGIS installation."""

from __future__ import annotations

import importlib.util
import math
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def profilers():
    return _load("_profile_math_regression", ROOT / "tools" / "profilers.py")


def test_grade_two_points(profilers):
    x, grade = profilers.slopes_pct({"l": [0, 10], "z": [2, 3]})
    np.testing.assert_allclose(x, [0, 10])
    np.testing.assert_allclose(grade, [10, 10])


def test_missing_elevations_are_not_fabricated_zero_slopes(profilers):
    _, grade = profilers.slopes_pct({"l": [0, 1, 2, 3, 4], "z": [2, 3, np.nan, 6, 7]})
    assert np.isfinite(grade[0])
    assert np.isnan(grade[1:4]).all()
    assert np.isfinite(grade[4])


def test_duplicate_chainage_is_not_assigned_zero_slope(profilers):
    _, grade = profilers.slopes_pct({"l": [0, 1, 1, 2], "z": [0, 2, 2, 4]})
    assert np.isnan(grade[1:3]).all()
    assert grade[0] == pytest.approx(200)
    assert grade[3] == pytest.approx(200)


def test_single_or_empty_profiles(profilers):
    for samples in ([], [0]):
        x, grades = profilers.slopes_pct({"l": samples, "z": samples})
        assert len(x) == len(grades)
        if samples:
            assert np.isnan(grades[0])


@pytest.fixture
def reader_module(monkeypatch):
    # Stub the minimal PyQGIS surface required to import the sampling module.
    qgis = types.ModuleType("qgis")
    qgis.__path__ = []
    core = types.ModuleType("qgis.core")
    qt = types.ModuleType("qgis.PyQt")
    qt.__path__ = []
    qtcore = types.ModuleType("qgis.PyQt.QtCore")
    qtcore.QCoreApplication = SimpleNamespace(translate=lambda _context, msg: msg)

    class Point:
        def __init__(self, x, y=None) -> None:
            self._x, self._y = (x.x(), x.y()) if y is None else (x, y)

        def x(self):
            return self._x

        def y(self):
            return self._y

    class ProjectCrs:
        def __init__(self, geographic=False) -> None:
            self.geographic = geographic

        def isGeographic(self):
            return self.geographic

        def mapUnits(self):
            return "feet" if not self.geographic else "degrees"

    project = SimpleNamespace(
        crs=ProjectCrs,
        transformContext=lambda: None,
        ellipsoid=lambda: "WGS84",
    )

    class DistanceArea:
        def setSourceCrs(self, crs, context):
            pass

        def setEllipsoid(self, ellipsoid):
            pass

        def measureLine(self, start, end):
            return math.hypot(end.x() - start.x(), end.y() - start.y()) * 111_000.0

    # Explicit PyQGIS imports should be importable without QGIS desktop.
    # Tests that exercise their geometry behaviour replace these stubs.
    core.QgsCoordinateTransform = object
    core.QgsFeatureRequest = object
    core.QgsGeometry = object
    core.QgsDistanceArea = DistanceArea
    core.QgsPointXY = Point
    core.QgsProject = SimpleNamespace(instance=lambda: project)
    core.Qgis = SimpleNamespace(DistanceUnit=SimpleNamespace(Meters="metres"))
    core.QgsUnitTypes = SimpleNamespace(fromUnitToUnitFactor=lambda source, _target: 0.3048 if source == "feet" else 1.0)
    qgis.core = core
    qgis.gui = types.ModuleType("qgis.gui")
    qgis.utils = SimpleNamespace(iface=None)
    qgis.PyQt = qt
    qt.QtCore = qtcore
    for name, value in [
        ("qgis", qgis),
        ("qgis.core", core),
        ("qgis.gui", qgis.gui),
        ("qgis.PyQt", qt),
        ("qgis.PyQt.QtCore", qtcore),
    ]:
        monkeypatch.setitem(sys.modules, name, value)

    package = types.ModuleType("_profile_tool_test")
    package.__path__ = [str(ROOT / "tools")]
    utils = types.ModuleType("_profile_tool_test.utils")
    utils.isProfilable = lambda _layer: False
    monkeypatch.setitem(sys.modules, package.__name__, package)
    monkeypatch.setitem(sys.modules, utils.__name__, utils)
    module = _load("_profile_tool_test.dataReaderTool", ROOT / "tools" / "dataReaderTool.py")
    return module, project, ProjectCrs


def test_project_crs_controls_chainage_units(reader_module):
    reader, project, Crs = reader_module

    class Provider:
        def sample(self, pt, band):
            return float(pt.x()), True

    class Layer:
        RasterLayer = 1
        PluginLayer = 2
        MeshLayer = 3

        def type(self):
            return self.RasterLayer

        def rasterUnitsPerPixelX(self):
            return 2

        def rasterUnitsPerPixelY(self):
            return 2

        def dataProvider(self):
            return Provider()

        def crs(self):
            return "source-layer-crs"

    class MapTool:
        def toLayerCoordinates(self, layer, point):
            return reader.QgsPointXY(point.x() * 2, point.y() * 2)

    class Interface:
        def mainWindow(self):
            return self

        def statusBar(self):
            return self

        def showMessage(self, value):
            pass

    for geographic, expected_end in [(True, 10.0), (False, 3.048)]:
        project.crs = lambda geographic=geographic: Crs(geographic)
        result = reader.DataReaderTool().dataRasterReaderTool(
            Interface(),
            MapTool(),
            {"layer": Layer(), "band": 1},
            [[0.0, 0.0], [10.0, 0.0]],
            "full",
        )
        assert result["l"][-1] == pytest.approx(expected_end)
        assert result["x"][-1] == pytest.approx(20.0)
        assert len(result["l"]) == 11
        assert result["crs"] == "source-layer-crs"
        assert result["l_slope"][-1] == pytest.approx(1_110_000 if geographic else 3.048)


def test_valid_zero_is_distinct_from_missing_sample(reader_module):
    reader, _, _ = reader_module

    class Provider:
        def sample(self, point, band):
            return (0.0, True) if point.x() == 0 else (0.0, False)

    class Layer:
        RasterLayer = 1
        PluginLayer = 2
        MeshLayer = 3

        def type(self):
            return self.RasterLayer

        def dataProvider(self):
            return Provider()

    tool = reader.DataReaderTool()
    tool.profiles = {"layer": Layer(), "band": 1}
    tool._status_update = lambda _pct: None
    values = tool._extractZValues([0, 1], [0, 0])
    assert values[0] == 0.0
    assert math.isnan(values[1])


def test_vector_chainage_dedup_keeps_closest_point(reader_module):
    reader, _, _ = reader_module
    array = np.array(
        [
            [1, 1, 0, 4, 0, 10, 1, 0, None],
            [1.004, 1, 0, 0.2, 0, 20, 1, 0, None],
            [2, 2, 0, 0.1, 0, 30, 2, 0, None],
        ],
        dtype=object,
    )
    deduped = reader.DataReaderTool().removeDuplicateLenght(array)
    assert len(deduped) == 2
    assert list(deduped[:, 5]) == [20, 30]


def test_geographic_chainage_dedup_tolerance(reader_module):
    reader, project, Crs = reader_module
    project.crs = lambda: Crs(True)
    assert reader.DataReaderTool._project_chainage_tolerance() == pytest.approx(1e-8)
    array = np.array(
        [
            [0.1, 1, 0, 0.1, 0, 10, 1, 0, None],
            [0.10001, 1, 0, 0.2, 0, 20, 1, 0, None],
        ],
        dtype=object,
    )
    assert len(reader.DataReaderTool().removeDuplicateLenght(array)) == 2


def test_only_clicked_part_of_multipart_feature(reader_module, monkeypatch):
    reader, _, _ = reader_module
    core = sys.modules["qgis.core"]

    class Geometry:
        def __init__(self, parts, multi=False) -> None:
            self.parts, self.multi = parts, multi

        def isMultipart(self):
            return self.multi

        def asMultiPolyline(self):
            return self.parts

        @staticmethod
        def fromPointXY(point) -> SimpleNamespace:
            return SimpleNamespace(point=point)

        @staticmethod
        def fromPolylineXY(part) -> Geometry:
            return Geometry([part])

        def distance(self, point_geom):
            return min(math.hypot(p.x() - point_geom.point.x(), p.y() - point_geom.point.y()) for p in self.parts[0])

    class Feature:
        def __init__(self, original=None) -> None:
            self.geom = original.geometry() if original else None

        def geometry(self):
            return self.geom

        def setGeometry(self, geometry):
            self.geom = geometry

    core.QgsFeature = Feature
    core.QgsGeometry = Geometry
    for name in (
        "QgsFeatureRequest",
        "QgsMapLayer",
        "QgsRectangle",
        "QgsSpatialIndex",
        "QgsVectorLayer",
        "QgsWkbTypes",
    ):
        setattr(core, name, object)
    widgets = types.ModuleType("qgis.PyQt.QtWidgets")
    widgets.QMessageBox = object
    monkeypatch.setitem(sys.modules, widgets.__name__, widgets)
    sys.modules["qgis.PyQt"].QtWidgets = widgets
    selected = _load("_profile_tool_test.selectlinetool", ROOT / "tools" / "selectlinetool.py")
    p = reader.QgsPointXY
    feature = Feature()
    feature.setGeometry(
        Geometry(
            [
                [p(0, 0), p(10, 0)],
                [p(0, 10), p(10, 10)],
            ],
            multi=True,
        )
    )
    result = selected.SelectLineTool.select_closest_part(feature, p(0, 9.9))
    assert result is not feature
    assert result.geometry().parts[0][0].y() == 10
    assert feature.geometry().isMultipart()


def test_geographic_grade_uses_metre_distance_without_changing_degree_axis(profilers):
    profile = {
        "l": [0, 0.01],
        "l_slope": [0, 1000],
        "z": [10, 20],
    }
    x, grades = profilers.slopes_pct(profile)
    np.testing.assert_allclose(x, [0, 0.01])
    np.testing.assert_allclose(grades, [1, 1])
