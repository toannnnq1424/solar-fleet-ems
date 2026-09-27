"""Plant metadata contracts against an isolated local server; no hardware writes."""

import pytest
from conftest import login
from playwright.sync_api import expect


@pytest.mark.parametrize("coordinates,capacity", [(None, None), (("0", "0"), "0"), (("10.5", "106.5"), "0.5")])
def test_wizard_preserves_missing_and_explicit_zero_metadata(browser_page, coordinates, capacity):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#plants/main")
    page.get_by_role("button", name="+ Add Plant Wizard", exact=True).click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Plant name", exact=True).fill("SIMULATOR metadata contract")
    dialog.get_by_role("button", name="Next →", exact=True).click()
    if coordinates:
        dialog.get_by_label("Latitude", exact=True).fill(coordinates[0])
        dialog.get_by_label("Longitude", exact=True).fill(coordinates[1])
    dialog.get_by_role("button", name="Next →", exact=True).click()
    if capacity is not None:
        dialog.get_by_label("PV Capacity (kWp)", exact=True).fill(capacity)
        dialog.get_by_label("Battery Capacity (kWh)", exact=True).fill("12.5")
        dialog.get_by_label("Declared export limit (kW)", exact=True).fill("0")
        dialog.get_by_label("Primary Inverter Vendor", exact=True).select_option("Solis")
        dialog.get_by_label("Declared tariff type", exact=True).select_option("FLAT_RATE")
    dialog.get_by_role("button", name="Next →", exact=True).click()
    expect(dialog).not_to_contain_text("null")
    with page.expect_response(lambda r: r.url.endswith("/api/sites") and r.request.method == "POST") as saved:
        dialog.get_by_role("button", name="Finish & Create", exact=True).click()
    assert saved.value.status == 201
    record = saved.value.json()
    assert record["latitude"] == (float(coordinates[0]) if coordinates else None)
    assert record["longitude"] == (float(coordinates[1]) if coordinates else None)
    assert record["capacity_kwp"] == (float(capacity) if capacity is not None else None)
    assert record["declared_specs"]["battery_capacity_kwh"] == (12.5 if capacity is not None else None)
    assert record["declared_specs"]["grid_limit_kw"] == (0 if capacity is not None else None)
    assert record["declared_specs"]["inverter_vendor"] == ("Solis" if capacity is not None else None)
    assert record["declared_specs"]["tariff_type"] == ("FLAT_RATE" if capacity is not None else None)
    fleet = page.request.get(origin + "/api/fleet").json()
    persisted = next(s for s in fleet["sites"] if s["id"] == record["id"])
    assert persisted["latitude"] == record["latitude"]
    assert persisted["capacity_kwp"] == record["capacity_kwp"]
    assert persisted["declared_specs"] == record["declared_specs"]


def test_benchmark_unknown_is_not_a_health_judgement_and_opens_correct_site(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#plants/main")
    page.get_by_role("button", name="Benchmarking", exact=True).click()
    expect(page.get_by_text("Plant Data Comparison", exact=True)).to_be_visible()
    content = page.locator("#content")
    expect(content).not_to_contain_text("null")
    expect(content).not_to_contain_text("undefined")
    expect(content).not_to_contain_text("Inspect")
    expect(content).not_to_contain_text("#1")
    expect(content).to_contain_text("Irradiance reference required")
    page.get_by_role("button", name="SIMULATOR plant 1", exact=True).click()
    expect(page.get_by_label("Plant scope", exact=True)).to_have_value("SIM-SITE-0")


def test_benchmark_bars_stay_inside_chart(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.route("**/api/fleet/plants-benchmarking", lambda route: route.fulfill(json={
        "plants": [{"name": "SIMULATOR high yield", "specific_yield_kwh_per_kwp": 12.5, "status": "UNKNOWN"}],
    }))
    page.goto(origin + "/#plants/main")
    page.get_by_role("button", name="Benchmarking", exact=True).click()
    chart = page.locator(".benchmarking-chart-svg")
    expect(chart).to_be_visible()
    bars = chart.locator("rect")
    expect(bars).to_have_count(1)
    assert float(bars.first.get_attribute("y")) >= 20
    assert float(bars.first.get_attribute("height")) <= 160