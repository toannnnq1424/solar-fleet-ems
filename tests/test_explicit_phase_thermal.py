import copy

import pytest
from test_workspaces import login


def phase_input():
    return {
        "measurement": {"v_l1": 230, "v_l2": 230, "v_l3": 230,
                        "i_l1": 10, "i_l2": 10, "i_l3": 10,
                        "p_l1": 2, "p_l2": 2, "p_l3": 2,
                        "q_l1": 0, "q_l2": 0, "q_l3": 0},
        "limits": {"max_total_kw": 3, "max_phase_kw": 4, "max_phase_kvar": 2,
                   "battery_max_charge_kw": 10, "battery_max_discharge_kw": 10,
                   "allows_independent_phases": True},
    }


def building_input():
    return {
        "building": {"indoor_temp_c": 20, "wall_temp_c": 20,
                     "air_heat_capacity_kwh_k": 1, "wall_heat_capacity_kwh_k": 5,
                     "r_indoor_wall_k_kw": 2, "r_wall_outdoor_k_kw": 2,
                     "solar_aperture_m2": 0, "internal_gain_base_kw": 0},
        "outdoor_temps_hourly": [20, 20], "solar_ghi_hourly": [0, 0], "heating_thermal_kw": 0,
    }


@pytest.mark.parametrize("path,factory", [
    ("phase-balancer/dispatch", phase_input), ("thermal/building-simulation", building_input),
])
def test_every_calculation_field_is_required(local, path, factory):
    client, _ = local
    headers = login(local, "operator")
    payload = factory()
    for key, value in payload.items():
        missing = copy.deepcopy(payload)
        del missing[key]
        assert client.post(f"/api/{path}", json=missing, headers=headers).status_code == 422
        if isinstance(value, dict):
            for nested_key in value:
                missing = copy.deepcopy(payload)
                del missing[key][nested_key]
                assert client.post(f"/api/{path}", json=missing, headers=headers).status_code == 422


@pytest.mark.parametrize("powers", [(2, 2, 2), (-2, -2, -2), (4, -4, 0)])
def test_phase_nameplate_limit_and_non_execution(local, powers):
    client, controller = local
    payload = phase_input()
    for index, power in enumerate(powers, 1):
        payload["measurement"][f"p_l{index}"] = power
    response = client.post("/api/phase-balancer/dispatch", json=payload, headers=login(local, "operator"))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["dispatch_enabled"] is False
    assert data["input_source"] == "USER_SUPPLIED"
    assert sum(abs(data["dispatch_setpoints"][f"p_l{i}_kw"]) for i in (1, 2, 3)) <= 3
    assert controller.store.list("command") == []


@pytest.mark.parametrize("case", ["nonfinite", "negative_limit", "zero_voltage", "unknown", "boolean"])
def test_phase_invalid_input(local, case):
    payload = phase_input()
    if case == "nonfinite":
        payload["measurement"]["p_l1"] = "NaN"
    elif case == "negative_limit":
        payload["limits"]["max_total_kw"] = -1
    elif case == "zero_voltage":
        payload["measurement"]["v_l1"] = 0
    elif case == "boolean":
        payload["limits"]["allows_independent_phases"] = "false"
    else:
        payload["invented"] = 1
    client, _ = local
    assert client.post("/api/phase-balancer/dispatch", json=payload,
                       headers=login(local, "operator")).status_code == 422


@pytest.mark.parametrize("case", ["short", "empty", "nonfinite", "negative", "unstable"])
def test_thermal_rejects_incomplete_or_invalid_series(local, case):
    payload = building_input()
    if case == "short":
        payload["solar_ghi_hourly"] = [0]
    elif case == "empty":
        payload["outdoor_temps_hourly"] = []
    elif case == "nonfinite":
        payload["outdoor_temps_hourly"] = ["Infinity", 20]
    elif case == "negative":
        payload["solar_ghi_hourly"] = [-1, 0]
    else:
        payload["building"]["air_heat_capacity_kwh_k"] = 0.001
    client, _ = local
    assert client.post("/api/thermal/building-simulation", json=payload,
                       headers=login(local, "operator")).status_code == 422


def test_thermal_preserves_explicit_zero_gains(local):
    client, controller = local
    response = client.post("/api/thermal/building-simulation", json=building_input(),
                           headers=login(local, "operator"))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["final_state"] == {"indoor_temp_c": 20, "wall_temp_c": 20}
    assert data["dispatch_enabled"] is False
    assert len(data["hourly_simulation"]) == 2
    assert controller.store.list("command") == []