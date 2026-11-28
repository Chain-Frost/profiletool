# Profile Tool ![image](https://github.com/PANOimagen/profiletool/blob/master/icons/profileIcon.png?raw=true)

This tool plots profile lines from raster layers or point vector layer with elevation field. 
Supports multiple lines as well as graph export to svg, pdf, png or csv file. 
Supports 3D polyline export to dxf. 

**Authors:** Borys Jurgiel - Patrice Verchere - Etienne Tourigny - Javier Becerra

**Current mantainer:** PANOimagen S.L.

**email:** *javier@panoimagen.com*

Fork of etiennesky/profiletool QGis plugin. We add support to select all 
the features in a Layer and visualization of slope profile in addition to height profile. 
This work has been partially funded by the C.A. La Rioja

**Profile Tool license:**

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

## Sampling and compatibility

Profile Tool supports QGIS 3.40 and later (including Qt5 and Qt6 builds). Projected chainage uses native map units and assumes elevation uses the same linear unit when computing grades. Geographic projects show angular chainage and use geodesic metre distances for slope; elevations are assumed to be metres. Missing or invalid elevation samples remain gaps rather than zero. Whole-layer line mode preserves provider order and may concatenate disconnected features.

Graph CSV export works in both plotting backends. Each source has a separate chainage/value pair, with missing samples blank. Profile coordinate tables can also be copied as tab-separated text. DXF export splits polylines at NoData gaps.

## Build and tests

Run `make zip` to create `profiletool.zip` with the required top-level plugin folder. Install it through QGIS Plugin Manager. `make deploy QGIS_PLUGIN_DIR=/path/to/plugins` deploys into a specified development profile. Use a disposable profile for testing.

Install development dependencies with `python -m pip install -r requirements-dev.txt`. Run the headless regression suite with `python -m pytest -q tests/test_profile_regressions.py tests/test_ui_typing_contract.py tests/test_csv_export.py`. The separate native QGIS tests (`tests/test_qgis_graphics.py` and `tests/test_qgis_layer_lifecycle.py`) require a matching QGIS Python environment. The GitHub QGIS 3.44 job uses an offscreen Linux container; it does not replace interactive desktop acceptance.

CI enforces a focused Python 3.10-compatible Ruff baseline, QGIS-independent strict Pyright checks, compilation, regressions and ZIP packaging. The typing check does not establish full QGIS-aware type coverage. The bundled graphics and DXF dependencies and generated resources are not subject to the plugin-owned lint baseline.
