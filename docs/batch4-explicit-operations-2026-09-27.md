# Batch 4: explicit operational calculations and persisted planning inputs

## Changes

- Grid response requires explicit measurements, curves, protection thresholds and equipment ratings. Results do not claim compliance or verified anti-islanding.
- Heat-pump COP is now POST with explicit temperatures, heat demand, efficiency and compressor limits. SG-ready requires explicit setpoints, thresholds and grid lock. Grid lock no longer silently yields to a cold tank.
- Genset calculations require complete equipment parameters, initial state/timers and battery charge/discharge limits. The hard-coded 15 kW discharge trigger is removed. Low-load output cannot exceed load plus battery absorption; below-minimum loading is reported rather than hidden by surplus generation.
- Black-start is explicitly a non-executing scenario with per-step observations, not commissioned restoration. Hardware start/synchronization acknowledgements are not verified.
- Corresponding UI calculators start blank and render actual API responses. The translator's fake queued-command success button is removed; actual commands continue through existing capability/preview/confirmation workflows.
- GET/POST `/api/sites/{site_id}/planning-configuration` stores explicit dispatch equipment, billing-meter boundary and advisory battery/tariff configuration in site storage. Saves require the existing administrator dependency, device/site matching and an audited transaction. Configuration can be cleared with nulls. Settings UI exposes this workflow. No configuration enables dispatch.
- Prices require 24 consecutive UTC hours, provenance and USD (planner degradation cost is denominated in USD). This is not a tariff ingestion provider or a completed billing engine.

## Evidence and limits

Branch and HEAD were observed: `fix/real-data-engine-integration`, `897d611f63aa0636db8a2f955e7a8a195691f0b8`. Prior batch-3 logs were read in this session and do contain 1009 Python / 19 browser passes and zero exit markers. Those artifacts are prior runs, not proof for this batch.

No sidebar definitions or shared CSS were edited by batch 4. Earlier cumulative CSS changes remain in the working tree. No hardware command, commit or push was performed.

## Still open — do not describe this as system-wide completion

- Real provider commissioning and real-device acknowledgements require external credentials/equipment and acceptance evidence.
- Full billing calculation with effective tariff versions and aligned reactive-energy data is not implemented here; meter selection is now persisted, not a fabricated bill.
- Other explicit-input migrations remain, including raw predbat planning, PV/microgrid equipment inputs and vendor packet/decode defaults. Black-start still contains simulator assumptions and must not drive hardware.
- Full decoder provenance, EV stale/reset regressions, screenshot review and cumulative UI review are not closed by this batch.
- Heat-pump COP clamp/temperature-lift approximation and grid curve shape assumptions remain model limitations, not measured equipment performance.

Validation artifacts for this batch use `/tmp/solar-batch4-*`; final rerun artifacts use `/tmp/solar-batch4-final-*`. Consult exit markers and logs, not merely the existence of files.

Observed final checks: 20 browser tests passed with exit marker 0; Ruff across source/tests/browser tests passed; all static JavaScript syntax checks and `git diff --check` passed; final sdist/wheel build succeeded in `/tmp/solar-batch4-final-dist`.

Final full Python suite: **1017 passed**, 12 dependency deprecation warnings, exit marker **0**, in `/tmp/solar-batch4-final-python.log` and `/tmp/solar-batch4-final-python.exit`.