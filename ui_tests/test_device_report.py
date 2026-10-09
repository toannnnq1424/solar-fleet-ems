"""Per-device summary presentation; isolated outbound-blocked fixture only."""

import pytest
from conftest import login
from playwright.sync_api import expect


def test_individual_inverter_overview_period_switch_null_and_no_physical_writes(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    def detail(route):
        response = route.fetch()
        body = response.json()
        body['latest']['received_at'] = '2026-10-08T01:00:00Z'
        body['latest']['reported'] = {
            'serial': body['device']['vendor_id'], 'ac_kw': 2.75, 'pv_dc_kw': 0,
            'rated_kw': 10, 'temperature_c': None, 'source_clock': None,
            'periods': {'today': {'generation_kwh': 7.5, 'charge_kwh': 0, 'discharge_kwh': None},
                        'month': {'generation_kwh': 82, 'charge_kwh': 15, 'discharge_kwh': 9}},
        }
        route.fulfill(response=response, json=body)
    page.route('**/api/devices/*', detail)
    page.route('**/api/devices/*/history', lambda route: route.fulfill(json={'samples': []}))
    page.goto(origin + '/#devices/main')
    page.get_by_role('button', name='Detail & native readings', exact=True).first.click()
    panel = page.locator('.device-report-panel')
    expect(panel).to_contain_text('2.75 kW')
    expect(panel).to_contain_text('not station totals')
    expect(panel.locator('.device-energy-metrics')).to_contain_text('7.5 kWh')
    expect(panel.locator('.device-energy-metrics .metric-copy strong').nth(1)).to_have_text('0 kWh')
    expect(panel.locator('.device-energy-metrics .metric-copy strong').nth(2)).to_have_text('—')
    panel.get_by_label('Device energy period', exact=True).select_option('month')
    expect(panel.locator('.device-energy-metrics')).to_contain_text('82 kWh')
    panel.get_by_label('Device energy period', exact=True).select_option('year')
    expect(panel).to_contain_text('No vendor data for this period.')
    for width in (1600, 1024, 430):
        page.set_viewport_size({'width': width, 'height': 1000})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.get_by_role('button', name='Close', exact=True).click()
    page.goto(origin + '/#operations/main/journal')
    page.get_by_role('button', name='Realtime Monitoring', exact=True).click()
    expect(page.locator('.device-report-panel')).to_contain_text('2.75 kW')
    assert page.request.get(origin + '/api/commands').json() == []


@pytest.mark.parametrize('surface', ['dialog', 'journal'])
def test_refresh_updates_all_readonly_panels_and_clears_them_on_failure(browser_page, surface):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    value, fail, requests = [17.25], [False], []

    def detail(route):
        response = route.fetch()
        body = response.json()
        body['latest']['reported'] = {
            'serial': body['device']['vendor_id'], 'ac_kw': value[0], 'periods': {}}
        body['latest']['samples'] = [{
            'metric': 'soc_pct', 'value': value[0], 'unit': '%',
            'quality': 'GOOD', 'source_timestamp': '2026-01-01T00:00:00Z'}]
        body['latest']['native'] = {'receipt_marker': f'current-{value[0]}'}
        route.fulfill(response=response, json=body)

    def realtime(route):
        requests.append(route.request.url)
        if fail[0]:
            route.fulfill(status=403, json={'detail': 'scope denied in isolated test'})
            return
        response = route.fetch()
        body = response.json()
        body['connectivity']['firmware_version'] = f'fixture-{value[0]}'
        body['parameters'] = [{'name': 'soc_pct', 'value': value[0], 'unit': '%',
                               'updated_at': '2026-01-01T00:00:00Z', 'quality': 'GOOD'}]
        route.fulfill(response=response, json=body)

    def history(route):
        # Option order changes between receipts; selection must keep its channel.
        metrics = ['soc_pct', 'retained_channel'] if value[0] == 17.25 else ['retained_channel', 'soc_pct']
        route.fulfill(json={'samples': [
            {'device_id': 'fixture-device', 'metric': metric, 'unit': '%', 'value': value[0],
             'binding_id': 'fixture-binding', 'source': 'VENDOR_CLOUD', 'quality': 'GOOD',
             'source_timestamp': '2026-01-01T00:00:00Z'} for metric in metrics]})

    page.route('**/api/devices/*', detail)
    page.route('**/api/devices/*/history', history)
    page.route('**/api/journal/realtime/*', realtime)
    if surface == 'dialog':
        page.goto(origin + '/#devices/main')
        page.get_by_role('button', name='Detail & native readings', exact=True).first.click()
    else:
        page.goto(origin + '/#operations/main/journal')
        page.get_by_role('button', name='Realtime Monitoring', exact=True).click()
    monitor = page.locator('.device-live-monitor')
    expect(monitor.locator('.device-report-current')).to_have_text('17.25 kW')
    readings = monitor.locator('.device-live-details')
    expect(readings).to_contain_text('17.25')
    picker = monitor.get_by_label('Observed metric', exact=True)
    picker.select_option('1')
    expect(picker.locator('option:checked')).to_contain_text('retained_channel')
    monitor.get_by_role('button', name='Equipment diagram', exact=True).click()
    monitor.get_by_role('button', name='Table view', exact=True).click()
    monitor.get_by_role('button', name='Pause motion', exact=True).click()
    value[0] = 73.5
    monitor.get_by_role('button', name='Load latest receipt', exact=True).click()
    expect(monitor.locator('.device-report-current')).to_have_text('73.5 kW')
    expect(readings).to_contain_text('73.5')
    expect(readings).not_to_contain_text('17.25')
    expect(picker.locator('option:checked')).to_contain_text('retained_channel')
    expect(picker).to_have_value('0')
    expect(monitor.locator('solar-energy-flow')).to_have_attribute('data-view', 'circuit')
    expect(monitor.get_by_role('button', name='Diagram view', exact=True)).to_have_attribute('aria-pressed', 'true')
    expect(monitor.get_by_role('button', name='Resume motion', exact=True)).to_have_attribute('aria-pressed', 'true')
    if surface == 'dialog':
        monitor.get_by_text('Native data details', exact=True).click()
        expect(readings).to_contain_text('current-73.5')
    else:
        expect(readings).to_contain_text('fixture-73.5')
    assert len(requests) >= 2
    fail[0] = True
    monitor.get_by_role('button', name='Load latest receipt', exact=True).click()
    expect(monitor).to_contain_text('Could not refresh.')
    expect(monitor.locator('.device-live-details')).to_have_count(0)
    expect(monitor.locator('.device-report-panel')).to_have_count(0)
    fail[0] = False
    monitor.get_by_role('button', name='Load latest receipt', exact=True).click()
    expect(monitor.locator('.device-report-current')).to_have_text('73.5 kW')
    assert page.request.get(origin + '/api/commands').json() == []


def test_open_monitor_refreshes_receipts_keeps_period_and_stops_on_close(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    reads = []
    power = [2.0]
    def detail(route):
        response = route.fetch()
        body = response.json()
        reads.append(route.request.url)
        body['latest']['collection_interval_seconds'] = 300
        body['latest']['reported'] = {
            'serial': body['device']['vendor_id'], 'ac_kw': power[0], 'periods': {
                'month': {'generation_kwh': power[0] * 10}}}
        route.fulfill(response=response, json=body)
    page.route('**/api/devices/*', detail)
    page.route('**/api/devices/*/history', lambda route: route.fulfill(json={'samples': []}))
    page.goto(origin + '/#devices/main')
    page.get_by_role('button', name='Detail & native readings', exact=True).first.click()
    monitor = page.locator('.device-live-monitor')
    expect(monitor).to_contain_text('Vendor collection: at least 5 minutes')
    expect(monitor.locator('.device-report-current')).to_have_text('2 kW')
    monitor.get_by_label('Device energy period', exact=True).select_option('month')
    # Defocus a read-only selector so automatic refresh can safely replace cards.
    page.locator('#dialog-title').click()
    power[0] = 3.0
    expect(monitor.locator('.device-report-current')).to_have_text('3 kW', timeout=20000)
    expect(monitor.get_by_label('Device energy period', exact=True)).to_have_value('month')
    expect(monitor.locator('.device-energy-metrics')).to_contain_text('30 kWh')
    power[0] = 4.0
    monitor.get_by_role('button', name='Load latest receipt', exact=True).click()
    expect(monitor.locator('.device-report-current')).to_have_text('4 kW')
    page.get_by_role('button', name='Close', exact=True).click()
    count = len(reads)
    page.clock.install()
    page.clock.fast_forward(31000)
    assert len(reads) == count
    assert page.request.get(origin + '/api/commands').json() == []
