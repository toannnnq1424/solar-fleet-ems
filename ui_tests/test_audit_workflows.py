"""Real local HTTP UI audit; isolated fixture, no vendor or customer traffic."""

from pathlib import Path

from conftest import login
from playwright.sync_api import expect

ROOT = Path(__file__).resolve().parents[1]


def ready(page):
    expect(page.locator("#content .progress-loading")).to_have_count(0)
    expect(page.get_by_text("Could not load this page", exact=True)).to_have_count(0)
    expect(page.get_by_role("navigation", name="Main navigation")).to_have_count(1)
    expect(page.locator('link[rel="stylesheet"]')).to_have_count(1)
    expect(page.locator("style")).to_have_count(0)


def test_all_sidebar_routes_and_site_tabs_use_real_local_services(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    routes = [
        "overview/main",
        "plants/main",
        "topology/main",
        "plants/map",
        "devices/main",
        "operations/main/control",
        "operations/main/schedules",
        "operations/main/rules",
        "reports/main",
        "incidents/main",
        "reports/analytics",
        "incidents/health",
        "operations/main/journal",
        "settings/main/users",
        "settings/main/connections",
        "reports/collection",
        "reports/mapping",
        "reports/sync",
        "settings/main/site_config",
        "settings/main/device_onboarding",
        "settings/main/security",
    ]
    artifact_dir = ROOT / "work" / "qa-audit"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    for route in routes:
        page.goto(origin + "/#" + route)
        ready(page)
        assert "undefined" not in page.locator("#content").inner_text(), route
        if route in {"settings/main/connections", "operations/main/schedules", "reports/main"}:
            page.screenshot(path=str(artifact_dir / (route.replace("/", "-") + ".png")), full_page=True)
    page.get_by_label("Plant scope", exact=True).select_option("SIM-SITE-0")
    for tab in [
        "overview",
        "data",
        "devices",
        "control",
        "schedules",
        "incidents",
        "journal",
        "diagnostics",
        "reports",
        "network",
    ]:
        page.goto(origin + "/#overview/main/" + tab)
        ready(page)
        assert "undefined" not in page.locator("#content").inner_text(), tab
        if tab == "overview":
            page.screenshot(path=str(artifact_dir / "site-overview.png"), full_page=True)
    page.get_by_label("Language / Ngôn ngữ").select_option("vi")
    page.goto(origin + "/#settings/main/connections")
    expect(page.locator("#content .progress-loading")).to_have_count(0)
    expect(page.get_by_role("navigation", name="Điều hướng chính")).to_have_count(1)
    expect(page.get_by_text("Chưa tải được trang", exact=True)).to_have_count(0)
    page.screenshot(path=str(artifact_dir / "accounts-vi.png"), full_page=True)


def test_collection_editor_updates_correct_integration_and_preserves_revision(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#reports/collection")
    ready(page)
    page.get_by_role("button", name="Edit", exact=True).first.click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Interval (seconds)", exact=True).fill("240")
    dialog.get_by_label("Devices per poll", exact=True).fill("3")
    with page.expect_response(
        lambda r: "/api/collection/" in r.url and r.request.method == "POST"
    ) as updated:
        dialog.get_by_role("button", name="Save", exact=True).click()
    assert updated.value.status == 200
    assert updated.value.json()["revision"] == 1
    expect(dialog).not_to_be_visible()
    expect(page.locator("#content")).to_contain_text("240")


def test_failed_reads_do_not_render_fabricated_healthy_equipment(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.route(
        "**/api/fleet/devices-overview",
        lambda r: r.fulfill(status=503, json={"detail": "fixture_unavailable"}),
    )
    page.goto(origin + "/#devices/main")
    expect(page.get_by_text("Could not load this page", exact=True)).to_be_visible()
    expect(page.locator("#content")).not_to_contain_text("99.85")
    expect(page.locator("#content")).not_to_contain_text("IEC 62109")


def test_bluesun_smartess_account_form_preserves_platform_and_brand(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#settings/main/connections")
    ready(page)
    page.get_by_role("button", name="+ Add vendor account", exact=True).click()
    page.get_by_role("dialog").get_by_role("button", name="Bluesun", exact=False).click()
    page.get_by_role("button", name="Connect SmartESS / Eybond", exact=True).click()
    dialog = page.get_by_role("dialog")
    expect(dialog.get_by_label("Platform company key")).to_have_attribute("type", "password")
    dialog.get_by_label("Account platform", exact=True).select_option("shinemonitor")
    dialog.get_by_label("Vendor username", exact=True).fill("SIMULATOR-smartess@example.invalid")
    dialog.get_by_label("Password", exact=True).fill("SIMULATOR-vendor-password")
    dialog.get_by_label("Platform company key", exact=True).fill("SIMULATOR-company-key")
    with page.expect_response(
        lambda r: r.url.endswith("/api/integrations") and r.request.method == "POST"
    ) as created:
        dialog.get_by_role("button", name="Save connection", exact=True).click()
    assert created.value.status == 201
    body = created.value.request.post_data_json
    assert body["equipment_brand"] == "Bluesun"
    assert body["vendor"] == "Eybond / SmartESS"
    assert body["region"] == "shinemonitor"
    expect(dialog).not_to_be_visible()
    expect(page.locator("#content")).to_contain_text("SIMULATOR-smartess@example.invalid")
    assert "SIMULATOR-vendor-password" not in page.content()
    assert "SIMULATOR-company-key" not in page.content()
    page.goto(origin + "/#reports/collection")
    ready(page)
    row = page.get_by_role("row").filter(has_text="Bluesun · Eybond / SmartESS Cloud")
    row.get_by_role("button", name="Edit", exact=True).click()
    expect(page.get_by_role("dialog").get_by_label("Interval (seconds)")).to_have_attribute("min", "300")
    expect(page.get_by_role("dialog").get_by_label("Interval (seconds)")).to_have_value("300")


def test_device_native_values_readable_without_invented_temperature(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#devices/main")
    ready(page)
    expect(page.locator("#content")).not_to_contain_text("38 °C")
    page.get_by_role("button", name="Detail & native readings", exact=True).first.click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_contain_text("Vendor native readings")
    expect(dialog).to_contain_text("SIMULATOR operating state")
    expect(dialog).to_contain_text("Charging")
    expect(dialog).to_contain_text("1.234")
    expect(dialog).to_contain_text("Receipt time does not replace")
