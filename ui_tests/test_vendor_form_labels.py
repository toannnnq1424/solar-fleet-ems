"""Vendor forms use local fixtures only; never authenticate with a vendor."""

import pytest
from conftest import login
from playwright.sync_api import expect

from solar_fleet.providers import PROVIDERS


@pytest.mark.parametrize("language", ["vi", "en"])
def test_all_read_connector_forms_have_localized_labels_and_mask_secrets(browser_page, language):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#settings/main/connections")
    page.get_by_label("Language / Ngôn ngữ").select_option(language)
    for provider in (item for item in PROVIDERS if item["implemented"]):
        page.get_by_role("button", name="+ Add vendor account" if language == "en"
                         else "+ Thêm tài khoản hãng", exact=True).click()
        page.get_by_role("dialog").get_by_role("button").filter(
            has=page.locator(".vendor-wordmark", has_text=provider["id"])).click()
        dialog = page.get_by_role("dialog")
        expect(dialog).to_contain_text(("Connect " if language == "en" else "Kết nối ") + provider["id"])
        # Name + credentials; exclude optional numeric organization and selects.
        controls = dialog.locator('input[type="text"], input[type="password"]')
        expect(controls).to_have_count(len(provider["fields"]) + 1)
        secrets = set(provider.get("secret_fields", [])) | {
            "key_secret", "app_secret", "password", "token", "system_code", "user_password",
        }
        for index, key in enumerate(provider["fields"], 1):
            control = controls.nth(index)
            label = control.evaluate("el => document.getElementById(el.getAttribute('aria-labelledby'))?.textContent || ''")
            assert label.strip() and label.strip() != key, (provider["id"], language, key, label)
            expect(control).to_have_attribute("type", "password" if key in secrets else "text")
            expect(control).to_have_attribute("required", "")
        if provider["id"] in {"GoodWe", "Sungrow"}:
            expect(dialog).to_contain_text("100")
            expect(dialog).to_contain_text("Solar Fleet")
        if provider["id"] == "Sungrow":
            expect(dialog).to_contain_text("200")
        # Leave without saving any credentials or invoking a remote connection.
        page.keyboard.press("Escape")
        expect(dialog).not_to_be_visible()