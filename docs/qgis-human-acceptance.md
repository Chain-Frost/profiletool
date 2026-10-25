# Profile Tool 4.4.0: native QGIS manual acceptance

**Status: NOT EXECUTED — evidence and sign-off required.**
This is the human validation record for the Chain-Frost maintenance fork's
proposed **Profile Tool 4.4.0** contribution to
[PANOimagen/profiletool](https://github.com/PANOimagen/profiletool).
Automated test success is **not** a substitute for the visual and interactive
checks below. Do not mark boxes based solely on scripted QtTest input, a Linux
offscreen QGIS container, or a previous code revision.

## Purpose and constraints

- Compare real user workflows against **upstream version 4.3.4** while allowing
  the documented bug fixes of 4.4.0. Do not introduce new features or redesign
  the original plugin.
- Use the release-ready ZIP from the **exact Git SHA being accepted** and check
  the installed plugin's `metadata.txt` reports version `4.4.0`. Record its SHA.
- Prefer **native Windows QGIS 3.44.x (PyQt5)** and **QGIS 4.x (PyQt6)**. Record
  exact QGIS, Qt, PyQt, Python, GDAL, OS and source commit for each run.
  If one installation is genuinely unavailable, record **NOT TESTED** and why;
  do not claim compatibility was visually verified.
- Test in a disposable QGIS profile and project. Do not alter live production
  files. If testing real project data, retain sensitive file paths, screenshots,
  names and model information **locally only**; post sanitised aggregate results.
- Avoid wholesale typing cleanups, vendored dependency upgrades and changes to
  whole-layer feature ordering; these are outside the human acceptance scope.

## Evidence to record

For **each** row/environment, enter PASS, FAIL, NOT TESTED or NOT APPLICABLE,
a short observed-versus-expected note, the QGIS version, and a sanitised
screenshot/export/log reference when relevant. Use private local artifact paths
only in your private handover; do **not** post raw filesystem paths or project
identifiers to public GitHub.

| Run | QGIS | Python | Qt / PyQt | Plugin SHA | Date | Tester | Outcome |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Windows 3.44/PyQt5 | NOT TESTED | — | — | — | — | — | NOT TESTED |
| Windows 4.x/PyQt6 | NOT TESTED | — | — | — | — | — | NOT TESTED |

## Manual desktop test matrix

| ID | User action and source scenario | Expected result | QGIS 3.44 | QGIS 4.x |
| --- | --- | --- | --- | --- |
| H01 | Install ZIP in clean development profile; activate, close, reopen and unload | No import error, duplicate action, stale signal, or destroyed-object exception | NOT TESTED | NOT TESTED |
| H02 | Manually add/remove/re-add a raster and multiband raster; change selected band | Correct values and source identity; source list remains editable | NOT TESTED | NOT TESTED |
| H03 | Add same-name raster layers; hide/recolour one; remove only one | Independently selected plots and controls, no confusion by duplicate name | NOT TESTED | NOT TESTED |
| H04 | Freehand: place vertices, move mouse, right-click to finish; hover afterwards | Completed path/plot retained; no spurious preview extension | NOT TESTED | NOT TESTED |
| H05 | Change project CRS with active and completed freehand profiles; repeat round trip | Path remains at same world location, plots/axis/markers resampled, completed preview stays inactive | NOT TESTED | NOT TESTED |
| H06 | Selected single and multipart line; click each part; reverse one feature | Only clicked part plotted, with correct orientation and chainage; existing QGIS selection preserved | NOT TESTED | NOT TESTED |
| H07 | Whole-layer line mode with multiple/disconnected/reversed features | Match documented upstream provider-order concatenation, including its limitations; no dropped features | NOT TESTED | NOT TESTED |
| H08 | Raster valid 0, internal/external NoData; switch height and both slope plots | Zero retained as elevation; NoData not fabricated as 0, plot breaks remain | NOT TESTED | NOT TESTED |
| H09 | Projected metre project, differing raster CRS, independently known sample points | Plot chainage in metres; sampled elevations correspond to source locations | NOT TESTED | NOT TESTED |
| H10 | Project CRS feet (with elevations also in feet), independent 10/100 grade | Chainage in native feet; slope 10%, not 32.8% | NOT TESTED | NOT TESTED |
| H11 | Geographic project (degrees), projected raster; switch map CRS | Degree axis; physical/geodesic-metre slope distance; map location and sampling valid | NOT TESTED | NOT TESTED |
| H12 | Point-vector sources with mixed CRSs, search buffer and numeric elevation field | Search interpreted in project units; correct points/grades and temporary layer CRS | NOT TESTED | NOT TESTED |
| H13 | Actual QGIS mesh layer with CRS different from project; inspect identifiable scalar | Compare against independently known mesh identify values; no map/layer CRS confusion | NOT TESTED | NOT TESTED |
| H14 | Where installed, existing supported Selafin/plugin layer, parameter/band selection | Original plugin-layer profiling works; if unavailable mark NOT TESTED | NOT TESTED | NOT TESTED |
| H15 | Switch PyQtGraph↔Matplotlib repeatedly; zoom, pan, tracking, visibility | Curves and axes render; mouse marker/labels update; no repeated callbacks | NOT TESTED | NOT TESTED |
| H16 | On slope plot, click to save profile points; copy sample/coordinate tables | Saved Z is source elevation, not grade; legitimate zero values survive | NOT TESTED | NOT TESTED |
| H17 | Save/reopen PNG, SVG and CSV from supported backends | Legible axes and correct series, units, NoData gaps and CSV columns | NOT TESTED | NOT TESTED |
| H18 | Matplotlib PDF (and existing PS option if functional); inspect output | PDF renders/opens; correct axis/curves/gaps; record unsupported PS honestly | NOT TESTED | NOT TESTED |
| H19 | Export 2D/3D DXF, reopen independently in CAD/QGIS | 2D distance/elevation and 3D source-coordinate lines correct; no lines bridging NoData | NOT TESTED | NOT TESTED |
| H20 | Rotated/warped raster with narrow source NoData column | Compare raw pixels to provider-visible samples; document QGIS resampling caveat, not fabricated preservation | NOT TESTED | NOT TESTED |
| H21 | Remove layer while dock is open; change map tools, then unload/reload | No dangling source wrappers, stale map tools or callback exceptions | NOT TESTED | NOT TESTED |

### How to assess output

Record independent checks, not just visual impressions. For geometric samples,
use known point coordinates or a separate GIS query. For CRS-change scenarios,
compare both the map overlay and output table, not only axis labels. For scalar
meshes, record whether identification was from a real mesh dataset rather than
a mock. For DXF, inspect vertex geometry independently of the plugin.

## Reporting and acceptance

- [ ] All applicable H01–H21 checks have recorded results for both target QGIS
  environments (or explicitly justified NOT TESTED/NOT APPLICABLE).
- [ ] Any FAIL has a reproducible issue and regression test, or a documented
  upstream parity decision.
- [ ] Screenshots and exported samples were visually inspected; sanitised
  evidence is linked from the PR without sharing private project data.
- [ ] Required quality workflow, QGIS 3.44 compatibility workflow and
  QGIS-aware typing results are recorded at the exact final source SHA;
  inherited full-Pyright findings are distinguished from changed-line defects.
- [ ] The candidate 4.4.0 metadata, licence/attributions and changelog were
  reviewed for submission to upstream; no GitHub release/tag is implied.
- [ ] Human tester records final PASS / QUALIFIED PASS / FAIL decision, date,
  environments and remaining exclusions in a PR comment.

**Acceptance outcome:** NOT TESTED. Do not merge this validation PR or claim
human sign-off until the results above are entered and reviewed.

## Related work

- [Correctness and CRS changes — PR #2](https://github.com/Chain-Frost/profiletool/pull/2)
- [CI, Ruff py310 and acceptance documentation — PR #3](https://github.com/Chain-Frost/profiletool/pull/3)
- [Mechanical Ruff cleanup — PR #4](https://github.com/Chain-Frost/profiletool/pull/4)
- [Historical desktop matrix](validation-matrix.md)
- [QGIS 3.44 compatibility evidence](qgis-3.44-compatibility.md)
