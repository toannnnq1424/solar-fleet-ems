from playwright.sync_api import expect
from test_planning_editor import open_editor


def fill_rate(page):
    page.get_by_label("Effective start (ISO)", exact=True).fill("2026-09-28T00:00:00+00:00")
    page.get_by_label("Effective end (ISO)", exact=True).fill("2026-09-29T00:00:00+00:00")
    page.get_by_label("Import rate (VND/kWh)", exact=True).fill("2000")
    page.get_by_label("Import rate source", exact=True).fill("SYNTHETIC browser contract")


def test_rate_save_reload(browser_page):
    page = open_editor(browser_page)
    fill_rate(page)
    page.get_by_role("button", name="Add import rate version", exact=True).click()
    expect(page.get_by_role("log", name="Import tariff status")).to_contain_text("Declared rate saved")
    page.reload()
    expect(page.get_by_role("cell", name="SYNTHETIC browser contract", exact=True)).to_be_visible()


def test_rate_conflict_preserves_inputs(browser_page):
    page = open_editor(browser_page)
    fill_rate(page)
    page.route("**/api/sites/*/import-tariffs", lambda route: route.fulfill(status=409, json={"detail": "stale"}))
    button = page.get_by_role("button", name="Add import rate version", exact=True)
    button.click()
    expect(page.get_by_role("log", name="Import tariff status")).to_contain_text("Inputs preserved")
    expect(button).to_be_disabled()
    expect(page.get_by_label("Import rate (VND/kWh)", exact=True)).to_have_value("2000")