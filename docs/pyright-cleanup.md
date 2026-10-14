# Pyright cleanup validation

Measured on 14 October 2026 using the configured OSGeo4W Python 3.12 / QGIS
4.2.1 environment and matching PyQt6 type definitions.

Full strict Pyright decreased from **2,259 errors at commit `84b3ed3`** to
**1,857 errors in the working tree**, with zero warnings: 402 fewer errors.
The working-tree result includes uncommitted changes and is not a hosted CI
result. Generated reports remain local and ignored.

## Changes

- Added a static contract for the widgets and layouts loaded from
  `ui/profiletool.ui`, with a regression test comparing it to the Designer XML.
- Added types for sampled profiles and plot series without weakening strict
  Pyright settings or checking bundled external libraries.
- Preserved the Designer `groupBox` and `verticalLayout` fields by giving
  coordinate-tab collections separate names. The QGIS lifecycle test checks
  these fields retain their widget types.
- Included the new files and form-contract test in the existing CI checks.

## Local validation

| Check | Result |
| --- | --- |
| Scoped CI Ruff | Passed |
| CI-scoped strict Pyright | Zero errors and warnings |
| Headless CI regression suite | 13 passed |
| Tests in isolated QGIS processes | 15 passed |
| Full strict Pyright | 1,857 errors, zero warnings |
| Full Ruff inventory | 682 findings remain |
| Formatting of changed Python files | Passed |

The isolated QGIS run used `QT_QPA_PLATFORM=offscreen` and excluded
`tests/test_dist.py`, which requires a live desktop `iface`. Desktop validation
remains paused. QGIS 3.44 compatibility has not been tested. These changes have
not been committed or pushed, so hosted CI has not run for this batch. The
separate report-sharing branch is unchanged.

## Remaining work

The largest remaining diagnostic groups are in `tools/plottingtool.py`,
`tools/dataReaderTool.py`, `tools/profiletool_core.py`, and
`tools/tableviewtool.py`. Unknown member and argument types account for most
findings. Typing the reader and plotting boundaries is the next useful step.

See the [full Pyright reproduction commands](../README.md#full-pyright-diagnostic-triage)
and the [desktop validation checklist](validation-matrix.md) for separate
validation workflows.
