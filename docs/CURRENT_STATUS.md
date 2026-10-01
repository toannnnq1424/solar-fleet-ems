# Current System Status (Truthful & Machine-Verifiable)

**Evaluation Date:** 2026-10-01  
**Repository Branch:** `fix/real-data-engine-integration`  
**Current Maturity Stage:** **Pre-HIL / Lab Candidate** (Software integration verified on synthetic contracts/fixtures; pending physical hardware-in-the-loop and live on-site commissioning).

---

## 1. Subsystem Engineering Reality

| Subsystem | Verified Implemented Capability | Current Operational Limitation & Truth |
|---|---|---|
| **Deye Remote Control** | - `/v1.0/strategy/dynamicControl/read` wired into `CommandEngine._read_config(..., dynamic_read=True)`<br>- Hardware readback provides authoritative device timestamp for `fresh()` verification<br>- CamelCase readback tolerance rules registered (`maxSellPower` ±50W/2%, `maxChargeCurrent` ±1A, `gridChargeAction` boolean, `timeUseSettingItems` TOU list) | Production write compiler currently active for Deye in `plugins.py`. Full live execution requires on-site inverter connectivity and user-authorized credentials. |
| **Semantic Readback Engine** | - `DEFAULT_READBACK_RULES` supports both snake_case and camelCase parameters<br>- `_compare_tou_slots()` compares TOU slots with time string, SOC (±1.0%), power (±50W), and boolean grid charge<br>- `verify_semantic_readback()` enforces intent congruence | Semantic comparison covers known field tolerances; intent validation enforces matching parameter groups before readback acceptance. |
| **Local Modbus & V5 Poller** | - `ModbusTcpPoller` and `SolarmanV5Poller` enforce `exact_profile=True`<br>- Explicit profile resolution via `get_exact_profile(vendor, model_series)` without silent fallback to generic profiles<br>- Startup errors logged to failure log and audited with `INVALID_STARTUP_CONFIGURATION`<br>- Device identity reconciled across site, vendor, model, and integration | Real local polling requires local network connectivity to target inverters/gateways. |
| **Local Diagnostics** | - `poll_cycle_ms` tracks cycle time across all blocks, delays, and decoding<br>- `network_rtt_ms` remains `None` unless measured per packet<br>- `firmware_seen` remains `None` unless explicitly decoded from nameplate registers | Conflation between total poll duration and network RTT has been eliminated. |
| **Sungrow Commercial Profiles** | - Segregated into `SungrowSG110CXProfile` (110 kW, 9 MPPTs, 18 strings) and `SungrowSG125HXProfile` (125 kW, 6 MPPTs, 12 strings)<br>- `build_active_power_command` enforces exact physical rating (110 kW vs 125 kW)<br>- Operational polling enforces `WIRE_ZERO_BASED` addressing<br>- Unverified `SG250HX` profile alias **removed** from registry | No wildcard profile aliasing. SG125HX derating is validated up to 125 kW; SG110CX up to 110 kW. |
| **EMS & Fleet Optimizer** | - Zero-fake-data enforced: missing battery SOC returns HTTP 422<br>- Fleet balancing requires verified `rated_power_w`, `battery_capacity_wh`, and `battery_soc`<br>- `optimize_24h` requires exact 24-hour input arrays (no `else 2.0 kW` fake load fallback)<br>- 24h representative curves computed as hourly mean of observations, not peak-of-peaks max<br>- Multi-scenario projections labeled as deterministic sensitivity projections (-55% / +35%), not statistical quantiles | Real optimizer execution requires verified historical observations or explicit inputs. |
| **Multi-Vendor Control Registry** | - Universal `ControlAdapter` protocol supports `dynamic_read`<br>- Multi-vendor read decoders active for 8 ecosystems | Write compilers for non-Deye vendors remain quarantined / pending physical acceptance records. |
| **Hardware Acceptance Gate** | - `/api/commissioning` endpoint enforces IEC 62446-1 6-stage testing before write unlocking | **ACCEPTED_HARDWARE = 0**. All live writes remain locked by default until on-site tests are submitted. |
| **CI & Release Engineering** | - Local verification: Ruff, Pytest (1775 backend + 38 UI), Node `--check`, package build pass locally<br>- Code inventory tracks git commit SHA and dirty state | **Hosted CI Evidence:** Pending GitHub Actions workflow run execution on clean commit. |

---

## 2. Zero-Fake-Data Enforcement Audit

- **Battery SOC:** Missing SOC in `/api/sites/{id}/ems-optimization` returns HTTP 422 `insufficient_measured_telemetry_for_site: verified battery_soc observation required`.
- **Fleet Balancing:** Missing device rating or battery capacity in `/api/sites/{id}/fleet-balance` returns HTTP 422 `insufficient_device_configuration`.
- **24-Hour Optimization:** Incomplete profile arrays (< 24 intervals) raise `ValueError("Full 24-hour solar and load profiles required")`.
- **24-Hour Profile Aggregation:** Hourly values are computed as the arithmetic mean across verified telemetry observations, eliminating artificial peak-of-peaks inflation.
- **Scenario Labels:** Frontend displays "Kịch bản nắng yếu (-55%)" and "Kịch bản nắng mạnh (+35%)" to accurately represent sensitivity multipliers.

---

## 3. Verified Artifact & Test Baseline

- **Local Python Environment:** Python 3.14.6 in `/tmp/solar-fleet-audit-8ec68fd/bin/python`
- **Node Environment:** v26.3.0
- **Historical Archived Report:** [historical-status-2026-10-01.md](historical-status-2026-10-01.md)
- **Detailed Remediation Roadmap:** [remediation-roadmap.md](remediation-roadmap.md)
