# Profile Tool regression verification

The automatic regression suite covers project CRS chainage units (degrees for a
geographic project, metres for a projected project), geographic-project grades
computed from physical metre distances, transformed sampling
locations, exact zero raster values versus missing raster samples, invalid
slope segments, short profiles, and vector point-chainage deduplication.

## QGIS MCP / Codex-assisted desktop verification

For an optional Windows Codex-to-QGIS bridge, see [QGIS MCP setup and desktop validation](qgis-mcp-desktop-validation.md). It documents the local network-installed MCP server, Python 3.14, QGIS-side plugin, connection check, and an example validation prompt. This integration does not run in GitHub Actions and does not replace visual inspection.

## QGIS desktop verification still required

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
