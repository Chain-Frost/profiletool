# QGIS 3.44 / PyQt5 compatibility

## Verified automated result (15 October 2026)

**The previously failing QGIS 3.44 graphics callback regression is fixed in the
CI container.** The official `qgis/qgis:3.44.15-noble` image reports QGIS
3.44.15-Solothurn, Qt 5.15.13, PyQt 5.15.10 and bundled PyQtGraph 0.13.7.

- The original tests failed with repeated
  `TypeError: unable to convert a QVariant back to a Python object` in
  `pyqtgraph/graphicsItems/GraphicsObject.py::itemChange`. This was a
  **PyQt5/SIP issue with scene and parent pointer QVariant conversion**.
- A disposable test proved that omitting only this Python virtual override
  eliminated the errors: **2/2 lifecycle tests passed**, whereas the normal
  override still failed.
- The committed **Qt5-only implementation** now leaves the native C++
  `itemChange` virtual in place while subscribing to the native
  `QGraphicsObject.parentChanged`, `xChanged`, `yChanged`,
  `rotationChanged` and `scaleChanged` signals. This retains view
  registration and movement/bounds updates without global SIP changes.
  The Qt6 path still uses its original Python `itemChange`.
- The authoritative clean CI run passed **3/3** QGIS 3.44 tests, including
  a new parent/scene attachment and movement-driven bounds notification
  regression, with **no captured Qt callback exceptions**.
  Normal hosted quality checks (Ruff, CI-scoped strict Pyright,
  19 headless regressions) also passed.
- Experimental changes that tried to convert/return opaque QVariant
  wrappers or disable process-wide SIP autoconversion were **not retained**.
  The disposable diagnostic probe was removed.

## Reproduction

[QGIS 3.44 CI workflow](../.github/workflows/qgis-3.44.yml)
runs for PRs and relevant changes to the plugin, test and vendored graphics
code.

```bash
docker run --rm --entrypoint /bin/bash \
  -e QT_QPA_PLATFORM=offscreen \
  -e QGIS_PREFIX_PATH=/usr \
  -e PYTHONPATH=/tests_directory:/usr/share/qgis/python \
  -v "$PWD:/tests_directory/profiletool" \
  qgis/qgis:3.44.15-noble -euc \
  'python3 -m pytest -s -q /tests_directory/profiletool/tests/test_qgis_layer_lifecycle.py'
```

## Remaining merge acceptance

The CI result resolves the **reproducible Qt5 QVariant code blocker**, not
every compatibility or visual requirement:

- [ ] On native Windows/OSGeo4W QGIS 3.44, repeat the complete scenario
  suite and inspect plot rendering, scene/item parenting, curve visibility,
  axis scaling, tracking and backend switching.
- [ ] Manually inspect PDF, SVG, PNG and DXF output and confirm interaction
  with real representative project data in QGIS 3.44 and QGIS 4.x.
- [ ] Verify the final exact PR head passes all GitHub checks and obtain
  full strict QGIS-aware Pyright evidence for that head if required by
  the merge policy.
- [ ] Record any remaining QGIS 3.44-specific differences. In particular,
  Qt5 signal-driven notifications replace the legacy Python override; visual
  and interactive tests must confirm all needed view/transform updates.

Qt's `QGraphicsItem.itemChange` can adjust parent/scene values, so the native
virtual remains authoritative in Qt5. Avoid silent exception suppression or
returning `None` for change requests. QGIS 4/PyQt6 behaviour is unchanged.
