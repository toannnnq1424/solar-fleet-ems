"""EMS observation presentation; responses below are explicit browser fixtures."""

import pytest
from conftest import login
from playwright.sync_api import expect


@pytest.mark.parametrize("language,status", [
    ("en", "PARTIAL_OBSERVATIONS"), ("vi", "INSUFFICIENT_DATA"),
])
def test_import_observations_are_localized_and_not_bills(browser_page, language, status):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.route("**/api/sites/*/tariff-analysis", lambda route: route.fulfill(json={
        "status": status, "observed_import_kwh": 1.25 if language == "en" else None,
        "coverage": 0.1 if language == "en" else 0,
        "total_active_bill_vnd": None, "reason": "RAW_BACKEND_REASON_NOT_FOR_DISPLAY",
    }))
    page.goto(origin + "/#operations/main/rules")
    page.get_by_label("Language / Ngôn ngữ").select_option(language)
    page.get_by_label("Plant scope" if language == "en" else "Phạm vi nhà máy", exact=True).select_option("SIM-SITE-0")
    button = page.get_by_role("button", name="Read import energy and coverage" if language == "en"
                              else "Đọc điện nhập và độ phủ dữ liệu", exact=True)
    button.click()
    expect(page.locator("#content")).to_contain_text(
        "Partial observations" if language == "en" else "Chưa đủ dữ liệu")
    expect(page.locator("#content")).not_to_contain_text("RAW_BACKEND_REASON_NOT_FOR_DISPLAY")
    expect(page.locator("#content")).not_to_contain_text(status)
    expect(button).to_be_enabled()
    bill = page.get_by_role("row").filter(has=page.get_by_role(
        "cell", name="Bill" if language == "en" else "Tiền điện", exact=True))
    expect(bill).to_contain_text("—")