"""Author/edit/simulate/review UI against the real isolated backend."""

from conftest import login
from playwright.sync_api import expect
from test_audit_workflows import ready


def create_mapping(page, origin):
    page.goto(origin + "/#reports/mapping")
    ready(page)
    page.get_by_role("button", name="Create mapping", exact=True).click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Mapping name", exact=True).fill("SIMULATOR grid mapping")
    expect(dialog.get_by_label("Data connection", exact=True)).to_have_value("SIM-MAPPING-BIND")
    expect(dialog).to_contain_text("SIMULATOR AC flow")
    dialog.get_by_role("button", name="Add mapping row", exact=True).click()
    dialog.get_by_label("Source field", exact=True).select_option("deye.lab_power\nkW")
    dialog.get_by_label("Target metric", exact=True).select_option("grid_import_w")
    dialog.get_by_label("Measurement direction", exact=True).select_option("positive")
    # A watt source must not offer a voltage metric with the same-looking value.
    expect(
        dialog.get_by_label("Target metric", exact=True).locator('option[value="grid_voltage_v"]')
    ).to_have_count(0)
    dialog.get_by_label("Supporting document", exact=True).select_option("DEYE_API_001")
    dialog.get_by_role("button", name="Add evidence", exact=True).click()
    dialog.get_by_label("Unit and direction notes", exact=True).fill(
        "Synthetic signed flow; positive is import for this fixture only."
    )
    with page.expect_response(
        lambda r: r.url.endswith("/api/mappings") and r.request.method == "POST"
    ) as created:
        dialog.get_by_role("button", name="Save draft", exact=True).click()
    assert created.value.status == 201, created.value.text()
    expect(dialog).not_to_be_visible()
    return created.value.json()


def test_mapping_editor_simulation_revision_review_and_viewer_access(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    row = create_mapping(page, origin)
    expect(page.locator("#content")).to_contain_text("Identity and connection match")
    page.get_by_role("button", name="Simulate", exact=True).click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_contain_text("2,500 W")
    expect(dialog).to_contain_text("Candidate only, not commissioned")
    page.locator("#dialog-close").click()
    page.get_by_role("button", name="Edit", exact=True).click()
    dialog = page.get_by_role("dialog")
    expect(dialog.get_by_label("Devices", exact=True)).to_be_disabled()
    expect(dialog.get_by_label("Source field", exact=True)).to_have_value("deye.lab_power\nkW")
    dialog.get_by_label("Measurement direction", exact=True).select_option("negative")
    with page.expect_response(
        lambda r: r.url.endswith("/api/mappings/" + row["id"]) and r.request.method == "POST"
    ) as updated:
        dialog.get_by_role("button", name="Save draft", exact=True).click()
    assert updated.value.json()["revision"] == 2
    expect(dialog).not_to_be_visible()
    page.get_by_role("button", name="History", exact=True).click()
    expect(page.get_by_role("dialog").get_by_role("row")).to_have_count(3)
    page.locator("#dialog-close").click()
    page.get_by_role("button", name="Sign out", exact=True).click()
    login(page, origin, "ui-review")
    page.goto(origin + "/#reports/mapping")
    ready(page)
    page.get_by_role("button", name="Independent review", exact=True).click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Technical review notes", exact=True).fill(
        "Independent synthetic review of units and measurement direction."
    )
    with page.expect_response(lambda r: r.url.endswith("/review") and "/mappings/" in r.url) as reviewed:
        dialog.get_by_role("button", name="Save review", exact=True).click()
    assert reviewed.value.status == 200
    assert reviewed.value.json()["active"] is False
    expect(dialog).not_to_be_visible()
    expect(page.locator("#content")).to_contain_text("Draft reviewed")
    page.get_by_role("button", name="Sign out", exact=True).click()
    login(page, origin, "ui-viewer")
    page.goto(origin + "/#reports/mapping")
    ready(page)
    expect(page.get_by_role("button", name="Create mapping", exact=True)).to_have_count(0)
    expect(page.get_by_role("button", name="Edit", exact=True)).to_have_count(0)
    expect(page.get_by_role("button", name="Independent review", exact=True)).to_have_count(0)
    page.get_by_role("button", name="Simulate", exact=True).click()
    expect(page.get_by_role("dialog")).to_contain_text("0 W")
    page.locator("#dialog-close").click()
    measurements = page.request.get(origin + "/api/data-workspace").json()
    assert measurements["mappings"][0]["active"] is False
    assert all(d["verified"] == 0 for d in measurements["devices"])
    page.get_by_label("Language / Ngôn ngữ").select_option("vi")
    expect(page.locator("#content")).to_contain_text("Đã duyệt bản nháp")
    expect(page.get_by_role("button", name="Mô phỏng", exact=True)).to_be_visible()


def test_mapping_duplicate_output_validation_preserves_unsaved_form(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#reports/mapping")
    ready(page)
    page.get_by_role("button", name="Create mapping", exact=True).click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Mapping name", exact=True).fill("Do not discard")
    expect(dialog.get_by_label("Devices", exact=True)).to_have_value("SIM-DEVICE-0")
    dialog.get_by_role("button", name="Add mapping row", exact=True).click()
    dialog.get_by_label("Source field", exact=True).select_option("deye.lab_power\nkW")
    dialog.get_by_label("Target metric", exact=True).select_option("pv_w")
    dialog.get_by_role("button", name="Add mapping row", exact=True).click()
    dialog.get_by_label("Source field", exact=True).nth(1).select_option("deye.lab_power\nkW")
    dialog.get_by_label("Target metric", exact=True).nth(1).select_option("pv_w")
    dialog.get_by_role("button", name="Save draft", exact=True).click()
    expect(dialog.get_by_role("alert")).to_contain_text("Each target metric can only be mapped once.")
    expect(dialog.get_by_label("Mapping name", exact=True)).to_have_value("Do not discard")
    dialog.get_by_role("button", name="Remove row", exact=True).last.click()
    expect(dialog.get_by_label("Source field", exact=True)).to_have_count(1)
    expect(page.locator('link[rel="stylesheet"]')).to_have_count(1)
    expect(page.locator("style")).to_have_count(0)


def test_data_legacy_routes_share_one_tab_row_and_measurements_remain_reachable(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    for route, title in [
        ("reports/main", "Overview"),
        ("reports/quality", "Overview"),
        ("reports/mapping", "Mapping"),
        ("reports/main/mapping", "Mapping"),
        ("reports/sync", "Sync log"),
        ("reports/cloud", "Cloud accounts"),
        ("reports/agents", "Local Agent"),
    ]:
        page.goto(origin + "/#" + route)
        ready(page)
        expect(page.locator("#content").get_by_role("tablist")).to_have_count(1)
        expect(page.get_by_role("tab", name=title, exact=True)).to_have_attribute("aria-selected", "true")
        expect(page.get_by_role("heading", name="Data & connections", exact=True)).to_be_visible()
    page.get_by_role("tab", name="Measurements", exact=True).click()
    page.get_by_label("Metric", exact=True).select_option("sim.power")
    expect(page.locator("#content")).to_contain_text("Native measurement points")
    page.goto(origin + "/#reports/main/mapping")
    page.get_by_label("Language / Ngôn ngữ").select_option("vi")
    expect(page.get_by_role("tab", name="Ánh xạ", exact=True)).to_have_attribute("aria-selected", "true")
    expect(page.locator("#content").get_by_role("tablist")).to_have_count(1)
