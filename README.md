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

## Development checks

Install the check tools with `python -m pip install -r requirements-dev.txt`.
Additional settings: Ruff linting and formatting (120 columns,
Google-style docstrings), strict Pyright, and EditorConfig/VS Code defaults.
The Python 3.9 target preserves compatibility with older QGIS Python environments.
Bundled `pyqtgraph`, `dxfwrite`, and generated `resources.py` are excluded.

    python -m ruff check .
    python -m ruff format --check .
    python -m pyright
    python -m pymarkdown -d MD013 scan README.md

These checks currently expose existing lint, formatting, and typing issues.
Run Pyright in an environment with QGIS and the plugin dependencies available
for complete import/type resolution. `tests/test_dist.py` is a QGIS console
script requiring `iface`; it is not a standalone pytest suite.
