"""Synthetic monitoring presentation; never inserts observations into real storage."""

from conftest import login
from playwright.sync_api import expect

REPORT = {
    'vendor': 'SIMULATOR', 'quality': 'VENDOR_REPORTED', 'control_eligible': False,
    'source_clock': '2026-10-08T06:45:00', 'received_at': '2026-10-08T00:00:00Z',
    'receipt_expired': True, 'power': {'pv_w': 0, 'load_w': 1234, 'battery_soc': 40, 'battery_w': 500, 'grid_w': 1734},
    'periods': {'today': {'start_date': '2026-10-08', 'end_date': '2026-10-08', 'generation_kwh': 12.0}},
    'daily_energy': [{'start_date': '2026-10-08', 'end_date': '2026-10-08', 'generation_kwh': 12.0}],
}


def test_fleet_site_reports_keep_real_zero_and_explicit_quality_without_control(browser_page):
    page, origin = browser_page
    def fleet(route):
        response = route.fetch()
        body = response.json()
        body['sites'][0]['vendor_report'] = REPORT
        route.fulfill(response=response, json=body)
    def overview(route):
        response = route.fetch()
        body = response.json()
        body['vendor_report'] = REPORT
        body['energy_flow'] = {'channels': {}, 'has_readings': False}
        body['plant_status'] = {}
        route.fulfill(response=response, json=body)
    page.route('**/api/fleet', fleet)
    page.route('**/api/sites/*/overview-summary', overview)
    login(page, origin, 'ui-admin')
    page.goto(origin + '/#overview/main')
    expect(page.locator('.vendor-report-summary')).to_contain_text('0 kW')
    expect(page.locator('.vendor-report-summary')).to_contain_text('Receipt expired')
    page.get_by_role('button', name='Open plant overview', exact=True).click()
    expect(page.locator('.site-metrics')).to_contain_text('12 kWh')
    expect(page.locator('.site-metrics')).to_contain_text('Vendor reported')
    expect(page.locator('.vendor-report-provenance')).to_contain_text('2026-10-08 06:45:00')
    chart = page.locator('.interactive-chart').first
    chart.locator('.chart-hit-target').first.hover()
    expect(chart.get_by_role('tooltip')).to_be_visible()
    expect(chart.get_by_role('tooltip')).to_contain_text('2026-10-08')
    expect(chart.get_by_role('tooltip')).to_contain_text('12 kWh')
    expect(chart.get_by_role('tooltip')).to_contain_text('—')
    chart.locator('.chart-hit-target').first.focus()
    chart.locator('.chart-hit-target').first.press('Escape')
    expect(chart.get_by_role('tooltip')).not_to_be_visible()
    expect(page.locator('.power-branch.is-active')).to_have_count(0)
    expect(page.locator('.power-flow')).to_contain_text('Vendor reported · time unverified')
    flow = page.locator('.power-flow')
    for view in ('Perspective model', 'Equipment diagram', 'Power flow'):
        flow.get_by_role('button', name=view, exact=True).click()
        expect(flow.locator('.node-battery')).to_contain_text('Charging')
        expect(flow.locator('.node-grid')).to_contain_text('Import')
        expect(flow.locator('.power-branch.is-active')).to_have_count(0)
        expect(flow.locator('.art-charging-bolt')).to_have_count(0)
    for width in (1600, 1024, 430):
        page.set_viewport_size({'width': width, 'height': 1000})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.goto(origin + '/#reports/analytics/main')
    expect(page.locator('.vendor-report-summary')).to_contain_text('Vendor reported')
    assert page.request.get(origin + '/api/commands').json() == []
