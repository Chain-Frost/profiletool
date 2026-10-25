# Profile Tool 4.4.0: native QGIS manual acceptance

**Status: automated preflight completed; human acceptance NOT TESTED.**
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

### Local-agent preflight, 25 October 2026

This is preparation evidence only. **H01–H21 remain NOT TESTED in both
environments; no human acceptance or signature is supplied.** The available
agent tools cannot perform the required physical mouse/keyboard testing or
independent human visual inspection.

- Current integrated `master`: `6a89e386283678effe8a31f2a862ae8f518422a9`.
  Prepared source: PR #5 head `22a44a2ce704fdffe92e0359371ffa307427d44e`,
  which already includes that baseline. No branch update was needed.
- A ZIP was built from the committed files at that exact SHA, using the
  Makefile's file/directory inclusion list. Its 534 entries include metadata
  reporting version `4.4.0`. SHA-256:
  `cf38b4151473cde6074cf307209aafc32942557e82d677f0c50d4d69b5714741`.
  It was extracted into a disposable profile's plugin directory locally.
  In a separate native desktop process, the installed ZIP subsequently passed
  two load/activate/unload cycles in that disposable profile. This is a scripted
  activation smoke check, not human H01 acceptance.
  All 534 packaged files were compared with committed content (normalising
  Windows line endings); extracted files match the ZIP byte for byte.
- A read-only query of the existing native Windows session confirmed QGIS
  **4.2.3**, Python **3.12.15**, Qt **6.11.0**, PyQt **6.11.0**, and GDAL
  **3.13.3**. This is environment discovery, not testing of the prepared ZIP.
  The existing default profile and unsaved project were preserved.
- No native QGIS 3.44 installation was found in the standard Program Files
  or OSGeo4W application locations checked. This is a limited installation
  search; native Windows 3.44 acceptance remains **NOT TESTED**.
- [Quality workflow run 40178805385](https://github.com/Chain-Frost/profiletool/actions/runs/40178805385)
  completed successfully at the prepared source SHA. The QGIS 3.44 workflow's
  path filter excludes this documentation-only PR. A manual dispatch attempt
  was rejected with HTTP 403 (repository admin rights required), so no new
  exact-head QGIS 3.44 run is claimed.
- Full strict QGIS-aware Pyright **1.1.411**, using the installed QGIS Python
  interpreter and the repository configuration, analysed 24 files and reported
  **74 errors, 0 warnings**. These findings are inherited relative to the
  integrated baseline: this PR changes only this Markdown document and has
  no changed Python lines. Raw diagnostic reports remain private. This does
  not replace the successful scoped CI typing check or establish full typing
  acceptance.

Additional local checks on 25 October 2026, against the same source SHA:

- Native OSGeo4W QGIS 4.2.3, isolated offscreen process: **37 passed, no skips**
  across `test_qgis_layer_lifecycle.py`, `test_profile_regressions.py`,
  `test_pyright_triage.py`, `test_ui_typing_contract.py` and `test_csv_export.py`.
  The lifecycle module contains 10 native-QGIS tests. This is automated Windows
  evidence, not native QGIS 3.44 or physical interaction evidence.
- The exact quality-workflow Ruff baseline passed with Ruff **0.16.6**.
  Scoped `pyright-ci.json` passed with **0 errors, 0 warnings**; plugin source
  compilation passed. Full QGIS-aware Pyright findings remain as recorded above.
- Package metadata, changelog and bundled GPLv2 licence were inspected: proposed
  version `4.4.0`, QGIS range `3.40`–`4.99`, Qt6 support flag, upstream author
  attributions and licence remain present. The declared range is not proof of
  acceptance on every listed QGIS version.
- The existing desktop and QtTest interaction scripts completed **17/17 scenario
  groups** in a separate native QGIS 4.2.3 disposable-profile process. These
  scripts load the checkout, whose runtime source matches the prepared SHA;
  the ZIP activation smoke check above tests the extracted package separately.
  Automated coverage includes mixed-CRS raster/point sampling, feet chainage,
  zero/NoData, multipart selection, duplicate names, both plot backends,
  source-Z saving, layer/band dialogs, PNG/SVG/DXF, PDF reopening/rendering,
  clipboard tables and rotated-raster provider parity. There were no recorded
  Qt callback or cleanup errors; layer IDs and project CRS were restored.
  All 22 runtime/script source hashes in the report match the tested checkout,
  whose content was also compared with the committed source.
  Raw reports and generated exports remain private.
- The historical scripts contain outdated statements that CSV is unavailable;
  the observed menus now include **Graph - CSV**. Those statements are not
  accepted as current capability evidence. CSV serialization has automated
  regression coverage, but actual desktop CSV export and independent reopening
  remain part of H17. PS, real mesh, Selafin and human visual inspection are
  likewise not established by these scripts.

A human tester must launch the prepared disposable profile, activate the ZIP,
execute and document H01–H21 with independent source/export checks, and sign
the acceptance decision. Repeat with native QGIS 3.44 when available; retain
explicit exclusions otherwise. An authorised maintainer must dispatch the
missing exact-head compatibility workflow. Recheck CI and typing after any
source changes, then request the documentation/evidence review specified in
the PR before handing back a signed recommendation. Keep this PR Draft and
unmerged. Local staging is not approval for release or upstream submission.

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

### Human tester: preparation and execution

1. Obtain the prepared ZIP and private launch instructions from the local
   handover. Verify the SHA-256 above. Use a disposable profile, not your normal
   QGIS profile. In another installation, use **Settings > User Profiles > New
   Profile**, then **Plugins > Manage and Install Plugins > Install from ZIP**.
   Confirm version `4.4.0` and record the source SHA and environment versions.
2. Prepare copies of a single-band and multiband raster, duplicate-name layers,
   a raster containing valid zero and NoData, multipart/disconnected lines,
   numeric-Z points and an actual scalar mesh. Include differing layer/project
   CRSs, a feet-based example, and a rotated raster. Optional Selafin requires
   its supported plugin. Keep sensitive data and raw evidence private.
3. Establish independent reference values **before** using Profile Tool: record
   coordinates, raster pixel/Identify values, mesh Identify values and point
   attributes. Include a known rise/run of 10/100 in matching feet units; the
   expected grade is 10%. Record your measurement method and tolerance rather
   than comparing the plugin against its own tables.
4. Execute every H01–H21 row above, using physical mouse/keyboard input. Suggested
   sessions: install/sources and lifecycle (H01–H07, H21); values/CRSs and mesh
   (H08–H14, H20); plotting and exports (H15–H19). Repeat in each available target
   installation. Leave unavailable cases explicitly NOT TESTED with a reason.
5. Open PNG/SVG/PDF in independent viewers, CSV in a spreadsheet/text editor,
   and DXF in CAD or a fresh QGIS layer. Compare sample values and vertices
   against your references; check axes, gaps, units and legibility. Do not
   count file existence alone as successful export acceptance.
6. Complete one result record per scenario/environment using the template below.
   For failures, include minimal reproduction steps and observed versus expected
   behaviour. Retest a corrected source SHA; do not carry forward old passes.
7. Complete the final checklist and sign the recommendation. Keep this PR Draft
   and unmerged pending a separate approval, including for a qualified pass.

Copy this record for each scenario (the matrix is the summary):

```text
Scenario: H__       Result: PASS / FAIL / NOT TESTED / NOT APPLICABLE
QGIS / Qt / PyQt / Python / GDAL / Windows:
Plugin SHA / ZIP SHA-256:
Date / human tester:
Source scenario (sanitised):
Actions taken:
Independent reference / method / tolerance:
Expected / observed values and behaviour:
Evidence reference (sanitised; raw files remain private):
Failure reproduction or reason for exclusion:
```

Final recommendation template:

```text
Human tester / date:
Accepted source SHA:
Environments actually tested:
PASS / FAIL / NOT TESTED / NOT APPLICABLE counts per environment:
Outstanding defects and exclusions:
Recommendation: PASS / QUALIFIED PASS / FAIL
Signature:
```

The agent supplies automated evidence, not the human signature. An authorised
maintainer must dispatch the missing exact-head QGIS 3.44 workflow and request
the Codex documentation/evidence review after human results are recorded.

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
