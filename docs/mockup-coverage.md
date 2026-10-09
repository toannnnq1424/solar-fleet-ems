# Current assessment and energy-flow slice — 09/10/2026

**All 26 screens / 15 sidebar owners remain in scope; user explicitly rejects current
UI as unfinished.** Three flow modes, illustrative projected SVG equipment, freshness-gated
direction, shared titled-card expansion and daily-chart inspector are implemented;
not full pixel parity, all-chart coverage or a production certificate.
[Final verification](evidence/energy-flow-ui-2026-10-09.md): **1,894 backend / 107 browser
passed**, 13 backend deprecation warnings; Ruff, 63 JS syntax checks and package build passed.
Final live visual re-acceptance and the unfinished workflows remain open.

[Assessment](project-assessment-2026-10-09.md): estimated core completion 35–40%, or about
30% including planned DE/AI; explicitly subjective acceptance-weighted estimates, not LOC.
[Reference manifest](evidence/ui-reference-manifest-2026-10-09.md): 12 user images kept
outside Git; quick-control E09.11 added to the backlog. Resume only on the next user command.

# GoodWe live native reads and UI correction — 08/10/2026 (historical)

Freshness follow-up: shared device dialog/monitor receipt GET every 15s; SEMS+ account
collection minimum 60s, slower policies/rotation/quotas preserved, no sub-second SLA.
Manual vendor-read button in common shell and device monitoring; plant scope includes
vendor/account label (login identity restricted to org admins). Verification and known
limits are in the dated evidence; no assertion of complete sidebar data/pixel parity.
Resume through the [current backlog checkpoint](vendor-feature-backlog-2026-10-05.md#resume-checkpoint).
Latest software slice: 1,894 backend / 104 browser passed; latest-client live QA and
BUG-LIVE-02 (lower readings table retains a different snapshot) remain open.

**Follow-up after the user's blank-overview complaint and 11 GoodWe screenshots:**
station flow/statistics plus per-inverter telecounting now have separate optional
shared report contracts and explicit vendor-reported UI. Live site: 6 populated KPI,
8 dated energy rows. Live both inverters: own serial/AC/DC/rated power and five energy
periods; shared detail/realtime panel and scoped equipment table. These are monitoring
snapshots, not GOOD telemetry, billing, commissioning or all-screen pixel parity.
See [latest evidence](evidence/goodwe-live-read-ui-2026-10-08.md) for test sequence and
the live statistics-decoder correction. The 26-screen/15-owner inventory still applies.

Screens 06/21/26 now separate native-read availability from verified measurements and
physical connectivity. Shared searchable/grouped inspector, VI/EN aliases, optional
technical codes, typed inventory filters, unknown connectivity, honest alarm/sync states
and account action hierarchy: [actual verification](evidence/goodwe-live-read-ui-2026-10-08.md).
Earlier native-inspector slice: BE 1,860 passed / UI 100 passed. Live inverter/meter readings visible; logger no-data
explained. All 15 sidebar owners manually opened with empty and real-account state.
All 26 screens remain in scope; **not** blanket pixel or full workflow acceptance.

## Previous SEMS+ read-only connection slice — 07/10/2026

The existing account screen now has a separate SEMS+ email/password/server form,
consent, encrypted persistence and auth/check/sync workflow through the same GoodWe
plugin. Unknown connectivity survives the shared data path. [Verification and limits](evidence/goodwe-semsplus-connector-2026-10-07.md):
1,843 backend and 98 browser tests passed. Ready for a user-entered controlled read
trial, not live acceptance or full mock pixel completion. All 26 screens/15 owners remain.

## Previous GoodWe portal QA and connection guidance — 07/10/2026

[Sanitized baseline](evidence/goodwe-portal-qa-2026-10-07.md): official portal sign-in
was observed, not a SolarOne connector acceptance. Screen 21 now separates portal
review from connector readiness; SEMS+ never opens the legacy credential form.
Classic adapter no longer invents positive connectivity. All 26 screens / 15 owners
remain unchanged; full pixel acceptance and the unfinished engineering below remain open.

## Deep EMS/network/observation UI — 07/10/2026

Capability-shaped draft actions, three-column rule inspection/dry-run results, detailed
declared-network layout, four explicitly assigned specialist observation panels and offline
map layers now extend the existing owners. [Evidence and boundaries](evidence/ui-deep-workspaces-2026-10-07.md).
No production seed data or new physical capability. Full pixel acceptance, nested rules,
automatic model mapping and live integration are not inferred from this UI work.

## Prior observation inspector UI — 07/10/2026

Device history and realtime monitoring now share a same-unit two-channel comparison,
loaded-history time filter, primary-channel min/max/count/time summary and source/quality table.
Device ID is part of channel identity. Unverified native observations require explicit opt-in
and hollow markers; this is display-only, not a profile/quality upgrade. Canonical metric labels
are translated; unknown native fields are not guessed into phase/MPPT names.
See [verification and limits](evidence/ui-observation-inspector-2026-10-07.md).
All 26 screens / 15 sidebar owners remain in scope; no full pixel acceptance or live-account readiness claim.

## Prior vendor audit and record-based onboarding — 05/10/2026

New: [vendor feature backlog](vendor-feature-backlog-2026-10-05.md),
[actual interface audit](vendor-interface-audit-2026-10-05.md), and
[UI evidence](evidence/ui-onboarding-audit-2026-10-05.md).
Onboarding now includes all registered platforms and declared OEM brands, inventory search,
actual record inspection with late-response fencing, collapsed technical bindings and responsive
left-column steps. Empty details stay visible without fictional connection results or electrical wiring.
Row 13 and the device-management estimate below are updated; all 26 screens / 15 sidebar owners
remain in scope. No claim of full pixel acceptance, complete integration or production readiness.

## Prior account readiness, EMS editor and TOU interactions — 04/10/2026

Latest slice: shared three-column EMS draft editor with blank values and observed metric selection;
TOU pointer/keyboard resize, cancel and touch-friendly destination selection;
account preflight without password collection, GoodWe platform warning and explicit global-sync scope.
[Evidence and remaining gates](evidence/ui-account-readiness-2026-10-04.md).
[Vendor API setup guides](vendor-api-access-guide-vi.md) distinguish credentials from customer grants.
No seed data added to production; no vendor login or hardware command. The 26-screen inventory
remains partly implemented: this does not assert all screens match their mockups pixel-for-pixel.

## Prior whole-workspace UI review — 04/10/2026

Current checkpoint: shared spacing, empty tables, mobile navigation and persistent plant scope;
geographic land map using actual GPS; three-column bulk editor; source/model field editors;
device monitoring and empty mini-charts; all 15 protocol panels now avoid fabricated readings.
**78 browser tests passed**, including a genuinely empty in-memory installation across 31 routes.
The visual sweep covered 32 primary/site views and 29 deeper desktop + 5 mobile states.
See [verification, changes and remaining gaps](evidence/ui-whole-workspace-2026-10-04.md).
This is a whole-workspace implementation/review pass, **not pixel-perfect acceptance or a claim
that all product workflows are implemented**. No production seed data, vendor login or hardware write.
Rows and ownership below supersede older historical checkpoints where they differ.

## Prior explicit calculation fields, multichannel history and network UI — 04/10/2026

Latest slice: seven blank schema-driven calculator forms replace JSON/presets; site history offers seven channels on shared time and separate kW/% axes; network keeps collectors/profiles/observed metadata visible when empty. Shared card headings/spacing and chart-local mobile scrolling refined. See [actual checks and limitations](evidence/ui-completion-pass-2026-10-04.md). No operational seed data or new hardware capability. Rows 06/08/17/24 and the estimate table below are updated; all 26 screens remain in scope, not accepted as pixel-perfect. [Deye setup guide](deye-developer-setup-vi.md) separates verified registration steps from unconfirmed cross-customer application grants.

## Managed Deye connection + UI — 04/10/2026

Latest authorized slice: separate administrator application setup from end-user-facing Deye email/password entry, actual authentication before persistence, revision/session fences and safe reconnection. Account dialogs use the shared shell/styles; mobile table retains readable columns with local horizontal scroll. See [evidence and limitations](evidence/deye-managed-connection-2026-10-04.md). This is not general customer self-service: linking remains organization-admin-only, and live Deye application grants are unverified. No production seed data or hardware commands added.

## Prior UI-first interactions

Latest: [Visual TOU, reports and explicit market fields](evidence/ui-interactions-2026-10-04.md). Added draft calendar click/keyboard/drag/copy/undo, mixed report charts and four mini-panels, compact archive/download rows, and a non-JSON market scenario editor. Existing 15-sidebar/26-screen responsibilities remain unchanged. This updates rows 09/12 and the TOU/Reports estimates below; it does not close overall pixel or production acceptance.

## UI-first reference pass — 03/10/2026

Latest: [UI refinement and authorized VND rounding correction](evidence/ui-refinement-2026-10-03.md) supersedes the older failed-rounding checkpoint. Added blank weekly matrix, non-JSON hourly prices, compact controls, alert tables/charts and deeper empty-state fixes. Shared styling does not close the 26-screen feature inventory or the estimate → code → unbuilt → acceptance matrix below. The simple SolarHub collage remains excluded as a style target.

Current user priority overrides the older backend-first sequence: finish UI before further core/adapter work. See [actual UI evidence and remaining gaps](evidence/ui-reference-pass-2026-10-03.md). Detailed mockups define the style and full feature scope; the simple SolarHub collage is conceptual only.

Shared shell/icons, site overview, portfolio/onboarding, vendor-account guidance, grouped control capabilities and saved weekly timeline have been revised against actual data paths. Three local plant illustrations now map only to declared installation type with a visible illustration label; unknown devices/types keep SVG fallbacks. No random model pictures or mock customer data were introduced.

This is **not closure of R10, all 26 screens or production readiness**. All current site tabs and capability groups remain discoverable, but basemaps, advanced chart/editor parity, long technical screens and live integrations still have unfinished work. Email/password-only Deye support is not implemented by changing form labels. UI/browser tests and visual QA are recorded separately from backend/hardware acceptance in the evidence file. Older dated conclusions below are historical and are not evidence for the current tree.

# R03/R06/R08 follow-up — declared import rates

Settings → Site configuration owns the append-only effective VND rate editor;
EMS owns observed import cost/coverage and declared sources. Both reuse the shared
shell and global styles, with VI/EN labels. API provides bounded interval provenance;
optional report/export snapshots now freeze source rows, rates and revisions in
CSV/XLSX/HTML ([evidence](evidence/report-cost-snapshot-2026-09-28.md)). This adds no sidebar/screen: the existing
15-sidebar/26-screen matrix remains applicable. Estimate → implementation: versioned
declared rates and interval estimates now exist; utility billing, correction workflow,
rate supersession, archive retention and full visual/mobile acceptance remain open. Completion requires
those workflows and release/hardware gates, not LOC. Counts regenerated with
`scripts/measure_code.py --update-doc`; [actual verification](evidence/import-rates-2026-09-28.md).

# Đợt rộng R04/R06/R09/R10/R11 — 28/09/2026

Settings planning now uses labeled device/battery fields and explicit USD hourly-price JSON,
not a whole-configuration JSON editor. BE requires the revision returned by GET; stale save
returns 409, session authority is rechecked inside the write transaction, and audit remains atomic.
FE preserves inputs and stops blind retry after conflicts. Advisory only: no command or billing
acceptance. Added API and browser contracts; consolidated evidence is recorded in
[wide-batch evidence](evidence/remediation-wide-2026-09-28.md).

R04: 30 local projects reconciled, 43 locked source files match; OpenEMS inventory differs and
Solis license remains unresolved. R11: separate browser CI job added (hosted execution pending).
R02: alerts revalidates after acquiring persistence lock; four second-connection ABA regressions.
The existing 15-sidebar/26-screen matrix and estimate → code → unbuilt → acceptance table remain
applicable: effective billing, optimizer, operational recovery and full visual acceptance are still
unbuilt/unverified, not merely waiting for credentials. No new screen or commissioned profile.

# R01/R02 selected-object read fences

Poll baseline follow-up: capture Device models, provenance and revisions in one synchronous transaction, released before latest I/O. Two regressions reproduced before fix; focused controller/authority 104 passed, browser 33 passed, Ruff/JS/build/diff passed. Backend pending at `/tmp/solar-poll-capture-backend.{log,exit}`. Alerts persistence lock-boundary remains a source-inspected next task; no FE or multiprocess acceptance claimed.

Poll lock-boundary follow-up: repeat full context validation inside the persistence transaction. Four regressions cover selected heartbeat conflicts and second-connection ABA for returned/omitted devices. Focused 68 passed; browser 33 passed; backend independently verified 1644 passed/12 warnings, exit 0 in `/tmp/solar-poll-lock-backend.{log,exit}`. Full-body heartbeat fences remain; no FE/protocol changes or multiprocess acceptance.

Command continuation: new scope-versioned plans fence selected device/site/integration/primary binding; legacy plans retain kind-wide digest semantics and non-sending replay. Full-device heartbeat invalidation remains. Eleven new synthetic cases; focused 211 passed. Browser initially 32 passed/1 maintenance timeout, unchanged full rerun 33 passed; cause unresolved. Final backend 1640 passed/12 warnings, exit 0 at `/tmp/solar-command-scope-backend.{log,exit}`. No FE/protocol or commissioned capability change; R01/R02 remain open.

Discovery follow-up: selected transport integration revision replaces the integration-wide fence; shared/unknown inventory remains kind-wide. Six extra paused-network cases cover unrelated integration and selected delete/restore versus inventory ABA. No UI/protocol/control change. Browser 33 passed; final backend 1629 passed/12 warnings, exit 0 in `/tmp/solar-discovery-backend.{log,exit}`. Command revision semantics and legacy plan compatibility remain open.

Follow-up storage correction: entity primary-key UPDATE now revises both old/new identity even with unchanged body; legacy trigger migration and rollback have two regressions. Final source: 1623 backend passed/12 warnings, 33 browser passed; focused 154 passed. No FE/protocol/commissioning changes; command/discovery dependency and heartbeat refinements remain open. See leading findings for artifacts and scope limits.

Poll and shared HTTP vendor history/configuration/alerts now capture only selected identity revisions, preserving full-body snapshots and tombstone ABA detection. Eight new synthetic cases cover unrelated writes and storage absence/ABA/rollback/second-connection/reopen. Focused 123 passed; Ruff/JS/build/diff check passed; full-suite evidence pending in the leading findings section. No screen, FE, adapter or commissioned capability changes; the existing 26-screen inventory remains applicable. Discovery/command kind-wide fences and selected-device heartbeat invalidation remain unbuilt refinements, not closed acceptance items.

# R01/R02 user/session authority batch

Durable per-user/per-session SQLite revisions now fence captured principals across shared read/command/rollout/reconciliation owners; command plans retain operator revision and WebSocket closes on changed authority, including ABA. No new screen, sidebar, stylesheet, protocol mapping or commissioned control. Synthetic tests cover storage migration/rollback/reopen/second connection, unrelated identities, HTTP boundaries, post-ACK quarantine, atomic rollout preview and WebSocket. Final evidence is in the leading findings section; inventory regenerated separately from tests. Existing 26-screen estimate → code → unbuilt → acceptance tables remain applicable.

Still unbuilt: exact-object entity fencing and fleet-scale availability (kind-wide heartbeat invalidation persists), complete transport/history/report/security-surface matrices, remaining background authority, restart/multiprocess/crash recovery and visual/hardware acceptance. Session snapshot reads now use a write-reserving transaction; contention is unmeasured. R01/R02 remain open.

# R01/R02 consolidated authority/telemetry batch

Backend now has persistent entity ABA fences for command preview/confirm/send and guarded read owners, shared ReadCloud budget/response authority checks, and cloud latest per-sample validation. Existing device/overview/EMS consumers use the same latest owner; no new FE workflow, stylesheet, sidebar or 26-screen responsibility was added. Simulator regressions cover rollback/reopen/tombstones, post-ACK quarantine, HTTP boundary counts, malformed cloud siblings and route/poll/discovery/reconciliation ABA. Final consolidated verification is recorded in remediation findings; until final artifacts are verified this batch is not a passed full-tree attestation.

Verification completed: 1542 backend passed / 12 warnings, 33 browser passed, exit 0. Full runs precede the final idempotent-replay-only refinement, which passed a subsequent 185-case command-family rerun; not an exact-final-tree full-suite claim. Final Ruff/build/inventory/whitespace checks passed; 33-module JS linkage passed. No manual visual or hardware acceptance. See findings for artifact paths and initial failures.

Unbuilt scope remains engineering work, not credential-only blockers: exact-object revisions (current kind-wide fences may invalidate on unrelated heartbeat), user/session ABA, remaining transports/owners and history/report consumer matrix, restart/multiprocess safety, security surface audit and hardware acceptance. Existing estimate → code → unbuilt → acceptance tables remain applicable; no LOC-based completion claim. R01/R02 stay open.

# R01.20 malformed agent observation checkpoint

Stored agent telemetry can no longer break device reads through malformed envelopes or invalid Sample fields; valid authorized siblings remain visible. No screen/sidebar/tab responsibility or FE code changed; no new visual/hardware acceptance claimed. Fourteen synthetic route cases; reproducer 9 failed/5 passed (one fixture corrected afterwards, no pre-fix claim), focused 43 passed/1 warning, exit 0. Ruff/JS/build passed, inventory regenerated; final backend 1501 passed/12 warnings and browser 33 passed, both exit 0 (`/tmp/solar-r0120-{backend,browser}.{log,exit}`). Cloud data and other consumers, general revision/ABA and remaining read transports are still unbuilt audit/remediation scope, not credential-only blockers. R01/R02 remain open.

# R01.19 internal read/order guard checkpoint

Final backend verification supersedes pending wording below: **1487 passed / 12 warnings**, exit 0 (`/tmp/solar-r0119-backend.log`, `/tmp/solar-r0119-backend.exit`), including all final additions.

Task-local guards now connect preview/execution/reconciliation/configuration reads to Deye auth-lock/budget/HTTP boundaries. No FE behavior or 26-screen responsibility changed. Synthetic pre-fix 7 failed/4 passed; focused 206 passed/1 warning, browser 33 passed, exit 0. Ruff/whitespace/JS linkage/build passed; inventory regenerated. Full backend pending in `/tmp/solar-r0119-backend.log`. Other adapters/read owners, general ABA, malformed telemetry and hardware acceptance remain open; R01/R02 not closed. Findings document exact evidence and scope.

# R01.18 partial checkpoint

Credential replacement now updates an opaque integration revision atomically and rejects stale cached authentication. Initial backend log verified: 1455 passed / 12 warnings (no separate exit artifact). After 19 additional queued/wave/credential cases, focused suite 144 passed / 1 warning and browser 33 passed, both exit 0; no final expanded full-tree run claimed. Initial pre-fix cases: 3 failed / 1 passed; no pre-fix claim for the expansion. Ruff/whitespace/build and JS syntax/linkage passed; inventory regenerated. No FE behavior or 26-screen responsibility changed. No hardware acceptance; general ABA, internal read/order transport awaits and malformed telemetry remain open. R01/R02 not closed.

## R01.17 command-origin / whole-wave context — 28/09/2026

Direct confirm routes now retain originating sessions; queued rollouts recheck live context of all targets. Net 28 added cases, including two-step order-wait quarantine and real device-lock contention. Corrected pre-fix 7 failed/45 passed; focused 151 passed/1 warning, browser 33 passed; final backend 1451 passed/12 warnings, exit 0. Ruff/JS/build passed, inventory regenerated. No frontend behavior or hardware acceptance added; 26-screen responsibilities and unfinished workflow criteria unchanged. ABA/credentials/internal read transport/malformed telemetry remain open; R01/R02 not closed. See findings for exact scope.

## R01.16 queued rollout safety — 28/09/2026

Final backend: **1420 passed / 12 warnings**, exit 0; supersedes pending status below. Collected before the final three cases, separately passed in the 99-case focused run; not a 1423-case full-tree attestation.

Queued rollout tasks now inherit origin-session/source/cancellation guards across device lock, configuration and transport/readback boundaries. Added 19 synthetic cases; focused 99 passed/1 warning, browser 33 passed; full backend pending. Ruff/JS/build passed and inventory regenerated. No new FE behavior or hardware acceptance; existing 26-screen responsibilities, estimates and unfinished-work criteria unchanged. Snapshot/ABA, credential revisions, exhaustive owner and transport-race coverage remain open. R01/R02 are not closed. See findings for artifact and fixture limitations.

## R01.15 rollout request/wave safety — 28/09/2026

Rollout preview now rechecks session, source and all target contexts and persists the wave atomically; confirm/cancel recheck authority after runtime.lock. Added 20 synthetic regression cases (pre-fix 15 failures / 5 controls); focused 113 passed, browser 33 passed. Final backend **1404 passed / 12 warnings**, exit 0; final-tree targeted rerun 20 passed. See findings for artifact scope and local-only limitations. No UI runtime or hardware acceptance added; 26-screen responsibilities and unfinished workflow criteria unchanged. Queued execution session/source fencing, ABA/credentials and malformed telemetry remain release-blocking; R01/R02 remain open.

## R01.14 preview safety verification — 28/09/2026

Final local verification: backend **1384 passed/12 warnings**, browser **33 passed**, both exit 0. Source/test/static hash check verified 264 unchanged files. These results supersede the pending-run status below; see findings for commands/artifacts and evidence limits.

Preview engine now revalidates live authority/context after lock and configuration awaits; both direct HTTP preview entry points recheck the originating session before plan persistence/disclosure. Added 24 synthetic cases: pre-fix 20 failed/4 controls passed; focused post-fix control/preview/reconciliation suite 80 passed/1 warning. Ruff, JS linkage and build passed; full backend/browser results pending. No frontend runtime feature or hardware acceptance added; 26-screen responsibilities and unfinished workflow criteria remain unchanged. Rollout session/revisions, credential/ABA and malformed telemetry remain release-blocking gates. R01/R02 remain open.

## R01.13 safety verification — 27/09/2026

Final local results: backend **1360 passed/12 warnings**, separate browser **33 passed**, mapping **18 passed/1 warning**, all exit 0. Ruff, JS syntax/linkage and no-isolation build passed; inventory updated. Evidence limits, including an unsuccessful durable hash-manifest verification command, are recorded in findings. Python 3.14 local results do not establish CI 3.12 matrix acceptance.

Account diagnostics (including admin alias), command reconciliation and weather/site overview now revalidate authority/context after vendor awaits. Failed account checks discard their adapter cache; denied reconciliation retains TIMEOUT quarantine. Latest reads reject stale caller Device before cloud/agent fallback. Synthetic regressions reproduce four confirmed gaps (RF-014–017); focused suites: 131 passed/12 warnings and 16 passed/1 warning. Final full-suite evidence is recorded in remediation-findings.md. No new frontend feature or hardware acceptance; unchanged 26-screen ownership/incomplete-workflow tables remain applicable. Preview/rollout authority, credential/ABA revisions, malformed samples and complete owner audit remain open release gates, not merely a need for credentials.

## R01.12 safety verification — 27/09/2026

Cloud latest read rejects inconsistent envelope/sample provenance and disabled current integration/binding, including native payload. Ingest stores site/binding; legacy snapshots remain NO_DATA until valid poll. Eleven failing reproducers now pass; focused 82 passed/1 warning. Final backend 1305 passed/12 warnings; browser 33 passed; Ruff, JS linkage, build, inventory and diff checks passed. Explicit synthetic cloud fixtures replace provenance-less test snapshots, without production bypass. No FE runtime capability or hardware acceptance added. Evidence in remediation-findings.md; access-check and direct store consumers remain open.

## R01.11 safety verification — 27/09/2026

Poll now validates device vendor and site id/vendor/source before transport and rejects selected-site changes across latest await. Five failing reproducers now pass; controller 41 passed, browser 33 passed. Ruff, JS syntax/linkage, build and inventory update passed. No FE or hardware capability added; cloud latest read provenance and access-check context/session/cache remain open. Backend full-suite result is recorded in remediation-findings.md.

## R01.10 safety verification — 27/09/2026

History/configuration now share alerts' pre-read context validation and post-await live session/scope/provenance revalidation (RF-013). Event barriers reproduced 14 failures before fix; unchanged controls pass. Three access-check barrier controls verify poll/disable route exclusion at stations/devices/latest, not complete DessMonitor cache correctness. Final focused 51 passed/1 warning, backend 1288 passed/12 warnings, browser separately 33 passed; Ruff, JS syntax/linkage, build, inventory and diff checks passed. No FE/commissioned capability changes or visual/hardware acceptance. R01.11 retains poll site/vendor identity, cloud latest and access-check context/session/cache audit.

# R01.9 safety verification — 27/09/2026

Alerts now reject changed authorization/integration/device/binding context after transport await; raw alerts and incident correlation persist atomically. Agent latest filters current device allowlist, snapshot site, sample device/binding/source. Synthetic regressions: 10 pre-fix failures plus two unchanged controls; final focused 49 passed, backend 1268 passed (12 warnings), browser separately 33 passed. Ruff/JS syntax/build/inventory/diff checks passed. No FE workflow or hardware capability added. Access-check/cache concurrency, poll site/vendor identity and cloud latest/history/configuration provenance remain open (R01.10); see remediation-findings.md RF-011/012. No production or visual acceptance implied.

# Control safety remediation — 27/09/2026

R01.8 rejects pre-existing cloud binding identity mismatches before latest requests and rolls back the entire latest persistence batch on decode/storage failure. Added 17 regression cases, including real DessMonitor with synthetic HTTP proving rejected discovery requires cache refresh before poll. Final backend 1256 passed (12 warnings), browser separately 33 passed, focused 45 passed (1 warning); Ruff/JS/build/inventory/diff verified. Covers final R01.7 refinements; no new UI/hardware acceptance. Alarm/agent/latest-read provenance, concurrent access-check and site-row/vendor identity remain audit work.

R01.7 stages discovery reads, revalidates context after each await and commits inventory atomically. Rediscovery preserves telemetry disable; poll excludes disabled/missing bindings and skips empty latest calls. Eleven regression cases added; final controller suite 20 passed. No FE screen or hardware capability added. Adapter internal cache, pre-existing binding identity mismatch and latest batch atomicity remain open; full-suite snapshot limitations are recorded in the findings register.

R01.6 guards poll persistence against integration/adapter/device/binding changes during latest await, including missing-device responses. Six poll and three existing-session report scope tests added. Backend 1228 passed (12 warnings); browser separately 33 passed; Ruff/JS/build/inventory verified. No UI screens or hardware capabilities added. Discovery awaits, pre-disabled telemetry bindings and full batch atomicity remain outside this acceptance.

R01.5 adds two real integration-disable route/controller tests with Deye MockTransport (authentication and budget barriers): no control request, adapter cache removed, TIMEOUT/quarantine retained. Focused backend validation: 99 passed, 1 warning; no runtime/UI changes or new full-suite/browser acceptance in this batch.

R01.4 extends the engine guard through Deye authentication/budget awaits to the HTTP request boundary; eight transport-barrier cases pass, full backend 1217 and browser 33 passed. Browser simulator follows the callback contract; no FE screen, vendor mapping or hardware capability added. Route-level integration-disable concurrency and HTTP-client internal awaits remain outside this slice's acceptance.

R01.3 adds a persisted preview binding fingerprint and five simulator regressions; no new FE screen or commissioned capability. Transport auth/budget-await revocation remains open as RF-006 in the remediation findings. The 26-screen feature inventory and unbuilt scope are unchanged.

RF-002 engine slice: revalidate current authority/binding immediately before each send; six simulator regressions, 1204 backend and 33 browser tests passed. No screen, FE workflow or hardware capability added. Existing 26-screen inventory and unbuilt acceptance scope remain unchanged. See [remediation findings](remediation-findings.md) for evidence and remaining transport/preview boundaries.

# Verified continuation — shared observation time and EMS VI/EN

Account-form follow-up: [VI/EN vendor forms](vendor-form-localization-2026-09-27.md)
adds meaningful credential labels, explicit GoodWe/Sungrow selection guidance
and browser checks across eight existing provider forms in both languages.
No new sidebar responsibility, client or commissioned capability is introduced;
broader submission/error/permission and visual acceptance remain open.

See [continuation evidence](continuation-observations-2026-09-27.md): shared
observed-energy arithmetic now uses UTC elapsed time across DST; the existing
EMS billing-meter card localizes known statuses/explanations and prevents
overlapping button submissions. No sidebar responsibilities changed. Bills
remain unknown without effective tariffs and aligned measurements. Verified:
1198 Python and 31 isolated browser tests; not live/hardware acceptance.
Additional legacy reuse and full vendor-form/visual coverage remain unbuilt.

# Consolidated sidebar continuation — 27 September 2026

Post-merge safety review: see [default-branch and legacy-source review](master-merge-review-2026-09-27.md).
The 15 sidebar destinations remain unchanged. Eight incoming simulated read
routes and seven uncommissioned standalone command routes are explicitly locked;
the seven affected device subtabs display a shared VI/EN warning. Live transport,
native field validation and full translation remain unbuilt/unverified for those
new paths. Existing scoped adapters are not replaced by these tools.

Growatt follow-up: removed an unused, incorrect global error table in the newly
merged client; reviewed errors are now scoped to `/v1/plant/details`, with unknown
pairs left unknown. This is a pure lookup, not live response handling or token
renewal. Sidebar, UI warnings and 503/409 gates are unchanged; full form VI/EN
translation and live wiring remain open. Verification is recorded in the
default-branch review linked above.

Confirmed BE/FE contract fixes: site-scoped devices/firmware, correct firmware
response fields and retry errors, truthful commissioning navigation, viewer report
permissions and alert filter labels. Backend notification configuration now uses
validated partial updates, Vault secrets and global-admin scope; an end-to-end
notification editor/delivery service is still unbuilt. Catalogue billing scenarios
validate full explicit inputs and remain advisory, not effective-version billing.

The 15-entry / 26-screen inventory and estimate-versus-completion boundaries below
remain unchanged. Full Python rerun: 1080 passed, 12 dependency warnings. Full
browser rerun after maintenance visual correction: 29 passed. Ruff, JavaScript
syntax, whitespace and package build passed.
see `sidebar-followup-2026-09-27.md` for the first-run finding, verification logs,
visual sampling and unresolved engineering. No hardware capability was enabled.

# EV advisory follow-up — 27 September 2026

EMS coordination now distinguishes unknown observation freshness from recent
user-declared timestamps, rejects supplied stale/future or timezone-naive inputs,
and shows actual vehicle identity in allocation results. BE/FE and API/browser
regressions are implemented; this remains a non-persistent advisory calculator,
not trusted telemetry or commissioned EV control. The 15-sidebar/26-screen scope
is unchanged. Effective billing, device-specific freshness/provenance and cumulative
visual acceptance remain unbuilt/unverified as detailed in
`docs/sidebar-followup-2026-09-27.md`. This batch: 56 targeted Python and 3 browser
tests passed; full suites were not rerun. No dispatch capability was enabled.

# Plant declaration follow-up — 27 September 2026

Wizard technical fields now persist as inventory-only `declared_specs`; no
controller limits or billing rates are applied. Benchmarking removes arbitrary
ranking and unknown-as-inspection labels, formats missing metrics and fixes site
navigation. Verified: 1054 Python tests (12 warnings), 25 browser tests, Ruff,
JS syntax, whitespace and build. See `sidebar-followup-2026-09-27.md` for scope;
this is not completion of all 15 sidebar workflows or hardware commissioning.

# Sidebar metadata follow-up (27 September 2026)

See [the 15-entry follow-up checklist](sidebar-followup-2026-09-27.md) for canonical
routes, the verified plant metadata/chart changes and explicitly unfinished
wizard persistence work. This increment does not mark any whole screen complete.

# Đối chiếu 26 mockup và phạm vi sản phẩm

Cập nhật **27/09/2026**, trên snapshot mã được rà soát trước commit. Báo cáo này thay thế các nhận định “hoàn chỉnh luồng mã” trước đó: nhiều nhận định dựa trên số route, nút khóa và dữ liệu dựng sẵn, chưa chứng minh workflow hoạt động. Kết quả hiện tại là **pilot một controller**, không phải nền tảng O&M/EMS trưởng thành và chưa nghiệm thu thiết bị khách hàng. Xem [README dự án](../README.md), [mục lục tài liệu](README.md) và [validation theo ngày](validation.md).

## Kết luận sau đọc mã và kiểm tra

**Đính chính batch 1 sau audit:** [Real-data remediation](real-data-remediation-2026-09-27.md) thay thế các tuyên bố seed-free/verified ở các phần cũ khi có mâu thuẫn. Giữ nguyên 15 sidebar và ma trận 26 ảnh; chưa hoàn thành rà seed toàn hệ thống.

| Phạm vi / ảnh | Mã hiện có batch 1 | Chưa xây / còn phải sửa | Điều kiện hoàn thành |
|---|---|---|---|
| Health — 07, 26 | BE đọc SOH/BMS thật, tích phân theo timestamp/coverage; FE bỏ chỉ số dựng sẵn | Lifetime model với nameplate và lịch sử đủ; cell diagnostics | Không thiếu/sai nguồn, unit, timestamp; hardware acceptance |
| EMS / lịch — 08, 24 | BE lịch sử EWMA → engine advisory; FE dùng chung kết quả, không giả tạo lịch | Config editor, tariff currency/expiry workflow, dispatch control | Regression dữ liệu thật/cold-start và commissioning trước ghi |
| Meter/tariff — 14, 23 | Meter boundary và điện nhập quan sát, không đoán phản kháng/tiết kiệm | Billing engine với biểu giá site hiệu lực, reactive interval alignment | Đối chiếu hóa đơn và meter thật |
| Vendor/native — 13, 16 | Chặn auth/readback giả, cờ bypass; registry review riêng | Toàn bộ seed trong technical tools, local transport, revalidation protocol | Exact evidence/identity + acceptance; không suy từ test fixture |

- Có BE + FE hoạt động cho quản lý dữ liệu nội bộ, tài khoản, một số đường đọc đa hãng, lập lịch nháp/biên dịch, xử lý sự cố và bảo trì. Các phép đo, báo cáo và điều khiển cần profile, quyền và dữ liệu phù hợp.
- Không có ảnh nào đã được chấp nhận đầy đủ toàn bộ chức năng, hành vi phần cứng và độ khớp UI. Chín ecosystem trong phạm vi không tương đương chín integration hoàn chỉnh.
- Đã sửa đường báo cáo/tổng quan đọc dữ liệu lưu thật; không dựng đường cong, SOC, uptime, sức khỏe, tiền tiết kiệm, CO₂ hay kết quả nghiệm thu. Dữ liệu không đủ được trả `null`/UNKNOWN, không đổi thành 0 hoặc thành công.
- Đã bỏ các compiler ghi phỏng đoán ngoài Deye. Đây là thu hồi tuyên bố hỗ trợ sai, không phải hoàn thành phần integration còn thiếu. Deye cũng chưa có hồ sơ phần cứng khách hàng được nghiệm thu trong đợt này.
- Test fixture, simulator và screenshot QA chỉ nằm trong thư mục kiểm thử/work; không là bằng chứng kết nối hãng hay thiết bị thật. Test qua được không thay nghiệm thu tại công trình.

Quy ước: **BE+FE một phần** = có luồng nối API nhưng thiếu chức năng trong ảnh; **BE riêng** = engine/API chưa nối đầy đủ vào màn hình; **khung** = catalog/form/read-only/khóa, chưa có hành vi vận hành. “Đạt test cục bộ” chỉ áp dụng đúng ca đã chạy.

## Tái sử dụng before_project — 27/09/2026

[Audit 30 dự án](legacy-project-audit.md) ghi rõ inventory khác với đọc sâu toàn bộ code; [hướng dẫn](model-library-and-home-assistant.md) mô tả luồng. File `legacy-validation-2026-09-27.md` từng được dẫn ở đây nhưng không có trong checkout hiện tại, nên chưa thể dùng làm bằng chứng xác minh.

| Phạm vi dự toán / ảnh | Mã hiện có sau đợt này | Phần chưa xây | Điều kiện hoàn thành |
|---|---|---|---|
| Model-aware device/native — 07, 13, 16, 26 | BE: importer, catalog 41 profile, 913 decoder trong 3.145 field, plan/validate/decode. FE: tìm/chọn field, source/digest, config/download | 2.232 field bị chặn; dynamic MPPT/pack/lookup/sentinel/derived; model-native write/readback | Đối chiếu từng field/variant, fixtures và exact hardware; không nghiệm thu chỉ vì decode được |
| Local Agent/home energy — 14, 17 | BE: TCP/V5 collector, HA sensor bridge, cùng outbox→inbox→native/mapping; FE chuẩn bị/validate config agent/site | Service/RTU/discovery/reconnect policy/mTLS/managed update; activation mapping còn thiếu | Pilot collection dài hạn, timestamp/unit/source đúng, replay/revoke/recovery và commissioning |
| EMS — 24 | BE hourly EWMA adapt từ SEM; FE baseline 24h hoặc lý do cold-start, không phát lệnh | EMHASS/OpenEMS optimizer, forecast dispatch, EV/load/generator arbitration, offline control | Forecast đánh giá trên holdout + constraints, command engine và acceptance phần cứng |
| Tổng quan/thiết bị — 02–04, 26 | BE quality/freshness/source-pair gating; FE cùng sơ đồ điện có motion, bảng/fullscreen/pause/reduced-motion, route chi tiết | Topology điện được nghiệm thu, nguồn cấp từng tải, chart hoàn chỉnh, mọi responsive state | So với meter/topology thật; QA các chiều và thiếu/cũ/conflict; usability đủ 26 ảnh |
| UI chung — tất cả | Sửa hai khối CSS thiếu dấu đóng; giữ một app.css/sidebar; bỏ số mẫu giờ chạy/SOH/chu kỳ/bảo hành còn sót | Design cleanup, full 26-screen accessibility/visual acceptance | Keyboard/error/loading/mobile và toàn bộ mockup states được quan sát |
| Core Physics & EMS Engine (Đợt 2) — 24, 08, 16 | BE: `load_predictor.py` (5 mô hình dự báo tải), `tariff_catalogue.py` (catalogue biểu giá đa quốc gia, spot feed, carbon tracker, bill calculator), `thermal_load_manager.py` (bơm nhiệt Carnot COP, bồn nước nóng DHW, mô hình 2R2C tòa nhà, SG-Ready 4 trạng thái, deferrable load scheduler), `phase_balancer.py` (thành phần đối xứng Fortescue, VUF/CUF IEC 61000-4-30, dispatch bất đối xứng 3 pha, zero-export PID, rolling peak demand shaver), `predbat_planner.py` (mô phỏng tiến 24-48h, hurdle rate khấu hao pin, arbitrage biểu giá động, lịch inverter), `genset_controller.py` (state machine máy phát diesel/gas, mô hình tiêu thụ nhiên liệu, chống wet stacking, black-start), `vendor_device_translator.py` (chuyển đổi lệnh EMS neutral sang Modbus FC06/FC16 cho GoodWe, Sungrow, Deye, Huawei, Solis, Growatt), `phase_d_api.py` (REST endpoints). | Tích hợp giao diện trực quan hóa unbalance 3 pha, thermal buffer view và timeline predbat | Thử nghiệm phần cứng thực tế, xác nhận đồng hồ đo công tơ 3 pha và máy phát vật lý |
| Grid Code, Industrial Meters, EV Fleet & Market (Đợt 3) — 24, 02, 14, 08 | BE: `grid_code_regulator.py` (Volt-Watt P(V), Volt-Var Q(V), Freq-Watt P(f), anti-islanding NA003), `smart_meter_driver.py` (driver 6 dòng công tơ 3 pha Eastron SDM630, Chint DTSU666, Carlo Gavazzi EM24, Janitza UMG96, Schneider iEM3000, ABB B23), `ev_fleet_coordinator.py` (Dynamic Load Management DLM, chuyển mạch 1p3p tự động, ngắt pin xe 80% SOC), `market_trader.py` (đấu thầu thị trường điện bán buôn DAM/IDM, phản ứng điều tần FCR sơ cấp). | Widget điều khiển trạm sạc đa cổng, giao diện giám sát 4 góc phần tư công tơ và bidding market | Thử nghiệm kết nối công tơ Modbus thực tế và trạm sạc OCPP |
| Tích hợp sâu Core Engine vào 14 Tab Sidebar (Đợt 4) — 27/09/2026 | BE: Bổ sung endpoints máy phát `/api/genset/evaluate-dispatch`, `/api/genset/black-start-sequence`, mô phỏng nhiệt 2R2C `/api/thermal/building-simulation`, tra cứu 30 hãng Modbus `/api/vendor-translator/supported-brands`. FE: Tích hợp đầy đủ vào 14 tab sidebar: Tab 1 Tổng quan (Grid code & VUF), Tab 3 SLD (phân định 4 ranh giới điện), Tab 6 Điều khiển (biên dịch Modbus FC06/FC16 30 hãng & máy phát Black-Start), Tab 7 Lịch (Predbat 24h & hurdle rate khấu hao), Tab 8 EMS (Quy chuẩn Volt-Watt/Var/Freq/NA003, Fortescue cân bằng pha, SG-Ready nhiệt & EV DLM 1p3p), Tab 9 Dữ liệu (6 công tơ 3 pha & 4 góc phần tư), Tab 11 Báo cáo (Thị trường bán buôn & FCR điều tần), Tab 12 Bảo trì (Chẩn đoán suy giảm cell pin SOH/ΔV). | Mọi chức năng đã nối trực tiếp vào giao diện 14 tab sidebar và kiểm tra cú pháp JS | Nghiệm thu thực tế trên phần cứng hiện trường |

**Sắp xếp sidebar:** Model inspector thuộc Thiết bị; link trong Tổng quan mở cùng module. Config HA/local thuộc Dữ liệu / Local Agent và dẫn tới Mapping, không tạo menu HA riêng. Baseline thuộc Điều phối EMS. Site overview và device monitoring dùng chung energy-flow component. Không nhân bản flow, policy hoặc credential UI theo nguồn dữ liệu.

## Bổ sung Eybond/SmartESS — 24/09/2026

| Ảnh / nhóm | Mã BE mới hoặc sửa | Mã FE và liên kết | Chưa hoàn thành |
|---|---|---|---|
| 13, 21 / Accounts, Bluesun onboarding | DessMonitor/ShineMonitor auth/session, vault, bounded plant→collector→device discovery, native latest; brand tách platform | Bluesun→SmartESS form VI/EN, nền tảng/company key, username trong account table; cùng sidebar/app.css | Live account acceptance, mọi model/OEM, complete onboarding/QR |
| 14 / Sources, collection, sync | Chu kỳ tối thiểu 300 s tại backend/controller; source CONNECTED/STALE/AUTH_REQUIRED; khám phá lại khi restart/check làm mất route | Collection editor cùng giới hạn 300 s, trạng thái đồng bộ lấy đúng field, kỳ polling theo nguồn thật | Source-time contract, model mappings, failover rộng, inventory lớn vượt call budget |
| 07, 26 / Device readings | Giữ title/string value/unit; stable native keys; không đặt timestamp nhận thành timestamp đo | Detail & native readings từ inventory; filter theo brand/platform; bỏ 38°C/0 kW giả và phân biệt Unknown | Phase/MPPT/latency charts, canonical profile/physical acceptance |
| 08, 16, 18 / Control | Không thêm compiler hoặc quyền ghi suy đoán từ đọc cloud thành công | Cùng capability/native groups và lý do chưa hỗ trợ | Native schemas, model controls, order/readback và hardware trial |

Đây là phạm vi code mới có thể kiểm tra, không thay thế các gap trong 26 hàng phía dưới. [Chi tiết contract](eybond-read-integration.md), [kết quả kiểm thử đợt này](eybond-validation-2026-09-24.md).

## Bổ sung Mapping workspace — 25/09/2026

| Phạm vi dự toán / ảnh | Mã hiện có | Phần chưa xây | Điều kiện hoàn thành |
|---|---|---|---|
| Sources/integrations; ảnh 14, liên quan 06/13/17/26 | `data_workspace.py`: context chọn device/binding/agent theo scope, giữ native key/unit/value/time/quality, không trả credentials; kiểm tra dimension/sign; draft/version/digest, mô phỏng không ghi canonical, independent review. `mapping-workspace.js`: một editor VI/EN dùng shared primitives/app.css; create/edit/evidence/simulate/history/review nối API thật | Canonical profiles theo model, trình nghiệm thu/đưa profile vào sử dụng, lifecycle/deployment của profile, đối chiếu native metadata mọi hãng | Hợp đồng source-time/unit/sign theo đúng OEM/model/FW, reviewer độc lập + nghiệm thu vật lý và hồi quy downstream KPI/report/EMS, invalidation khi nguồn/profile đổi |
| Liên kết tài khoản/thiết bị → ánh xạ → dữ liệu; ảnh 14/21 | Context chỉ liệt kê kết nối còn hiệu lực. Duyệt và mô phỏng kiểm tra lại identity, site binding, tài khoản enabled hoặc agent/device membership. Sửa draft sau review tạo phiên bản mới không giữ trạng thái đã duyệt | Tự động migration profile khi đổi firmware; ảnh hưởng trên fleet và báo cáo commissioning | Không dùng bản cũ nếu identity/source khác, lịch sử review truy vết được, không nâng UNVERIFIED thành GOOD chỉ vì bấm duyệt |
| Test/QA đợt này | Test BE nguồn quá hạn/không hợp lệ, đơn vị đổi, duplicate source, nonfinite, revoke account/binding/agent, revision race. Browser create→edit→simulate→history→review→Viewer, VI/EN và dùng một stylesheet | Tài khoản/model thật, load/soak, accessibility và usability toàn 26 ảnh | Kết quả thực thi và lỗi/rerun phải ghi tại [mapping-validation-2026-09-25.md](mapping-validation-2026-09-25.md), không suy hoàn thành từ test được viết |

Luồng editor đã qua 450 test BE trong toàn suite và 13 test browser trong toàn suite trước sửa navigation. QA phát hiện hai hàng tab Data trùng nhau, đã gộp lại và chạy hồi quy navigation riêng; xem kết quả cuối ở báo cáo validation. Phần này không tự kích hoạt profile, không đổi telemetry/KPI/control và không chứng nhận tương thích hãng.

## Ma trận 26 ảnh

Số thứ tự theo 26 ảnh gốc. Ảnh gửi sau `Screenshot 2026-09-13 192858.png` là chuẩn bố cục cập nhật của **ảnh 21**. Các ảnh tổng quan lặp được quy về cùng trang nhà máy; không nhân bản sidebar hoặc command engine.

| Ảnh | Chức năng bắt buộc từ ảnh | BE hiện có và bằng chứng mã | FE hiện có | Thiếu / điều kiện hoàn thành |
|---|---|---|---|---|
| 01 | Fleet, list, site, nhanh, lịch, map, alert, report | `workspaces.py`, `operational_views.py`, management/control/report APIs | Các workspace chung và link chi tiết | **BE+FE một phần**; fleet energy/preset đa hãng còn thiếu. Map nền địa lý đã có ở owner #22; không dùng collage này làm chuẩn style. |
| 02 | Site flow PV/inverter/grid/battery/load/EPS, nhanh, status, weather, equipment, log | Overview có nguồn/scope/null; counter theo kỳ; weather Open-Meteo khi có GPS | 11 khối, flow component dùng chung site/device, bảng/toàn màn hình/motion/reduced-motion, route chi tiết | **Một phần**; đã có motion theo chiều công suất và freshness; chưa topology điện/source-to-load được nghiệm thu, dashboard đa biểu đồ chưa đủ, quick preset chưa triển khai theo model |
| 03 | Site chart, ưu tiên local/cloud, vị trí, trạng thái, cấu hình | Telemetry quality/source, profile, inventory, command engine | Site tabs/data/nguồn/control | **Một phần**; không suy luận flow từ cloud fields chưa xác minh; chưa hợp nhất topology và tất cả KPI |
| 04 | Site 6 KPI, flow, biểu đồ, tổng năng lượng, kết nối | Counter delta và kênh StationReport riêng từ hãng; exact scope, signed units, dated kWh buckets | 6 KPI fallback có nhãn, sơ đồ tĩnh khi chưa verified time; chart điện năng ngày theo response | **Một phần**; live GoodWe có số, nhưng source TZ, công suất theo giờ, tự dùng/savings, map và presets còn thiếu |
| 05 | Portfolio/filter/customer/region/source, table/card, map/statistics | Site CRUD/profile, scoped inventory, tọa độ thật | Portfolio/table/card, tìm/lọc, khách hàng; không dựng benchmark | **Một phần**; map đất liền/GPS/zoom đã có ở owner #22; PR/yield benchmarking và nhóm vùng cần bằng chứng/cấu hình hợp lệ. |
| 06 | History ngày/tháng/năm/tổng, nhiều metric/trục, bảng, CSV/XLSX/PDF | Stored samples, time bounds, source ambiguity, export limits | Bảy kênh site kW/%; device/realtime có so sánh hai kênh cùng đơn vị, lọc thời gian/chất lượng, min/max và bảng nguồn; native chưa xác minh opt-in dấu rỗng, không tự gán pha/MPPT | **Một phần**; thiếu rollup dài hạn, mapping pha/MPPT/latency, zoom/drill-down, PDF riêng, backfill hãng; chưa đủ pixel parity |
| 07 | Device inventory/topology/link/discover/reboot/firmware | Device/binding/integration; capability/native descriptors; catalogue 41 model/913 decoder có provenance | Inventory/detail + thư viện model hai cột, nhập thanh ghi theo dòng và cấu hình collector theo field; 15 mục giao thức dẫn tới công cụ thật/thiết bị đã đồng bộ, không còn panel dựng telemetry/session mẫu | **Một phần**; không có universal Modbus scanner; sức khỏe 96/100 và uptime giả đã bỏ; discovery vật lý/OTA chưa xây đủ |
| 08 | Remote control mode/export/SOC/charge/EPS/CT/BMS/generator/grid/raw, readback | Shared preview→confirm→order→readback; scope/idempotency/locks | Thẻ nhóm chức năng gọn, đủ 34 intent theo API, số đo bên phải và shared preview; calculator máy phát/black-start có field trống thay JSON, tách khỏi lệnh thực | **Khung + engine**; chưa nhóm model-specific vận hành đầy đủ; nút khóa hay calculator không chứng minh hỗ trợ |
| 09 | TOU tuần, tariff, reserve, backup/generator/load-priority, simulate/deploy | Schedule CRUD/revision/copy, timezone/DST, compile artifact và rollout preparation | Ma trận trống/đã lưu; click/keyboard/desktop drag, resize bằng pointer/phím 15 phút, hủy kéo bằng Esc; chuyển bằng chọn ô đích trên mobile; copy/undo/revision conflict | **Một phần**; chưa vẽ tự do, kiểm thao tác trên điện thoại vật lý, ROI đã nghiệm thu hoặc universal register translator; không tự triển khai |
| 10 | Alert trend/severity/category/device/filter, diagnostic/playbook | Incident correlation, dedup/order/recovery, trend API, SLA snapshot | 3 chart số đếm thật, bảng 8 cột, detail/filter/assign/triage/note/playbook | **Một phần**; chưa đủ drill-down/group chart như ảnh; decoder alarm/SOP theo model, external notifications chưa nghiệm thu |
| 11 | Command timeline, old/new, ack/readback/verify, filter/export | Journal nối command/audit thật, VERIFIED tách ACK | Bảng 12 cột + detail kể cả trống; loại actor/vendor/source mẫu, giữ số 0 và trạng thái phân trang | **Một phần**; cần nghiệm thu pagination/tìm kiếm toàn lịch sử, export lớn; chưa physical verification |
| 12 | Energy reports, self-use/cost/CO₂/cycles/uptime, PDF/XLSX/email | Actual scoped counter report, immutable CSV/XLSX/HTML artifacts | Mixed chart có bật/tắt kênh + bảng, 4 mini-panels kể cả trống, xuất/tải tệp ở cột phải; form kịch bản thị trường thay JSON | **Một phần**; PDF/email và các loại báo cáo bổ sung chưa có; savings/CO₂/cycles/uptime để unknown nếu thiếu mô hình/bằng chứng |
| 13 | Link wizard brand/type/cloud/local, scan, topology, kiểm tra | Chỉ hoàn tất với binding đã quan sát; không tạo SN giả; scan thiếu transport trả lỗi rõ | Bốn bước ở cột trái; platform từ registry + OEM khai báo, tìm thiết bị, panel chi tiết hồ sơ/API thật, source bindings thu gọn, empty/error/late-response fence; không giả sơ đồ điện/online | **Một phần**; QR, physical discovery, topology acceptance, complete guided onboarding còn thiếu; UI chưa nghiệm thu pixel toàn bộ |
| 14 | Data sources/cloud/agent/collection/mapping/diagnostic/sync | Integration state, source policy, collection revisions; scoped mapping-context, version/digest/review; recheck identity + binding/account/agent | Bảng nguồn/agent inbox; model/HA collector editor dùng field trống, register editor theo dòng; mapping author/simulate/version/review giữ owner hiện tại | **BE+FE một phần**; editor mapping đã nối, vẫn chưa có quy trình đưa profile vào production từ UI; health/freshness/failover chưa mọi đường |
| 15 | Site general/tariff/ownership/notification/sources/automation | Merge site config, finite GPS/IANA validation, versioned local drafts; sửa bất nhất làm tròn VND optimizer | Forms chia card; bảng giá 24h thay JSON, hiệu suất %, thời gian Việt Nam → UTC; giữ revision/conflict | **Một phần**; lưu tư vấn không ghi máy; chưa email/SMS/Zalo/push, tariff billing đầy đủ, owner policy granular |
| 16 | Advanced CT/BMS/export/grid/generator/raw/vendor-native + diff | Intent/capability/constraints, evidence and write guards | Nhóm native theo adapter + lý do khóa | **Khung**; model-specific read/edit schemas, enum/unit conversions/readback còn thiếu, không gọi register đoán |
| 17 | Logger/agent/network, IP/RSSI/SIM, Wi-Fi/DHCP, discovery/mTLS/firmware | Enrollment, scoped ingest, sequence/replay, outbox; đọc FC03/04 TCP/V5 theo digest, HA sensor bridge; network metadata quan sát | Bố cục list/configuration/diagram/diagnostics theo ảnh 133208; chọn hồ sơ mạng, hiển thị địa chỉ/baud/parity/DHCP khai báo riêng khỏi số đo; đường nét đứt chỉ nối thiết bị–hồ sơ đã lưu; chứng chỉ/ping/RS485 thiếu dữ liệu giữ unknown | **Một phần**; chưa topology truyền thông được quan sát đầy đủ, agent service, Wi-Fi changes, RTU scan, mTLS, OTA/update/recovery. Không suy online từ enrollment. |
| 18 | Bulk wizard, model compatibility Exact/Partial/Review, dry-run, canary/readback | Shared policy compilation, digest revalidation, rollout/canary/outcomes | Năm bước + ba cột chọn thiết bị/cấu hình/xem bản nháp, không chọn giá trị hộ người dùng; lưu/review/compile/canary theo API thật | **Engine + FE một phần**; kết quả phụ thuộc actual profile; chưa multi-vendor production rollout/scheduler |
| 19 | User/role/site scope, 2FA, vendor accounts, security log | Local users/session revoke, RBAC, vault, scoped keys; five roles | User/filter/role matrix/account/log; shared scope giữ qua reload theo user, mobile drawer + Escape/focus; không mở thêm quyền | **Một phần**; đã sửa role filter/Admin control claim; MFA/SSO/multitenancy chưa xây; Raw Command là permission, không thêm role thứ sáu |
| 20 | Commissioning topology/CT/direction/BMS/control/alarm, evidence/signatures/handover | Six manual check records, handover gate; không unlock hardware | Khung hai cột chọn nhà máy + sáu mục nghiệm thu kể cả chưa chọn nhà máy, nhập bằng chứng và lịch sử chung | **Một phần**; không tự PASS điện trở/điện áp/tần số; thiếu electrical tests, signature/file storage, physical acceptance |
| 21 | Vendor accounts + diagnostic inspector + cert/key/vault, mẫu UI bắt buộc | Accounts/check/sync/vault/keys; Deye managed app; SEMS+ auth/typed discovery/native read cùng GoodWe plugin, unknown connectivity, revision/session/CSRF guards | Table/inspector; separate Deye/SEMS+ dialogs, consent/server selection/password clearing/autofill separation; preflight, check and global-sync scope confirmation | **BE+FE một phần**; Q1 read-only connector trial ready, live acceptance pending; org-admin-only; Deye customer grants, SEMS+ source timestamps/unit/sign/history/alarms, pixel/usability, cert mTLS still open |
| 22 | Fleet geographic map/satellite/cluster/filter/site summary/maintenance links | Finite GPS, regional groups, haversine/clustering | Natural Earth offline/GPS thật; pan/zoom/fit, list/detail/filter/keyboard; lớp coastline/tên/trạng thái giữ lựa chọn; NORMAL có số đo không đồng nghĩa online | **Một phần**; chưa street/satellite, province boundaries, clustering UX, khảo sát tọa độ cực/kinh tuyến 180°. |
| 23 | Health/work orders/firmware/calendar | Observation health, work plan versions, execution/evidence/time, independent review | Work orders/plans/service calendar/health; linked incident | **Luồng nội bộ đã kiểm tra, vẫn thiếu sản phẩm**; vật tư/SLA dịch vụ/file attachments/real OTA/compatibility/rollback chưa đủ |
| 24 | EMS trigger/condition/action, bounds, simulate/activate/log | Deterministic evaluation, quality/unit/freshness, monitor hold/notify, saved drafts; hourly baseline từ lịch sử đủ điều kiện | Danh sách–chi tiết–chạy thử ba cột; editor chọn metric thật và schema hành động từ đúng thiết bị; ngưỡng trống, enum/nested fields, fence response cũ, giữ nguyên tham số cũ không render được; giải thích dry-run thay JSON | **Một phần**; physical dispatch disabled; OR/nested conditions khác nested parameter fields và chưa triển khai; forecast dispatch, conflict/hysteresis/offline, pixel acceptance còn mở. |
| 25 | Incident detail/assignment/ack/workorder/note/timeline/SLA/escalation | Persisted correlation/revision/history, SLA snapshot, playbook versions, jobs | Create→respond→note→timeline→workorder; filter/card spacing và SLA 2×2 desktop, xếp dọc mobile | **Luồng nội bộ đã kiểm tra**; thiếu channels escalation thật, vendor-specific causes, evidence attachments and service SLA |
| 26 | Device realtime energy/phase/string/battery/latency charts, status/native params | Latest source-aware metrics, DeviceReport riêng inverter AC/DC/rated/temperature + 5 kỳ điện năng; native fields; shared collector manual refresh | Monitor/dialog tự tải bản nhận 15s, tuổi dữ liệu và chu kỳ hãng; giữ bộ lọc; nút đọc mới; bảng gốc, flow/chart có kiểm chất lượng | **Một phần**; SEMS+ thu thập tối thiểu 60s không phải realtime từng giây; history/MPPT/runtime/battery mapping và pixel/hardware acceptance còn mở. |

Tên module là bằng chứng vị trí mã, không là bằng chứng hoàn thành. Regression tests nằm trong `tests/test_*workspace*.py`, các test adapter, `tests/test_incident_center.py`, `tests/test_maintenance_execution.py`, `tests/test_schedule_planning.py`, `ui_tests/`.

## Kết luận cấu trúc sidebar: 15 mục, một nơi sở hữu mỗi chức năng

Hash hiện tại có dạng `#page/section/tab`. Label giao diện tách khỏi tên kỹ thuật. Một site được chọn là **phạm vi**, không tạo một bộ sidebar khác. `Nhà máy` quản lý tài sản/khách hàng; `Hệ thống` chỉ topology/SLD, không lặp site CRUD. Các subtab dưới đây là hợp đồng bố trí đích; cột trạng thái phân biệt phần đã nối và phần còn thiếu.

| Sidebar / route chuẩn | Phải hiển thị / subtab sở hữu | Liên kết chung và tình trạng |
|---|---|---|
| Tổng quan `#overview/main` | Fleet summary; theo site: Overview, Data, Equipment, Control, Schedule/TOU, Alerts, Journal, Diagnostics, Reports, Network | API scoped/unknown; calculator grid-code là tư vấn, không là chứng nhận tuân thủ. |
| Nhà máy `#plants/main` | Portfolio list/card, khách hàng, vùng, thêm nhà máy, benchmarking, tài sản khai báo | Danh sách/API thật; thiếu bằng chứng không dựng PR/yield hoặc nguồn điện. |
| Hệ thống / SLD `#topology/main` | Quan hệ inverter–meter–battery–load–logger; ranh giới đo và tài sản | Graph/bảng theo record; chưa nghiệm thu electrical topology hay suy sơ đồ dây thật. |
| Bản đồ `#plants/map` | Bộ lọc, bản đồ đất liền/GPS, pan/zoom/fit, list/detail, deep links | Natural Earth nền địa lý tổng quan; cluster/satellite UX chưa đủ. |
| Thiết bị `#devices/main` | Inventory, detail/monitoring, model inspection, native parameters, health, firmware, protocol tools | 41 model catalogue là bằng chứng cộng đồng, không universal support; 15 protocol mục dẫn công cụ thật, không fake telemetry. |
| Điều khiển `#operations/main/control` | Site/device, nhóm intent, BMS/TOU/CT/export/generator/grid/native, preview/confirm/readback; rollout | Shared engine và capability gates; không tuyên bố FC06/FC16 mọi hãng hoặc điều độ máy phát đã hoạt động thực. |
| Lịch / TOU `#operations/main/schedules` | Weekly editor/resize/move/copy/undo, tariff reference, compile, prepare rollout | Lịch trống vẫn có ma trận; pointer/keyboard resize và chọn ô đích dùng chung editor; simulation/compile không tự triển khai hay chứng minh scheduler thực địa. |
| Điều phối EMS `#operations/main/rules` | Rules/conditions/actions, simulation, monitoring; calculators grid/phase/thermal/EV/generator | Shared rule-editor.js cho các nút tạo/sửa; điều kiện AND/metric thật/ngưỡng trống; physical dispatch, nested rules và parity đầy đủ còn mở. |
| Dữ liệu & kết nối `#reports/main` | Overview, Sources, Cloud accounts, Local Agent, Collection, Mapping, Diagnostics, Sync, Telemetry, Meters | Collection/model/HA theo field, mapping review; meter decoder không là live scan/commissioned meter. |
| Cảnh báo `#incidents/main` | Trend/filter/list/detail, assign/triage, notes/timeline, playbook, SLA, linked jobs | Workflow nội bộ từ bản ghi; danh mục lỗi/SOP không chứng minh vendor alarms đã được ingest. |
| Báo cáo `#reports/analytics` | Scope/period, energy/artifacts/export; market advisory | CSV/XLSX/HTML và calculations theo đầu vào; PDF/email và giao dịch DAM/FCR thực không được triển khai. |
| Bảo trì `#incidents/health` | Health, Work orders, Plans/calendar, Firmware, execution/checklist/time/review | Phiếu và review nội bộ; BESS calculator tư vấn, không thay chẩn đoán/hardware OTA. |
| Nhật ký `#operations/main/journal` | Commands/readback, sync, hash audit; realtime device monitoring | Nhật ký từ record; sáu KPI/flow/charts/state/bảng kể cả trống, thiếu pha/MPPT/latency mapping. |
| Người dùng `#settings/main/users` | Users, Roles/permissions, Site scope, account/security links | Local RBAC năm vai trò; chưa MFA/SSO/customer tenancy. Giữ scope qua reload theo user. |
| Cài đặt & Hãng `#settings/main/connections` | Vendor accounts, Site/general/tariff/ownership, notification/source policy, linking, API keys/evidence | Bố cục ảnh 21; Deye managed app/user dialogs; preflight, platform guide, diagnostics và global-sync confirmation cùng owner; live/customer grants và GoodWe SEMS+ chưa nghiệm thu. |

Các routes tắt trong card phải giữ site scope và dẫn đến cùng chức năng sở hữu. Không thêm CSS riêng theo route; shared primitives và `static/app.css` sở hữu mọi layout/typography/semantic state. Account route tuân bố cục ảnh 21. VI/EN đã có cơ chế chung nhưng còn nhãn kỹ thuật/translation cần trau chuốt.

## Site → Tổng quan: 11 khối phải bao phủ

| Khối | Trạng thái hiện tại | Còn thiếu |
|---|---|---|
| Sơ đồ realtime | Scoped PV/battery/grid/load/EPS; null-safe, display/fullscreen, links | Inverter hub, topology/arrow direction, keyboard/fullscreen polish, streaming chart |
| Điều khiển nhanh | Preset names và route tới shared device control | Chuyển preset thành exact model intents, preview/diff và apply sau acceptance |
| Trạng thái nhà máy | Today/month/year counters; lifetime unknown khi không có nguồn | Kỳ tùy chọn/tổng/bộ chart ngay trong khối; current data không chứng minh toàn site khỏe |
| Sản lượng & tiêu thụ | Bảng kỳ từ counter; link actual timeseries chart | Multi-series chart đồng kỳ, coverage và nhiều meter boundary |
| Tỉ lệ tự dùng | Trường nullable; không mặc định 78%/65% | Energy accounting xác minh battery/grid/meter, không suy từ PV đơn lẻ |
| Thời tiết & dự báo | GPS→Open-Meteo/cache/stale metadata; chart forecast có nguồn | Vendor weather priority, malformed response tests sâu, commercial deployment terms/config |
| Thiết bị hệ thống | Actual scoped devices, status/detail links | Model-specific icons/topology/phase strings và stale freshness nhất quán |
| Kết nối & nguồn | Enrollment phân biệt online; integration metadata/unknown | Agent heartbeat, measurements latency, authority/failover ở tất cả view |
| Cảnh báo gần đây | Persisted incidents→center | Trend/widgets và live vendor decoder completeness |
| Nhật ký điều khiển | Persisted commands→journal, không suy ACK thành verified | Actor/readback diff/large history ngay card và trạng thái nhất quán |
| Vị trí & thông tin | GPS/address/customer/timezone/capacity thật; links map/edit/diagnostics | Mini-basemap, ảnh site uploads, owner metadata |

## Phạm vi dự toán → mã hiện có → phần chưa xây → điều kiện hoàn thành

Các khoảng kLOC dưới đây là **dự toán tham khảo do chủ dự án đưa ra**, không là target phải viết đủ dòng. Các khối overlap, không cộng lại để báo tổng. BE/FE thực đo ở mục inventory bên dưới. Một module có một file không tương đương đạt toàn bộ dự toán.

| Phạm vi dự toán (BE / FE kLOC) | Mã hiện có | Phần chưa xây hoặc chưa nối | Điều kiện hoàn thành có thể kiểm chứng |
|---|---|---|---|
| Domain/API/site/device 10–18 / 4–7 | Domain models, SQLite entities, scoped CRUD, topology records | Schema migrations dài hạn, tenant/org/customer lifecycle sâu, electrical topology | Migration/recovery, isolation, referential integrity, CRUD+link E2E và topology acceptance |
| Auth/RBAC/secrets 7–12 / 5–8 | Local password/session/CSRF, 5 roles, vault, scoped API keys, revoke | MFA/SSO/tenant boundary, key rotation/backup UI, trusted external audit | Auth failure/revoke/concurrent reads passed; tenant/adversarial tests; restore/rotation diễn tập |
| Dashboard/site 4–7 / 8–14 | Operational read model, 11 site blocks, period counter, weather service, shared flow có motion/freshness | Full energy accounting, verified topology/source-to-load attribution, multi-axis charts, preset acceptance | Reconcile with site meter/counter and all missing states; 26 reference visual/usability acceptance |
| Telemetry/WS 8–14 / 5–9 | Poll clients, normalized samples/provenance, quality/source policy, scoped WS/invalidation | Production fanout/storage/backfill, broad exact profiles, clock/failover acceptance | Long-running ingest/reconnect/load tests and live profile comparison with vendor UI |
| History/analytics 6–10 / 7–12 | Bounded stored points, seven-channel power/SOC chart, device-aware same-unit comparison, time/quality filters, native opt-in, source table, four empty/observed mini-charts, counter/reset/coverage analysis, export | Durable years of rollup, query/downsample, exact phase/MPPT/latency mapping, zoom/drill-down, cloud backfill | No mixed unit/source/device series; unknown/native labels remain honest; known energy baselines, gaps/reset/rollover, timezone periods and scalable export; visual and accessibility acceptance |
| Device management 5–9 / 6–11 | Discovered IDs/bindings/inventory; shared DeviceReport with per-inverter AC/DC/rated/temperature and period energy panel; scoped unit/identity checks | QR/scan, identity reconciliation, battery topology, MPPT/runtime history, guided connection and pixel acceptance | Each report matches its own serial, no station/device mixing; scoped read/revoke, unit/null/zero and responsive checks plus live observation |
| Remote engine 10–18 / 8–14 | Intent/capability/preview/confirm/locks/idempotency/readback/quarantine | Most model write mappings/translators, hardware commissioning | Exact account/model/logger/FW identity + accepted range/unit + physical readback + failure recovery |
| Advanced/native 5–10 / 8–15 | Native groups/evidence/catalog, unknown reasons; blank typed generator/black-start advisory forms | Real field read/write schemas for CT/BMS/grid/ATS/generator, per-model screens; advisory forms are not device read/write editors | Compare each field/enum/scale with native API and device; reviewed independent sensitive gates |
| TOU 5–9 / 5–9 | Versioned schedules, empty/saved matrix, click/keyboard/desktop drag/copy/undo; pointer/keyboard resize and mobile-friendly choose-destination move; validation/compile/source digest/prepare rollout | Freehand painting, physical touch-device acceptance, per-vendor semantics/slot limits, unattended job execution | Resize/cancel/overlap/undo roundtrip; full week/DST/concurrent revisions pass; hardware schedule readback matches intent |
| EMS 8–16 / 7–12 | Conditions/actions evaluator, monitor hold/notify; three-column directory/inspector/dry-run; observed conditions, device capability schemas, blank targets, stale-response fences and lossless unchanged legacy parameters | Nested/OR conditions and full mock parity, production optimizer, hysteresis/conflict arbitration, weather/tariff dispatch, offline policy | Real draft create/edit, exact field schema and unchanged legacy preservation; explicit zero/boolean; scenario failovers and field acceptance; no preset/JSON-input dependency |
| Bulk 6–12 / 4–8 | Five-stage guide, blank three-column equipment/settings/review editor, actual draft persistence, canary/compatibility/cancel/outcomes | Complete multi-vendor profiles, distributed rollout worker/rate budget; complex action bundles in one editor | Blank/invalid/zero-value draft tested without commands; partial/unknown outcomes isolated; per-device authority; recover interrupted rollout |
| Sources/integrations 6–10 / 7–12 | Account/grants/check/sync; Deye managed app; experimental SEMS+ auth/typed discovery/native read and tri-state connectivity; separate credential form with consent; collection/source/mapping policies | SEMS+ live regional/time/unit/sign contract and partial-read recovery; Solis OAuth reconciliation, customer self-service/tenancy, Deye cross-customer grants; canonical profiles/history/alarm/failover; visual density | Credential→discovery→binding→telemetry→incident/report verified per ecosystem; synthetic checks do not prove live acceptance; UI error/reconnect/mobile, pixel and actual grants separately recorded |
| Commissioning 5–9 / 6–10 | Manual check/evidence text, six-check handover gate; two-column chooser/checklist visible before selecting a site | Electrical procedures, measurements integration, uploads/signatures | Recorded real test procedure/outcome reviewed; never auto-unlock from self-attested PASS |
| Incidents 6–11 / 7–12 | Dedup/out-of-order/recovery, 3 actual-count charts, full-width list, triage/assign/notes/history, SLA, versioned playbook/jobs | Remaining chart/drill-down parity, actual vendor alarm decoders/playbooks, external escalation channels/files | Alarm fixture→incident→assignment→job→recovery→close; channels independently observed |
| Maintenance/OTA 5–10 / 6–10 | Work plans, execution/results/time/void/review, health from observations | Parts/service contracts/uploads; firmware package verification/compatibility/transfer/rollback | Independent review plus actual OTA lab fail/recovery trials on exact hardware |
| Reports 5–9 / 5–9 | Scoped CSV/XLSX/HTML artifacts, main/mini charts from API, legend/table interactions, archive downloads, explicit non-JSON advisory market inputs | PDF/email, additional report workflows, tariffs/CO₂ assumptions, signed customer reports | Reproduce report from source set; correct scope and saved bytes; actual delivery receipt |
| Audit/journal 5–8 / 4–7 | Hash-linked append-only local DB audit, command state history | External anchoring, retention/search/export at scale | Tamper/recovery check and immutable external checkpoint; all commands traced to authorization |
| Map/fleet 3–6 / 5–9 | Public-domain Natural Earth land geometry, Mercator projection, actual finite GPS, pan/zoom/fit, keyboard markers, filters/list/detail; provenance recorded | Detailed street/satellite maps, boundary data, marker-cluster interaction; antimeridian/polar UX | No invented pins; invalid GPS, zoom persistence, filter and retry browser checks; geography/attribution review at supported zoom levels |
| Settings 5–8 / 7–11 | Local settings/ownership/source/notification drafts and adapters forms | Granular ownership, delivery integrations, versioned tariff rules | Configuration produces real downstream effect or explicitly remains draft, with audit/revert |
| Shared UI 1–3 / 10–18 | Single shell/sidebar/app.css, reusable forms/tables/dialogs, VI/EN; scope persistence, mobile drawer/Escape/focus, empty tables, preserve drafts against live refresh, retry; shared rule/platform guides | Component cleanup, comprehensive assistive-technology/contrast/translation review and pixel/usability acceptance | 84 isolated browser contracts; 31 empty-installation routes; previous wide sweep plus 12 new VI/EN states and 430px checks; not exhaustive action or pixel acceptance |
| 8 vendor platforms 65–115 / 35–68; Bluesun profile extra | Eight cloud read paths of different depth, including Eybond platform/session/collector/native read; profile/registry; Deye-only guarded compiler | Eybond source time/canonical mapping/history/alarm/control, incremental inventory; complete vendor-native maps and OEM acceptance | Contract + field evidence + live account/device acceptance per variant; cannot certify by logo |
| Site Agent 20–35 BE | Token enrollment/ingest, sequence/replay, SQLite outbox, model FC03/04 TCP/V5 và HA bridge; 41 community profile | Service install/discovery, RTU và full model TCP suite, mTLS/rotations, reconnect/backfill/update/diagnostics | Prolonged offline→reconnect/replay/load test, cert/revoke/update drills and site hardware trial |
| Tests/simulator/E2E 175–315 combined | BE contracts/workflows and isolated browser simulator; inventory below | Large model/error fixture corpus, HIL, soak/load/security/accessibility/visual acceptance | Trace each acceptance criterion to executable check and actual observed evidence |
| Infra/migrations/scripts 15–25 | Package/build, controller CLI, dev scripts, source inventory | Production deploy/HA/tenant observability/backup restore/migrations/oncall | Install/upgrade/restore/runbook and workload SLO verified in target environment |

### Vì sao code nhỏ hơn dự toán nhiều lần?

**Vì hiện còn thiếu phần lớn độ sâu của sản phẩm trưởng thành.** Reuse có giảm trùng lặp, nhưng không giải thích được toàn bộ chênh lệch. Frontend hiện là JavaScript ES modules, không phải React/TypeScript theo giả định dự toán. Storage/controller đơn tiến trình và tập workflow hẹp cũng nhỏ hơn kiến trúc SaaS/SCADA dài hạn.

Bảng dự toán 400k–630k production bao gồm nhiều model/hãng, native-control, đầy đủ agent, vận hành offline, optimizer, OTA, tenancy, long-term telemetry, reports/delivery, và UI 55–75 screen/state. Repo chưa có phần lớn các lớp đó. Có catalog/nút/form/API alias không đồng nghĩa triển khai chúng. Xóa code dựng dữ liệu hoặc compiler đoán có thể làm LOC giảm nhưng làm kết luận đúng hơn.

Không thể dùng `LOC hiện có / LOC dự toán` làm % hoàn thành; cũng không thể dùng “kiến trúc sạch” để kết luận đã làm xong. Chỉ đóng một mục khi đủ điều kiện ở cột cuối, có BE/FE liên kết, test tương ứng và bằng chứng cần thiết.

## Liên kết chức năng đã kiểm tra và ranh giới

1. Cloud account → adapter → discovery → device binding → telemetry/native provenance → mapping/quality/source → chart/report. Discovery/latest có contract theo từng hãng; shipping canonical profiles/backfill chưa đầy đủ. Editor mapping đã nối tới native observations và version/review service; approved draft vẫn không phải commissioned profile và không thay dữ liệu vận hành.
2. Device intent → capability → preview/diff → confirmation → serialize/idempotency → send/order → readback → journal. ACK không phải VERIFIED; UNKNOWN_OUTCOME không tự retry ghi. Chưa chứng minh hardware acceptance.
3. Schedule revision → compile/capability report → source digest recheck → rollout/canary → per-device outcomes. Lịch đổi hoặc profile bị thu hồi phải vô hiệu kế hoạch cũ. Không có universal slot/register mapping.
4. Native alarm → normalized alarm observation → correlation/dedup/order → incident → response/note/playbook → work order → execution/time → independent review → close. Core có test; vendor alarm decoding/delivery còn thiếu.
5. Site/profile/source policy → all relevant views. Đã bỏ các alias ghi không gắn engine và dữ liệu hardcode; topology reconciliation/source selection mọi metric vẫn cần mở rộng.

## Kiểm thử và QA

Baseline 27/09 từng tham chiếu `legacy-validation-2026-09-27.md` cho browser/CSS/flow desktop/mobile; file hiện không có trong checkout nên cần đối chiếu lại bằng chứng. Các bản dưới đây giữ số liệu snapshot cũ; checkpoint hiện tại ở đầu tài liệu.

Kết quả tổng hợp cuối được ghi trong [audit-validation-2026-09-23.md](audit-validation-2026-09-23.md). Các lỗi phát hiện được sửa rồi chỉ chạy lại kiểm tra bị ảnh hưởng; không coi lần chạy trước sửa là kiểm thử bản cuối. Không dùng tài khoản/thiết bị thật trong suite này.

Đợt Eybond bổ sung: full BE 429 pass/3 fail; sau sửa, 73 ca thuộc nhóm bị ảnh hưởng đều pass. Full browser 10 pass/1 fail; sửa selector test rồi ca đó pass. Ruff/28 module JS qua. Chi tiết, log và giới hạn QA nằm tại [eybond-validation-2026-09-24.md](eybond-validation-2026-09-24.md), không cộng số ca rerun vào tổng suite.

Đợt Mapping 25/09: xem [mapping-validation-2026-09-25.md](mapping-validation-2026-09-25.md). Full BE **450 passed**; full browser **13 passed** trước sửa tab theo QA. Gộp điều hướng Data về một hàng tab dùng chung; hồi quy riêng ghi trong validation. Số test không được cộng qua các lần chạy.

Screenshots local QA: `work/qa-audit/accounts-vi.png`, `site-overview.png`, ảnh alert mobile và work-order workflow. Đã xem trực tiếp các ảnh đại diện: chung sidebar/styles; account layout theo cấu trúc ảnh 21, có Bluesun/Eybond; các trường unknown không tô thành thành công. Còn khoảng cách UI: tổng quan quá dọc, topology điện/phân bổ nguồn→tải chưa đầy đủ, một số bảng ở độ rộng nhỏ chưa tối ưu. Đợt 27/09 đã bổ sung flow có motion và sửa CSS toàn cục; ảnh mới được ghi trong validation mới. Không kết luận khớp 100% 26 ảnh.


<!-- actual-code-inventory:start -->
## Số dòng thực tế có thể đo lại

Đo lúc **2026-10-09T03:10:57.106004+00:00** trên working tree, gồm code chưa commit.

| Nhóm | Số file | Dòng vật lý | Dòng không trống |
|---|---:|---:|---:|
| Backend Python | 141 | 50,202 | 43,944 |
| Frontend JavaScript | 62 | 15,684 | 15,099 |
| Frontend CSS / HTML | 2 | 9,120 | 8,373 |
| Test BE / simulator / fixture | 121 | 23,712 | 20,169 |
| Test UI / browser fixture | 32 | 3,217 | 2,914 |
| Scripts tự viết | 4 | 624 | 570 |
| **Tổng FE (JS + CSS/HTML)** | **64** | **24,804** | **23,472** |
| **Tổng code ứng dụng BE + FE** | **205** | **75,006** | **67,416** |
| **Tổng test / simulator / fixture** | **153** | **26,929** | **23,083** |
| **Tổng code ứng dụng + test + scripts** | **362** | **102,559** | **91,069** |

Phương pháp: đếm dòng vật lý (gồm comment và dòng trống), đồng thời công bố số dòng không trống. Không phải semantic SLOC. Không tính dependency, môi trường ảo, lock, generated, assets/ảnh, JSON hợp đồng, tài liệu, build output hoặc cache. Nhóm simulator/fixture không được tính vào production. Không cộng các dòng tổng lần nữa.

Đo lại bằng `python scripts/measure_code.py --update-doc`; lệnh chỉ đọc source và cập nhật báo cáo, không chạy test, build, QA hoặc gọi thiết bị.

Danh sách từng file và số dòng nằm trong [code-inventory.json](evidence/code-inventory.json). LOC phản ánh kích thước mã, không chứng minh workflow đúng, hoàn thiện UI hoặc nghiệm thu phần cứng.
<!-- actual-code-inventory:end -->
