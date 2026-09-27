# Batch 3: explicit phase and building calculations

## Verified environment

- Branch: `fix/real-data-engine-integration`.
- HEAD before this uncommitted batch: `897d611f63aa0636db8a2f955e7a8a195691f0b8`.
- Tool output is visible again. Earlier reported validation is superseded by the fresh runs below; this does not retrospectively establish the earlier logs.

## Changes

- Phase dispatch requires nested `measurement` (all voltage, current, active and reactive measurements) and `limits` (all inverter/battery limits and independent-phase capability). No missing equipment or measurements are filled from defaults.
- Phase UI starts with blank JSON, documents required fields, reads the actual neutral-current response, and does not promise compliance or voltage correction. This remains a manual advisory calculator, not provider telemetry.
- Engine enforces total absolute active-power throughput against inverter nameplate capacity, including opposing phase flows, before battery net-power limits.
- Building simulation requires explicit physical parameters, initial temperatures, heating input and aligned temperature/irradiance series. Missing irradiance is not padded with zero. Invalid/nonfinite data and time constants incompatible with the one-hour Euler integration are rejected.
- Both responses identify user-supplied estimated results and disabled dispatch. Request contracts intentionally reject legacy partial/default-driven payloads.
- This batch does not modify shared CSS or sidebar definitions.

## Fresh validation with visible output

- Focused API/engine suite: **35 passed**.
- Full Python suite: **1009 passed**, 12 dependency deprecation warnings; exit marker **0**.
- Full browser suite: **19 passed**; exit marker **0**, including the new phase workflow and existing navigation coverage.
- Ruff across source/tests/browser tests: passed.
- Syntax checks for every static JavaScript module: passed.
- `git diff --check`: passed.
- Source distribution and wheel build: passed, exit **0**.

Artifacts: `/tmp/solar-batch3-python.log`, `/tmp/solar-batch3-python.exit`,
`/tmp/solar-batch3-browser.log`, `/tmp/solar-batch3-browser.exit`,
`/tmp/solar-batch3-build.log`, `/tmp/solar-batch3-dist`.

## Still open

This is not completion of system-wide seed removal. Grid-code, heat-pump/SG-ready,
genset and black-start endpoints still contain defaults that require separate
contract/UI/engine remediation. Persisted dispatch/billing configuration workflows,
real provider commissioning, broader decoder review, and screenshot review remain
outstanding. No hardware commands, commit or push were performed in this batch.