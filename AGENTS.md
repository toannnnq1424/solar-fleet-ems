# Repository workflow

- Read docs/research-architecture-report.md, docs/implementation-status.md and the scoped vendor evidence before changing an adapter or control.
- Do not infer protocol/register/control semantics from branding, a UI menu, a similar field name, or a public endpoint alone. Missing evidence stays UNKNOWN.
- Default READ ONLY. Never use real credentials, hardware, browser sessions or production writes in automated tests. Simulator fixtures belong only under tests/.
- New commissioned capabilities require exact device/logger/firmware/account/region identity, official evidence, reviewed range/unit/enum, fresh readback and an acceptance record. Do not add wildcard profiles or bypass the command engine.
- Keep native features discoverable with a reason when locked; do not collapse independent export/battery/meter/grid controls into an inaccurate universal action.
- Run ruff check, relevant pytest tests, JavaScript syntax check for UI edits and python -m build before delivering an implementation change.
- Use one controller process. Preserve idempotency, per-device serialization, site isolation and unknown-outcome quarantine.
- Never commit secrets, raw customer payloads, browser cookies, database files or screenshots containing customer identifiers.
