"""New vendor workspaces must not turn simulator results into live evidence."""

import pytest
from test_workspaces import local as local
from test_workspaces import login


@pytest.mark.parametrize("path", [
    "growatt-cloud/plants", "growatt-cloud/devices", "growatt-cloud/sph-detail",
    "goodwe-local/telemetry", "huawei-sun2000/telemetry",
    "solarman-profile/telemetry", "sungrow-shx/telemetry", "deye-mqtt/telemetry",
])
def test_unwired_vendor_reads_do_not_return_simulated_telemetry(local, path):
    client, controller = local
    headers = login(local)
    response = client.post("/api/" + path, headers=headers, json={})
    assert response.status_code == 503
    assert "LIVE_TRANSPORT_UNAVAILABLE" in response.json()["detail"]
    assert not controller.store.commands()


@pytest.mark.parametrize("vendor", [
    "growatt-cloud", "eybond-collector", "goodwe-local", "huawei-sun2000",
    "solarman-profile", "sungrow-shx", "deye-mqtt",
])
@pytest.mark.parametrize("unlocked", [False, True])
def test_request_flag_cannot_commission_vendor_control(local, vendor, unlocked):
    client, controller = local
    headers = login(local)
    response = client.post("/api/" + vendor + "/command", headers=headers, json={
        "command_type": "workmode", "parameter_name": "workmode",
        "value": 0, "unlocked": unlocked,
    })
    assert response.status_code == 409
    assert "UNCOMMISSIONED_CONTROL" in response.json()["detail"]
    assert not controller.store.commands()