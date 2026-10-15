# Codex-assisted desktop validation with QGIS MCP

Use this on the **Windows desktop that has QGIS installed**, while verifying
[Profile Tool PR #1](https://github.com/Chain-Frost/profiletool/pull/1).
The QGIS MCP server is separate from the **Profile Tool** plugin being tested.

## Configure the local MCP server

The Codex configuration already exists at
`%USERPROFILE%\.codex\config.toml`. Add this block at the end,
avoiding a second `[mcp_servers.qgis]` section if it already exists:

```toml
[mcp_servers.qgis]
command = "C:\\Program Files\\Python314\\python.exe"
args = ["-B", "-m", "qgis_mcp.server"]
```

Install the MCP server from the approved internal source into the **same Python
3.14 interpreter** specified above. The drive must be accessible to that
interpreter, for example from a regular PowerShell terminal:

```powershell
& "C:\Program Files\Python314\python.exe" -m pip install --user "Q:\BGER\PER\RPRT\qgis-mcp"
& "C:\Program Files\Python314\python.exe" -B -c "import mcp, qgis_mcp.server; print('QGIS MCP imports OK')"
```

An unqualified `python -m pip` may select a different interpreter, leaving
Codex unable to import the package even if installation appeared successful.
The `-B` flag prevents bytecode file creation.

This installation source is **site-specific**. It is not tracked by the
Profile Tool repository and is not installed or tested by its CI.

## Start the QGIS end of the bridge

1. Install **QGIS MCP** ([nkarasiak/qgis-mcp](https://github.com/nkarasiak/qgis-mcp))
   from QGIS's plugin manager or the approved internal plugin package.
2. Restart QGIS, show the QGIS MCP dock and click **Start Server**.
3. Restart Codex so it reloads the updated MCP configuration.
4. In Codex, invoke QGIS MCP's **ping** tool. Expect an affirmative response
   (normally `{"pong": true}`); if available, also run **diagnose**.
5. Keep the QGIS MCP plugin and external `qgis_mcp.server` versions
   compatible; mismatched revisions may expose commands that the QGIS plugin
   cannot handle.

The upstream qgis-mcp README explains how its external MCP server connects
over a local socket to the QGIS-side plugin. Merely importing Python modules
does **not** verify a live QGIS connection.

## Validate the Profile Tool checkout

Use a disposable QGIS test project, not a live production model. Load the
feature branch checkout `fix/profile-correctness-reliability` of
`Chain-Frost/profiletool` as the **Profile Tool** plugin under test.

The existing [validation matrix](validation-matrix.md) remains the acceptance
checklist. Codex/QGIS MCP can inspect the project, load fixtures, query feature
selections, confirm layer CRSs and automate repeatable checks, but graphical
profile rendering, clicking the precise selected member of a multipart feature
and DXF appearance still need independent inspection or documented screenshots.

Suggested Codex validation prompt:

> Connect to the running QGIS session using QGIS MCP. First ping and diagnose
> the connection. Use a disposable project and verify the Profile Tool feature
> branch against docs/validation-matrix.md. Add rasters to Profile Tool manually
> as designed; do not replace its UI with QGIS's native elevation profile.
> Preserve and check existing feature selections. Check geographic vs projected
> project chainage, mixed source CRSs, raster NoData holes, the clicked part of
> a multipart line, vector point buffers and profile-point elevations. Record
> measured values, CRS details, observed UI behaviour and any exceptions.
> Do not modify the source repository or production layers during validation.
> Report tests as passed, failed or not run; include screenshots where useful.

## Troubleshooting

- **Imports fail:** verify the exact interpreter and user-site package
  installation. Use the Python 3.14 path from `config.toml`.
- **Ping fails:** verify QGIS is running and the QGIS MCP dock server is started;
  then restart Codex and confirm that the client loaded the QGIS MCP definition.
- **Tools are missing:** check server/plugin version alignment using **diagnose**.
- **GUI interaction is incomplete:** use a manual mouse/UI verification for that
  test and record the result rather than assuming a passing MCP query is enough.
