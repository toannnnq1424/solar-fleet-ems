from conftest import login
from playwright.sync_api import expect


def test_import_snapshot_export_and_missing_meter_feedback(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#reports/analytics")
    choice = page.get_by_label("Include import estimate snapshot", exact=True)
    expect(choice).to_have_value("no")
    page.get_by_label("Period", exact=True).select_option("day")
    choice = page.get_by_label("Include import estimate snapshot", exact=True)
    choice.select_option("yes")
    with page.expect_response("**/api/reports/generate") as response:
        page.get_by_role("button", name="Generate report", exact=True).click()
    assert response.value.status == 422
    assert response.value.request.post_data_json["include_import_estimate"] is True
    expect(page.get_by_role("button", name="Generate report", exact=True)).to_be_enabled()
    choice.select_option("no")
    with page.expect_download(), page.expect_response("**/api/reports/generate") as response:
        page.get_by_role("button", name="Generate report", exact=True).click()
    assert response.value.status == 201
    expect(page.get_by_text("Report saved and downloaded.", exact=True)).to_be_visible()