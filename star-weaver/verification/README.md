# Verification receipt — Star Weaver 0.2.0

Executed locally on Windows with Python 3.12.14, Node.js 24.21.0, PowerShell 7.6.6, and the in-app Chromium browser against the actual loopback service. Test state was isolated from the default runtime directory.

| Acceptance item | Result | Evidence |
|---|---|---|
| Actual skill, lineage, store and HTTP behavior | PASS | `python -B verify.py`: 75 tests in `unit-results.json` (25 skill, 32 hereditary, 18 persistence/HTTP) |
| Formal data shape | PASS | PowerShell `Test-Json`: skill fixture, lineage catalog, four direct pathway outputs and two generation outputs in `schema-results.json` |
| Browser learning, costs, completion and interruption | PASS | Five nodes learned; beacon charged focus/charge once, survived reload, emitted one output; axis loss aborted without rank loss or a new output |
| Browser save and recovery boundaries | PASS | Exported active action, imported it through the file chooser, resumed once; invalid import preserved current state; stale second view refreshed without retry |
| Browser lineage and multi-generation route | PASS | Generated fixed-seed first generation, registered it, generated the documented second generation, exported it, and applied a new untrained incarnation |
| Refund and scenario recovery | PASS | Exact growth refund observed; confirmed reset cleared generated parents and restored the initial scenario |
| Responsive and keyboard checks | PASS | Actual 390px viewport had no page-level horizontal overflow; graph scroll stayed inside its own region; keyboard tabs and seed submission worked |
| Reduced motion | PASS | Reduced-motion preference was recognized and the idle chamber had no nonzero animation durations; this is a bounded check, not accessibility certification |
| JavaScript syntax and whitespace | PASS | `node --check web/app.js`; `git diff --check` |
| Independent backend and lineage review | PASS | Four concrete recovery findings repaired and rechecked; details in `review-results.json` |
| Representative human feel and balance | HUMAN_CHECK | Technical execution cannot settle creative fit or player enjoyment |
| Full MAGECH kernel conformance | NOT_RUN | Complete frozen kernel text was not recovered in the bounded source review |
| GitHub Actions / remote CI | NOT_RUN | Checks were executed locally |

`browser-qa.json` records observed UI actions and limitations. The retained debugger-event window contained no exception events, but earlier events were evicted; no complete session-wide console claim is made. Deliberate invalid-save and stale-revision checks produced expected HTTP 400/409 responses. An initial missing favicon request was cosmetic.

Run `python -B verify.py` from this module to repeat the automated suite and refresh its receipt. Tests use temporary directories and synthetic data. The formal schemas remain editable alongside the runtime's stricter semantic and recomputation checks.

The approved skill baseline is authorized for implementation. Hereditary thresholds, synthetic profiles and branch suggestions remain experimental. Verification establishes observed software behavior, not canon adoption.
