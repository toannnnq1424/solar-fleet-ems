from datetime import timedelta

import pytest
from test_workspaces import login

pytest_plugins = ["test_workspaces"]

from solar_fleet.domain import utcnow
from solar_fleet.genset_controller import GeneratorSpecs
from solar_fleet.grid_code_regulator import FreqWattDroop, ProtectionRelayLimits, VoltVarCurve, VoltWattCurve
from solar_fleet.predbat_planner import BatterySpecs, PredbatPlanner


@pytest.mark.parametrize("arbitrage", [False, True])
def test_predbat_energy_conservation(arbitrage):
    specs = BatterySpecs(charge_efficiency=0.8, discharge_efficiency=0.7, max_soc_pct=80)
    solar = [0.0, 20.0, 0.0, 0.0] * 6
    load = [5.0] * 24
    plan = PredbatPlanner(specs).plan_horizon(solar, load, [0.2] * 24, [0.9] * 24,
                                            current_soc_pct=75, enable_arbitrage=arbitrage)
    energy = 7.5
    for slot in plan["slots"]:
        energy += slot["battery_charge_kw"] * 0.8 - slot["battery_discharge_kw"] / 0.7
        assert specs.min_soc_pct / 100 * specs.capacity_kwh - 0.003 <= energy <= 8.003
        assert slot["battery_soc_pct"] == pytest.approx(energy / 10 * 100, abs=0.06)
        assert slot["solar_kw"] + slot["grid_import_kw"] + slot["battery_discharge_kw"] == pytest.approx(
            slot["load_kw"] + slot["battery_charge_kw"] + slot["grid_export_kw"], abs=0.002)


@pytest.mark.parametrize("field,value", [
    ("solar_forecast_hourly", [-1.0] * 24),
    ("load_forecast_hourly", [1.0] * 25),
    ("import_tariffs_hourly", ["NaN"] * 24),
    ("current_soc_pct", 0), ("tariff_source", " "), ("currency", "VND"),
])
def test_predbat_rejects_invalid_inputs(local, field, value):
    client, _ = local
    body = {**scenarios()["predbat/plan"], field: value}
    assert client.post("/api/predbat/plan", json=body, headers=login(local)).status_code == 422


def scenarios():
    return {
        "microgrid/simulate": {"parameters": {
            "nominal_frequency_hz": 60.0, "nominal_voltage_pu": 1.0,
            "frequency_threshold_hz": 0.5, "voltage_threshold_pu": 0.1,
            "resync_frequency_tolerance_hz": 0.05, "resync_voltage_tolerance_pu": 0.02,
            "resync_phase_tolerance_deg": 5.0}, "inverters": [], "loads": [],
            "grid_voltage_pu": 1.0, "grid_frequency_hz": 60.0,
            "grid_phase_deg": 0.0, "dt_seconds": 1.0},
        "solar/estimate": {"latitude": 10.0, "longitude": 106.0, "peak_power_kwp": 10.0,
                           "date": "2026-09-27", "altitude_m": 20.0, "tilt_deg": 15.0,
                           "azimuth_deg": 180.0, "system_loss": 0.14, "inverter_efficiency": 0.97,
                           "hourly_temperature": [25.0] * 24, "hourly_wind": [1.0] * 24},
        "predbat/plan": {**vars(BatterySpecs()), "solar_forecast_hourly": [0.0] * 24,
                         "load_forecast_hourly": [2.0] * 24,
                         "import_tariffs_hourly": [0.2] * 24,
                         "export_tariffs_hourly": [0.05] * 24,
                         "current_soc_pct": 50.0, "enable_arbitrage": False,
                         "currency": "USD", "tariff_source": "TEST_ONLY"},
        "thermal/heat-pump-cop": {"ambient_temp_c": 7, "supply_temp_c": 35, "required_thermal_kw": 6,
                                  "carnot_efficiency": 0.5, "min_electric_kw": 0.5, "max_electric_kw": 3.5},
        "thermal/sg-ready-evaluate": {"pv_surplus_kw": 3, "grid_price": 0.15, "is_grid_peak_lock": True,
                                      "surplus_threshold_kw": 1.8, "forced_surplus_kw": 3.5,
                                      "tank_temp_c": 20, "min_temp_c": 42,
                                      "normal_setpoint_c": 52, "boost_setpoint_c": 65},
        "genset/evaluate-dispatch": {"specs": vars(GeneratorSpecs()), "initial_state": "running_loaded",
                                     "elapsed_in_state_seconds": 10, "cumulative_run_seconds": 100,
                                     "microgrid_load_kw": 30, "battery_soc_pct": 20,
                                     "is_grid_available": False, "battery_max_charge_kw": 15,
                                     "battery_max_discharge_kw": 15, "dt_seconds": 60},
        "genset/black-start-sequence": {"specs": vars(GeneratorSpecs()),
                                        "observations": [{"bus_voltage_v": 230, "pv_frequency_hz": 50,
                                                          "critical_load_kw": 8}]},
        "grid-code/evaluate": {"voltage_v": 258, "frequency_hz": 50, "current_power_kw": 10,
                               "volt_watt": vars(VoltWattCurve()), "volt_var": vars(VoltVarCurve()),
                               "freq_watt": vars(FreqWattDroop()), "protection": vars(ProtectionRelayLimits())},
    }


@pytest.mark.parametrize("route", scenarios())
def test_explicit_calculations_reject_missing_inputs_and_never_execute(local, route):
    client, controller = local
    headers = login(local)
    body = scenarios()[route]
    url = "/api/" + route
    assert client.post(url, json={}, headers=headers).status_code == 422
    for key in body:
        partial = {k: v for k, v in body.items() if k != key}
        assert client.post(url, json=partial, headers=headers).status_code == 422
    assert client.post(url, json={**body, "unknown": 1}, headers=headers).status_code == 422
    result = client.post(url, json=body, headers=headers)
    assert result.status_code == 200, result.text
    assert result.json()["dispatch_enabled"] is False
    assert result.json()["input_source"] == "USER_SUPPLIED"
    if "sg-ready" in route:
        assert result.json()["sg_ready_state"] == 1  # Grid lock must not be silently overridden.
    if "black-start" in route:
        assert result.json()["current_stage"] == "failed"
    assert controller.store.list("command") == []


def configuration():
    start = utcnow().replace(minute=0, second=0, microsecond=0)
    return {"dispatch_device_id": "sim-device", "billing_meter_device_id": "sim-device",
            "dispatch_config": {**vars(BatterySpecs()), "currency": "USD", "tariff_source": "TEST_ONLY",
                                "hourly_prices": [{"timestamp": (start + timedelta(hours=h)).isoformat(),
                                                   "import_per_kwh": 0.2, "export_per_kwh": 0.05}
                                                  for h in range(24)]}}


def test_microgrid_uses_only_supplied_equipment(local):
    client, controller = local
    headers = login(local)
    body = scenarios()["microgrid/simulate"]
    response = client.post("/api/microgrid/simulate", json=body, headers=headers).json()
    assert response["simulation"]["state"] == "grid_connected"
    assert response["controller_status"]["inverters"] == []
    assert response["controller_status"]["loads"] == []
    inverter = {"inverter_id": "supplied", "mode": "grid_following", "real_power_kw": 2.0,
                "reactive_power_kvar": 0.0, "voltage_pu": 1.0, "frequency_hz": 60.0,
                "power_factor": 1.0, "rated_power_kw": 4.0, "is_online": True}
    body["inverters"] = [inverter]
    body["grid_frequency_hz"] = 0.0
    response = client.post("/api/microgrid/simulate", json=body, headers=headers).json()
    assert response["simulation"]["state"] == "islanding"
    assert response["controller_status"]["total_generation_kw"] == 2.0
    assert response["hardware_acknowledgements_verified"] is False
    for field in inverter:
        body["inverters"] = [{k: v for k, v in inverter.items() if k != field}]
        assert client.post("/api/microgrid/simulate", json=body, headers=headers).status_code == 422
    body["inverters"] = [inverter, inverter]
    assert client.post("/api/microgrid/simulate", json=body, headers=headers).status_code == 422
    body["inverters"] = [inverter]
    load = {"load_id": "supplied-load", "name": "Supplied load", "power_kw": 1,
            "priority": 1, "is_shed": False, "is_critical": True}
    body["loads"] = [load]
    assert client.post("/api/microgrid/simulate", json=body, headers=headers).status_code == 200
    for field in load:
        body["loads"] = [{k: v for k, v in load.items() if k != field}]
        assert client.post("/api/microgrid/simulate", json=body, headers=headers).status_code == 422
    for field, value in (("power_kw", -1), ("priority", 0), ("priority", 11), ("power_kw", "NaN")):
        body["loads"] = [{**load, field: value}]
        assert client.post("/api/microgrid/simulate", json=body, headers=headers).status_code == 422
    body["loads"] = [load, load]
    assert client.post("/api/microgrid/simulate", json=body, headers=headers).status_code == 422
    body["loads"] = [load]
    parameters = body["parameters"].copy()
    for field, value in (
        ("frequency_threshold_hz", parameters["nominal_frequency_hz"]),
        ("voltage_threshold_pu", parameters["nominal_voltage_pu"]),
        ("resync_frequency_tolerance_hz", parameters["frequency_threshold_hz"] + 1),
        ("resync_voltage_tolerance_pu", parameters["voltage_threshold_pu"] + 1),
    ):
        body["parameters"] = {**parameters, field: value}
        assert client.post("/api/microgrid/simulate", json=body, headers=headers).status_code == 422
    assert controller.store.list("command") == []


def test_clearsky_requires_explicit_location_date_and_altitude(local):
    client, _ = local
    headers = login(local)
    params = {"lat": 10, "lon": 106, "date": "2026-09-27", "altitude_m": 20}
    url = "/api/solar/clearsky"
    for field in params:
        assert client.get(url, params={k: v for k, v in params.items() if k != field},
                          headers=headers).status_code == 422
    for field, value in (("lat", "nan"), ("lon", 181), ("altitude_m", "inf")):
        assert client.get(url, params={**params, field: value}, headers=headers).status_code == 422
    for date, status in (("2026-02-30", 400), ("0000-01-01", 400), ("27/09/2026", 422)):
        assert client.get(url, params={**params, "date": date}, headers=headers).status_code == status
    result = client.get(url, params=params, headers=headers)
    assert result.status_code == 200
    assert result.json()["weather_forecast_verified"] is False
    assert result.json()["dispatch_enabled"] is False


def test_generator_respects_absorption_and_explicit_discharge_budget(local):
    client, _ = local
    headers = login(local)
    body = scenarios()["genset/evaluate-dispatch"]
    body.update(microgrid_load_kw=1, battery_max_charge_kw=0)
    response = client.post("/api/genset/evaluate-dispatch", json=body, headers=headers)
    assert response.status_code == 200
    dispatch = response.json()["dispatch"]
    assert dispatch["output_power_kw"] == 1
    assert dispatch["battery_charge_kw"] == 0
    assert dispatch["below_minimum_loading"] is True
    body.update(initial_state="off", battery_soc_pct=60, microgrid_load_kw=20,
                battery_max_discharge_kw=25)
    response = client.post("/api/genset/evaluate-dispatch", json=body, headers=headers)
    assert response.json()["dispatch"]["state"] == "off"
    body["battery_max_discharge_kw"] = 10
    response = client.post("/api/genset/evaluate-dispatch", json=body, headers=headers)
    assert response.json()["dispatch"]["state"] == "cranking"


def test_planning_persists_and_clears_scoped_configuration(local):
    client, controller = local
    headers = login(local)
    url = "/api/sites/sim-site/planning-configuration"
    body = configuration()
    revision = client.get(url).json()["revision"]
    result = client.post(url, json={**body, "expected_revision": revision}, headers=headers)
    assert result.status_code == 200, result.text
    assert result.json()["dispatch_enabled"] is False
    assert client.get(url).json()["configuration"] == body
    assert controller.store.get("site", "sim-site")["dispatch_config"] == body["dispatch_config"]
    cleared = dict.fromkeys(body)
    assert client.post(url, json={**cleared, "expected_revision": result.json()["revision"]},
                       headers=headers).status_code == 200
    assert client.get(url).json()["configuration"] == cleared
    assert controller.store.list("command") == []


def test_planning_scope_permissions_and_invalid_inputs(local):
    client, controller = local
    url = "/api/sites/sim-site/planning-configuration"
    headers = login(local, "viewer")
    assert client.post(url, json=configuration(), headers=headers).status_code == 403
    login(local, "other")
    assert client.get(url).status_code == 404
    headers = login(local, "scoped-admin")
    assert client.post("/api/sites/other-site/planning-configuration", json=configuration(),
                       headers=headers).status_code == 403
    headers = login(local)
    invalid = configuration()
    invalid["expected_revision"] = client.get(url).json()["revision"]
    invalid["billing_meter_device_id"] = "other-device"
    assert client.post(url, json=invalid, headers=headers).status_code == 422
    invalid = configuration()
    invalid["dispatch_config"]["charge_efficiency"] = 0
    assert client.post(url, json=invalid, headers=headers).status_code == 422
    invalid = configuration()
    invalid["dispatch_config"]["hourly_prices"][1] = invalid["dispatch_config"]["hourly_prices"][0]
    assert client.post(url, json=invalid, headers=headers).status_code == 422
    assert controller.store.get("site", "sim-site").get("dispatch_config") is None