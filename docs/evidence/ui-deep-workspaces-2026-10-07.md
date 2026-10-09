# Deep UI follow-up — 7 October 2026

Branch `fix/real-data-engine-integration`, existing dirty worktree preserved. This is
an uncommitted frontend batch, not a claim that the entire diff from HEAD belongs to it.
No production seeds, vendor credentials, controller writes, deployment or push.

## Implemented

- EMS action editor loads the selected device's actual capabilities and parameter
  constraints. Bounded numbers, enum, boolean and supported nested schemas use the
  shared form renderer, initially blank. Changing intent/device clears previous
  parameters. Late responses are fenced. Existing parameters that cannot be rendered
  are preserved unchanged, not silently dropped; editing requires a usable profile.
- EMS main page has a searchable rule directory, read-only condition/action inspector,
  explicit AND/freshness requirements and a dry-run results panel with readable failure
  reasons. The existing monitoring owner is moved below the primary workspace. No new
  rule engine, activation or physical dispatch path was introduced.
- Network screen uses the detailed `133208` mock's list/configuration/diagram/diagnostic
  layout. Stored connection profile selection shows declared equipment/address/port/
  Modbus/baud/parity/DHCP separately from observed connectivity. Missing certificates,
  diagnostics and RS485 observations remain unknown. Links go to existing owners.
  Dashed topology represents **only declared device/profile associations**; no invented
  logger-agent-cloud edges, online status or successful ping.
- Realtime/history retain four specialist panels: AC phase channels, DC/PV strings,
  battery and latency. Channel selection is explicit, source-separated and same-unit;
  AC/DC naming is not inferred from V/A. Battery choices use existing canonical metrics.
  A display choice does not create a mapping or promote UNVERIFIED quality. Empty
  specialist charts remain visible. Automatic exact-model mapping remains unbuilt.
- Offline map exposes coastline/name/status layers and preserves display preferences
  across selection. NORMAL (observations available) is not treated as online.

## Verification

- Initial focused browser batch: **17 passed**, 26.37s.
- Initial full browser batch: **93 passed, 1 failed**, 145.62s. New test fixture POST
  lacked mandatory Origin/CSRF headers; protections were not weakened.
- Following affected batch: **9 passed**, 13.55s, after correcting fixture setup,
  reload sequencing and using a registered intent when testing obsolete parameters.
- Backend: **1,810 passed**, 13 deprecation warnings, 293.97s. No backend runtime
  changes in this batch.
- Ruff, module linking and package build executed; final verification is recorded below
  after remaining visual/refinement checks. A successful build is not hardware acceptance.
- Captures in `work/qa-deep-ui-20261007/` use an explicitly marked in-memory simulator,
  never customer data. Initial 11 EN/VI/desktop/tablet/mobile states had no page errors
  or page overflow. Visual inspection found the old monitoring block preceding the
  main EMS workspace; its placement and network fact spacing were corrected.

### Final consolidated result

- **96 browser tests passed**, 150.38s (`python -m pytest ui_tests -q`).
  The preceding run had 95 passes and a test-driver timestamp issue: Chromium
  canonicalizes datetime-local seconds `:00` away. Corrected the fixture's timestamp
  string, retaining real UI entry and API assertions; no production validation bypass.
- **1,810 backend tests passed**, as recorded above; no BE runtime edits afterwards.
- Ruff passed; **55 JS modules** parsed/linked (54 handwritten + generated map data).
  Final sdist/wheel built; **56 assets** (55 JS + app.css) byte-match source.
- Final capture sweep: **16 states**, network/EMS/map/realtime × VI/EN × 1600/430,
  no page exceptions, no horizontal page overflow, no commands. Earlier capture
  attempts used a wrong Vietnamese locator and an initialization script forcing EN;
  those captures were not VI evidence. Corrected to use the real language picker and
  await the actual workspace, then overwrote the final-state captures.
- Inventory regenerated and `git diff --check` passed. These checks are local,
  simulator-based evidence, not production, physical-device or pixel-diff acceptance.

The official SEMS+ login tab was opened and left for user handoff. No fields were
filled, no terms were accepted, no cookies/tokens were exported and no account was
inspected. Awaiting the user to complete login for a read-only portal baseline.

## Still bounded / not implemented

Nested OR conditions, automatic phase/MPPT mapping, production forecast dispatch,
real network diagnostic execution/Wi-Fi changes/mTLS/OTA, street/satellite layers,
clustering UX and full pixel/accessibility acceptance remain open. These are engineering
items, **not all solved by a user login**. All 26 screens and 15 sidebar owners remain
in scope; this batch adds no competing UI shell or universal vendor facade.

## Account QA gate

On 7 October, official [SEMS+](https://semsplus.goodwe.com/) exposes email/password
login. GoodWe's [product page](https://en.goodwe.com/semsplus-series-smart-energy-management-system)
says existing accounts can sign in; the [legacy portal](https://eu.semsportal.com/)
points to SEMS+. This does not verify the user's account/region, nor compatibility of
SolarOne's legacy connector. A user-assisted **read-only vendor-portal inspection**
can establish that baseline before modifying the connector. It is not successful
SolarOne end-to-end QA and does not unlock control.

Deye's SolarOne email/password path still needs the application's keys and grants
described in `deye-developer-setup-vi.md`. Do not ask for secrets in chat or save tokens,
cookies, raw customer responses or identifying screenshots in Git.
