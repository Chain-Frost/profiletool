"""Focused regression tests without requiring a desktop QGIS installation."""

from __future__ import annotations

import importlib.util
import math
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Protocol, cast

import numpy as np
import pytest

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from profiletool.tools.profilers import ProfileData, ProfileSeries


class _ProfileMath(Protocol):
    """Math functions exposed by the dynamically loaded regression module."""

    def slopes_pct(self, p: ProfileData) -> tuple[ProfileSeries, NDArray[np.float64]]: ...

    def slopes_deg(self, p: ProfileData) -> tuple[ProfileSeries, NDArray[np.float64]]: ...


class _Coordinates(Protocol):
    """Coordinate access used when copying points in the headless fixture."""

    def x(self) -> float: ...

    def y(self) -> float: ...


@dataclass
class _PointGeometry:
    """Point wrapper consumed by the multipart geometry fixture."""

    point: _Coordinates


class _CRSFactory(Protocol):
    """Construct the fixture's CRS with an explicit geographic-mode flag."""

    def __call__(self, *, geographic: bool = False) -> object: ...


def _translate(_context: str, message: str) -> str:
    """Keep translated text unchanged in the headless Qt fixture."""
    return message


def _unit_factor(source: str, _target: str) -> float:
    """Convert the fixture's foot distances to metres."""
    return {"feet": 0.3048, "survey-feet": 1200 / 3937}.get(source, 1.0)


def _not_profilable(_layer: object) -> bool:
    """Disable plugin-layer sampling in the headless reader fixture."""
    return False


def _ignore_progress(_percentage: int) -> None:
    """Discard progress callbacks in headless sampling tests."""


def _same_point(point: object) -> object:
    """Model QgsGeometry.fromPointXY as an identity mapping for tests."""
    return point


ROOT = Path(__file__).resolve().parents[1]
ReaderFixture = tuple[types.ModuleType, SimpleNamespace, _CRSFactory]


def _load(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec
    assert spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def profilers() -> _ProfileMath:
    return cast(_ProfileMath, _load("_profile_math_regression", ROOT / "tools" / "profilers.py"))


def test_grade_two_points(profilers: _ProfileMath) -> None:
    x, grade = profilers.slopes_pct({"l": [0, 10], "z": [2, 3]})
    np.testing.assert_allclose(x, [0, 10])
    np.testing.assert_allclose(grade, [10, 10])


def test_missing_elevations_are_not_fabricated_zero_slopes(profilers: _ProfileMath) -> None:
    _, grade = profilers.slopes_pct({"l": [0, 1, 2, 3, 4], "z": [2, 3, np.nan, 6, 7]})
    assert np.isfinite(grade[0])
    assert np.isnan(grade[1:4]).all()
    assert np.isfinite(grade[4])


def test_duplicate_chainage_is_not_assigned_zero_slope(profilers: _ProfileMath) -> None:
    _, grade = profilers.slopes_pct({"l": [0, 1, 1, 2], "z": [0, 2, 2, 4]})
    assert np.isnan(grade[1:3]).all()
    assert grade[0] == pytest.approx(200)
    assert grade[3] == pytest.approx(200)


def test_single_or_empty_profiles(profilers: _ProfileMath) -> None:
    for samples in ([], [0]):
        x, grades = profilers.slopes_pct({"l": samples, "z": samples})
        assert len(x) == len(grades)
        if samples:
            assert np.isnan(grades[0])


@pytest.fixture
def reader_module(monkeypatch: pytest.MonkeyPatch) -> ReaderFixture:
    # Stub the minimal PyQGIS surface required to import the sampling module.
    qgis = types.ModuleType("qgis")
    qgis.__path__ = []
    core = types.ModuleType("qgis.core")
    qt = types.ModuleType("qgis.PyQt")
    qt.__path__ = []
    qtcore = types.ModuleType("qgis.PyQt.QtCore")
    qtcore.__dict__["QCoreApplication"] = SimpleNamespace(translate=_translate)

    class Point:
        def __init__(self, x: float | _Coordinates, y: float | None = None) -> None:
            if isinstance(x, (int, float)):
                if y is None:
                    msg = "Numeric point construction requires both coordinates"
                    raise ValueError(msg)
                self._x, self._y = float(x), y
            else:
                self._x, self._y = x.x(), x.y()

        def x(self) -> float:
            return self._x

        def y(self) -> float:
            return self._y

    class ProjectCrs:
        def __init__(self, *, geographic: bool = False) -> None:
            self.geographic = geographic

        def isGeographic(self) -> bool:
            return self.geographic

        def mapUnits(self) -> str:
            return "feet" if not self.geographic else "degrees"

    project = SimpleNamespace(
        crs=ProjectCrs,
        transformContext=lambda: None,
        ellipsoid=lambda: "WGS84",
    )

    class DistanceArea:
        def setSourceCrs(self, crs: object, context: object) -> None:
            pass

        def setEllipsoid(self, ellipsoid: str) -> None:
            pass

        def measureLine(self, start: _Coordinates, end: _Coordinates) -> float:
            return math.hypot(end.x() - start.x(), end.y() - start.y()) * 111_000.0

    # Explicit PyQGIS imports should be importable without QGIS desktop.
    # Tests that exercise their geometry behaviour replace these stubs.
    core.__dict__.update(
        QgsCoordinateTransform=object,
        QgsFeatureRequest=object,
        QgsGeometry=object,
        QgsDistanceArea=DistanceArea,
        QgsPointXY=Point,
        QgsProject=SimpleNamespace(instance=lambda: project),
        Qgis=SimpleNamespace(
            DistanceUnit=SimpleNamespace(Meters="metres"),
            LayerType=SimpleNamespace(Raster=1, Plugin=2, Mesh=3),
        ),
        QgsUnitTypes=SimpleNamespace(fromUnitToUnitFactor=_unit_factor),
    )
    gui = types.ModuleType("qgis.gui")
    qgis.__dict__.update(core=core, gui=gui, utils=SimpleNamespace(iface=None), PyQt=qt)
    qt.__dict__["QtCore"] = qtcore
    for name, value in [
        ("qgis", qgis),
        ("qgis.core", core),
        ("qgis.gui", gui),
        ("qgis.PyQt", qt),
        ("qgis.PyQt.QtCore", qtcore),
    ]:
        monkeypatch.setitem(sys.modules, name, value)

    package = types.ModuleType("_profile_tool_test")
    package.__path__ = [str(ROOT / "tools")]
    utils = types.ModuleType("_profile_tool_test.utils")
    utils.__dict__["isProfilable"] = _not_profilable
    monkeypatch.setitem(sys.modules, package.__name__, package)
    monkeypatch.setitem(sys.modules, utils.__name__, utils)
    module = _load("_profile_tool_test.dataReaderTool", ROOT / "tools" / "dataReaderTool.py")
    return module, project, ProjectCrs


def test_project_crs_controls_chainage_units(reader_module: ReaderFixture) -> None:
    reader, project, crs_factory = reader_module

    class Provider:
        def sample(self, pt: _Coordinates, _band: int) -> tuple[float, bool]:
            return float(pt.x()), True

    class Layer:
        RasterLayer = 1
        PluginLayer = 2
        MeshLayer = 3

        def type(self) -> int:
            return self.RasterLayer

        def rasterUnitsPerPixelX(self) -> int:
            return 2

        def rasterUnitsPerPixelY(self) -> int:
            return 2

        def dataProvider(self) -> Provider:
            return Provider()

        def crs(self) -> str:
            return "source-layer-crs"

    class MapTool:
        def toLayerCoordinates(self, _layer: object, point: _Coordinates) -> _Coordinates:
            return reader.QgsPointXY(point.x() * 2, point.y() * 2)

    class Interface:
        def mainWindow(self) -> Interface:
            return self

        def statusBar(self) -> Interface:
            return self

        def showMessage(self, value: str) -> None:
            pass

    for geographic, expected_end in [(True, 10.0), (False, 10.0)]:
        project.crs = lambda geographic=geographic: crs_factory(geographic=geographic)
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


def test_valid_zero_is_distinct_from_missing_sample(reader_module: ReaderFixture) -> None:
    reader, _, _ = reader_module

    class Provider:
        def sample(self, point: _Coordinates, _band: int) -> tuple[float, bool]:
            return (0.0, True) if point.x() == 0 else (0.0, False)

    class Layer:
        RasterLayer = 1
        PluginLayer = 2
        MeshLayer = 3

        def type(self) -> int:
            return self.RasterLayer

        def dataProvider(self) -> Provider:
            return Provider()

    tool = reader.DataReaderTool()
    tool.profiles = {"layer": Layer(), "band": 1}
    tool._status_update = _ignore_progress
    values = tool._extractZValues([0, 1], [0, 0])
    assert values[0] == 0.0
    assert math.isnan(values[1])


def test_vector_chainage_dedup_keeps_closest_point(reader_module: ReaderFixture) -> None:
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


def test_geographic_chainage_dedup_tolerance(reader_module: ReaderFixture) -> None:
    reader, project, crs_factory = reader_module
    project.crs = lambda: crs_factory(geographic=True)
    assert reader.DataReaderTool._project_chainage_tolerance() == pytest.approx(1e-8)
    array = np.array(
        [
            [0.1, 1, 0, 0.1, 0, 10, 1, 0, None],
            [0.10001, 1, 0, 0.2, 0, 20, 1, 0, None],
        ],
        dtype=object,
    )
    assert len(reader.DataReaderTool().removeDuplicateLenght(array)) == 2


@pytest.mark.parametrize(("unit", "factor"), [("metres", 1.0), ("feet", 0.3048), ("survey-feet", 1200 / 3937)])
def test_native_project_units_keep_separate_grade_distances(
    reader_module: ReaderFixture, unit: str, factor: float
) -> None:
    """Display native units while preserving the established metre-based grade distances."""
    reader, project, _factory = reader_module
    project.crs = lambda: SimpleNamespace(isGeographic=lambda: False, mapUnits=lambda: unit)
    points = [reader.QgsPointXY(0, 0), reader.QgsPointXY(12, 0)]
    assert reader.DataReaderTool.project_distance_scale() == 1.0
    assert reader.DataReaderTool._slope_distances(points, [0.0, 12.0]) == pytest.approx([0.0, 12 * factor])
    assert reader.DataReaderTool._project_chainage_tolerance() == pytest.approx(0.01 / factor)


def test_only_clicked_part_of_multipart_feature(reader_module: ReaderFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    reader, _, _ = reader_module
    core = sys.modules["qgis.core"]

    class Geometry:
        def __init__(self, parts: list[list[_Coordinates]], *, multi: bool = False) -> None:
            self.parts, self.multi = parts, multi

        def isMultipart(self) -> bool:
            return self.multi

        def asMultiPolyline(self) -> list[list[_Coordinates]]:
            return self.parts

        @staticmethod
        def fromPointXY(point: _Coordinates) -> _PointGeometry:
            return _PointGeometry(point)

        @staticmethod
        def fromPolylineXY(part: list[_Coordinates]) -> Geometry:
            return Geometry([part])

        def distance(self, point_geom: _PointGeometry) -> float:
            return min(math.hypot(p.x() - point_geom.point.x(), p.y() - point_geom.point.y()) for p in self.parts[0])

    class Feature:
        def __init__(self, original: Feature | None = None) -> None:
            self.geom = original.geometry() if original else None

        def geometry(self) -> Geometry | None:
            return self.geom

        def setGeometry(self, geometry: Geometry) -> None:
            self.geom = geometry

    core.__dict__.update(QgsFeature=Feature, QgsGeometry=Geometry)
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
    widgets.__dict__["QMessageBox"] = object
    monkeypatch.setitem(sys.modules, widgets.__name__, widgets)
    sys.modules["qgis.PyQt"].__dict__["QtWidgets"] = widgets
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
    original_geometry = feature.geometry()
    assert original_geometry is not None
    assert original_geometry.isMultipart()


def test_geographic_grade_uses_metre_distance_without_changing_degree_axis(profilers: _ProfileMath) -> None:
    profile: ProfileData = {
        "l": [0, 0.01],
        "l_slope": [0, 1000],
        "z": [10, 20],
    }
    x, grades = profilers.slopes_pct(profile)
    np.testing.assert_allclose(x, [0, 0.01])
    np.testing.assert_allclose(grades, [1, 1])


@pytest.mark.parametrize("scalar", ["12.5", None, "invalid"])
def test_mesh_sampling_uses_the_supplied_interface(
    reader_module: ReaderFixture, monkeypatch: pytest.MonkeyPatch, scalar: str | None
) -> None:
    """Mesh identify must use the reader's canvas rather than global iface state."""
    reader, _project, _crs = reader_module
    canvas = object()
    received_canvases: list[object] = []

    class Identifier:
        IdentifyMode = SimpleNamespace(DefaultQgsSetting=0)
        Type = SimpleNamespace(MeshLayer=3)

        def __init__(self, selected_canvas: object) -> None:
            received_canvases.append(selected_canvas)

        def identify(self, *_args: object) -> list[SimpleNamespace]:
            return [SimpleNamespace(mAttributes={"Scalar Value": scalar})]

    monkeypatch.setattr(sys.modules["qgis.gui"], "QgsMapToolIdentify", Identifier, raising=False)
    monkeypatch.setattr(reader, "QgsGeometry", SimpleNamespace(fromPointXY=_same_point))
    tool = reader.DataReaderTool()
    tool.profiles = {"layer": SimpleNamespace(type=lambda: 3), "band": 0}
    tool.iface = SimpleNamespace(mapCanvas=lambda: canvas)
    tool._status_update = _ignore_progress
    values = tool._extractZValues([1.0], [2.0])
    if scalar == "12.5":
        assert values == [12.5]
    else:
        assert len(values) == 1
        assert math.isnan(values[0])
    assert received_canvases == [canvas]
