
from conftest import login
from playwright.sync_api import expect


def fill_fields(scope, values, prefix=""):
    for key, value in values.items():
        path = prefix + key
        if isinstance(value, dict):
            fill_fields(scope, value, path + ".")
        else:
            control = scope.locator('[data-input-path="' + path + '"]')
            if control.evaluate("el => el.tagName") == "SELECT":
                control.select_option(str(value).lower())
            else:
                control.fill(str(value))


def test_heat_pump_uses_blank_inputs_and_actual_response(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#operations/main/rules")
    page.locator(".engineering-tools > summary").click()
    panel = page.locator('[data-calculator="/thermal/heat-pump-cop"]')
    expect(panel.locator('textarea')).to_have_count(0)
    expect(panel.get_by_label('Ambient temperature (°C)', exact=True)).to_have_value("")
    fill_fields(panel, {"ambient_temp_c": 7, "supply_temp_c": 35, "required_thermal_kw": 6,
                        "carnot_efficiency": 50, "min_electric_kw": 0.5, "max_electric_kw": 3.5})
    with page.expect_response(lambda r: r.url.endswith("/api/thermal/heat-pump-cop")) as response:
        panel.get_by_role("button", name="Calculate supplied inputs", exact=True).click()
    assert response.value.status == 200
    assert response.value.json()["dispatch_enabled"] is False
    expect(panel).to_contain_text('"status": "ESTIMATED"')
    assert response.value.request.post_data_json["carnot_efficiency"] == 0.5


def test_phase_calculator_requires_explicit_measurements(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#operations/main/rules")
    phase = page.locator('[data-input-path="measurement.v_l1"]')
    page.locator(".engineering-tools > summary").click()
    expect(phase).to_have_value("")
    fill_fields(page, {
        "measurement": {"v_l1": 230, "v_l2": 230, "v_l3": 230,
                        "i_l1": 10, "i_l2": 10, "i_l3": 10,
                        "p_l1": 2, "p_l2": 2, "p_l3": 2,
                        "q_l1": 0, "q_l2": 0, "q_l3": 0},
        "limits": {"max_total_kw": 3, "max_phase_kw": 4, "max_phase_kvar": 2,
                   "battery_max_charge_kw": 10, "battery_max_discharge_kw": 10,
                   "allows_independent_phases": True},
    })
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
    charger_field = page.locator('[data-input-path="site_breaker_limit_kw"]')
    page.locator(".engineering-tools > summary").click()
    expect(charger_field).to_have_value("")
    page.get_by_label("Main Breaker Limit (kW)", exact=True).fill("10")
    page.get_by_label("Solar Surplus Available (kW)", exact=True).fill("2")
    page.get_by_label("Base Building Load (kW)", exact=True).fill("1")
    page.get_by_role("button", name="Add entry", exact=True).click()
    fill_fields(page, {
        "id": "test-port", "name": "Browser fixture only", "vehicle_id": "test-car",
        "soc_pct": 20, "target_soc_pct": 70, "mode": "pv", "priority": 1,
        "min_current_amps": 6, "max_current_amps": 16, "voltage_per_phase_v": 220, "phases": 1,
    }, "chargers.")
    with page.expect_response(lambda r: r.url.endswith("/api/ev-fleet/optimize-dlm")) as response:
        page.get_by_role("button", name="Optimize Dynamic EV Fleet DLM", exact=True).click()
    assert response.value.status == 200
    assert response.value.json()["dispatch_enabled"] is False
    expect(page.locator("#content")).to_contain_text("1.98")
    expect(page.locator("#content")).to_contain_text("Proposed charging")
    expect(page.locator("#content")).to_contain_text("Freshness unknown")
    expect(page.locator("#content")).to_contain_text("test-car")
    # datetime-local canonicalizes :00 seconds away; Playwright checks the exact value.
    observed_at = page.evaluate("new Date(Date.now()-5000-new Date().getTimezoneOffset()*60000).toISOString().slice(0,19).replace(/:00$/, '')")
    page.get_by_label("Site observation time", exact=True).fill(observed_at)
    page.get_by_label("Charger observation time", exact=True).fill(observed_at)
    with page.expect_response(lambda r: r.url.endswith("/api/ev-fleet/optimize-dlm")) as recent:
        page.get_by_role("button", name="Optimize Dynamic EV Fleet DLM", exact=True).click()
    assert recent.value.status == 200
    assert recent.value.json()["freshness"]["telemetry_verified"] is False
    expect(page.locator("#content")).to_contain_text("telemetry remains unverified")
    expect(page.get_by_role("button", name="Optimize Dynamic EV Fleet DLM", exact=True)).to_be_enabled()
    assert "undefined" not in page.locator("#content").inner_text()

    page.goto(origin + "/#reports/analytics")
    page.get_by_text("Engineering tools · market scenarios", exact=True).click()
    expect(page.locator('.market-scenario-editor textarea')).to_have_count(0)
    capacity=page.get_by_label('Available capacity (MW)',exact=True)
    expect(capacity).to_have_value('')
    capacity.fill('2')
    page.get_by_role('button',name='Add scenario',exact=True).click()
    page.get_by_label('Scenario name',exact=True).fill('test-bid')
    page.get_by_label('Market',exact=True).select_option('day_ahead')
    page.get_by_label('Direction',exact=True).select_option('sell_discharge')
    page.get_by_label('Delivery hour',exact=True).select_option('12')
    page.get_by_label('Quantity (MW)',exact=True).fill('1')
    page.get_by_label('Bid price (EUR/MWh)',exact=True).fill('40')
    page.get_by_label('Assumed market price (EUR/MWh)',exact=True).fill('60')
    with page.expect_response(lambda r: r.url.endswith("/api/market-trader/submit-and-clear")) as response:
        page.get_by_role("button", name="Calculate supplied market scenario", exact=True).click()
    assert response.value.status == 200
    assert response.value.json()["submitted_to_market"] is False
    expect(page.locator("#content")).to_contain_text("Estimated net value (EUR)")
    assert "undefined" not in page.locator("#content").inner_text()
