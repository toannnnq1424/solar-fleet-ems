"""Whole-workspace finishing contracts. All synthetic cases stay in this test fixture."""

import pytest
from conftest import login
from playwright.sync_api import expect


def test_scope_survives_reload_and_mobile_navigation_is_accessible(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    page.get_by_label('Plant scope', exact=True).select_option('SIM-SITE-0')
    page.goto(origin + '/#overview/main/network')
    page.reload()
    expect(page.get_by_label('Plant scope', exact=True)).to_have_value('SIM-SITE-0')
    expect(page.locator('.network-reference')).to_be_visible()
    page.set_viewport_size({'width': 430, 'height': 932})
    nav = page.get_by_role('navigation', name='Main navigation', include_hidden=True)
    expect(nav).not_to_be_visible()
    menu = page.get_by_role('button', name='Menu', exact=True)
    menu.click()
    expect(menu).to_have_attribute('aria-expanded', 'true')
    expect(nav).to_be_visible()
    nav.get_by_role('button', name='Devices', exact=True).click()
    expect(nav).not_to_be_visible()
    expect(page.locator('.device-workspace-container')).to_be_visible()
    menu.click()
    page.keyboard.press('Escape')
    expect(menu).to_be_focused()
    expect(nav).not_to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')


def test_geographic_map_filters_invalid_positions_and_preserves_zoom(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')

    def positions(route):
        response = route.fetch()
        body = response.json()
        for site, lat, lon in zip(body['plants'], [0, 10.5, 200], [0, 106.5, 30]):
            site.update(latitude=lat, longitude=lon)
        route.fulfill(response=response, json=body)

    page.route('**/api/fleet/map-data', positions)
    page.goto(origin + '/#plants/map')
    expect(page.locator('.geo-marker')).to_have_count(2)
    initial = page.locator('.geographic-map').get_attribute('viewBox')
    page.get_by_role('button', name='Zoom in map', exact=True).click()
    zoomed = page.locator('.geographic-map').get_attribute('viewBox')
    assert float(zoomed.split()[2]) < float(initial.split()[2])
    page.locator('.geo-marker').nth(1).focus()
    page.keyboard.press('Enter')
    expect(page.locator('.map-site-detail')).to_contain_text('SIMULATOR plant 2')
    assert page.locator('.geographic-map').get_attribute('viewBox') == zoomed
    page.get_by_label('Find a plant', exact=True).fill('SIMULATOR plant 3')
    expect(page.locator('.geo-marker')).to_have_count(0)
    expect(page.locator('.map-empty-overlay')).to_be_visible()
    assert page.request.get(origin + '/api/commands').json() == []


def test_realtime_keeps_reference_layout_without_equipment_or_samples(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    page.goto(origin + '/#operations/main/journal')
    page.get_by_role('button', name='Realtime Monitoring', exact=True).click()
    expect(page.locator('.monitor-reference-layout > .card')).to_have_count(3)
    expect(page.locator('.monitor-kpis .metric-tile')).to_have_count(6)
    expect(page.locator('.monitor-reference-layout > .device-mini-charts .card')).to_have_count(4)
    expect(page.locator('.monitor-reference-layout')).not_to_contain_text('cloud_connection')
    for width in (1600, 1024, 430):
        page.set_viewport_size({'width': width, 'height': 1000})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    assert page.request.get(origin + '/api/commands').json() == []


def test_rollout_is_blank_draft_with_real_selection_no_commands(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    page.goto(origin + '/#operations/rollouts')
    expect(page.locator('.rollout-editor-grid > .card')).to_have_count(3)
    expect(page.get_by_label('Rollout name', exact=True)).to_have_value('')
    expect(page.get_by_label('Setting', exact=True)).to_have_value('')
    expect(page.get_by_label('Value in device profile units', exact=True)).to_have_value('')
    page.get_by_label('Rollout name', exact=True).fill('ISOLATED draft only')
    page.get_by_label('Setting', exact=True).select_option('SET_RESERVE_SOC')
    page.get_by_label('Value in device profile units', exact=True).fill('0')
    page.get_by_role('button', name='Save draft for review', exact=True).click()
    expect(page.locator('.rollout-editor [role="alert"]')).to_contain_text('Select between 1 and 20')
    page.locator('.rollout-target input').first.check()
    with page.expect_response(lambda r: r.url.endswith('/api/rollouts') and r.request.method == 'POST') as result:
        page.get_by_role('button', name='Save draft for review', exact=True).click()
    assert result.value.status == 201
    assert result.value.request.post_data_json['actions'][0]['parameters']['value'] == 0
    assert page.request.get(origin + '/api/commands').json() == []


def test_all_protocol_panels_have_no_mock_telemetry_or_raw_json(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    page.goto(origin + '/#devices/main')
    page.get_by_role('button', name='Engineering tools', exact=True).click()
    expect(page.get_by_label('Protocol to inspect', exact=True)).to_be_visible()
    options = page.get_by_label('Protocol to inspect', exact=True).locator('option').evaluate_all('nodes => nodes.map(n => n.value)')
    assert len(options) == 15
    for key in options:
        page.get_by_label('Protocol to inspect', exact=True).select_option(key)
        expect(page.locator('.protocol-reference-layout')).to_be_visible()
        expect(page.locator('.protocol-reference-layout textarea')).to_have_count(0)
        expect(page.locator('#content')).not_to_contain_text('86.5%')
        expect(page.locator('#content')).not_to_contain_text('SIMULATED_SESSION')
        expect(page.locator('#content')).not_to_contain_text('LIVE_CONNECTED')
    assert page.request.get(origin + '/api/commands').json() == []


def test_device_observation_layout_keeps_empty_minicharts_and_exact_units(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    page.route('**/api/devices/*/history', lambda route: route.fulfill(json={'samples': [], 'scope': 'LOCAL_RETENTION_7_DAYS'}))
    page.goto(origin + '/#devices/main')
    page.get_by_role('button', name='Detail & native readings', exact=True).first.click()
    expect(page.locator('.device-mini-charts > .card')).to_have_count(4)
    expect(page.locator('.device-history circle')).to_have_count(0)
    for width in (1600, 1024, 430):
        page.set_viewport_size({'width': width, 'height': 1000})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    assert page.request.get(origin + '/api/commands').json() == []


@pytest.mark.parametrize('fixture_server', ['empty'], indirect=True)
def test_empty_installation_keeps_all_workspaces_without_invented_records(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    routes = [
        'overview/main', 'plants/main', 'plants/map', 'topology/main', 'devices/main',
        'operations/main/control', 'operations/main/schedules', 'operations/main/rules',
        'reports/main', 'incidents/main', 'reports/analytics', 'incidents/health',
        'operations/main/journal', 'settings/main/users', 'settings/main/connections',
        'settings/main/site_config', 'settings/main/device_onboarding', 'settings/main/security',
        'operations/rollouts', 'operations/handover', 'reports/main/sources',
        'incidents/jobs', 'incidents/plans', 'incidents/firmware', 'incidents/playbooks',
        'incidents/sla', 'operations/schedule-plans', 'devices/network_profile',
        'devices/document', 'settings/source_policy', 'settings/notification_policy',
    ]
    fleet = page.request.get(origin + '/api/fleet').json()
    assert fleet['devices'] == []
    assert fleet['sites'] == []
    for route in routes:
        page.goto(origin + '/#' + route)
        expect(page.locator('#content .progress-loading')).to_have_count(0)
        expect(page.locator('#content')).not_to_be_empty()
        expect(page.locator('#content')).not_to_contain_text('Could not load this page')
        expect(page.locator('#content')).not_to_contain_text('SIMULATOR plant')
        expect(page.locator('#content')).not_to_contain_text('[object Object]')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), route
    page.goto(origin + '/#operations/main/journal')
    page.get_by_role('button', name='Realtime Monitoring', exact=True).click()
    expect(page.locator('.monitor-kpis .metric-tile')).to_have_count(6)
    expect(page.locator('.monitor-reference-layout > .device-mini-charts .card')).to_have_count(4)
    expect(page.locator('.device-history circle')).to_have_count(0)
    page.set_viewport_size({'width': 430, 'height': 932})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    assert page.request.get(origin + '/api/commands').json() == []


def test_map_read_failure_offers_retry_without_fabricated_locations(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    page.route('**/api/fleet/map-data', lambda route: route.fulfill(status=503, json={'detail': 'TEST read unavailable'}))
    page.goto(origin + '/#plants/map')
    expect(page.locator('.geo-marker')).to_have_count(0)
    expect(page.locator('#content')).to_contain_text('TEST read unavailable')
    page.unroute('**/api/fleet/map-data')
    page.get_by_role('button', name='Try again', exact=True).click()
    expect(page.locator('.geographic-map')).to_be_visible()
    expect(page.locator('.geo-marker')).to_have_count(0)
