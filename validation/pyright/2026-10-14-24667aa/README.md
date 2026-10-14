# QGIS-environment Pyright report

- Measurement date: 2026-10-14 (Australia/Perth).
- Source revision: `24667aa3b8b02522398f3fc93f9fca58494cb8ad`.
- Environment: OSGeo4W QGIS 4.2.1, Python 3.12.14, matching PyQt6 analysis definitions.
- Pyright version: `1.1.414`.
- Full strict configuration: `pyrightconfig.json`.
- Reported and collected errors: **2291**.
- Desktop validation remains paused; these files record type diagnostics only.

[Full diagnostics](pyright-full.json) and [grouped summary](pyright-summary.json)
are exact copies of the locally generated reports. The full report retains
local absolute source paths; the summary uses repository-relative paths.

## Reproduction

Run in the configured QGIS development terminal:

```powershell
cmd /c "python -m pyright --project pyrightconfig.json --outputjson > pyright-full.json"
python scripts/pyright_triage.py pyright-full.json --output pyright-summary.json
```

## SHA-256

- `pyright-full.json`: `597f199869537b1d12f181e02a73d03e12f63d08436aaf6d12a7dfa2c61cad08`
- `pyright-summary.json`: `3be9ed60b657b7bfc7dbecad40fb001aed45c8d436b0c90b2eadeef388249aa8`
