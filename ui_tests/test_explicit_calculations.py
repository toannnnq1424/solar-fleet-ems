import json
from datetime import datetime, timedelta, timezone

from conftest import login
from playwright.sync_api import expect


def test_heat_pump_uses_blank_inputs_and_actual_response(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#operations/main/rules")
    data = page.get_by_label("Heat pump estimate JSON", exact=True)
    expect(data).to_have_value("")
    data.fill(json.dumps({"ambient_temp_c": 7, "supply_temp_c": 35, "required_thermal_kw": 6,
                          "carnot_efficiency": 0.5, "min_electric_kw": 0.5, "max_electric_kw": 3.5}))
    panel = data.locator("..")
    with page.expect_response(lambda r: r.url.endswith("/api/thermal/heat-pump-cop")) as response:
        panel.get_by_role("button", name="Calculate supplied inputs", exact=True).click()
    assert response.value.status == 200
    assert response.value.json()["dispatch_enabled"] is False
    expect(panel).to_contain_text('"status": "ESTIMATED"')


def test_phase_calculator_requires_explicit_measurements(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#operations/main/rules")
    phase = page.get_by_label("Phase measurements and equipment limits JSON", exact=True)
    expect(phase).to_have_value("")
    phase.fill(json.dumps({
        "measurement": {"v_l1": 230, "v_l2": 230, "v_l3": 230,
                        "i_l1": 10, "i_l2": 10, "i_l3": 10,
                        "p_l1": 2, "p_l2": 2, "p_l3": 2,
                        "q_l1": 0, "q_l2": 0, "q_l3": 0},
        "limits": {"max_total_kw": 3, "max_phase_kw": 4, "max_phase_kvar": 2,
                   "battery_max_charge_kw": 10, "battery_max_discharge_kw": 10,
                   "allows_independent_phases": True},
    }))
    with page.expect_response(lambda r: r.url.endswith("/api/phase-balancer/dispatch")) as response:
        page.get_by_role("button", name="Analyze 3-Phase Unbalance & Dispatch", exact=True).click()
    assert response.value.status == 200
    assert response.value.json()["dispatch_setpoints"]["total_p_kw"] == 3
    expect(page.locator("#content")).to_contain_text("Estimated neutral current")
    expect(page.locator("#content")).to_contain_text("Not a compliance assessment")
    assert "undefined" not in page.locator("#content").inner_text()


def test_ev_and_market_use_explicit_inputs_and_real_api(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#operations/main/rules")
    charger_field = page.get_by_label("Actual charger list (JSON)", exact=True)
    expect(charger_field).to_have_value("")
    page.get_by_label("Main Breaker Limit (kW)", exact=True).fill("10")
    page.get_by_label("Solar Surplus Available (kW)", exact=True).fill("2")
    page.get_by_label("Base Building Load (kW)", exact=True).fill("1")
    charger_field.fill(json.dumps([{
        "id": "test-port", "name": "Browser fixture only", "vehicle_id": "test-car",
        "soc_pct": 20, "target_soc_pct": 70, "mode": "pv", "priority": 1,
        "min_current_amps": 6, "max_current_amps": 16, "voltage_per_phase_v": 220, "phases": 1,
    }]))
    with page.expect_response(lambda r: r.url.endswith("/api/ev-fleet/optimize-dlm")) as response:
        page.get_by_role("button", name="Optimize Dynamic EV Fleet DLM", exact=True).click()
    assert response.value.status == 200
    assert response.value.json()["dispatch_enabled"] is False
    expect(page.locator("#content")).to_contain_text("1.98")
    expect(page.locator("#content")).to_contain_text("Proposed charging")
    expect(page.locator("#content")).to_contain_text("Freshness unknown")
    expect(page.locator("#content")).to_contain_text("test-car")
    observed_at = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
    page.get_by_label("Site observation time (ISO 8601 with timezone)", exact=True).fill(observed_at)
    chargers = json.loads(charger_field.input_value())
    chargers[0]["observed_at"] = observed_at
    charger_field.fill(json.dumps(chargers))
    with page.expect_response(lambda r: r.url.endswith("/api/ev-fleet/optimize-dlm")) as recent:
        page.get_by_role("button", name="Optimize Dynamic EV Fleet DLM", exact=True).click()
    assert recent.value.status == 200
    assert recent.value.json()["freshness"]["telemetry_verified"] is False
    expect(page.locator("#content")).to_contain_text("telemetry remains unverified")
    expect(page.get_by_role("button", name="Optimize Dynamic EV Fleet DLM", exact=True)).to_be_enabled()
    assert "undefined" not in page.locator("#content").inner_text()

    page.goto(origin + "/#reports/analytics")
    market_field = page.get_by_label("Market inputs (JSON)", exact=True)
    expect(market_field).to_have_value("")
    market_field.fill(json.dumps({
        "fleet_capacity_mw": 2, "clearing_prices": {"12": 60},
        "bids": [{"id": "test-bid", "market": "day_ahead", "direction": "sell_discharge",
                  "delivery_hour": 12, "quantity_mw": 1, "price_eur_per_mwh": 40}],
    }))
    with page.expect_response(lambda r: r.url.endswith("/api/market-trader/submit-and-clear")) as response:
        page.get_by_role("button", name="Calculate supplied market scenario", exact=True).click()
    assert response.value.status == 200
    assert response.value.json()["submitted_to_market"] is False
    expect(page.locator("#content")).to_contain_text("Estimated net value (EUR)")
    assert "undefined" not in page.locator("#content").inner_text()