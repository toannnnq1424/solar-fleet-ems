"""Shared manual read actions and disambiguated scope; no external network."""

from conftest import login
from playwright.sync_api import expect


def test_shared_refresh_and_plant_vendor_account_labels(browser_page):
    page, origin = browser_page
    def fleet(route):
        response = route.fetch()
        body = response.json()
        for site in body['sites']:
            site['account_label'] = 'synthetic-owner@example.invalid'
        route.fulfill(response=response, json=body)
    page.route('**/api/fleet', fleet)
    login(page, origin, 'ui-admin')
    scope = page.get_by_label('Plant scope', exact=True)
    scope.select_option('SIM-SITE-0')
    expect(scope.locator('option:checked')).to_contain_text('Deye · synthetic-owner@example.invalid')
    requests = []
    def refresh(route):
        requests.append(route.request.post_data_json)
        route.fulfill(json={'state': 'WAITING', 'updated': 0, 'retry_after_seconds': 45})
    page.route('**/api/readings/refresh', refresh)
    for route in ('overview/main', 'devices/main', 'reports/main', 'operations/main/journal',
                  'operations/main/ems', 'devices/main/network', 'incidents/health'):
        page.goto(origin + '/#' + route)
        action = page.get_by_role('button', name='Fetch latest readings', exact=True)
        expect(action).to_be_visible()
        action.click()
        expect(page.get_by_text('Waiting for the next permitted account read. Retry in about 45 seconds.', exact=True)).to_be_visible()
        assert requests[-1] == {'site_id': 'SIM-SITE-0'}
    page.goto(origin + '/#devices/main')
    page.get_by_role('button', name='Detail & native readings', exact=True).first.click()
    page.locator('.device-live-monitor').get_by_role('button', name='Fetch latest readings', exact=True).click()
    expect(page.locator('.device-live-monitor')).to_contain_text('Retry in about 45 seconds.')
    assert requests[-1].get('device_id')
    assert page.request.get(origin + '/api/commands').json() == []
