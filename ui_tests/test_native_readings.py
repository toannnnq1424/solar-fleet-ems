"""Synthetic native observations only, on an isolated outbound-blocked server."""

from conftest import login
from playwright.sync_api import expect


def test_native_panel_preserves_zero_null_units_filters_and_escapes_vendor_text(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')

    def native(route):
        response = route.fetch()
        body = response.json()
        body['latest'] = {'samples': [], 'received_at': '2026-10-07T00:00:00Z', 'native': {
            'collectionTime': None, 'dataList': [
                {'key': 'test:ac:power', 'title': 'active_power', 'group_id': 'ac', 'group': 'ac_parameters', 'value': 0, 'unit': 'kW'},
                {'key': 'test:ac:missing', 'title': 'Missing', 'group_id': 'ac', 'group': 'AC', 'value': None, 'unit': 'V'},
                {'key': 'test:pv:p', 'title': '<img src=x onerror=alert(1)>', 'group_id': 'pv', 'group': 'PV', 'value': '1.23', 'unit': 'kW'},
            ]}}
        route.fulfill(response=response, json=body)

    page.route('**/api/devices/*', native)
    page.route('**/api/devices/*/history', lambda route: route.fulfill(json={'samples': []}))
    page.goto(origin + '/#devices/main')
    page.get_by_role('button', name='Detail & native readings', exact=True).first.click()
    panel = page.locator('.native-readings')
    expect(panel.locator('tbody tr')).to_have_count(3)
    expect(panel.locator('.native-reading-value').nth(0)).to_have_text('0')
    expect(panel.locator('.native-reading-value').nth(1)).to_have_text('—')
    expect(panel.locator('img')).to_have_count(0)
    expect(panel).to_contain_text('Active power')
    expect(panel.locator('.native-reading-name small')).to_have_count(0)
    panel.get_by_label('Show technical codes', exact=True).check()
    expect(panel.locator('.native-reading-name small')).to_have_count(3)
    panel.get_by_label('Show technical codes', exact=True).uncheck()
    panel.get_by_label('Find parameters', exact=True).fill('Active power')
    expect(panel.locator('tbody tr')).to_have_count(1)
    panel.get_by_label('Find parameters', exact=True).fill('')
    expect(panel).to_contain_text('Measurement time: —')
    expect(page.locator('.device-history circle')).to_have_count(0)
    panel.get_by_label('Parameter group', exact=True).select_option('pv')
    expect(panel.locator('tbody tr')).to_have_count(1)
    panel.get_by_label('Find parameters', exact=True).fill('missing')
    expect(panel).to_contain_text('No parameters match')
    panel.get_by_label('Parameter group', exact=True).select_option('')
    expect(panel.locator('tbody tr')).to_have_count(1)
    for width in (1600, 1024, 430):
        page.set_viewport_size({'width': width, 'height': 1000})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.get_by_role('button', name='Close', exact=True).click()
    page.goto(origin + '/#operations/main/journal')
    page.get_by_role('button', name='Realtime Monitoring', exact=True).click()
    expect(page.locator('.native-readings tbody tr')).to_have_count(3)
    assert page.request.get(origin + '/api/commands').json() == []


def test_unknown_connectivity_is_not_the_same_as_missing_measurement_quality(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')

    def summary(route):
        response = route.fetch()
        body = response.json()
        body['summary'].update(unknown_count=0, unknown_connectivity_count=6)
        body['devices'][0].update(type='SMART_METER', name=None, online=None)
        body['devices'][1].update(type='DATA_LOGGER', name=None, online=False)
        route.fulfill(response=response, json=body)

    page.route('**/api/fleet/devices-overview*', summary)
    page.goto(origin + '/#devices/main')
    expect(page.locator('.overview-kpis .fact').filter(has_text='Connection unknown')).to_contain_text('6')
    page.get_by_label('Equipment type', exact=True).select_option('SMART_METER')
    expect(page.locator('#content tbody tr')).to_have_count(1)
    expect(page.locator('#content tbody tr').first).to_contain_text('Smart meter')
    expect(page.locator('#content tbody tr').first).not_to_contain_text('SMART_METER')
    page.get_by_label('Equipment type', exact=True).select_option('DATA_LOGGER')
    expect(page.locator('#content tbody tr')).to_have_count(1)
    expect(page.locator('#content tbody tr').first).to_contain_text('Disconnected')
