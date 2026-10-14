# QGIS 3.44 compatibility smoke test

## Verified result

- Tested the official QGIS 3.44.15 (Qt5/PyQt5) image `qgis/qgis:3.44.15-noble` in GitHub Actions.
- `tests/test_qgis_layer_lifecycle.py`: **one passes; one fails**. Plugin startup and unload pass; the source deletion/coordinate export lifecycle test fails because Qt emits Python callback exceptions during PyQtGraph graphics-item setup.
- Native error: `TypeError: unable to convert a QVariant back to a Python object` from vendored `pyqtgraph/graphicsItems/GraphicsObject.py`, during `itemChange`. The pre-change event values for scene/parent are opaque `PyQt5.QtCore.QVariant` wrappers in this environment.
- Existing QGIS 4.2.x tests and the standard Python/Ruff/headless-Pyright checks are separate and passing. **This QGIS 3.44 failure is a compatibility blocker, not a passing test.**
- Narrow Qt5 return/conversion experiments did **not** resolve the native failure and were reverted. Do not suppress the callback errors or treat the new smoke test as a substitute for complete QGIS 3.44 desktop/manual verification.

## Reproduction

The separate [QGIS 3.44 workflow](../.github/workflows/qgis-3.44.yml) runs this exact regression. It is manually dispatchable and automatically runs when the workflow, the lifecycle test, or the vendored graphics-item implementation changes.

A local Linux Docker reproduction is:

```bash
docker run --rm --entrypoint /bin/bash \
  -e QT_QPA_PLATFORM=offscreen \
  -e QGIS_PREFIX_PATH=/usr \
  -e PYTHONPATH=/tests_directory:/usr/share/qgis/python \
  -v "$PWD:/tests_directory/profiletool" \
  qgis/qgis:3.44.15-noble -euc \
  'python3 -m pytest -s -q /tests_directory/profiletool/tests/test_qgis_layer_lifecycle.py'
```

## Work remaining

Investigate the QGIS 3.44 PyQt5/SIP QVariant conversion boundary for graphics-item parent/scene changes, including whether it is specific to the QGIS Docker build. Compare the native Windows OSGeo4W QGIS 3.44 environment before changing vendored PyQtGraph. Preserve valid parent/scene changes and graphical scene ownership. Acceptance requires no captured Qt callback exceptions, both container tests passing, and no regression in QGIS 4.x; full desktop scenarios and human checks remain separate gates.
