# Microgrid inputs, observation gaps and EV reset regressions

## Implemented

- Microgrid simulation no longer registers fabricated inverter/load records. Equipment lists (including explicitly empty lists), complete equipment state and controller thresholds must be supplied. Duplicate identifiers, nested omissions, nonfinite inputs and out-of-range values are rejected. The response explicitly identifies one advisory step from grid-connected state, not hardware acknowledgement or a persistent controller session.
- Clear-sky GET requires date and altitude as well as bounded, finite coordinates. Results identify an unverified clear-sky model, not measured production/weather.
- Directional energy integration no longer bridges known rejected samples (bad/stale quality, wrong units, missing binding, nonfinite or negative power). Bad timestamps fail the integration window closed; bad duplicate samples block adjacent intervals. Good intervals away from the outage remain available with partial coverage. This affects observed tariff energy and battery throughput, not just a standalone calculator.
- EV repeated-cycle regressions verify old allocations are cleared after disconnection, mode off, target SOC, headroom loss and solar loss. These are allocation-reset tests, not proof of telemetry freshness or hardware stopping.

## Compatibility and scope

Legacy partial microgrid requests and clear-sky requests omitting date/altitude now fail validation. No static UI callers of these endpoints were found. This batch did not edit sidebar/CSS or the verified hardware command workflow; earlier cumulative working-tree changes remain present.

The microgrid engine still has internal multi-step simulator assumptions (grid-forming capability, load-management margins and acknowledgements). The API deliberately exposes only one step from grid-connected state and does not claim commissioned island operation.

## Validation

- Full Python suite: **1044 passed**, 12 dependency deprecation warnings; exit code 0.
- Browser suite: **20 passed**; exit code 0.
- Focused suite after expanding nested-load, threshold and invalid-date assertions: **47 passed**, one dependency deprecation warning. The terminal wrapper reported closure after printing the completed result; the test log records completion.
- Ruff, JavaScript syntax and diff whitespace checks passed.
- Source distribution and wheel build succeeded; exit code 0.

Full-run logs and exit markers are under `/tmp/solar-batch6-{python,browser,build}.*`; the final focused log is `/tmp/solar-batch6-focused-final.log`. The full suite was collected before the final test-only assertion expansion; the focused rerun covers those additions. No production code changed after the full run started.

## Remaining work

Effective-version billing storage/calculation and aligned reactive-energy billing are not implemented. Existing tariff analysis still returns a null bill rather than inventing rates. Historical EVN rate tables require authoritative review and must not be represented as current verified tariffs. Vendor/API defaults and decoder provenance need continued review. EV allocation-reset coverage does not establish measurement-age acceptance. External provider/device commissioning still requires real credentials/equipment and evidence.