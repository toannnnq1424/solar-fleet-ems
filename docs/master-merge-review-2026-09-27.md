# Default-branch integration and legacy-source review

Saved remediation as `7c2a1e5`; merged remote default `master` through `88676f3`
as `3e7df52` into `fix/real-data-engine-integration`. No push or hardware writes.

Legacy sources: `/Users/toanlamsaoduocc/Downloads/before_project`, containing
30 project directories. Discovery is not a completed review of all projects.
Keep the shared 15-entry sidebar and existing controller/adapter ownership.

## Regression containment

Eight newly merged read routes returned simulator observations as operational
data. Seven standalone command routes allowed request flags to influence
acceptance/execution claims. They now return 503 (missing live integration) or
409 (uncommissioned control), without invoking those engines. Existing scoped
adapter paths remain unchanged. Relevant subtabs display a shared VI/EN warning.
This is containment, not completion of live transport integration.

Unreviewed incoming source declarations are retained in
`evidence/master-88676f3-unreviewed-sources.json`, outside both identical reviewed
registries. Incoming vendor-audit narrative claims remain unverified.

## Growatt source finding

Read the MIT license, README and `growattServer/open_api_v1/__init__.py` in local
`PyPi_GrowattServer-6469d881462eaa4a3b3c6e3cfa6f17082e86eaf5` and fetched the
same public source on 2026-09-27:
<https://raw.githubusercontent.com/indykoning/PyPi_GrowattServer/6469d881462eaa4a3b3c6e3cfa6f17082e86eaf5/growattServer/open_api_v1/__init__.py>.
No upstream code copied in this batch.

It uses token-header authentication and endpoint-specific error semantics:
plant-details 10002 means missing plant, not necessarily expired authentication.
The merged client's global error table must not drive renewal/UI status without
correction. SPH and MIN have separate device implementations and scheduling
helpers; do not infer a universal brand-wide schedule contract.

The manufacturer-linked page
<https://www.showdoc.com.cn/262556420217021/1494060394238679> returned only an HTML
shell; official API behavior was not independently confirmed.

## Remaining work

Inventory revisions/licenses, reusable functions and existing implementation
owners across all legacy projects. Extend existing account/binding/ingestion
paths rather than duplicate clients. Preserve native unit, direction, time,
model, firmware and transport identity alongside canonical fields. Exact-profile
decoder/command/readback evidence is still required before commissioning.

VI/EN infrastructure exists; newly merged forms still contain untranslated
strings. Billing intervals/history, EV freshness, notification delivery, complete
interaction/visual acceptance and field commissioning remain open.

## Validation

Initial merged snapshot: 1,162 Python passes, one registry consistency failure;
29 browser passes. Combined suite collection failed on duplicate module names,
so suites run separately. After containment and registry synchronization,
24 focused tests passed. Final validation must not be confused with hardware
acceptance or a complete legacy-source audit.

The first containment full run exposed 12 old API tests expecting simulator
responses. Their production-route contracts now require explicit failure and
no command creation; module-level decoder/compiler tests remain intact.
All 95 affected tests passed, as did all 29 browser tests, Ruff, all static JS
syntax checks, whitespace checks and source/wheel build.

Final full Python suite: **1,185 passed, 12 dependency warnings**, exit 0.
Final browser suite: **29 passed**, exit 0. Logs:
`/tmp/solar-merge-final2-python.log`, `/tmp/solar-merge-final-browser.log`,
`/tmp/solar-merge-final-build.log`. These are software checks, not hardware
acceptance or complete interaction/translation coverage.