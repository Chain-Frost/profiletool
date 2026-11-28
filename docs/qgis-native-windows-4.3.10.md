# Native Windows acceptance evidence for 4.3.10

Recorded 28 November 2026 on Windows 10 Pro (build 19045). The verified candidate is
`f22371dfd312f0afda200085de626ac5552c4a52` on `upstream/06-dxf-layer-names`.
Upstream master and the contribution base were both
`ca5223983629f625e904248d4cbb229fb6341716`. Fork master was
`54045fe12a15961d67abbdc9961a122eb8a1fb25`.

| Draft PR | Refreshed head |
| --- | --- |
| [#5](https://github.com/Chain-Frost/profiletool/pull/5) | `11c1b80d21799016838861dfffdd4f24e2543dca` before this evidence update |
| [#7](https://github.com/Chain-Frost/profiletool/pull/7) | `b0f426d38fa65b3519bd869d7cb1c11f9fb60dc1` |
| [#8](https://github.com/Chain-Frost/profiletool/pull/8) | `8818b7311afed35132538b7b68c20525f83b2214` |
| [#9](https://github.com/Chain-Frost/profiletool/pull/9) | `ac629f0ff3e7080af1e225a9b977996dc29f12cd` |
| [#10](https://github.com/Chain-Frost/profiletool/pull/10) | `73cd9e8650644aecea317171c7b9999d49745579` |
| [#11](https://github.com/Chain-Frost/profiletool/pull/11) | `645047d80f6fd31fd0526a2e063f400775259191` |
| [#12](https://github.com/Chain-Frost/profiletool/pull/12) | `f22371dfd312f0afda200085de626ac5552c4a52` |

The [exact-head independent Codex review of #12](https://github.com/Chain-Frost/profiletool/pull/12#issuecomment-7162554672)
completed with no findings. Hosted [quality](https://github.com/Chain-Frost/profiletool/actions/runs/45614939325)
(27 tests) and [Linux QGIS 3.44](https://github.com/Chain-Frost/profiletool/actions/runs/45614939329)
(15 tests) passed at that head.

## Package and native results

- `profiletool-4.3.10.zip` SHA-256
  `1c1d8c6075c8d97fd7c7f515eaecad203539276e843907c6ee70da2baa523026`.
  The ZIP contains 534 committed files selected by the candidate Makefile's
  packaging lists. ZIP integrity, version 4.3.10, and all 534 extracted files
  were verified in the two scripted and two human-test profiles.
- QGIS 4.2.3, Python 3.12.16, Qt 6.11.1, PyQt 6.12.0, GDAL 3.13.3
  came from the existing OSGeo4W installation. QGIS 3.44.15, Python 3.12.14,
  Qt 5.15.13, PyQt 5.15.11, GDAL 3.13.3 came from an isolated administrative
  extraction of the [official Windows MSI](https://download.qgis.org/downloads/QGIS-OSGeo4W-3.44.15-1.msi).
  Each used a disposable profile.
- Each environment passed **42 pytest regressions** (including 15 QGIS tests)
  and **17 scripted desktop scenario groups**. A separate desktop script
  passed seven supplemental checks and reproduced one inherited H15 deviation
  in each environment. Two package load/activate/unload cycles were exercised.
  The desktop-only distance inspection ran separately and returned 1:1 metre
  conversions in each direction. Scenario scripts adapt the fork's existing
  fixtures to start and unload the installed ZIP through QGIS.
- The contribution's Ruff 0.16.6 CI baseline, CI-scoped Pyright 1.1.414,
  plugin source compilation and ZIP integrity passed. An exploratory broader
  Ruff profile reported 465 diagnostics and five format differences. This
  wider run used the available local Ruff configuration, outside the
  contribution's enforced rule and file set.
- Strict QGIS-aware Pyright 1.1.414 used the fork master include/exclude scope
  because the contribution carries only a scoped configuration. Across 24
  files it reported **14 errors, 0 warnings** with the QGIS 4/PyQt6 interpreter
  and matching wheel stubs. All 14 were in `test_qgis_graphics.py`
  (unknown signal/member types and one optional member access). With the
  QGIS 3.44 interpreter and matching PyQt5 wheel stubs it reported
  **474 errors, 0 warnings**, dominated by unknown Qt member types through
  the compatibility bindings. Full typing remains open in both environments.

## Desktop and export observations

The scripted results exercise H01–H13 and H15–H21 to varying degrees. The
source fixtures include a multiband gapped raster, duplicate and colliding
names, disconnected multipart lines, mixed-CRS points, a 100 ft / 10 ft
grade, a real MDAL scalar mesh, a Selafin mesh and a rotated raster. Independent
pixel/attribute, geometry, unit and scalar references were prepared for the
human matrix. Both native QGIS versions sampled the real mixed-CRS bed at
0.5, 1.5, 2.5, 3.5 and 4.5. In the rotated raster reproduction the raw
one-column gap vanished in the provider and the wider gap still produced
two missing samples. The plugin matched provider-visible samples.

- **H15 deviation on both versions.** Switching from a populated PyQtGraph
  graph to Matplotlib replaced the widget and left the existing curve
  blank until a redraw. The upstream switch handler also replaces the
  widget without redrawing. The earlier scripted scenarios explicitly
  refreshed the plot after switching. This record preserves upstream
  behavior and the reviewed contribution scope. Human disposition remains
  open. Reproduce by drawing a raster profile, changing the backend and
  inspecting the plot before any profile redraw.
- Both backends produced CSV with the correct metre chainage, heights
  including zero and the blank at 20 m. PNG and SVG reopened through Qt.
  Matplotlib PDF and PostScript rendered via Ghostscript after a profile
  redraw. The reference series has segments from (0 m, 0) to (10 m, 2)
  and (30 m, 4) to (40 m, 5).
- The synthetic Selafin file loaded through MDAL. The legacy Selafin
  plugin-layer selector (H14) still requires a compatible external provider.
- H01 still needs the human Install from ZIP dialog workflow. H01–H21
  remain unsigned for both versions. The desktop evidence uses scripted
  interactions including QtTest and automated dialog selections.

## Actual Autodesk DXF verification

DWG TrueView 2027 (26.0.60.0, Autodesk Core Engine X.60.0.0) opened the
candidate 2D and 3D files via its native console. Its `LIST` output
independently confirmed seven distinct source layers and 14 polylines in
each drawing. Checks covered duplicate and sanitization-colliding raster
names, case, a 40-character name, reserved names and Unicode. Each source
had two open polylines with two vertices each. Zero was retained and the
NoData point at 20 m was omitted without a bridging segment.

| Mode | Independently matched vertices | DXF SHA-256 |
| --- | --- | --- |
| 2D | (0, 0, 0), (10, 2, 0) and (30, 4, 0), (40, 5, 0) | `64ef67c192e0bb49df26b294d161a86cafc876b437717102adf1b453dfb88155` |
| 3D | X=400005, 400015, 400035, 400045; Y=6499955; Z=0, 2, 4, 5 | `e0364daa96a15099769b618b23e154fafefa8092642fc2965c29e86ed9d57f75` |

The same Autodesk engine rejected both 4.3.9 control files at
`645047d80f6fd31fd0526a2e063f400775259191` with
`Improper table entry name RASTER-0.200 on line 532` and discarded the
drawings. This reproduces [upstream #105](https://github.com/PANOimagen/profiletool/issues/105)
and verifies that both candidate fixture exports reopen in Autodesk's
engine. Interactive CAD inspection is part of human H19.

Return to the [human acceptance matrix](qgis-human-acceptance.md) for the
per-environment visual and physical-input checks and signed recommendation.
