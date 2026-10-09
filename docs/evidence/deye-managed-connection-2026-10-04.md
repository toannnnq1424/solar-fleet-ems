# Managed Deye application and email/password connection — 04/10/2026

User explicitly authorized this core-backend slice alongside continued UI work. Working tree on `fix/real-data-engine-integration`, based on `af4f1b8`, already contained extensive uncommitted changes; these were preserved. No commit, push, deployment, real-account login or hardware command was performed.

## Implemented

- Organization administrator configures a Deye application per region, separately from the account login form. App ID/App Secret are encrypted by the existing vault and never returned by these APIs. Save is configuration only, not proof of vendor authorization. Revision checking prevents stale overwrites; application changes/disable pause dependent integrations, invalidate cached adapters and require reconnection.
- Account form asks for Deye email/password and region; it automatically selects the only configured region when possible. It explains that this is the Deye password, not the Gmail mailbox password. Missing application configuration does not ask for a password. Advanced bring-your-own API configuration remains available.
- `POST /api/connections/deye` uses the existing official Deye adapter to authenticate before saving the integration. Plaintext password is transformed by the adapter's existing SHA-256 preparation; the reusable hash and application credentials are encrypted in the vault. The hash remains a credential-equivalent secret, not harmless public data. Token remains in the short-lived adapter and is not returned or persisted by this route.
- Server checks organization-admin role, CSRF, current session and application/integration revision across vendor I/O and again before commit, including change-and-restore races. Uses the controller poll lock, a 30-second auth timeout, and a process-local six-attempts-per-minute guard. These are not a distributed abuse-prevention or vendor-quota guarantee.
- Success means authenticated only: response explicitly says inventory not synchronized and control not enabled. Existing discovery/poll paths handle later reads; control commissioning gates remain unchanged. Login does not call equipment commands or import sample inventory. Existing diagnostic state is reset to NOT_CHECKED, and diagnostics now tolerate a null unchecked timestamp.
- UI has separate administrator and account dialogs, password masking/clearing, readable translated errors, blocked fields while submitting and a reconnect action. It uses shared CSS, SVG icons, a compact 700px desktop dialog and local horizontal scrolling for readable mobile account columns. Removed the accidental form-divider styling from account header actions.

## Evidence / source scope

Read the manufacturer's [Open MCP tool documentation](https://developer.deyecloud.com/openmcp/docs/deye-open-mcp-tools.html), specifically `account_token` / `get_access_token`, on 2026-10-04. It documents application credentials plus account credentials and `eu/am/india` centers. This implementation independently orchestrates the existing adapter; it adds no dependency, copied upstream code, private mobile API, browser scraping or invented refresh endpoint. Both source registries record this review separately from their original snapshot date/hash.

This does **not** establish that any application key can access arbitrary customers. Exact application approval/account grants, supported customer ownership, quotas, region and live expiry/renewal behavior require separate vendor and live verification.

## Executed verification

Use the ignored `work/ui-venv` environment from repository root:

```sh
work/ui-venv/bin/pytest tests -q
work/ui-venv/bin/pytest ui_tests -q
work/ui-venv/bin/pytest ui_tests/test_deye_connection.py ui_tests/test_clear_ui_contract.py ui_tests/test_vendor_form_labels.py -q
work/ui-venv/bin/pytest tests/test_deye_connection.py tests/test_source_registry.py -q
work/ui-venv/bin/ruff check .
for js_file in src/solar_fleet/static/*.js; do node --check "$js_file" || exit 1; done
work/ui-venv/bin/python -m build --no-isolation --outdir /tmp/solar-deye-managed-dist
work/ui-venv/bin/python scripts/measure_code.py --update-doc
git diff --check
```

- Full backend: **1,810 passed**, 13 dependency deprecation warnings, **298.96s**.
- Full browser initial pass: **66 passed**, **107.83s**. After visual corrections and one additional mobile regression: **11 affected tests passed**, **18.34s**.
- Final full browser rerun on the corrected UI: **67 passed**, **103.96s**. Inventory and whitespace checks passed; the owned manual fixture process on port 8879 was stopped after capture.
- Deye/source-registry rerun after review metadata update: **21 passed**, 2 dependency warnings, **7.39s**.
- Ruff and all JavaScript syntax checks passed. Initial Ruff found import ordering and compressed test statements; these were corrected, with no suppressed rules. Source distribution and wheel built successfully, including a repeated build after the final CSS/source metadata changes.

Nineteen new backend cases cover the three regions, role/CSRF denial, encrypted persistence/redaction, existing read diagnostic reuse, malformed/failed auth, duplicate linking, application rotation/disable/reconnect, app/session/role/integration change-and-restore races, rate limiting, input validation and transactional application-save rollback. No network reaches Deye: these use the actual adapter with MockTransport. Browser authentication outcomes are explicitly intercepted test responses, not evidence of a live successful login. Browser application setup/disable uses the isolated fixture's actual API and storage.

Visual QA compared account mockup `images/Screenshot 2026-09-13 192858.png` with the account page and dialogs. Local capture script: `/Users/toanlamsaoduocc/Documents/Codex/2026-09-30/users-toanlamsaoduocc-desktop/work/deye_connection_capture.py`; captures in sibling `deye-connection/`. Repeated after final CSS at 1600px and 430px, VI/EN, missing/configured application and empty credential states. All seven captures reported no document overflow and no browser exceptions; a separate browser test checks a 1024px dialog and mobile scroll-to-actions. The fixture blocks outbound transport and browser requests to external origins. Screenshots contain only synthetic fixture identities; no production seeds were added. This is sampled visual inspection, not pixel-diff acceptance of all 26 screens.

## Limits / next checkpoint

- Linking remains restricted to an organization-wide administrator, matching existing permissions. This is **not** general viewer/customer self-service. Customer ownership, consent, tenant isolation and delegated account management still need a separately reviewed design and implementation.
- Configure genuinely authorized application keys before trying an actual account. A Gmail address is only the Deye login identifier; Google sign-in/OAuth is not implemented. MFA/CAPTCHA/federated-only accounts are not bypassed.
- Reconnection currently matches the stored email exactly; there is no cross-region or legacy-integration migration wizard. Application disable pauses use locally, not remote token revocation. Secrets remain encrypted until normal retention/removal is explicitly implemented.
- No live token renewal, discovery, telemetry reconciliation, long-running polling, quota/soak or physical-control acceptance was performed. Not production-ready on the strength of these tests.
- UI still has broader unfinished work: remaining EMS JSON calculators, multichannel/phase charts, map basemap, network/onboarding/rollout detail and whole-system visual/usability acceptance. R10 remains IN_PROGRESS; the simplified SolarHub collage is not the design target.
