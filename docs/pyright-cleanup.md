# Pyright cleanup validation

Measured on 14 October 2026 using the configured OSGeo4W Python 3.12 / QGIS
4.2.1 environment and matching PyQt6 type definitions.

Full strict Pyright decreased from **2,259 errors at commit `84b3ed3`** to
**1,205 errors in the working tree**, with zero warnings: 1,054 fewer errors.
The first batch reduced the count to 1,857 and was committed as `1e0a667`.
The reader, plotting, table-model and map-tool follow-up removes another 652 errors.
The working-tree result includes uncommitted changes and is not a hosted CI
result. Generated reports remain local and ignored.

## Changes

- Typed the map renderer, mouse positions, drawn points and core constructor.
  Missing canvases fail explicitly, and mouse callbacks skip unavailable
  coordinate transforms.
- Added a static contract for the widgets and layouts loaded from
  `ui/profiletool.ui`, with a regression test comparing it to the Designer XML.
- Added types for sampled profiles and plot series without weakening strict
  Pyright settings or checking bundled external libraries.
- Preserved the Designer `groupBox` and `verticalLayout` fields by giving
  coordinate-tab collections separate names. The QGIS lifecycle test checks
  these fields retain their widget types.
- Included the new files and form-contract test in the existing CI checks.
- Typed plotting profile collections, table models and numeric reader helpers.
  Plotting now safely skips missing widgets or incomplete model rows.
- Typed table removal/click handlers and guarded missing model items.
- Typed the reader's interface, map tool and drawn points, plus the table's
  layer-add handler. Layer selection uses `Qgis.LayerType` and narrows raster
  and vector layers before using their specific methods.
- Defined the reader's mutable profile record separately from a fully sampled
  profile. Raster/vector and main-window casts document the concrete types at
  existing dispatch boundaries; absent raster providers remain sampling gaps.

## Legacy name audit

An AST comparison against the branch base `ca522398` checked 115 function and
method definitions in the retained legacy plugin files. No function or method
names were removed or renamed. Four earlier parameter renames were restored:
`setPointOnMap(..., y)` and the three canvas callbacks' `event` parameters.
All audited parameter names now match the base. Established methods such as
`changePlotWidget` retain their names. Obsolete QGIS 2 files removed earlier
are outside this retained-file audit.

The restored canvas parameter names produce three Pyright override diagnostics
because QGIS's stubs use `e`. These are retained to preserve existing keyword
calls; no diagnostics were suppressed. Targeted renames of misleading names
remain acceptable after checking callers and compatibility.

## Local validation

| Check | Result |
| --- | --- |
| Scoped CI Ruff | Passed |
| CI-scoped strict Pyright | Zero errors and warnings |
| Headless CI regression suite | 13 passed |
| Tests in isolated QGIS processes | 15 passed |
| Full strict Pyright | 1,205 errors, zero warnings |
| Full Ruff inventory | 448 findings remain after legacy naming exemptions |
| Formatting of changed Python files | Passed |

The isolated QGIS run used `QT_QPA_PLATFORM=offscreen` and excluded
`tests/test_dist.py`, which requires a live desktop `iface`. Desktop validation
remains paused. QGIS 3.44 compatibility has not been tested. The reader and
plotting follow-up has not been committed or pushed; hosted CI has not been
verified for this batch. The
separate report-sharing branch is unchanged.

## Remaining work

The largest remaining diagnostic groups are in `tools/plottingtool.py`,
`tools/dataReaderTool.py`, `tools/profiletool_core.py`, and
`tools/tableviewtool.py`. Unknown member and argument types account for most
findings. Typing the reader and plotting boundaries is the next useful step.

See the [full Pyright reproduction commands](../README.md#full-pyright-diagnostic-triage)
and the [desktop validation checklist](validation-matrix.md) for separate
validation workflows.
