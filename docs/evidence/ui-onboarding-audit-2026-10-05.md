# Vendor audit and onboarding verification — 05/10/2026

## Scope

Branch `fix/real-data-engine-integration`, HEAD `af4f1b8ab70d91e24ca0b44bc8b71d1c9f274be0`; accumulated dirty worktree preserved. This slice adds `static/device-onboarding.js`, delegates the existing settings tab to it, uses shared `app.css`, and adds `ui_tests/test_onboarding_records.py`. Other modified files in Git status predate this slice; no claim to own their whole diff. Backend was read, not changed in this slice.

Research deliverables: [vendor feature backlog](../vendor-feature-backlog-2026-10-05.md) and [interface audit](../vendor-interface-audit-2026-10-05.md). Public manufacturer documentation only; no account use, application submission or hardware command. Source PDF inspection used the PDF skill, including visual inspection of Growatt's service/warranty pages; UI menu names were not treated as API specifications.

## UI behavior

- Four steps retained with existing owner links; left column matches the detailed onboarding reference composition more closely. No duplicate shell/sidebar/CSS.
- Platforms come from the provider catalogue, including Eybond; Bluesun filtering requires actual declared brand, not an assumption that SOLARMAN devices are Bluesun.
- Search actual inventory; inspect model/firmware/logger/last-seen/quality from device-detail API. Missing values remain unknown.
- Record links are explicitly not an electrical topology. No fake DC/AC edges, connection speed, successful scan or control acceptance.
- Source bindings are available in a collapsed technical section; source enums use existing translations.
- Late responses cannot replace an inspector whose selection was removed by filtering.
- Empty inspector and no-match state remain structured; zero hardware commands in contracts/captures.

## Executed checks

Python: `work/ui-venv/bin/python`, from repository root.

| Check | Observed result |
|---|---|
| `python -m pytest tests -q` | **1,810 passed**, 13 warnings, 303.13s. Before final frontend refinements; no backend changes afterward |
| Initial `python -m pytest ui_tests -q` | **86 passed, 1 failed**, 148.83s |
| After fixture setup correction, focused onboarding | **3 passed**, 4.52s |
| Full browser rerun | **87 passed**, 136.94s; overlapped final visual refinements, so not claimed as exclusively final-tree evidence |
| Final affected `python -m pytest ui_tests/test_onboarding_records.py ui_tests/test_ui_refinement.py -q` | **12 passed**, 17.51s, includes null/undefined and collapsed-source regression |
| Final `python -m ruff check src tests ui_tests scripts` | Passed |
| Final `node --experimental-vm-modules scripts/check-ui.cjs` | **51 modules** parsed/linked, not executed |
| Final `python -m build` | sdist and wheel built successfully |
| Final wheel/source byte comparison | **52 assets** match: 51 JS plus app.css |
| `python scripts/measure_code.py --update-doc` | Regenerated; 50 handwritten JS files plus excluded generated map asset; not a completion percentage |
| `git diff --check`; new-document local links | Passed |

The first failure was a test interception installed after login had already fetched inventory. Moving interception before login made the declared-OEM assertion exercise the intended response. No production default or fixture data was added to pass it.

Visual QA then found literal `null` rendered by DOM `replaceChildren`, plus an excessively long technical bindings table. Removed the null argument, added a regression, collapsed bindings and moved the stepper to the left column. These are actual QA corrections, not inferred from passing tests.

## Visual inspection

Detailed reference: `images/Screenshot 2026-09-13 133058.png`, not the conceptual SolarHub collage. Captured ten VI/EN states: empty inspector, selected record, no matching brand, 1024px and 430px. Desktop width 1600px. Viewed full desktop/mobile images; no page overflow at tested widths and no page errors.

Artifacts: `work/qa-feature-audit-20261005/`, ignored local screenshots, explicitly SIMULATOR data. They must never be used as production seeds or customer evidence. The marked fixture on port 8879 (`ui-feature-audit-20261005`) blocked outbound HTTP; browser requests were restricted to its loopback origin. Existing unrelated port 8767 was not modified.

The owned port-8879 fixture was stopped after QA. Temporary logs: `/tmp/solar-feature-audit-{ui,ui-final,ui-focused,be,js-final,build-final}.log`; commands/counts above preserve evidence even if temporary files disappear.

## Limits and remaining work

- This is one coherent UI slice, not a new visual sweep or acceptance of every screen. Previous 26-screen work remains historical evidence, not a claim that all mocks match pixel-for-pixel.
- No full QR/provisioning/physical discovery/electrical topology. The mock's sample devices, powers, RSSI and success badges are not fabricated.
- Deye real-account prerequisites and GoodWe platform/connector gaps remain open, not merely a styling task.
- Audit findings are documented; backend corrections were not silently bundled with UI work.
- No commit/push/deployment or real vendor authentication in this slice.
