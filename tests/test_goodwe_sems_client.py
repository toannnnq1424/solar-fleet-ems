"""Unit and contract tests for GoodWe SEMS Portal Cloud Client & Telemetry Normalizer.

Derived from upstream project:
pygoodwe-main (MIT License, Copyright (c) 2017 James Hodgkinson).
"""

from __future__ import annotations

from test_workspaces import login

from solar_fleet.goodwe_sems_client import (
    GoodWeSEMSClient,
    parse_goodwe_numeric,
)

# ---------------------------------------------------------------------------
# Unit Tests: Parser & Logic
# ---------------------------------------------------------------------------

def test_parse_goodwe_numeric():
    """Verify numeric parser handles raw values and unit strings."""
    assert parse_goodwe_numeric(123) == 123.0
    assert parse_goodwe_numeric(45.67) == 45.67
    assert parse_goodwe_numeric("2678.67(W)") == 2678.67
    assert parse_goodwe_numeric("123(W)") == 123.0
    assert parse_goodwe_numeric("50.02(Hz)") == 50.02
    assert parse_goodwe_numeric("95.5(%)") == 95.5
    assert parse_goodwe_numeric("invalid") == 0.0
    assert parse_goodwe_numeric(None) == 0.0


def test_process_login_response():
    """Verify login response parsing and dynamic regional redirection."""
    client = GoodWeSEMSClient(account="test@example.com", password="pwd")
    assert not client.is_authenticated

    # 1. Failure case
    fail_data = {"code": 100005, "msg": "Email or password error.", "data": None}
    assert not client.process_login_response(fail_data)
    assert not client.is_authenticated

    # 2. Success case with dynamic regional URL redirection
    success_data = {
        "code": 0,
        "msg": "success",
        "data": {"uid": "user_123", "token": "tok_xyz", "timestamp": 1700000000},
        "api": "https://au.semsportal.com/api/",
    }
    assert client.process_login_response(success_data)
    assert client.is_authenticated
    assert client.base_url == "https://au.semsportal.com/api/"
    assert "user_123" in client.token
    assert "tok_xyz" in client.token

    # Check headers format
    headers = client.headers
    assert "User-Agent" in headers
    assert "Token" in headers
    assert "tok_xyz" in headers["Token"]


def test_parse_station_detail_full():
    """Verify parsing of station detail including powerflow and inverters."""
    raw_payload = {
        "info": {
            "powerstation_id": "test_st_01",
            "stationname": "HCMC Solar Roof",
            "capacity": "20.0",
            "latitude": 10.8231,
            "longitude": 106.6297,
            "address": "Tan Binh, Ho Chi Minh",
            "status": 1,
            "battery_capacity": 30.0,
            "time": "09/27/2026 10:30:00",
        },
        "kpi": {
            "power": "45.2",
            "total_power": "18950.0",
            "day_income": "81.36",
            "total_income": "34110.0",
            "pac": "12500",
        },
        "powerflow": {
            "pv": "14200(W)",
            "load": "4500(W)",
            "loadStatus": -1,  # Importing
            "bettery": "5000(W)",
            "grid": "4700(W)",
        },
        "soc": {"power": "92.0"},
        "inverter": [
            {
                "sn": "GW15K-ET-001",
                "name": "Hybrid Inverter 1",
                "model_type": "GoodWe ET",
                "status": 1,
                "tempperature": "44.5",
                "invert_full": {
                    "pac": 12500,
                    "vac1": 230.1,
                    "vac2": 230.5,
                    "vac3": 229.9,
                    "iac1": 18.1,
                    "iac2": 18.2,
                    "iac3": 18.0,
                    "fac1": 50.01,
                    "vpv1": 580.0,
                    "vpv2": 575.5,
                    "ipv1": 12.3,
                    "ipv2": 12.3,
                    "soc": 92.0,
                    "pmeter": 4700,
                },
            }
        ],
    }

    detail = GoodWeSEMSClient.parse_station_detail(raw_payload, system_id="test_st_01")
    assert detail.station_info.station_id == "test_st_01"
    assert detail.station_info.station_name == "HCMC Solar Roof"
    assert detail.station_info.capacity_kw == 20.0
    assert detail.station_info.latitude == 10.8231

    # Check KPI
    assert detail.kpi["day_generation_kwh"] == 45.2
    assert detail.kpi["total_generation_kwh"] == 18950.0
    assert detail.kpi["pac_w"] == 12500.0

    # Check Powerflow
    assert detail.powerflow.pv_power_w == 14200.0
    assert detail.powerflow.load_power_w == 4500.0
    assert detail.powerflow.load_status == -1
    assert detail.powerflow.load_direction == "Importing"
    assert detail.powerflow.battery_power_w == 5000.0
    assert detail.powerflow.soc_pct == 92.0

    # Check Inverters
    assert len(detail.inverters) == 1
    inv = detail.inverters[0]
    assert inv.serial_number == "GW15K-ET-001"
    assert inv.temperature_c == 44.5
    assert inv.vac1 == 230.1
    assert inv.fac1_hz == 50.01
    assert inv.vpv1 == 580.0
    assert inv.pmeter_w == 4700.0


def test_powerflow_load_status_direction():
    """Verify loadStatus direction interpretation (-1 Importing, 1 Using Battery)."""
    raw_import = {
        "powerflow": {"load": "3000(W)", "loadStatus": -1},
    }
    detail_import = GoodWeSEMSClient.parse_station_detail(raw_import)
    assert detail_import.powerflow.load_direction == "Importing"

    raw_battery = {
        "powerflow": {"load": "3000(W)", "loadStatus": 1},
    }
    detail_battery = GoodWeSEMSClient.parse_station_detail(raw_battery)
    assert detail_battery.powerflow.load_direction == "Using Battery"


def test_normalize_to_fleet_telemetry():
    """Verify normalization of SEMS detail into unified Solar Fleet EMS schema."""
    raw_payload = {
        "info": {
            "powerstation_id": "st_vn_02",
            "stationname": "Da Nang Warehouse",
            "time": "2026-09-27T10:00:00Z",
        },
        "kpi": {
            "power": "28.4",
            "total_power": "9800.0",
            "pac": "6500",
        },
        "powerflow": {
            "pv": "7000(W)",
            "load": "2500(W)",
            "loadStatus": 1,
            "bettery": "3000(W)",
            "grid": "1500(W)",
        },
        "soc": {"power": "78.0"},
        "inverter": [
            {
                "sn": "GW10K-002",
                "tempperature": "39.0",
                "invert_full": {"vac1": 229.5, "fac1": 50.0, "pac": 6500},
            }
        ],
    }

    detail = GoodWeSEMSClient.parse_station_detail(raw_payload, system_id="st_vn_02")
    norm = GoodWeSEMSClient.normalize_to_fleet_telemetry(detail)

    assert norm["station_id"] == "st_vn_02"
    assert norm["pv_power_kw"] == 7.0
    assert norm["active_power_kw"] == 6.5
    assert norm["load_power_kw"] == 2.5
    assert norm["battery_power_kw"] == 3.0
    assert norm["grid_power_kw"] == 1.5
    assert norm["load_direction"] == "Using Battery"
    assert norm["soc_pct"] == 78.0
    assert norm["daily_generation_kwh"] == 28.4
    assert norm["total_generation_kwh"] == 9800.0
    assert norm["grid_voltage_v"] == 229.5
    assert norm["inverter_temperature_c"] == 39.0


def test_parse_monthly_report():
    """Verify parsing of monthly power generation report."""
    raw_report = {
        "record": 2,
        "list": [
            {
                "pw_id": "st_01",
                "pw_name": "Plant 1",
                "capacity": 10.0,
                "month_power": 850.5,
                "avg_day_power": 31.5,
                "total_power": 12500.0,
            },
            {
                "pw_id": "st_02",
                "pw_name": "Plant 2",
                "capacity": 25.0,
                "month_power": 2100.0,
                "avg_day_power": 77.8,
                "total_power": 38400.0,
            },
        ],
    }

    parsed = GoodWeSEMSClient.parse_monthly_report(raw_report)
    assert parsed["total_records"] == 2
    assert len(parsed["stations"]) == 2
    assert parsed["stations"][0]["month_generation_kwh"] == 850.5
    assert parsed["stations"][1]["avg_daily_generation_kwh"] == 77.8


# ---------------------------------------------------------------------------
# Integration Tests: REST API Endpoints
# ---------------------------------------------------------------------------

def test_api_goodwe_sems_routes(local):
    """Test REST API endpoints under /api/goodwe-sems."""
    client, _ctl = local
    headers = login(local, "operator")

    # 1. Login endpoint
    res_login = client.post(
        "/api/goodwe-sems/login",
        json={"account": "demo@example.com", "password": "secret_password"},
        headers=headers,
    )
    assert res_login.status_code == 409
    assert "authenticated" not in res_login.json()
    assert "token" not in res_login.json()

    # 2. Station detail endpoint
    res_station = client.post(
        "/api/goodwe-sems/station-detail",
        json={"station_id": "test_gw_st_01"},
        headers=headers,
    )
    assert res_station.status_code == 422
    assert "provider_payload_required" in res_station.json()["detail"]

    # 3. Monthly report endpoint
    res_rep = client.post(
        "/api/goodwe-sems/monthly-report",
        json={"station_id": "test_gw_st_01", "year_month": "2026-09"},
        headers=headers,
    )
    assert res_rep.status_code == 422
    assert "provider_payload_required" in res_rep.json()["detail"]
