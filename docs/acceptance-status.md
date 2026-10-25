# Fork parity and acceptance status

**Reviewed:** 25 October 2026. This is the post-merge acceptance record for
`Chain-Frost/profiletool`, not a claim that all manual checks have passed.

## Objective and baseline

- **Upstream:** [PANOimagen/profiletool](https://github.com/PANOimagen/profiletool),
  `master` at `ca5223983629f625e904248d4cbb229fb6341716`.
- **Fork before follow-up work:** `master` at
  `e14adc91e52c995e2396b9ebed45e46ecf97b8e9`, containing merged
  [PR #1](https://github.com/Chain-Frost/profiletool/pull/1).
- **Scope:** Retain the established plugin's manual addition of raster, point-vector,
  mesh and supported plugin sources; freehand, selected-feature and whole-layer
  profiles; height/slope plotting; PyQtGraph and optional Matplotlib; coordinate
  tables and exports.
- **Excluded:** Replacement with QGIS native elevation profiling, topology-aware
  feature ordering, plotting-library replacement and unrelated features.
- **Upstream-compatible choices:** Whole-layer mode retains upstream provider order
  and historical concatenation limits; clicked multipart lines use only their clicked
  part. Projected chainage and grades retain native map units and assume compatible
  vertical units.

## Recorded automated evidence

| Environment and scope | Last recorded outcome | Limitation |
| --- | --- | --- |
| GitHub quality workflow, merged `master` (`e14adc91`, 15 Oct) | Passed | Scoped Ruff/Pyright, headless regressions, syntax and ZIP, not QGIS desktop |
| QGIS 3.44.15 / Qt5 Linux Docker on final PR #1 head (`cf71830`) | 7 QGIS lifecycle regressions passed | Not native Windows or comprehensive visual testing |
| QGIS 4.2.x automated desktop test scripts (14–15 Oct) | 17 scenario groups recorded as passed | QtTest input, not hardware clicks or full visual review |
| Full strict Pyright/Ruff in local QGIS environment | Reported clean in PR #1 handoff | Repeat after changes; hosted CI Pyright only covers QGIS-independent modules |

The historical [validation matrix](validation-matrix.md), [Qt5 compatibility
report](qgis-3.44-compatibility.md), and merged PR provide reproducible scenarios
and dated results. Old results are not proof for a changed branch head.

## Acceptance required before distributing or proposing upstream

- [ ] **Windows QGIS 3.44.x/PyQt5:** Run the interactive plugin workflow natively
  and record QGIS, Python, Qt, PyQt and plugin commit. Verify graph rendering,
  scene attachment, tracking and callbacks without Qt exceptions.
- [ ] **Windows QGIS 4.x/PyQt6:** Repeat key scenarios on the supported deployment
  version (including QGIS 4.0.1 when available): source add/remove, backend
  switching, map cursor, tool restoration and unload/reload.
- [ ] **Representative project data:** Independently compare raster, point-vector
  and mesh sampling, including differing layer/project CRSs; geographic, metre
  and feet-based projects; valid zero and internal/external NoData.
- [ ] **Project CRS changes:** With an existing profile, change project CRS and
  verify path geometry, source sampling, chainage, slope, map overlays and saved
  point coordinates. Correct or invalidate stale state and add a QGIS regression.
- [ ] **Exports:** Inspect PNG, SVG, CSV, PDF (Matplotlib) and 2D/3D DXF;
  reopen files and verify NoData gaps, coordinates, values and legibility.
- [ ] **Rotated raster NoData:** Reproduce the provider-resampling case where
  a narrow raw-source gap disappears. Explicitly record whether provider-visible
  sample values are acceptable; do not claim raw NoData preservation.
- [ ] **Final head:** Run both hosted workflows, strict QGIS-aware Pyright and
  Ruff, and applicable native tests at the exact accepted commit.

## Independent workstreams

Both workstreams branch directly from post-PR-#1 master:

1. `fix/profiletool-mesh-crs-parity`: sampling/CRS correctness and regression
   tests. Owns `tools/dataReaderTool.py`, `tools/profiletool_core.py`, and
   targeted `tests/` only.
2. `chore/profiletool-ci-acceptance`: CI triggers and authoritative acceptance
   documentation. Owns `.github/workflows/`, `README.md` and `docs/` only.

Do not edit the other workstream's files, modify master, merge either PR, or
claim native Windows test execution without actual evidence.

## Intentional limitations

- Whole-layer mode still concatenates provider-ordered features and can bridge
  disconnected or reversed linework. This matches the accepted upstream behaviour;
  it is not graph-topology-aware ordering.
- The horizontal CRS alone does not establish vertical elevation units. Projected
  grades assume consistent horizontal/vertical units; geographic projects use
  geodesic metres and assume elevations are in metres.
- Warped/rotated raster resampling may suppress narrow source NoData gaps.
- Fork metadata still reports upstream version 4.3.4 until a separate distribution
  or release decision. These changes are not an upstream version release.
