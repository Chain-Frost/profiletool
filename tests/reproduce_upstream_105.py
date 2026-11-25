"""Reproduce the reported R12 layer-name problem using the exact v4.3.9 exporter."""
import re
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from qgis.core import QgsVectorLayer
from qgis.testing import start_app
from qgis.testing.mocked import get_iface

from profiletool.tools.plottingtool import PlottingTool

app = start_app()
layer = QgsVectorLayer("Point?crs=EPSG:28350", "RASTER-0.200", "memory")
assert layer.isValid()
profile = {"layer": layer, "l": [0.0, 1.0], "z": [0.0, 2.0], "x": [10.0, 11.0], "y": [20.0, 21.0]}
with tempfile.TemporaryDirectory() as tmp:
    dock = SimpleNamespace(profiletoolcore=SimpleNamespace(loaddirectory=tmp))
    for mode in ("2D", "3D"):
        out = Path(tmp) / f"reported-{mode}.dxf"
        with patch("profiletool.tools.plottingtool.getSaveFileName", return_value=str(out)):
            PlottingTool().outDXF(get_iface(), dock, None, None, [profile], type=mode)
        lines = out.read_text(encoding="cp1252").splitlines()
        tags = [(int(code), value.strip()) for code, value in zip(lines[::2], lines[1::2], strict=True)]
        version = tags[tags.index((9, "$ACADVER")) + 1]
        names = [tags[i+1][1] for i, pair in enumerate(tags[:-1]) if pair == (0, "LAYER") and tags[i+1][0] == 2]
        assert version == (1, "AC1009"), version
        assert "RASTER-0.200" in names, names
        assert not re.fullmatch(r"[A-Z0-9_$-]{1,31}", "RASTER-0.200")
        print(f"{mode}: {version}; layer names {names}; invalid R12 symbol RASTER-0.200 reproduced")
print("Reproduced file-format nonconformance; actual AutoCAD opening remains untested.")
