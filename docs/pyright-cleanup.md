# Pyright cleanup validation

> **Committed-head note (15 October 2026):** The most recent complete QGIS
> Pyright JSON checked into `validation/pyright/latest-working-tree/` records
> **26 errors and 0 warnings**, produced from a working tree based on
> `c8adac6`. Those changes were subsequently committed as `21ab42c`.
> Additional low-risk typing changes on PR #1 address numeric NoData guards,
> QGIS polyline-return signatures and narrow Matplotlib/PyQtGraph/DXF export
> call contracts. **No full QGIS Pyright recount has been verified at the
> latest PR head.** The separate headless CI Pyright test cannot establish
> that count. QGIS 3.44 remains a separate failing compatibility test.


Measured on 14 October 2026 using the configured OSGeo4W Python 3.12 / QGIS
4.2.1 environment and matching PyQt6 type definitions.

Full strict Pyright decreased from **2,259 errors at commit `84b3ed3`** to
**26 errors in the working tree**, with zero warnings: 2,233 fewer errors.
The first batch reduced the count to 1,857 and was committed as `1e0a667`.
The subsequent reader, plotting, table-model, map-tool, core and UI work removes
another 1,831 errors.
The working-tree result includes uncommitted changes and is not a hosted CI
result. Generated reports remain local and ignored.

## Changes

- Renamed the mutable TYPE attribute to plot_type and updated every repository
  caller; TITLE remains a constant. Added the Matplotlib file-export contract,
  reducing full strict Pyright from 32 to 26 errors. All 21 isolated tests and
  17 QGIS 4.x desktop cases passed. Intermediate report directories were
  consolidated into validation/pyright/latest-working-tree; verified c540dd1
  and f23009d baseline reports are retained. The latest set remains explicitly
  uncommitted working-tree evidence.

- Expanded plugin-owned type declarations for the concrete PyQtGraph scene,
  plot, view-box and cursor methods used by this plugin. Runtime classes and
  library code are unchanged; strict settings and exclusions are unchanged.
  Shared resolution now clears the native-test and dock forwarding diagnostics.
  Kept the lazy legacy Matplotlib fallback while resolving its modern type
  identity and importing rcParams within the backend branch. Removed casts
  made redundant by these contracts. Full Pyright fell from 60 to 32 errors.
  Remaining: 24 incomplete library members, three legacy callback parameter
  overrides, two mutable uppercase attributes and three defensive None checks.
  All 21 isolated tests and 17 QGIS 4.x desktop cases passed. No QGIS 3.44 work
  or new diagnostic suppressions were introduced.

- The next export/cursor pass reduced full strict Pyright from 69 to 60 errors.
  SVG rendering now uses the real QGraphicsView contract, retaining the same
  runtime render override. PNG resolves a valid plot item before exporting.
  Sample arrays and scalar indices are typed, and cursor callbacks skip curves
  whose data is unavailable. Font configuration keeps the existing values via
  rcParams. All 21 isolated tests and 17 live QGIS 4.x desktop cases passed.

- On 15 October, typed polyline points and collected buffer geometries and
  replaced dynamic pen/brush construction with Qt QPen/QBrush values. Cosmetic
  pixel widths, colors and label fills remain equivalent. Full strict Pyright
  decreased from 82 to 69 errors. All 21 isolated tests and 17 live QGIS 4.x
  cases passed. QGIS 3.44 and bundled library source remain untouched. This
  result is an uncommitted working tree based on c8adac6, not a committed-head
  or hosted CI measurement.

- The committed head f23009d was independently measured at 151 errors, zero
  warnings using OSGeo4W QGIS 4.2.3 and Pyright 1.1.414. The current plotting
  and cursor boundary cleanup reduces that to 82 errors (69 fewer). Shared
  helpers describe the actual profile-generated PlotDataItem curves and
  concrete plot/view objects; missing or mismatched backends return safely.
  All 21 isolated tests and 17 live QGIS 4.x desktop cases passed. No QGIS
  3.44 tests or vendor changes were made in this batch.

- Cleared all 49 table-selection diagnostics. Documented the optional Selafin
  parser boundary, shared its band-ID/name lookup and typed removal labels.
  Existing IDs, label values, extra row metadata and dialog cancellation codes
  remain unchanged. A native QGIS plugin-layer contract fixture verified sparse
  IDs 7/42 through selection, editing and cancellation. The actual external
  Selafin plugin remains untested. All 21 isolated tests and 17 desktop cases
  passed again.

- Typed the dock's PyQtGraph plot-item and range-signal boundary and guarded
  missing plot items/view boxes and Matplotlib backend calls. Replaced string
  class checks with actual cursor/label classes in the dock and core, and made
  empty cursor labels safe. The native regression checks visibility, range
  reconnection and aspect locking across backend switches. All 21 isolated
  tests and all 17 live desktop cases passed; this batch removed 54 diagnostics.

- Display chainage and axis labels in the native project CRS units using QGIS's
  unit metadata. Metre, international-foot and US-survey-foot projects passed
  live sampling checks. Separate metre distances preserve the existing grade
  calculation convention; elevation units are not inferred from the CRS.
  Three headless regressions cover these linear units.
- Typed the actual PyQtGraph scene signals and guarded missing scenes and plot
  items. Live inspection verified that both signals are Qt bound signals.

- Cleared the final Ruff findings: scoped the synthetic diagnostic-path
  exception, combined cursor visibility conditions, declared both plot-widget
  return types, and extracted source/band selection and nearest-sample lookup
  into focused helpers. Public method names and cancellation results remain
  compatible. Live dialog coverage now also cancels layer, band, field and
  removal dialogs and verifies that the source table remains unchanged.
- Reviewed boolean conventions: named flags in plugin-owned calls,
  keyword-only flags in test fixtures, and targeted exceptions for Qt payloads
  and legacy positional signatures. All FBT001/002/003 findings are clear.
  Standalone development scripts are exempt from INP001 while retaining their
  other checks. All 18 isolated tests and 17 live desktop cases passed afterward.
- Converted plugin-owned filesystem operations to `pathlib` while keeping
  strings at Qt/QGIS boundaries. Renamed shadowing locals, preserved legacy
  keyword and callback parameters, and documented compatibility exemptions.
- Kept optional imports lazy and test-double Qt names intact. Startup reporting
  retains its outer exception boundary; JSON-schema validation retains its
  tested ValueError contract. Model cleanup now catches only RuntimeError, and
  tracking-line cleanup tolerates only an already-removed artist. Regression
  coverage checks that case. Added a public distance-scale helper while keeping
  the legacy private method available.
- Reviewed and applied six Ruff suggestions: two PT018 assertion splits, three
  SIM102 condition merges and one RUF005 DXF list-unpacking change. All 18
  isolated tests and 17 live desktop cases passed afterward.
- Cleared EM101, D101, D102 and SIM108 findings: seven exception-message
  extractions, 93 descriptive public API docstrings, and three reviewed
  conditional-assignment simplifications. The docstring pass preserved the
  executable AST. Applied the subsequent safe max-expression and no-op cleanup.
- Live dialog validation caught unsupported `getItem(parent=...)` calls.
  Restored positional Qt arguments, retained a focused FBT003 compatibility
  exception and verified all 17 desktop cases pass again.
- Added explicit missing/invalid mesh-scalar handling and parameterized
  regression coverage. Typed the shared fixture tuple and documented feature
  iteration in the real-QGIS export check. Repeated all 17 live desktop cases
  successfully against this reader change.
- Added a safe map-tool status-message helper and typed the console-only
  distance script's live interface, canvas and project requirements. The
  console script was also executed successfully through the live QGIS MCP
  connection with a temporary EPSG:28350 layer in an EPSG:4326 project.
- Typed headless provider and multipart-geometry fixtures, and registered
  dynamically constructed module attributes through their dictionaries.
  Fixture geometry wrappers now have concrete typed coordinate fields.
- Typed vector candidate rows, DXF vertex runs and headless coordinate fixtures.
  Documented QGIS's iterable feature-iterator contract despite its optional
  `__iter__` stub, updated map-tool enum access and guarded missing plot widgets.
- Guarded incomplete source-table items and missing layer providers/message
  bars. Typed the dynamically loaded math-test module with its actual profiler
  signatures rather than leaving the fixture's calls unknown.
- Fixed Matplotlib cursor tracking at zero chainage and replaced removed
  `axes.lines.remove` usage with the artist's `remove()` method. An isolated
  QGIS regression checks cursor replacement and tracking-disable cleanup.
- Guarded missing plot objects during export and cursor callbacks. Typed the
  mouse-click scene-coordinate contract, and removed an ineffective attempt
  to disconnect a callback on the plotting helper rather than its owning core.
- Typed object-dtype interpolation arrays and geometry inputs, and centralized
  the reader's required project lookup. Mesh identification uses the supplied
  interface's canvas and explicit imports; a headless regression checks this
  while global `iface` is unset.
- Typed dock-widget handlers and plotting/export inputs, preserving established
  names. Guarded missing layout items, headers, signal senders and clipboards.
- Fixed temporary-layer export's Qt 6 field enum (`QMetaType.Type.Double`).
  The isolated QGIS regression now clicks the coordinate-tab buttons, checks
  clipboard output and verifies exported feature values and CRS.
- Typed feature-selection inputs, cursor positions, point-layer state and core
  lifecycle methods. Missing map canvases/renderers are guarded before access.
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
| Headless CI regression suite | 19 passed |
| Tests in isolated QGIS processes | 21 passed |
| Full strict Pyright | 26 errors, zero warnings |
| Full Ruff inventory | Zero findings with documented compatibility exemptions |
| EM101, D101, D102, SIM108 | Zero findings |
| Live QGIS desktop automation through MCP | All 17 cases passed |
| Live console distance script | Passed; temporary layer removed |
| Formatting of changed Python files | Passed |

The isolated QGIS run used `QT_QPA_PLATFORM=offscreen` and excluded
`tests/test_dist.py`, which requires a live desktop `iface`. Desktop validation
was resumed through MCP: all 17 scripted cases passed with no Qt callback or
cleanup errors, and layer IDs/CRS were restored. Evidence is recorded in the
ignored `validation_artifacts/qgis-desktop/interaction-report.json` and
`distance-report.json`. Native CRS unit checks are recorded in
`native-units-report.json`. Human hardware clicks and visual export inspection
remain manual. QGIS 3.44 was subsequently smoke-tested using the official Linux Docker image. One QGIS lifecycle test passes; the other **fails** due to PyQt5 QVariant conversion during vendored PyQtGraph graphics-item changes. See [the QGIS 3.44 compatibility blocker](qgis-3.44-compatibility.md). Full QGIS 3.44 desktop scenarios remain unverified. The reader and
plotting follow-up has not been committed or pushed; hosted CI has not been
verified for this batch. The
separate report-sharing branch is unchanged.

## Remaining work

| Diagnostic category | Count | Typical difficulty |
| --- | --- | --- |
| Unknown member/argument/variable/lambda types | 20 | Moderate to hard: QGIS and plotting-library API boundaries |
| Undeclared attributes | 0 | Moderate to hard: generated stubs and legacy plugin interfaces |
| Possibly missing objects | 0 | Easy to moderate: lifecycle and state checks |
| Compatibility and cleanup findings | 6 | Easy to moderate; some preserve intentional legacy APIs |

The earlier reader pass typed its polyline return and interpolation collections
and guarded progress status bars. All 18 isolated tests and 17 live desktop
cases passed against the change.

The largest remaining diagnostic groups are in `tools/plottingtool.py`,
`tools/dataReaderTool.py`, `tools/profiletool_core.py`, and
`tools/tableviewtool.py`. Unknown member and argument types account for most
findings. Typing the reader and plotting boundaries is the next useful step.

See the [full Pyright reproduction commands](../README.md#full-pyright-diagnostic-triage)
and the [desktop validation checklist](validation-matrix.md) for separate
validation workflows.


## Committed-head Pyright follow-on and QGIS 3.44 compatibility

The uploaded strict Pyright JSON, summary and metadata independently verify **167 errors, zero warnings** at clean committed `c540dd12` under QGIS **4.2.3**, Python **3.12.15**, and Pyright **1.1.414**. This report supersedes the earlier working-tree-only count and does not imply that the latest head has been recounted.

The follow-on commits after `c540dd12` have typed the optional plugin-layer `identify` boundary, QGIS geometry polyline-return contracts and Qt plot-selection callback. They also replaced untyped headless-test lambdas. Both GitHub quality runs pass (19 headless tests and zero headless strict Pyright errors); **full local strict Pyright has not been rerun at this later head**.

A new independently running QGIS **3.44.15/PyQt5** container test exposed an actual graphics callback error in bundled PyQtGraph. It remains a **failed compatibility gate**, not a successful QGIS 3.44 validation. Unverified vendor modifications were reverted; documentation and reproduction instructions are in [qgis-3.44-compatibility.md](qgis-3.44-compatibility.md).
