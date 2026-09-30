"""Synthetic weather awaits must not leak a pre-revocation site overview."""

import pytest
from test_workspaces import login


@pytest.mark.parametrize("path", ["/api/weather/sim-site", "/api/sites/sim-site/overview-summary"])
@pytest.mark.parametrize("change", ["session", "scope", "site", "unchanged"])
def test_weather_read_revalidates_after_transport(local, monkeypatch, path, change):
    client, ctl = local
    login(local, "viewer")
    site = ctl.store.get("site", "sim-site") | {"latitude": 10, "longitude": 106}
    ctl.store.put("site", "sim-site", site)

    async def fetch(*args):
        if change == "session":
            ctl.store.db.execute("DELETE FROM sessions")
        elif change == "scope":
            ctl.store.db.execute("UPDATE users SET sites='[]' WHERE id='viewer'")
        elif change == "site":
            ctl.store.put("site", "sim-site", site | {"latitude": 20})
        return {"current": {}, "hourly_forecast": []}

    monkeypatch.setattr("solar_fleet.weather.fetch_weather", fetch)
    response = client.get(path)
    assert response.status_code == 200 if change == "unchanged" else response.status_code in (401, 403, 409)