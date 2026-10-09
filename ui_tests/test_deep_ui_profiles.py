"""Read-only synthetic profile and network cases. Never exercises vendor transports."""

from conftest import login
from playwright.sync_api import expect


def test_rule_parameters_follow_exact_profile_and_clear_on_action_change(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    capabilities = [
        {'intent': 'SET_RESERVE_SOC', 'state': 'UNKNOWN', 'reason': 'TEST uncommissioned',
         'constraints': {'value': {'min': 10, 'max': 80, 'step': 5, 'unit': '%'}}},
        {'intent': 'SET_WORK_MODE', 'state': 'UNKNOWN', 'constraints': {'mode': {'enum': ['TEST_A', 'TEST_B']}}},
        {'intent': 'ENABLE_GRID_CHARGE', 'state': 'UNKNOWN', 'constraints': {}},
    ]

    def detail(route):
        response = route.fetch()
        body = response.json()
        body['capabilities'] = capabilities
        route.fulfill(response=response, json=body)

    page.route('**/api/devices/SIM-DEVICE-0', detail)
    page.goto(origin + '/#operations/main/rules')
    page.get_by_role('button', name='+ Create draft rule', exact=True).click()
    dialog = page.get_by_role('dialog')
    dialog.get_by_label('Name', exact=True).fill('ISOLATED bounded action')
    dialog.get_by_label('Monitored equipment', exact=True).select_option('SIM-DEVICE-0')
    dialog.get_by_label('Observed metric', exact=True).select_option('0')
    dialog.get_by_label('Comparison', exact=True).select_option('gt')
    dialog.get_by_label('Threshold in selected unit', exact=True).fill('0')
    dialog.get_by_label('Target equipment', exact=True).select_option('SIM-DEVICE-0')
    intent = dialog.get_by_label('Proposed change', exact=True)
    expect(intent.locator('option')).to_have_count(4)
    intent.select_option('SET_RESERVE_SOC')
    value = dialog.get_by_label('Proposed value (%)', exact=True)
    expect(value).to_have_value('')
    expect(value).to_have_attribute('min', '10')
    expect(value).to_have_attribute('max', '80')
    value.fill('15')
    intent.select_option('SET_WORK_MODE')
    expect(dialog.locator('.rule-profile-fields select')).to_have_value('')
    dialog.locator('.rule-profile-fields select').select_option('1')
    with page.expect_response(lambda r: r.url.endswith('/api/rules') and r.request.method == 'POST') as saved:
        dialog.get_by_role('button', name='Save draft', exact=True).click()
    assert saved.value.status == 201
    assert saved.value.request.post_data_json['actions'][0]['parameters'] == {'mode': 'TEST_B'}
    page.get_by_role('button', name='Edit', exact=True).click()
    expect(dialog.locator('.rule-profile-fields select')).to_have_value('1')
    for width in (1600, 1024, 430):
        page.set_viewport_size({'width': width, 'height': 1000})
        assert dialog.evaluate('d=>d.scrollWidth<=d.clientWidth+1')
    assert page.request.get(origin + '/api/commands').json() == []


def test_rule_inspector_keeps_unknown_and_offers_retry_after_dry_run(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    csrf = page.request.get(origin + '/api/me').json()['csrf']
    response = page.request.post(origin + '/api/rules', headers={'X-CSRF-Token': csrf, 'Origin': origin}, data={
        'site_id': 'SIM-SITE-0', 'name': 'ISOLATED dry run inspector',
        'conditions': [{'device_id': 'SIM-DEVICE-0', 'metric': 'TEST_UNOBSERVED', 'unit': 'W',
                        'comparison': 'gt', 'threshold': 0}],
        'actions': [{'device_id': 'SIM-DEVICE-0', 'intent': 'ENABLE_GRID_CHARGE', 'parameters': {}}],
    })
    assert response.status == 201
    page.goto(origin + '/#operations/main/rules')
    page.reload()
    expect(page.locator('.rule-reference-layout > .card')).to_have_count(3)
    page.get_by_role('button', name='Evaluate current readings', exact=True).click()
    expect(page.locator('.rule-evaluation')).to_contain_text('Insufficient data')
    expect(page.locator('.rule-evaluation')).to_contain_text('No measurement')
    expect(page.get_by_role('button', name='Evaluate current readings', exact=True)).to_be_enabled()
    page.get_by_label('Find a rule', exact=True).fill('no match')
    expect(page.locator('.rule-evaluation')).to_have_count(0)
    expect(page.get_by_role('button', name='Evaluate current readings', exact=True)).to_be_disabled()
    page.get_by_label('Find a rule', exact=True).fill('')
    for width in (1600, 1024, 430):
        page.set_viewport_size({'width': width, 'height': 1000})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    assert page.request.get(origin + '/api/commands').json() == []


def test_map_layers_preserve_declared_positions_without_inventing_status(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')

    def positions(route):
        response = route.fetch()
        body = response.json()
        body['plants'][0].update(latitude=10, longitude=106, status='UNKNOWN')
        route.fulfill(response=response, json=body)

    page.route('**/api/fleet/map-data', positions)
    page.goto(origin + '/#plants/map')
    expect(page.locator('.geo-marker.geo-unknown')).to_have_count(1)
    page.locator('.map-layers > summary').click()
    page.get_by_label('Plant names', exact=True).check()
    expect(page.locator('.geo-name')).to_have_count(1)
    page.get_by_label('Coastline', exact=True).uncheck()
    expect(page.locator('.geographic-land')).to_have_attribute('visibility', 'hidden')
    page.get_by_label('Status colors', exact=True).uncheck()
    expect(page.locator('.geo-marker.geo-plain')).to_have_count(1)
    page.locator('.map-site-button').first.click()
    page.locator('.map-layers > summary').click()
    expect(page.get_by_label('Plant names', exact=True)).to_be_checked()
    expect(page.get_by_label('Coastline', exact=True)).not_to_be_checked()
    page.set_viewport_size({'width': 430, 'height': 932})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')


def test_rule_late_profile_does_not_restore_previous_equipment(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    page.goto(origin + '/#operations/main/rules')
    page.get_by_role('button', name='+ Create draft rule', exact=True).click()
    dialog = page.get_by_role('dialog')
    pending = []
    page.route('**/api/devices/SIM-DEVICE-0', lambda route: pending.append(route))
    dialog.get_by_label('Target equipment', exact=True).select_option('SIM-DEVICE-0')
    page.wait_for_timeout(100)
    dialog.get_by_label('Target equipment', exact=True).select_option('')
    pending[0].fulfill(json={'capabilities': [{'intent': 'TEST_LATE', 'state': 'VERIFIED', 'constraints': {}}]})
    expect(dialog.get_by_label('Proposed change', exact=True)).to_be_disabled()
    expect(dialog).not_to_contain_text('TEST_LATE')


def test_edit_preserves_unrepresentable_parameters_without_silent_loss(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    csrf = page.request.get(origin + '/api/me').json()['csrf']
    parameters = {'mode': 'TEST_REMOVED', 'nested': {'preserve': [0, False, 'TEST']}}
    response = page.request.post(origin + '/api/rules', headers={'X-CSRF-Token': csrf, 'Origin': origin}, data={
        'site_id': 'SIM-SITE-0', 'name': 'ISOLATED preserve unknown fields',
        'conditions': [{'device_id': 'SIM-DEVICE-0', 'metric': 'TEST_UNOBSERVED', 'unit': 'W',
                        'comparison': 'gt', 'threshold': 0}],
        'actions': [{'device_id': 'SIM-DEVICE-0', 'intent': 'SET_WORK_MODE', 'parameters': parameters}],
    })
    assert response.status == 201
    rule_id = response.json()['id']
    page.goto(origin + '/#operations/main/rules')
    page.reload()
    page.get_by_role('button', name='Edit', exact=True).click()
    dialog = page.get_by_role('dialog')
    expect(dialog).to_contain_text('The saved action will be preserved unchanged.')
    dialog.get_by_label('Name', exact=True).fill('ISOLATED renamed only')
    with page.expect_response(lambda r: r.url.endswith('/rules/' + rule_id + '/edit')) as saved:
        dialog.get_by_role('button', name='Save draft', exact=True).click()
    assert saved.value.status == 200
    assert saved.value.request.post_data_json['data']['actions'][0]['parameters'] == parameters
    assert page.request.get(origin + '/api/commands').json() == []


def test_network_declarations_do_not_imply_live_connectivity(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    page.get_by_label('Plant scope', exact=True).select_option('SIM-SITE-0')
    page.route('**/api/sites/SIM-SITE-0/network-status', lambda route: route.fulfill(json={
        'agents': [{'id': 'TEST_AGENT', 'name': 'TEST enrolled', 'enabled': True}],
        'profiles': [{'id': 'TEST_PROFILE', 'name': 'TEST declared', 'device_id': 'SIM-DEVICE-0',
                      'connection': 'Modbus TCP', 'address': '192.0.2.1', 'port': 502}],
        'local_agent': {'connected': None, 'latency_ms': None},
    }))
    page.goto(origin + '/#overview/main/network')
    root = page.locator('.network-reference')
    expect(root).to_contain_text('TEST enrolled')
    expect(root.locator('.network-topology')).to_contain_text('Modbus TCP')
    expect(root).to_contain_text('192.0.2.1')
    expect(root).to_contain_text('No evidence')
    expect(root).not_to_contain_text('Confirmed')
    for width in (1600, 1024, 430):
        page.set_viewport_size({'width': width, 'height': 1000})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    assert page.request.get(origin + '/api/commands').json() == []
