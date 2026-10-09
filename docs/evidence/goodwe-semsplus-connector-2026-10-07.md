# SEMS+ connector — controlled read-only trial, 07/10/2026

This follows the [portal baseline](goodwe-portal-qa-2026-10-07.md). It supersedes that
snapshot's statements that only classic SEMS exists and connectivity is boolean.
**Historical pre-trial snapshot.** A later authorized login/read trial and its fixes are
recorded in [08/10 live-read evidence](goodwe-live-read-ui-2026-10-08.md). No physical writes.

## Implemented slice

- Existing GoodWe registry/plugin selects `platform=sems_plus`; factory uses new
  `adapters/goodwe_plus.py`, not another controller or vendor namespace.
- Explicit hk/eu/au/us/cn server; email/password and mandatory user terms confirmation.
  Login, signed reads, local token refresh, typed/paginated discovery and explicit related
  devices; finite limits and strict route validation. No browser session, redirect or
  regional fallback, arbitrary endpoint, repeated blind login or raw vendor error exposure.
- POST `/api/connections/goodwe`: org-admin, CSRF, post-await session/config revision
  guards, authentication before vault persistence, duplicate/reconnect handling, local
  login limit and vendor cooldown retained across temporary adapter disposal.
- Shared Controller owns inventory/binding/ingestion. Native group/factor/unit/zero/null
  preserved; no canonical metric promotion. Missing source time/connectivity stays unknown.
  Successful linking enables periodic reads in the existing controller; the form now
  states this explicitly. Check/sync are separate diagnostics/actions, not a promise that
  no background discovery can happen before a manual sync click.
- UI: separate SEMS+ form, required blank server and unchecked consent, no app keys or
  manual plant IDs. Identity frozen in flight, password cleared on completion/failure,
  readable VI/EN errors, encrypted storage explanation, no duplicated cancel action.
- Direct browser inspection found SolarOne login autofilling vendor credential fields.
  Scoped credential names/autocomplete sections and new-password hints corrected this
  in the inspected browser; explicit email/password fields were then observed empty.
  Password-manager behavior elsewhere is not guaranteed by autocomplete hints.
- Unlinked rows now say “Not authenticated” instead of suggesting verified readiness.

## Sources / licensing

See [source audit](../vendor-source-audit.md) and `THIRD_PARTY_NOTICES.md` for pinned
MIT ioBroker source, official public regional configuration, and separately inspected
station-query facts from an unclear-license project (no code copied from that project).
Both source registries match. No source claim grants model/control acceptance.

## Consolidated verification

- `work/ui-venv/bin/python -m pytest tests -q`: **1,843 passed**, 13 dependency
  deprecation warnings, 306.01s; `/tmp/solar-semsplus-python-final.log`.
- `work/ui-venv/bin/python -m pytest ui_tests -q`: **98 passed**, 157.65s;
  `/tmp/solar-semsplus-ui-final.log`. Browser processes use isolated test servers and
  block outbound services; all account data is synthetic only under tests.
- Focused GoodWe adapter/link suites after safety fixes: **37 passed**, 5.90s.
- Ruff passed; all shipped JS parsed/linked with
  `node --experimental-vm-modules scripts/check-ui.cjs`; sdist/wheel built successfully.
  New adapter, connection API/form, MIT notice and source registry byte-match the wheel;
  both registry copies equal. Inventory regenerated with `scripts/measure_code.py --update-doc`.
  An initial JS command omitted the required VM flag and could not run; corrected run passed.
- Earlier whole backend run: 1,840 passed / 1 failed. New logout test expected 401/403
  but the existing shared post-await authority guard returns 409 session_authority_changed.
  Corrected the assertion, preserving no-save/closed-client checks. Not counted as a pass.
- Earlier focused browser rerun failed on an obsolete guidance text assertion; updated
  to the new two-platform guidance, then full 98-test rerun passed.
- Browser direct visual check: VI form on the empty fixture, no outbound request, no
  customer data. `work/qa-semsplus-20261007/form-empty-desktop.jpg` is the clean final
  empty form. Automated responsive checks cover 1600/1024/430px. An in-app viewport
  screenshot immediately after resizing was distorted and is not mobile acceptance.

## Remaining gates, not hidden by passing tests

Q1 connector now permits a **user-entered read-only trial**, not a supported/production
claim. Verify actual regional auth response, exact inventory counts/types/relationships,
native field shapes/units and timestamps against the portal. Regional gateway differences,
unsupported telemetry on an inventory type and multi-page contracts may still reject a
sync; fail closed instead of inserting a synthetic successful result. Missing timestamps
currently prevent native observations from becoming trusted real-time KPI data.

History/alarm/recovery/acknowledgment, canonical unit/sign mappings, model/logger/firmware,
refresh/expiry under real service behavior, partial read recovery and soak remain open.
All configuration, schedule deployment, battery/grid writes and diagnostics affecting
hardware stay locked pending exact-profile evidence and explicit physical-write approval.

UI is **not pixel-complete across 26 screens**. Shared shell/colors/icons and structural
coverage exist; account toolbar density and table width, deep EMS panel hierarchy,
network detail density, nested rule authoring, automatic exact-model chart assignment
and complete accessibility/visual acceptance remain work, not merely “waiting for login”.

No production seed data, commit, push or deployment. A localhost controller restart
for this trial is not a production rollout; retain its database/keyring and READ ONLY.
The existing empty local controller on port 8765 was gracefully restarted with
`SOLAR_WRITES_ENABLED=false`, unchanged database and keyring. The new endpoint rejects
GET with 405 and the served form matches source. OpenAPI is intentionally disabled (404),
so it was not used as route evidence. Login page opened for the user; no local account
reset or vendor credentials entered. Browser tab state was reset by the app during this
turn; previous portal session was not re-read or reused.
