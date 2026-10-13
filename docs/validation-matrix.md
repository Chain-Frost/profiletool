# Profile Tool regression verification

The automatic regression suite covers project CRS chainage units (degrees for a
geographic project, metres for a projected project), geographic-project grades
computed from physical metre distances, transformed sampling
locations, exact zero raster values versus missing raster samples, invalid
slope segments, short profiles, and vector point-chainage deduplication.

## QGIS MCP / Codex-assisted desktop verification

For an optional Windows Codex-to-QGIS bridge, see [QGIS MCP setup and desktop validation](qgis-mcp-desktop-validation.md). It documents the local network-installed MCP server, Python 3.14, QGIS-side plugin, connection check, and an example validation prompt. This integration does not run in GitHub Actions and does not replace visual inspection.

## Desktop checklist

Run these representative scenarios in QGIS 3.40+/3.44 and QGIS 4.x:

1. Geographic project + geographic raster: confirm plotted distance in degrees.
2. Geographic project + projected raster: confirm plotted distance remains in
   project degrees and elevation sampling uses the transformed layer CRS.
3. Projected project (metres) + geographic raster: confirm chainage is in metres;
   verify sampled values at known coordinates and the local location.
4. Projected project (feet) + raster: confirm chainage converts to metres.
5. NoData outside raster boundaries and through internal gaps: confirm visible
   gaps rather than zero elevations; verify slope and DXF output do not bridge.
6. Feature-selection mode: click either part of one multipart line, confirm
   only that part is profiled. Existing QGIS selections must remain unchanged.
7. Add/remove several rasters manually, adjust band and vector search buffer,
   switch plot libraries and repeat refreshes. Confirm no duplicate curves or
   signal callbacks, and controls still work after coordinate-tab updates.
8. Mixed source CRSs in point-vector profiling: verify buffer in project map
   units and returned temporary point coordinates/CRS.
9. Select source line in a layer containing duplicate layer names; remove an
   individual source layer and verify only its corresponding profile disappears.
10. Add profile points while viewing slope plot and check that the saved z field
    holds source elevation, not slope.
11. Close and reopen the dock, switch map tools repeatedly and unload plugin.
    Confirm map tool restores and no callbacks remain connected.
12. Verify plot exports and that 2D/3D DXF lines split at NoData samples.

The GitHub workflow checks Python syntax and QGIS-independent regression
tests. It does not substitute for running this checklist in real QGIS.

## QGIS 4.2.1 evidence from 2026-10-14

The fixture runner exercised all twelve scenario groups through real QGIS
objects, widgets and plugin handlers in the default desktop session over MCP.
All twelve automated scenarios passed, with no captured Qt callback errors or
cleanup errors. This covers the automated portions described below, rather
than every manual action in the checklist.

| Items | Verified in the live desktop | Still required |
| --- | --- | --- |
| 1–4 | Geographic/projected raster sampling, transformed endpoints, degree/metre/survey-foot chainage | Broader terrain and CRS combinations |
| 5 | Valid zero, internal/external NoData, grade gaps | More raster formats |
| 6 | Nearest multipart-part selection handler; existing selections preserved | Physical canvas clicks |
| 7 | Add/remove two rasters, four refreshes, two cycles through PyQtGraph/Matplotlib; stable tracking callback count | Raster-band selection through its dialog |
| 8 | Geographic point source, metre buffer inclusion/exclusion, temporary-layer button and projected output coordinates | Additional vector CRSs |
| 9 | Two sources with identical names; separate curves; remove one source and retain the other | Physical source-selection dialog interaction |
| 10 | Plot-click handler saves elevation 3 while the displayed grade is 100 percent | Physical plot clicks |
| 11 | Three close/reopen cycles, unload, disconnected callbacks; original map tool restored | Additional manual map-tool transitions |
| 12 | PNG/SVG exported; DXF reopened with GDAL; two gap-separated 2D/3D lines with elevations 0–9 and 11–19; PNG visually inspected | Visual SVG review; PDF/CSV workflows where available |

All items still need comparison on QGIS 3.40/3.44. PDF and CSV are absent from
the tested PyQtGraph export menu; this run does not claim they were validated.

The run discovered and repaired a native crash caused by retaining deleted
layer wrappers in the source table, non-unique curve labels derived from layer
ID prefixes, a Qt 6 SVG export parser failure, and accumulating tracking
callbacks after plotting-library switches. The table now stores source IDs and
resolves them through the project before use. SVG export uses Qt's vector
renderer. Tracking callbacks are disconnected before reconnection.

Run the independent regression checks using the configured QGIS environment:

    python -m pytest tests/test_profile_regressions.py tests/test_qgis_layer_lifecycle.py -q -ra

Result: **11 passed**. The lifecycle regression uses real QGIS layers, a real
canvas, Qt models and the plugin dock in a separate process; QGIS's test helper
provides the application interface. It verifies deletion of one/several sources
and callback counts across library switches.

To repeat the desktop checks, start with an empty development project, then run
this in the QGIS Python console or the MCP `execute_code` tool:

    import runpy
    runpy.run_path("E:/Github/profiletool/scripts/validate_qgis_desktop.py")

The runner reloads this checkout, creates fixtures, and writes a JSON report
and exports under the ignored `validation_artifacts/qgis-desktop/` directory.
The report records QGIS/Python versions, source hashes, per-scenario results,
callback errors and restoration checks. The first failed run is retained as
`first-run.json`; the crash-interrupted run was captured in `progress.json`
before later reruns replaced that progress file. No commit or push was made.
