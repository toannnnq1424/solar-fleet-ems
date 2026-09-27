# Planner and PV follow-up

- `/api/predbat/plan` now requires every battery specification, explicit arbitrage choice, USD currency and tariff provenance. Unknown fields, missing parameters, unequal horizons, negative generation/load and SOC outside configured bounds are rejected. Horizons are 24–48 hourly values. Results are advisory and never enable dispatch.
- Planner discharge is consistently measured on the AC side; available energy accounts for discharge losses. Charging accounts for efficiency and configured maximum SOC, not a hard-coded 95%. Solar surplus during grid-charge windows is accounted for. Degradation throughput uses supplied usable capacity rather than an assumed 80% depth of discharge.
- `/api/solar/estimate` requires equipment losses/efficiency, date, site geometry and 24 explicit temperature/wind values. Results identify clear-sky simulation, not verified weather forecasts.
- Added required-field/API validation regressions and hour-by-hour battery/bus energy-conservation tests for arbitrage on and off.

Breaking contract: old partial predbat and PV requests now return validation errors. No static UI caller of either endpoint was found. No sidebar/CSS or hardware command workflow changed.

Observed checks: 18 operational-input tests passed after final test additions; Ruff and diff whitespace checks passed. Browser suite: 20 passed. Wheel/sdist build and static JavaScript syntax checks passed. Full Python rerun artifacts: `/tmp/solar-batch5-python.log` and `/tmp/solar-batch5-python.exit`.

Not completed by this follow-up: microgrid still registers synthetic equipment; clear-sky GET still has model defaults; actual effective-version billing, provider commissioning, remaining vendor defaults/decoder review and EV stale/reset review remain open. Planner remains a heuristic, not a proven optimal or commissioned dispatch controller. Raw forecast arrays have relative hours, not verified timestamp alignment. These limitations must not be interpreted as completed acceptance.