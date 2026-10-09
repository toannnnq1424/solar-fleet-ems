"""Non-technical UI contracts. Isolated simulator only; no vendor traffic."""

from conftest import login
from playwright.sync_api import expect


def test_email_only_guidance_never_claims_authentication(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#settings/main/connections")
    page.get_by_role("button", name="+ Add vendor account", exact=True).click()
    page.get_by_role("dialog").get_by_role("button").filter(
        has=page.locator(".vendor-wordmark", has_text="Deye")
    ).click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label('Account region',exact=True).select_option('eu')
    expect(dialog).to_contain_text("Your administrator has not configured")
    expect(dialog.locator("input")).to_have_count(0)
    expect(dialog).not_to_contain_text("Successfully authenticated")
    dialog.get_by_role('button',name='Application setup · administrator',exact=True).click()
    expect(dialog).to_contain_text('Administrator setup only')
    expect(dialog.locator('input[type="password"]')).to_have_count(2)
    dialog.get_by_role("button", name="Back to account connection", exact=True).click()
    dialog.get_by_role("button", name="Advanced API connection", exact=True).click()
    expect(dialog.get_by_role("button", name="Save connection", exact=True)).to_be_visible()
    expect(dialog.locator('input[type="password"]')).not_to_have_count(0)


def test_site_unknown_values_have_no_demo_chart_or_fake_equipment(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.get_by_label("Plant scope", exact=True).select_option("SIM-SITE-0")
    page.route("**/overview-summary", lambda route: route.fulfill(json={
        "site": {"id": "SIM-SITE-0", "name": "SIMULATOR no measurements"},
        "plant_status": {"status": "UNKNOWN"}, "equipment": {"items": []},
    }))
    page.route("**/telemetry-timeseries?**", lambda route: route.fulfill(json={
        "samples": [], "total_points": 0, "reason": "STORED_TELEMETRY",
    }))
    page.goto(origin + "/#overview/main/overview")
    expect(page.locator(".site-heading")).to_contain_text("Unknown")
    expect(page.locator(".site-metrics")).not_to_contain_text("0 kW")
    expect(page.locator(".measurement-chart circle")).to_have_count(0)
    expect(page.locator(".measurement-chart")).to_contain_text("No matching observations")
    expect(page.locator("#content")).to_contain_text("No synchronized equipment")
    expect(page.locator("#content")).not_to_contain_text("30 %")
    page.get_by_role("button", name="Show all plants", exact=True).click()
    expect(page.get_by_label("Plant scope", exact=True)).to_have_value("")
    expect(page.locator(".site-heading")).to_have_count(0)


def test_primary_routes_use_svg_icons_and_reflow(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    routes = ["overview/main", "plants/main", "plants/map", "devices/main",
              "operations/main/control", "operations/main/schedules", "operations/main/rules",
              "reports/main", "reports/analytics", "incidents/main", "incidents/health",
              "operations/main/journal", "settings/main/users", "settings/main/connections"]
    page.get_by_label("Language / Ngôn ngữ").select_option("vi")
    for width in (1600, 430):
        page.set_viewport_size({"width": width, "height": 1000})
        for route in routes:
            page.goto(origin + "/#" + route)
            expect(page.locator("#content .progress-loading")).to_have_count(0)
            expect(page.locator("#content")).not_to_contain_text("Chưa tải được trang")
            assert page.evaluate("! /\\p{Extended_Pictographic}/u.test(document.body.innerText)"), route
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (route, width)
            assert page.locator(".sidebar svg.ui-icon").count() >= 10
    page.goto(origin + "/#operations/main/rules")
    expect(page.locator(".engineering-tools")).not_to_have_attribute("open", "")


def test_plant_illustrations_match_explicit_type_and_remain_labeled(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#plants/main")
    page.get_by_role("button", name="+ Add plant", exact=True).click()
    dialog = page.get_by_role("dialog")
    expect(dialog.get_by_label("Installation type", exact=True)).to_have_value("")
    expect(dialog.locator('.step-item[aria-current="step"]')).to_have_count(1)
    expect(dialog.locator('.step-item.completed')).to_have_count(0)
    expect(dialog.locator(".plant-type-choices img")).to_have_count(3)
    expect(dialog.locator(".plant-type-choices figcaption")).to_have_text(["Illustration"] * 3)
    dialog.get_by_role("button", name="Residential", exact=True).click()
    expect(dialog.get_by_label("Installation type", exact=True)).to_have_value("RESIDENTIAL")
    expect(dialog.get_by_role("button", name="Residential", exact=True)).to_have_attribute("aria-pressed", "true")
    page.keyboard.press("Escape")
    page.get_by_label("Plant scope", exact=True).select_option("SIM-SITE-0")
    page.route("**/overview-summary", lambda route: route.fulfill(json={
        "site": {"id": "SIM-SITE-0", "name": "SIMULATOR factory", "declared_specs": {"plant_type": "ROOFTOP_CI"}},
    }))
    page.goto(origin + "/#overview/main/plant_info")
    expect(page.locator(".site-heading img")).to_have_attribute("src", "/static/img/plant_commercial.jpg")
    expect(page.locator(".site-heading figcaption")).to_have_text("Illustration")
    assert page.locator(".site-heading img").evaluate("img => img.complete && img.naturalWidth > 0")


def test_all_control_capabilities_remain_discoverable_with_plain_labels(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#operations/main/control")
    data = page.request.get(origin + "/api/control/device-state/SIM-DEVICE-0").json()
    # Every intent remains selectable once, organized into compact function cards.
    expect(page.locator('.capability-choice').first).to_be_visible()
    intents = page.locator(".capability-choice option").evaluate_all("options=>options.map(o=>o.value)")
    assert sorted(intents) == sorted(c["intent"] for c in data["intent_capabilities"])
    expect(page.locator(".capability-grid")).not_to_contain_text("SET_MAX_CHARGE_CURRENT")
    verified = next(c for c in data["intent_capabilities"] if c["state"] == "VERIFIED" and c["semantic_match"] == "exact")
    page.locator(".capability-choice").filter(has=page.locator(f'option[value="{verified["intent"]}"]')).select_option(verified["intent"])
    expect(page.get_by_role("button", name="Preview change", exact=True)).to_be_visible()
    page.get_by_role("button", name="Preview change", exact=True).click()
    expect(page.get_by_role("dialog")).to_be_visible()
    # Opening the form does not send a physical command.
    assert page.request.get(origin + "/api/commands").json() == []


def test_weekly_timeline_uses_only_valid_saved_slots(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    result = page.evaluate("""async () => {
        const {scheduleTimeline} = await import('/static/schedule-timeline.js');
        const days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
        const empty = scheduleTimeline([], days);
        const diagram = scheduleTimeline([
            {day:0,start:'06:00',end:'12:00',mode:'charge'},
            {day:6,start:'23:00',end:'24:00',mode:'hold'},
            {day:7,start:'00:00',end:'06:00',mode:'charge'},
            {day:2,start:'25:00',end:'26:00',mode:'discharge'},
            {day:2,start:'06:00',end:'05:00',mode:'discharge'},
            {day:3,start:'05:90',end:'08:00',mode:'charge'},
        ], days);
        return {empty:empty.querySelectorAll('rect').length,
            slots:[...diagram.querySelectorAll('rect')].map(el => ({
                x:Number(el.getAttribute('x')), width:Number(el.getAttribute('width')),
                label:el.textContent, style:el.getAttribute('style'),
            })), label:diagram.getAttribute('aria-label')};
    }""")
    assert result["empty"] == 0
    assert len(result["slots"]) == 2
    assert result["slots"][0]["x"] == 287.5
    assert result["slots"][0]["width"] == 197.5
    assert "Monday · 06:00–12:00" in result["slots"][0]["label"]
    assert "not execution status" in result["label"]
    assert all(slot["style"] is None for slot in result["slots"])
