# Real-data remediation — batch 1, 27/09/2026

Branch: `fix/real-data-engine-integration`, starting HEAD `897d611f63aa0636db8a2f955e7a8a195691f0b8`.
User approved implementation and requires removal of operational seed data. No commit/push or hardware access.

## Implemented scope

- Restored packaged registry from the reviewed registry. Four additional unreviewed records are preserved in `docs/evidence/post-feb82ef-unreviewed-sources.json`, not accepted as commissioned evidence.
- SmartESS local client has no embedded device state. Polling fails explicitly without transport; client `unlocked` cannot produce execution/readback success. Existing registered Eybond cloud adapter remains the real read path.
- Standalone GoodWe mock login is rejected. Decoder routes require supplied payloads; actual account authentication/sync remains in the registry/vault workflow.
- Growatt/Solis compiler flags cannot grant commissioning. Unknown exact models and vendor substring matches cannot acquire register/alarm semantics. Known catalogue models are uncommissioned references.
- Battery health reads recent GOOD observations, returns unknown for unavailable lifetime/warranty fields. Directional energy integration uses actual timestamps, one binding, no gaps over 15 minutes, explicit window coverage; never extrapolates seven-day storage into lifetime health.
- Site tariff endpoint integrates an explicitly configured `billing_meter_device_id`; it does not assume signed-grid semantics, tariffs, reactive energy or savings. Billing calculation integration remains incomplete.
- Site dispatch uses `dispatch_device_id`, verified historical EWMA, fresh SOC, explicit complete `dispatch_config` battery parameters, 24 timestamp-aligned USD hourly prices and tariff provenance. Advisory only; no commands or schedules created. This configuration currently requires stored metadata; a supported configuration editor is still needed.
- Schedule/EMS share the storage-backed dispatch view. Removed fake “schedule created” action, static maintenance health values, meter sample register payload and grid-compliance success. Several device decoder forms now require explicit register JSON. Removed per-element style assignments; preserve sidebar/shared stylesheet.
- Restored existing `energy-transfer` animation name while retaining dash-offset behavior; browser motion/pause/reduced-motion contract retained unchanged.

## Not complete — do not claim seed-free production

Remaining inventory includes numeric prefilled technical tools in EMS/control/vendor tabs, market/EV fleet demo scenarios, default device parameters in Phase D APIs and engine dataclasses, empty/offline decoder defaults, tariff catalogue applicability, and public-source revalidation of post-baseline protocol claims. `load_predictor` cold-start seed curves were removed, but the full tree still needs semantic review (a grep match alone cannot distinguish algorithm constants from fake measurements).

No local SmartESS transport or vendor capability has been commissioned by this change. No manufacturer/provider/hardware acceptance or complete screenshot review. Existing factory defaults used by standalone calculations are not proof of installed equipment configuration.

## Batch 2 — explicit EV and market calculation contracts

- Removed the three seeded vehicles and three seeded market bids/prices from EMS and reports. Blank, labeled JSON inputs now reach real calculation APIs; these inputs are user-supplied, not verified telemetry. No operational observations or provider records are fabricated or persisted.
- EV requests require actual charger identity, SOC, target, current limits, voltage and phase count plus site load/surplus/breaker inputs. Reject duplicate IDs, missing fields, nonfinite values, unsupported modes and inverted current limits. Phase switching is disabled for this stateless calculator; results explicitly say ESTIMATED, dispatch disabled.
- Corrected UI/engine field mismatches (charger list, current, power, SOC, headroom; market bid counts and estimated net settlement). Removed unsupported EVN/reactive compliance and actual charging/trading claims from these cards.
- EV engine resets stale allocations for disconnected/disabled ports, rounds current down rather than exceeding the power budget, and does not draw grid power just to meet a three-phase PV-only minimum.
- Market requests require explicit per-hour prices and all bid fields, reject duplicate IDs and aggregate hourly quantities above capacity. Engine validates all needed prices before changing bid state; no implicit 50 EUR/MWh fallback. Calculation responses explicitly state no market submission.
- This is **not** a provider/storage integration for EV or markets. They remain manual advisory calculators. Supported persistent dispatch/billing configuration editors, other thermal/grid/genset tools and remaining protocol/default inventory are still unfinished.

Batch-2 Python validation: **993 passed**, 12 dependency warnings, 102.05s. Ruff passed including browser tests; JavaScript syntax and whitespace checks passed; wheel/sdist rebuilt successfully. Initial browser regression exposed that a terminal-based edit had not executed, leaving the old market card; reapplied with the patch tool and reran browser tests. Final browser result is recorded after completion. Logs: `/tmp/solar-batch2-pytest-final.log`, `/tmp/solar-batch2-browser-rerun.log`, `/tmp/solar-batch2-build.log`.

## Verification

Batch-2 final browser rerun: **18 passed in 28.83s**, exit 0, including explicit EV and market UI → API → engine workflows. This does not establish provider/hardware acceptance or complete seed removal.

Initial consolidated run: 951 passed / 24 failed Python tests. All 24 failures were old `VERIFIED_AUDITED` expectations; contracts are being updated to require `UNCOMMISSIONED_REFERENCE` without removing register/decoder assertions. Browser: 17 passed. JavaScript syntax/linkage and sdist/wheel build passed. Final rerun recorded below when complete.

Logs: `/tmp/solar-real-data-{pytest,browser,js,build,ruff}.log`. These are ephemeral local artifacts.

Final batch-1 verification: **977 Python tests passed**, 12 dependency deprecation warnings, 96.30 seconds; **17 browser tests passed**, 27.89 seconds. Ruff and git diff whitespace checks passed. All 32 JavaScript modules passed syntax/import linkage. Final sdist/wheel build passed. Exit markers for final Python, browser and build are all 0. Final logs: `/tmp/solar-real-data-pytest-final.log`, `/tmp/solar-real-data-build-final.log`. Added storage-to-dispatch success test, zero/latest SOH and site-isolation regressions, and actual-time/coverage/source-conflict tests. No tests touched real provider credentials or hardware. These results certify only this batch, not completion of the remaining inventory above.