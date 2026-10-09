"""Synthetic application configuration; vendor authentication responses are intercepted.

No vendor traffic, real account, device discovery or hardware commands.
"""

from conftest import login
from playwright.sync_api import expect


def open_connection(page, origin):
    page.goto(origin + "/#settings/main/connections")
    page.get_by_role("button", name="+ Add vendor account", exact=True).click()
    page.get_by_role("dialog").get_by_role("button").filter(
        has=page.locator(".vendor-wordmark", has_text="Deye")
    ).click()
    return page.get_by_role("dialog")


def configure(page, dialog):
    dialog.get_by_role("button", name="Application setup · administrator", exact=True).click()
    dialog.get_by_label("App ID", exact=True).fill("SYNTHETIC-APP-ID")
    dialog.get_by_label("App Secret", exact=True).fill("SYNTHETIC-APP-SECRET")
    dialog.get_by_role("checkbox").check()
    dialog.get_by_role("button", name="Save application configuration", exact=True).click()
    expect(dialog).to_contain_text("Configured · individual account access has not been verified.")
    expect(dialog.get_by_label("App ID", exact=True)).to_have_value("")
    expect(dialog.get_by_label("App Secret", exact=True)).to_have_value("")


def test_application_setup_region_and_disable_are_real_fixture_mutations(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    dialog = open_connection(page, origin)
    configure(page, dialog)
    for width in (1600, 1024, 430):
        page.set_viewport_size({"width": width, "height": 1000})
        expect(dialog.get_by_label("App Secret", exact=True)).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        box = dialog.bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= width + 1
    dialog.get_by_label("Application region", exact=True).select_option("am")
    expect(dialog).to_contain_text("User connections are not enabled")
    dialog.get_by_label("Application region", exact=True).select_option("eu")
    dialog.get_by_role("checkbox").check()
    dialog.get_by_role("button", name="Disable application in this region", exact=True).click()
    expect(dialog).to_contain_text("User connections are not enabled")
    dialog.get_by_role("button", name="Back to account connection", exact=True).click()
    dialog.get_by_label("Account region", exact=True).select_option("eu")
    expect(dialog.locator("input")).to_have_count(0)


def test_account_table_remains_readable_and_scrolls_inside_mobile_card(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.set_viewport_size({"width": 430, "height": 932})
    page.goto(origin + "/#settings/main/connections")
    table = page.locator('[data-view="vendor-accounts"] table')
    expect(table).to_be_visible()
    assert table.bounding_box()["width"] >= 900
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    scroller = table.locator("..")
    assert scroller.evaluate("el => el.scrollWidth > el.clientWidth")
    scroller.evaluate("el => el.scrollLeft = el.scrollWidth")
    expect(table.get_by_role("button").first).to_be_in_viewport()


def test_email_password_only_auth_failure_then_success_without_fake_inventory(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    dialog = open_connection(page, origin)
    configure(page, dialog)
    dialog.get_by_role("button", name="Back to account connection", exact=True).click()
    expect(dialog.get_by_label("Account region", exact=True)).to_have_value("eu")
    expect(dialog.locator("input")).to_have_count(2)
    expect(dialog.locator('input[type="password"]')).to_have_count(1)
    expect(dialog).not_to_contain_text("App Secret")
    requests = []

    def authenticate(route):
        requests.append(route.request.post_data_json)
        if len(requests) == 1:
            route.fulfill(status=400, json={"detail": "deye_authentication_failed"})
        else:
            route.fulfill(
                status=201,
                json={
                    "id": "SYNTHETIC-ONLY",
                    "state": "AUTHENTICATED",
                    "inventory_synced": False,
                    "write_enabled": False,
                },
            )

    page.route("**/api/connections/deye", authenticate)
    dialog.get_by_label("Deye email", exact=True).fill("synthetic@example.invalid")
    dialog.get_by_label("Deye password", exact=True).fill("SYNTHETIC-PASSWORD")
    dialog.get_by_role("button", name="Authenticate & link", exact=True).click()
    expect(dialog.get_by_label("Deye password", exact=True)).to_have_value("")
    expect(dialog.get_by_label("Deye email", exact=True)).to_have_value("synthetic@example.invalid")
    expect(dialog.get_by_role("button", name="Authenticate & link", exact=True)).to_be_enabled()
    assert set(requests[0]) == {"region", "application_revision", "email", "password", "integration_id"}
    assert requests[0]["region"] == "eu"
    dialog.get_by_label("Deye password", exact=True).fill("SYNTHETIC-PASSWORD")
    dialog.get_by_role("button", name="Authenticate & link", exact=True).click()
    expect(dialog).not_to_be_visible()
    expect(page.locator("body")).to_contain_text(
        "Inventory has not been synchronized; control is not enabled."
    )
    assert len(requests) == 2
