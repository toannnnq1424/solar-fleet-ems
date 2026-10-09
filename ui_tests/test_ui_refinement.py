"""Empty reference layouts and explicit user input; simulator-only workflows."""

from conftest import login
from playwright.sync_api import expect
from test_planning_editor import open_editor


def test_hourly_rate_table_saves_utc_and_reloads_without_json(browser_page):
    page = open_editor(browser_page)
    _, origin = browser_page
    expect(page.locator('.hourly-price-editor input[type="number"]')).to_have_count(50)
    assert page.locator('.hourly-price-editor input').evaluate_all("els => els.every(e => e.value === '')")
    expect(page.locator('.planning-editor textarea')).to_have_count(0)
    device = page.get_by_label("Advisory planning device", exact=True)
    device.select_option(device.locator("option").nth(1).get_attribute("value"))
    values = {"Capacity (kWh)": "15", "Usable capacity (kWh)": "12",
              "Maximum charge (kW)": "5", "Maximum discharge (kW)": "5",
              "Charge efficiency (%)": "95", "Discharge efficiency (%)": "95",
              "Minimum battery level (%)": "10", "Maximum battery level (%)": "90",
              "Reserve battery level (%)": "20", "Replacement cost (USD)": "1000",
              "Rated cycle life": "4000", "USD tariff source": "SYNTHETIC user input only"}
    for label, value in values.items():
        page.get_by_label(label, exact=True).fill(value)
    page.get_by_label("Price start (Vietnam time, UTC+7)", exact=True).fill("2026-10-03T07:00")
    page.get_by_label("Bulk import rate (USD/kWh)", exact=True).fill("0.12")
    page.get_by_label("Bulk export rate (USD/kWh)", exact=True).fill("0")
    page.get_by_role("button", name="Apply rates to all 24 hours", exact=True).click()
    page.get_by_label("Hour 2 import price (USD/kWh)", exact=True).fill("0.15")
    with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/planning-configuration")) as response:
        page.get_by_role("button", name="Save advisory configuration", exact=True).click()
    assert response.value.status == 200
    assert response.value.json()['configuration']['dispatch_config']['charge_efficiency'] == 0.95
    prices = response.value.json()["configuration"]["dispatch_config"]["hourly_prices"]
    assert len(prices) == 24
    assert prices[0]["timestamp"] == "2026-10-03T00:00:00+00:00"
    assert prices[-1]["timestamp"] == "2026-10-03T23:00:00+00:00"
    assert prices[1]["import_per_kwh"] == 0.15
    assert prices[0]["export_per_kwh"] == 0
    page.reload()
    expect(page.get_by_label("Price start (Vietnam time, UTC+7)", exact=True)).to_have_value("2026-10-03T07:00")
    expect(page.get_by_label("Hour 2 import price (USD/kWh)", exact=True)).to_have_value("0.15")
    expect(page.get_by_label('Charge efficiency (%)', exact=True)).to_have_value('95')
    assert page.request.get(origin + "/api/commands").json() == []


def test_price_table_rejects_missing_or_non_hourly_input(browser_page):
    page = open_editor(browser_page)
    result = page.evaluate("""async () => {
      const {vietnamToUTC}=await import('/static/hourly-price-editor.js');
      const bad=['','2026-02-30T08:00','wrong'];
      return {valid:vietnamToUTC('2026-10-03T00:00'),
        rejected:bad.map(s=>{try{vietnamToUTC(s);return false;}catch{return true;}})};
    }""")
    assert result == {"valid": "2026-10-02T17:00:00.000Z", "rejected": [True, True, True]}
    page.get_by_role("button", name="Apply rates to all 24 hours", exact=True).click()
    expect(page.get_by_role("note")).to_contain_text("Enter both rates")
    assert page.locator('.hourly-price-scroll input').evaluate_all("els => els.every(e => e.value === '')")


def test_empty_week_has_structure_and_no_invented_slots(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#operations/main/schedules")
    grid = page.get_by_role("table", name="Weekly battery schedule", exact=True)
    expect(grid.locator("thead th")).to_have_count(8)
    expect(grid.locator("tbody tr")).to_have_count(6)
    expect(grid.locator(".week-empty")).to_have_count(42)
    expect(grid.locator(".week-slot")).to_have_count(0)
    grid.locator("button").first.click()
    dialog = page.get_by_role("dialog")
    # Times come from the explicitly selected cell, not a prefilled operational schedule.
    expect(dialog.get_by_label("From", exact=True)).to_have_value("00:00")
    expect(dialog.get_by_label("To", exact=True)).to_have_value("04:00")
    expect(dialog.get_by_label("Mode", exact=True)).to_have_value("")
    assert page.request.get(origin + "/api/commands").json() == []


def test_all_new_compositions_reflow_and_have_spaced_fields(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.get_by_label("Language / Ngôn ngữ").select_option("vi")
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    for width in (1600, 1024, 430):
        page.set_viewport_size({"width": width, "height": 1000})
        for route, selector in [("settings/main/site_config", ".hourly-price-editor"),
                                ("settings/main/device_onboarding", ".onboarding-layout"),
                                ("operations/main/schedules", ".schedule-week-grid"),
                                ("reports/main/sources", ".source-settings-row"),
                                ("incidents/main", ".incident-charts"),
                                ("operations/main/control", ".control-tile-grid")]:
            page.goto(origin + "/#" + route)
            expect(page.locator(selector).first).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (route, width)
    page.goto(origin + "/#reports/analytics")
    fields = page.locator(".report-aside label.field")
    expect(fields).to_have_count(2)
    first, second = fields.nth(0).bounding_box(), fields.nth(1).bounding_box()
    assert second["y"] - (first["y"] + first["height"]) >= 14
    assert not errors


def test_onboarding_steps_never_claim_completed_discovery(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#settings/main/device_onboarding")
    expect(page.locator(".onboarding-step")).to_have_count(4)
    expect(page.locator('.onboarding-step[aria-current="step"]')).to_have_count(1)
    page.get_by_role("button", name="Huawei", exact=True).click()
    expect(page.locator(".onboarding-layout")).to_contain_text("No matching equipment")
    page.get_by_role("button", name="Next", exact=True).click()
    expect(page.get_by_role("button", name="Open vendor accounts", exact=True)).to_be_visible()
    expect(page.locator(".onboarding-layout")).not_to_contain_text("Successfully connected")
    assert page.request.get(origin + "/api/commands").json() == []


def test_empty_journal_keeps_columns_and_detail_panel(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#operations/main/journal")
    expect(page.locator('.journal-table thead th')).to_have_count(12)
    expect(page.locator('.journal-table tbody')).to_contain_text('No command logs match')
    expect(page.locator('.journal-drawer-pane')).to_contain_text('Command details')
    expect(page.locator('.journal-pagination-bar button')).to_have_count(2)
    for button in page.locator('.journal-pagination-bar button').all():
        expect(button).to_be_disabled()


def test_journal_does_not_invent_actor_vendor_or_replace_zero(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    command = {"id": "SYNTHETIC-UI-ONLY", "intent": "SET_EXPORT_LIMIT", "command_name": "Export limit",
               "old_value": 0, "new_value": 0, "status": "PENDING", "verification_status": "UNKNOWN"}
    page.route('**/api/journal/commands?*', lambda route: route.fulfill(json={
        "items": [command], "total_items": 1, "total_pages": 1, "current_page": 1}))
    page.route('**/api/journal/commands/SYNTHETIC-UI-ONLY', lambda route: route.fulfill(json={
        "command": command, "stages": []}))
    page.goto(origin + "/#operations/main/journal")
    row = page.locator('.journal-table tbody tr').first
    expect(row.locator('td').nth(5)).to_have_text('0')
    expect(row.locator('td').nth(6)).to_have_text('0')
    expect(row.locator('td').nth(7)).to_have_text('—')
    expect(row.locator('td').nth(10)).to_have_text('—')
    expect(page.locator('.drawer-title')).to_have_text('Export limit')
    expect(page.locator('.journal-drawer-pane')).not_to_contain_text('Deye')
    expect(page.locator('.journal-workspace-root')).not_to_contain_text('Nguyễn Văn A')


def test_deep_screens_keep_empty_structure_and_honest_labels(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + '/#devices/main')
    page.get_by_role('button', name='Device parameters', exact=True).click()
    expect(page.locator('.plant-card-title').first).to_be_visible()
    expect(page.locator('#content')).not_to_contain_text('[object Object]')
    page.goto(origin + '/#plants/main')
    page.get_by_role('button', name='Regions & Clusters', exact=True).click()
    expect(page.locator('.region-summary .card')).to_have_count(3)
    expect(page.locator('#content')).not_to_contain_text('null%')
    expect(page.locator('.loss-breakdown-bar')).to_have_count(0)
    page.get_by_label('Plant scope', exact=True).select_option('SIM-SITE-0')
    for route in ['devices/document', 'devices/network_profile', 'settings/notification_policy',
                  'reports/main/agent', 'incidents/plans', 'incidents/firmware']:
        page.goto(origin + '/#' + route)
        expect(page.locator('#content table thead').first).to_be_visible()
        expect(page.locator('#content')).not_to_contain_text('Page unavailable')
    expect(page.locator('.maintenance-preflight-box .badge.good')).to_have_count(0)
    expect(page.locator('#content')).to_contain_text('requirements, not passed checks')
    page.goto(origin + '/#reports/main/diagnostics')
    expect(page.locator('#content')).to_contain_text('Accepted / received observations')
    expect(page.locator('#content')).not_to_contain_text('NO_VERIFIED_DATA')


def test_week_grid_uses_saved_boundaries_and_marks_overlaps(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    result = page.evaluate("""async () => {
      const {scheduleWeekGrid}=await import('/static/schedule-week-grid.js');
      const e=(tag,text='',cls='')=>{const n=document.createElement(tag);n.textContent=text;n.className=cls;return n;};
      const div=(cls,...children)=>{const n=e('div','',cls);n.append(...children);return n;};
      const days=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
      const slots=[{day:0,start:'06:00',end:'11:00',mode:'charge',target_soc:75},
        {day:2,start:'06:00',end:'11:00',mode:'hold'},
        {day:2,start:'06:00',end:'11:00',mode:'discharge'},
        {day:7,start:'00:00',end:'02:00',mode:'charge'}];
      const n=scheduleWeekGrid({e,div},slots,days);
      return {bands:[...n.querySelectorAll('tbody th')].map(e=>e.textContent),
        slots:n.querySelectorAll('.week-slot').length,
        text:n.textContent,empty:n.querySelectorAll('.week-empty').length};
    }""")
    assert result['bands'] == ['00:00–06:00', '06:00–11:00', '11:00–24:00']
    assert result['slots'] == 1
    assert result['empty'] == 20
    assert '75%' in result['text'] and 'Overlapping slots' in result['text']
