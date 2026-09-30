"""Real local API save/reload plus deterministic stale editor conflict."""

from conftest import login
from playwright.sync_api import expect


def open_editor(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#settings/main/site_config")
    expect(page.get_by_role("button", name="Save advisory configuration", exact=True)).to_be_visible()
    return page


def test_planning_boundary_save_reload_without_dispatch(browser_page):
    page = open_editor(browser_page)
    meter = page.get_by_label("Measurement boundary device", exact=True)
    value = meter.locator("option").nth(1).get_attribute("value")
    meter.select_option(value)
    page.get_by_role("button", name="Save advisory configuration", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Advisory configuration saved; no commands sent.")
    page.reload()
    expect(page.get_by_label("Measurement boundary device", exact=True)).to_have_value(value)
    expect(page.get_by_label("Advisory planning device", exact=True)).to_have_value("")


def test_planning_conflict_preserves_inputs_and_disables_retry(browser_page):
    page = open_editor(browser_page)
    page.get_by_label("Capacity (kWh)", exact=True).fill("17")
    page.route("**/api/sites/*/planning-configuration", lambda route: route.fulfill(
        status=409, json={"detail": "planning_configuration_changed_reload_required"}))
    button = page.get_by_role("button", name="Save advisory configuration", exact=True)
    button.click()
    expect(page.get_by_role("status")).to_contain_text("Configuration changed.")
    expect(page.get_by_label("Capacity (kWh)", exact=True)).to_have_value("17")
    expect(button).to_be_disabled()