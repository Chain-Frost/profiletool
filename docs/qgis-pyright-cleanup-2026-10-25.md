# QGIS-aware typing cleanup

Validated locally on 25 October 2026, on branch `chore/qgis-pyright-cleanup`
against integrated master `6a89e386283678effe8a31f2a862ae8f518422a9`.

Full strict Pyright 1.1.411, using native OSGeo4W QGIS 4.2.3 / Python 3.12.15
and the repository's QGIS typing setup, now reports **0 errors, 0 warnings**
across 24 analysed files. The recorded baseline had 74 errors: 62 in tests
and 12 in plugin-owned plotting code and type contracts.

## Changes

- Import concrete PyQtGraph base classes inside `TYPE_CHECKING`, avoiding
  dynamically exported aliases that Pyright could not resolve as base classes.
- Complete plugin-owned contracts for plot/view geometry, ranges, axis labels,
  scale locking and forwarded widget methods. Allow omission of the curve pen,
  as the existing tests and bundled implementation already support.
- Annotate empty sample-series lists and test callback functions; explicitly
  narrow optional plot items and widgets before use.
- Use line-specific `reportPrivateUsage` exceptions for 11 intentional assertions
  against private state. Other diagnostics remain enabled on those statements.
- Remove three casts made redundant by the completed contracts.

Bundled dependencies and application behaviour are unchanged. Test assertions
retain their behavioural checks, with additional checks for missing widgets.

## Validation

| Check | Result |
| --- | --- |
| Full QGIS-aware Pyright | 0 errors, 0 warnings; 24 files |
| CI-scoped Pyright | 0 errors, 0 warnings |
| Exact quality-workflow Ruff baseline, Ruff 0.16.6 | Passed |
| Plugin source compilation | Passed |
| Native QGIS lifecycle and four headless test modules | 37 passed, no skips |
| `git diff --check` | Passed |

Native tests used an isolated OSGeo4W process with Qt's offscreen platform;
they did not alter the user's running QGIS session. Modules were
`test_qgis_layer_lifecycle`, `test_profile_regressions`, `test_pyright_triage`,
`test_ui_typing_contract` and `test_csv_export`.

An additional exploratory lint check including `profiletool_core.py`, which
the enforced workflow baseline excludes, found existing import-layout and
`zip()`-without-`strict` findings. They remain outside this typing change;
the enforced workflow baseline passes.

This is local validation evidence recorded before publication. No native Windows QGIS
3.44 run is claimed; consult the pull request for hosted CI and delivery status. The PR #5 human acceptance
documentation and prepared package remain separate and unchanged by this work.
Human acceptance is still outstanding; these results do not sign it off.

Raw diagnostic reports and the native test log remain under the ignored
`validation_artifacts/typing-cleanup/` directory in the isolated checkout.
