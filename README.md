# Profile Tool ![image](https://github.com/PANOimagen/profiletool/blob/master/icons/profileIcon.png?raw=true)

This tool plots profile lines from raster layers or point vector layer with elevation field.
Supports multiple lines and graph export to SVG/PNG, plus PDF with Matplotlib.
Profile tables can be copied as tab-separated text for spreadsheet import;
there is no native CSV file export action.
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

## QGIS development session on Windows

Run `open-qgis-dev.bat` to open `C:\OSGeo4W` QGIS with an isolated development
profile and load this checkout directly. The Profile Tool dock opens on startup.
The plugin instance is accessible in the QGIS Python console as
`iface.profiletool_dev`. Restart this session after changing Python sources.
Startup results are written to `%TEMP%\profiletool-qgis-dev-status.json`.

To load or reload the checkout in an existing QGIS session, run this in its
Python console (or through the MCP `execute_code` tool):

    import runpy
    runpy.run_path("E:/Github/profiletool/scripts/qgis_dev.py")

The helper unloads the previous Profile Tool instance and reloads its Python
modules from the checkout. It keeps the current project and MCP connection.
The separate-window launcher does not start another MCP server.

Use `C:\OSGeo4W\bin\python-qgis.bat` for commands requiring the QGIS Python
environment. Desktop verification scenarios are listed in
[the validation checklist](docs/validation-matrix.md).

## VS Code with OSGeo4W Python

The workspace selects `C:\OSGeo4W\apps\Python312\python.exe`. If VS Code
already has a different interpreter selected, use **Python: Select Interpreter**
and enter this path. Close existing integrated terminals and open a new one.

The generated `.vscode/qgis.env` supplies QGIS, Qt, GDAL and PROJ variables to
Python tools and the debugger. Refresh it after an OSGeo4W upgrade:

    C:\OSGeo4W\bin\python-qgis.bat scripts\write_qgis_env.py

Development tools live in an ignored workspace directory, separate from the
OSGeo4W installation. Install or refresh them with:

    C:\OSGeo4W\bin\python-qgis.bat -m pip install --target .vscode/qgis-tools -r requirements-dev.txt

QGIS import paths are also configured for editor analysis. The VS Code test
runner selects the regression suite. **Python: QGIS environment (current file)**
is available in Run and Debug for standalone scripts. A Python interpreter does
not create a running QGIS desktop `iface`; use the existing MCP connection for
scripts requiring the live application.

OSGeo4W may omit PyQt's type definition files even though its compiled modules
are installed. Generate matching editor/Pyright definitions with:

    C:\OSGeo4W\bin\python-qgis.bat scripts\setup_qgis_typing.py

This downloads the official PyQt6 wheel matching the installed binding version
and extracts only `.pyi` definitions into the ignored `.vscode/qgis-type-stubs/`
folder. The wheel version, SHA-256 and source URL are recorded in its manifest.
Two missing names in the generated callback types are normalized for analysis.
The workspace analysis paths use this folder; it is not added to the runtime
Python path and no OSGeo4W binaries are replaced. Refresh after an OSGeo4W
upgrade. This helper currently targets the installed PyQt6 environment.

Editor/Pyright analysis also includes the workspace's parent folder so tests
can resolve the `profiletool` package, matching their runtime import path.

## Full Pyright diagnostic triage

Legacy plugin modules retain their established function and local-variable
names through explicit Ruff N802/N806 exceptions in `ruff.toml`. Use snake_case
for all new code, including additions to those modules. New files retain the
naming checks; review must enforce the convention for additions within exempt
legacy files. Do not rename existing public functions solely to satisfy lint.

The latest local typing cleanup and validation results are recorded in
[the cleanup report](docs/pyright-cleanup.md).

The full strict type check must run in a matching OSGeo4W QGIS/PyQt
environment. It is not comparable to a headless CI run without QGIS. To
capture and classify the **actual** full-workspace errors in PowerShell:

```powershell
& "C:\OSGeo4W\bin\python-qgis.bat" -m pyright --project pyrightconfig.json --outputjson > pyright-full.json
& "C:\OSGeo4W\bin\python-qgis.bat" scripts/pyright_triage.py pyright-full.json --output pyright-summary.json
```

Pyright normally returns a nonzero exit status when errors are present. This
is expected; run the second command regardless. The summary groups error
codes, affected source files and unresolved imports. It strips local path
prefixes and uses only the real diagnostics; no missing QGIS symbols are
replaced with permissive `Any` types.

The old `apicompat/` QGIS 2 monkey-patches have been removed because the
QGIS 3.40+/4.x plugin entry point no longer loads them; these pre-PyQt5
compatibility shims must not be reintroduced to address typing warnings.
