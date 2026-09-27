"""Action contracts for equipment and reports, using only the isolated simulator."""

from conftest import login
from playwright.sync_api import expect


def test_device_scope_firmware_contract_and_maintenance_navigation(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#devices/main")
    page.get_by_label("Plant scope", exact=True).select_option("SIM-SITE-0")
    expect(page.locator("#content")).to_contain_text("SIMULATOR Deye")
    expect(page.locator("#content")).not_to_contain_text("SIMULATOR Solis")
    page.get_by_role("button", name="Firmware Compliance & OTA", exact=True).click()
    expect(page.locator("#content")).to_contain_text("SIMULATOR Deye")
    expect(page.locator("#content")).to_contain_text("TEST")
    expect(page.get_by_role("button", name="Open maintenance records", exact=True)).to_have_count(1)
    page.get_by_role("button", name="Open maintenance records", exact=True).click()
    expect(page).to_have_url(origin + "/#incidents/health")
    expect(page.get_by_label("Plant scope", exact=True)).to_have_value("SIM-SITE-0")
    expect(page.get_by_role("heading", name="Connectivity, measurements and work", exact=True)).to_be_visible()
    expect(page.locator("#content .progress-loading")).to_have_count(0)
    kpis = page.locator(".maintenance-kpi-grid")
    expect(kpis).not_to_contain_text("Up to date")
    expect(kpis).to_contain_text("No enabled plans")
    expect(kpis.locator(".card").first).to_have_css("background-color", "rgb(255, 255, 255)")


def test_firmware_error_is_not_an_empty_success(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.route("**/api/fleet/firmware-matrix", lambda r: r.fulfill(status=503, json={"detail": "unavailable"}))
    page.goto(origin + "/#devices/main")
    page.get_by_role("button", name="Firmware Compliance & OTA", exact=True).click()
    expect(page.get_by_text("Could not load this page", exact=True)).to_be_visible()
    page.unroute("**/api/fleet/firmware-matrix")
    page.get_by_role("button", name="Try again", exact=True).click()
    expect(page.get_by_role("button", name="Open maintenance records", exact=True)).to_have_count(3)


def test_report_viewer_has_no_generate_action(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-viewer")
    page.goto(origin + "/#reports/analytics")
    expect(page.get_by_text("Report archive", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Generate report", exact=True)).to_have_count(0)


def test_incident_filter_labels_are_not_plant_scope(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#incidents/main")
    expect(page.get_by_label("Severity", exact=True).locator("option:checked")).to_have_text("All severities")
    expect(page.get_by_label("Status", exact=True).locator("option:checked")).to_have_text("All statuses")