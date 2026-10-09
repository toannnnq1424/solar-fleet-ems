"""Detailed-reference compositions with isolated observations, never production seed data."""

from conftest import login
from playwright.sync_api import expect


def test_visual_charts_preserve_unknown_and_zero(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    result = page.evaluate("""async () => {
      const {dailyEnergyChart,percentageGauge}=await import('/static/ui-visuals.js');
      const empty=dailyEnergyChart([{date:'2026-10-01',pv_kwh:null}]);
      const chart=dailyEnergyChart([
        {date:'2026-10-01',pv_kwh:12,load_kwh:6,grid_export_kwh:null},
        {date:'2026-10-02',pv_kwh:0,load_kwh:-1,grid_export_kwh:'15'},
      ]);
      return {empty:empty.querySelectorAll('rect').length,
        bars:[...chart.querySelectorAll('.energy-bar')].map(el=>({height:Number(el.getAttribute('height')),label:el.textContent})),
        unknown:percentageGauge(null,'Self use').querySelectorAll('.gauge-value').length,
        invalid:percentageGauge(110,'Self use').querySelectorAll('.gauge-value').length,
        zero:percentageGauge(0,'Self use').querySelector('.gauge-number').textContent};
    }""")
    assert result["empty"] == result["unknown"] == result["invalid"] == 0
    assert [bar["height"] for bar in result["bars"]] == [180, 90, 0]
    assert "12 kWh" in result["bars"][0]["label"]
    assert result["zero"] == "0%"


def test_reference_compositions_reflow_without_changing_data(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page_errors = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    views = [
        ("reports/analytics", ".report-layout"),
        ("operations/main/control", ".control-layout"),
        ("operations/main/rules", ".ems-reference-grid"),
        ("settings/main/users", ".users-reference-layout"),
        ("plants/map", ".map-reference-layout"),
        ("incidents/main", ".filter-strip"),
        ("settings/main/site_config", ".planning-battery-fields"),
    ]
    for width in (1600, 1024, 430):
        page.set_viewport_size({"width": width, "height": 1000})
        for route, selector in views:
            page.goto(origin + "/#" + route)
            expect(page.locator(selector)).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1"), (route, width)
    page.get_by_label("Language / Ngôn ngữ").select_option("vi")
    page.goto(origin + "/#settings/main/site_config")
    expect(page.get_by_role("heading", name="Hồ sơ đã lưu", exact=True)).to_be_visible()
    # Technical keys remain in the deliberately collapsed raw draft, not in the checklist.
    checklist = page.get_by_role("table").filter(has=page.get_by_role("columnheader", name="Hạng mục", exact=True))
    expect(checklist).not_to_contain_text("NOT_CONFIGURED")
    expect(checklist).not_to_contain_text("tou_rates")
    expect(checklist).to_contain_text("Biểu giá theo giờ")
    expect(checklist).to_contain_text("Chưa cấu hình")
    expect(page.get_by_label("Mức pin dự phòng (%)", exact=True)).to_be_visible()
    page.get_by_label("Language / Ngôn ngữ").select_option("en")
    page.set_viewport_size({"width": 1600, "height": 1000})
    page.get_by_label("Plant scope", exact=True).select_option("SIM-SITE-0")
    page.goto(origin + "/#overview/main/overview")
    expect(page.locator(".site-dashboard-grid")).to_be_visible()
    expect(page.locator(".site-dashboard-grid > .card")).to_have_count(11)
    assert page.locator(".dashboard-chart").bounding_box()["x"] > page.locator(".dashboard-flow").bounding_box()["x"]
    assert not page_errors


def test_map_never_invents_positions_and_keeps_selection(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#plants/map")
    expect(page.locator(".map-site-button")).to_have_count(3)
    expect(page.locator(".geographic-land path")).to_have_count(127)
    expect(page.locator(".geo-marker")).to_have_count(0)
    page.locator(".map-site-button").nth(1).click()
    expect(page.locator(".map-site-detail")).to_contain_text("SIMULATOR plant 2")
    page.get_by_label("Find a plant", exact=True).fill("no-such-plant")
    expect(page.locator(".map-site-button")).to_have_count(0)
    expect(page.locator(".map-site-detail")).to_contain_text("No matching plants")
    assert page.request.get(origin + "/api/commands").json() == []
