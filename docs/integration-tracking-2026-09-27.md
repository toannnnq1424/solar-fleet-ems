# Integration Tracking Log - before_project Merge

> Created: 2026-09-27T01:25 (Asia/Ho_Chi_Minh)
> Baseline commit: `feb82ef` "chore: pre-integration checkpoint"
> Baseline LOC: BE 15,567 / FE-JS 12,019 / CSS 5,913 / Tests 9,089+702 / Scripts 518 = **43,808 total**
> Post-Integration LOC: BE 16,839 / FE-JS 12,187 / CSS 6,012 / Tests 9,437+702 / Scripts 518 = **45,695 total** (+1,887 LOC)

## Phase A: Audit & Planning [DONE]

### A1. Committed baseline [DONE]
- Git commit `feb82ef` captures all existing work before integration.

### A2. Read docs [DONE]
- `docs/legacy-project-audit.md`: 30 projects, 4M+ lines total, license decisions per project.
- `docs/model-library-and-home-assistant.md`: 41 profiles, 3,145 fields, 913 decoders already imported.
- `docs/evidence/legacy-project-inventory.json`: hash manifest of all 30 projects.

### A3. Read before_project directories [DONE]
All 30 projects scanned. Key sources identified and integrated:
1. **ha-solarman-main** (MIT): 30 profile definitions imported via model-library.json.
2. **solar-inverter-modbus-registers-main** (MIT): 10 profiles imported.
3. **Sungrow-SHx-Inverter-Modbus-Home-Assistant-main** (MIT): 1 profile (99 fields) imported; Modbus SHx register maps and fault codes extracted into `vendor_registers.py`.
4. **sem-community-main** (MIT): EWMA baseline adapted; EVN TOU tariff & Circular 15 penalty engine cleanly implemented in `tariff_engine.py`.
5. **evcc-master** (MIT): Energyflow Visualization design concepts; power-proportional wire speeds, glow filters, and particle dashes implemented in `app.css` & `energy-flow.js`.
6. **goodwe-master** (MIT): ET/EH/ES holding register map (35100-35182) and 20+ fault codes with remediation SOP in `vendor_registers.py`.
7. **huawei-solar-lib-develop** (AGPL-3.0) & **deye-inverter-mqtt-main** (Apache-2.0): Holding register maps and fault codes extracted into `vendor_registers.py`.
8. **growatt_modbus-main** & **solis2mqtt**: Holding registers and alarm tables in `vendor_registers.py`.
9. **vpplib-dev** (GPL-3.0): Clean-room physical battery degradation model (EFC cycles, square-root calendar aging, Arrhenius thermal acceleration, and warranty compliance) in `battery_health.py`.
10. **emhass-master** (MIT): 24-hour economic dispatch optimization under EVN 3-tier tariffs in `forecast_baseline.py`.

---

## Phase B: Implementation & Verification [DONE]

### B1. Model-Specific Registers & Alarms [DONE]
- Implemented in `src/solar_fleet/vendor_registers.py`:
  - GoodWe (ET/EH/ES series): 25 holding registers, 20 alarm codes with SOP and severity.
  - Deye (SUN-SG04LP3 series): 19 holding registers, 18 alarm codes with SOP and severity.
  - Sungrow (SH5.0 - SH10RT series): 22 holding registers, 17 alarm codes with SOP and severity.
  - Huawei (SUN2000 series): 22 holding registers, 13 alarm codes with SOP and severity.
  - Growatt (SPH/SPF series): 19 holding registers, 12 alarm codes with SOP and severity.
  - Solis (RHI / S5-EH1P series): 18 holding registers, 11 alarm codes with SOP and severity.
  - Exact device identity invariant preserved: brand alone returns UNKNOWN severity and empty registers; exact model returns verified registers and alarms.
  - Wired to `/api/vendor-registers/{brand}` and `/api/alarms/decode/{vendor}/{code}`.

### B2. Energy Flow Animation Upgrade [DONE]
- Upgraded `src/solar_fleet/static/app.css`:
  - Added power-proportional particle flow speeds (high, medium, low).
  - Added track illumination, drop-shadow glow filters, and hover micro-interactions.
- Upgraded `src/solar_fleet/static/energy-flow.js`:
  - Set `data-power` attribute dynamically based on wattage.
  - Display battery SOC indicator via dataset attributes without `.style.` violations.
  - Fully verified with `node --input-type=module --check`.

### B3. Forecast & Optimization Engine [DONE]
- Implemented in `src/solar_fleet/forecast_baseline.py`:
  - `calculate_clearsky_pv_profile(...)`: Physical solar zenith and clear-sky GHI model for any latitude/longitude and hour.
  - `optimize_economic_dispatch(...)`: 24-hour ahead battery charge/discharge optimization under EVN 3-tier tariffs (self-consumption maximization, peak tariff shaving, off-peak pre-charging).
  - API endpoint: `GET /api/sites/{site_id}/dispatch-schedule`.

### B4. Battery Degradation & Health Model [DONE]
- Implemented in `src/solar_fleet/battery_health.py`:
  - Equivalent Full Cycle (EFC) counting: throughput / nominal capacity.
  - Arrhenius thermal acceleration factor: doubling rate every 10°C rise above 25°C.
  - Depth of Discharge (DoD) stress factor power law.
  - Fusion between physical degradation model and reported BMS Coulomb counting.
  - Remaining Useful Life (RUL) estimation to EOL threshold (70% SOH).
  - Warranty compliance tracking (remaining cycles, remaining calendar days).
  - API endpoints: `GET /api/devices/{device_id}/battery-health` and `GET /api/sites/{site_id}/battery-health`.

### B5. Tariff Engine Enhancement [DONE]
- Implemented in `src/solar_fleet/tariff_engine.py`:
  - Official EVN retail electricity tariff tables (Decision 2699/QĐ-BCT / 14/2023/QĐ-TTg) across Manufacturing, Commercial, Administrative tiers and High/Medium/Low voltage levels.
  - Time-of-Use schedule classifier (Mon-Sat Peak 09:30-11:30 & 17:00-20:00, Off-peak 22:00-04:00, Sunday no peak).
  - Circular 15/2014/TT-BCT Power Factor penalty: $k = (0.90 / \cos \varphi - 1.0) \times 100\%$ reactive power purchase surcharge and required kvar compensation.
  - Peak Shaving opportunity analysis.
  - API endpoints: `GET /api/tariff/evn-rates` and `GET /api/sites/{site_id}/tariff-analysis`.

### B6. UI Polish & 14-Tab Integration [DONE]
- `src/solar_fleet/static/ems-workspace.js`:
  - Added 24-Hour Economic Dispatch & EVN Peak Optimizer interactive card.
  - Added EVN Tariff & Circular 15 Power Factor Evaluation interactive card with compliance badges and cost breakdowns.
- `src/solar_fleet/static/device-workspace.js`:
  - Updated Subtab 4 "Health & Reliability" to load real SOH %, EFC cycles, thermal stress multipliers, and warranty status.
- `src/solar_fleet/static/plant-workspace.js`:
  - Replaced UI arrow and checkmark strings with clean text.
- Validated all 31 JavaScript modules: zero syntax errors, zero `.style.` inline violations, all global design system compliant.

### B7. Test Suite Expansion [DONE]
- Added 4 new test modules:
  - `tests/test_battery_health.py`: 4 tests (Arrhenius, DoD stress, SOH estimation, BMS fusion).
  - `tests/test_tariff_engine.py`: 3 tests (EVN TOU schedule, Circular 15 PF penalty, site tariff analysis).
  - `tests/test_dispatch_optimizer.py`: 2 tests (ClearSky solar profile, 24h dispatch cost savings).
  - `tests/test_vendor_registers_expanded.py`: 4 tests (alarm counts, exact model decoding, brand alone invariant, query).
- Fixed relative import in `tests/test_gis_and_topology.py`.
- Fixed fallback format in `src/solar_fleet/vendor_registers.py`.
- Full pytest test suite: **549 tests passing**.

---

## Phase C: Verification Records

- `ruff check src tests`: **PASSED** (0 errors)
- `node --input-type=module --check`: **PASSED** (All 31 static JS modules valid)
- `pytest`: **549 passed**
- `python -m build`: **PASSED** (Built `solar_fleet_ems-0.2.0-py3-none-any.whl`)
- `measure_code.py --update-doc`: **PASSED** (Updated `docs/mockup-coverage.md`)
