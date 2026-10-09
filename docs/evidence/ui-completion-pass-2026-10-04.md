# UI calculation/history/network pass — 04 October 2026

Scope: continued user-authorized UI work, no production seed data, no live customer credentials, no device commands. Working branch `fix/real-data-engine-integration`; existing dirty changes preserved. This pass does not certify all 26 screens, production or vendor cross-account grants.

## Implemented

- `calculation-fields.js`: seven endpoint-specific schemas; blank required numbers and explicit choices, labels/units, percent→ratio conversion, nested groups, add/remove EV charger and black-start observation rows. No observation presets or JSON input. Optional inputs remain null, not zero.
- `advisory-calculator.js` and `ems-workspace.js`: use field schemas, disable fields/buttons while waiting, clear stale output on changes; result tables use actual API fields. SG-ready target temperature fixed to `target_tank_temp_c`; phase unknown VUF/CUF no longer becomes 0 or a green compliance claim. Advisory does not dispatch hardware.
- Site history: seven independent selected channels, same time axis with kW/% axes, per-channel source ambiguity/error states, recent-observation table, existing export workflow. Reject invalid unit/quality/time, preserve valid zero, connect only adjacent same-identity observations within five minutes; do not aggregate different devices, smooth or bridge gaps. Rendering bounded to selected existing points, not synthetic downsample values.
- Network: collectors/profiles counts from API, observed details and RS485 fields with missing markers, links to source/agent/network owners. Enrollment does not imply online, missing latency does not become 0 ms.
- Shared CSS: readable title hierarchy, spaced field groups, explicit result separation. Visual review found an older final `.card > h2` rule overriding the earlier size; corrected the effective rule to 16px. Chart selector now compact; two-line timestamp ticks, single timestamp displayed once; plot scrolls locally on narrow screens rather than shrinking all labels.
- `docs/deye-developer-setup-vi.md`: verified public registration/developer sign-in sequence and support inquiry template; no invented logged-in application fields, approval duration or cross-customer authorization guarantee.

## Consolidated verification actually run

Repository root: `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems`.

| Check | Result |
|---|---|
| `work/ui-venv/bin/pytest tests -q` | **1810 passed**, 13 dependency deprecation warnings, 301.77 seconds, exit 0. No backend code changed after this run. |
| `work/ui-venv/bin/pytest ui_tests -q` initial | **70 passed**, 114.87 seconds, exit 0. |
| Same full UI command after visual corrections and stronger chart tests | **70 passed**, 112.29 seconds, exit 0. |
| `work/ui-venv/bin/ruff check src tests ui_tests` | Passed. |
| `node --check` for every `src/solar_fleet/static/*.js` | Passed. |
| `work/ui-venv/bin/python -m build --no-isolation --outdir /tmp/solar-ui-completion-dist` | Built sdist and wheel successfully, exit 0. |

UI contracts cover explicit inputs with real local API responses, engineering empty validation/clear/add/remove, no JSON/presets, command list unchanged, chart unit/quality/gap/zero/timestamp cases, ambiguous/empty channel states, and 1600/1024/430px document overflow checks. Fixture identities and samples live only in isolated tests; outbound browser requests are blocked by the suite guard. These are not vendor/hardware tests.

Previous process IDs from the interrupted context were no longer accessible. Their unobserved completion is not claimed; the results above are from the fresh runs actually observed in this continuation.

## Visual review

- Reviewed detailed reference images for overview, portfolio, history, device inventory, control, TOU, alerts, journal, reports, onboarding, data sources, site settings, native settings, network, bulk, users, commissioning, map, maintenance and rules. Repeated screenshots/phone-frame examples are not new screens; the conceptual `131827` collage is not the design target. Embedded chat instructions in screenshots were treated as reference content, not new authority.
- Manually inspected current Vietnamese history desktop, engineer forms and network desktop using an owned isolated fixture on port 8879, run marker `ui-completion-20261004`. No real signed-in vendor session used.
- Reviewed actual English mobile network screenshot from `work/qa-audit/test_multichannel_and_network_empty_layouts_remain_honest.png`; labels/cards stack without document overflow. Other suite captures are in `work/qa-audit/` and can be regenerated with the commands above.
- Browser viewport tool did not change the existing in-app tab from 1600px to 430px as requested; its screenshot is **not** mobile evidence. Mobile evidence is the explicit Playwright suite viewport assertion and captured fixture image.
- A page reload resets the selected site to all plants; selecting the site again restores its subtabs. This existing navigation issue remains open, not silently treated as a network rendering failure.

## Open work / acceptance limits

- Not pixel-perfect across all screens. Existing chart density, model-specific panels, rich rule-builder/onboarding/bulk workflows, GIS basemap/satellite and phase/MPPT charts still require implementation and visual review.
- Blank engineer forms are more accessible than JSON but still long. ISO timestamp fields and engineering vocabulary need a further usability pass; no claim that non-specialists can commission electrical parameters safely.
- Network layout is truthful but not full mock topology/Wi-Fi/scan/mTLS/OTA parity. Unsupported backend capabilities remain visibly unavailable.
- Deye app A → unrelated account B grant is unverified. Public registration has no plant field, which does not establish permission for developer-only or multi-customer applications. Application creation form is behind login and was not inspected. No application keys or customer credentials were entered.
- Current Deye linking stays organization-admin-only, not self-service SaaS. GoodWe account platform (classic SEMS vs SEMS+) still needs identification; current adapter additionally requires plant IDs. Neither is declared end-to-end production-ready from these UI checks.
- No new push, commit, deployment, account registration, permission application, support email or hardware write performed.
