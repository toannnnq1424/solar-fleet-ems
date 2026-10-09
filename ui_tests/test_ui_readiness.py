"""Local-only account guidance, rule drafts and accessible schedule interactions."""

from conftest import login
from playwright.sync_api import expect


def test_account_preflight_does_not_collect_password_or_claim_live_readiness(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    page.goto(origin + '/#settings/main/connections')
    page.get_by_role('button', name='Connection & testing guide', exact=True).click()
    dialog = page.get_by_role('dialog')
    expect(dialog).to_contain_text('Application setup missing')
    expect(dialog).to_contain_text('SEMS+ · read-only trial')
    expect(dialog.locator('input[type="password"]')).to_have_count(0)
    dialog.get_by_role('button', name='View GoodWe requirements', exact=True).click()
    expect(dialog).to_contain_text('SEMS Portal and SEMS+ use different connections')
    next_button = dialog.get_by_role('button', name='I have the connection details', exact=True)
    expect(next_button).to_be_disabled()
    dialog.get_by_label('Your GoodWe app', exact=True).select_option('sems_plus')
    expect(next_button).to_be_enabled()
    expect(dialog.locator('input[type="password"]')).to_have_count(0)
    expect(dialog).to_contain_text('portal sign-in and SolarOne connection are separate')
    expect(dialog).to_contain_text('does not require your own App ID/App Secret')
    expect(dialog).to_contain_text('does not verify the SolarOne connection or unlock controls')
    for width in (1600, 1024, 430):
        page.set_viewport_size({'width': width, 'height': 932})
        assert dialog.evaluate('d => d.scrollWidth <= d.clientWidth + 1')
        expect(next_button).to_be_enabled()
    dialog.get_by_label('Your GoodWe app', exact=True).select_option('sems')
    expect(dialog).to_contain_text('does not require an App ID/App Secret')
    expect(next_button).to_be_enabled()
    for width in (1600, 1024, 430):
        page.set_viewport_size({'width': width, 'height': 932})
        assert dialog.evaluate('d => d.scrollWidth <= d.clientWidth + 1')
    assert page.request.get(origin + '/api/commands').json() == []


def test_diagnostic_locks_selection_and_global_sync_requires_scope_confirmation(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    page.goto(origin + '/#settings/main/connections')
    captured = []
    page.route('**/api/integrations/*/check', lambda route: captured.append(route))
    page.get_by_role('button', name='Check connection', exact=True).click()
    expect(page.get_by_label('Vendor', exact=True)).to_be_disabled()
    expect(page.get_by_label('Account', exact=True)).to_be_disabled()
    expect(page.get_by_role('button', name='Check connection', exact=True)).to_be_disabled()
    page.wait_for_timeout(100)
    assert len(captured) == 1
    captured[0].fulfill(json={'state': 'PASS', 'checks': [
        {'key': 'plants', 'state': 'PASS', 'count': 0},
        {'key': 'devices', 'state': 'NO_DATA'}, {'key': 'sample', 'state': 'NO_DATA'},
        {'key': 'control', 'state': 'NOT_COMMISSIONED'},
    ]})
    expect(page.locator('.detail-panel')).to_contain_text('0 items received')
    expect(page.get_by_label('Vendor', exact=True)).to_be_enabled()
    synced = []
    page.route('**/api/sync', lambda route: (synced.append(1), route.fulfill(json={'ok': True})))
    page.get_by_role('button', name='Next: review synchronization scope', exact=True).click()
    dialog = page.get_by_role('dialog')
    expect(dialog).to_contain_text('all enabled accounts, not only the selected account')
    assert not synced
    page.keyboard.press('Escape')
    assert not synced
    page.get_by_role('button', name='Next: review synchronization scope', exact=True).click()
    dialog.get_by_role('button', name='Synchronize enabled accounts', exact=True).click()
    expect(dialog).not_to_be_visible()
    assert synced == [1]
    assert page.request.get(origin + '/api/commands').json() == []


def test_rule_editor_uses_observed_metrics_blank_targets_and_real_draft_save(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    page.goto(origin + '/#operations/main/rules')
    page.get_by_role('button', name='+ Create draft rule', exact=True).click()
    dialog = page.get_by_role('dialog')
    expect(dialog.locator('.rule-builder-grid > .card')).to_have_count(3)
    expect(dialog.get_by_label('Threshold in selected unit', exact=True)).to_have_value('')
    expect(dialog.get_by_label('Proposed change', exact=True)).to_be_disabled()
    dialog.get_by_label('Name', exact=True).fill('ISOLATED rule draft')
    dialog.get_by_label('Monitored equipment', exact=True).select_option('SIM-DEVICE-0')
    expect(dialog.get_by_label('Observed metric', exact=True)).to_be_enabled()
    dialog.get_by_label('Observed metric', exact=True).select_option('0')
    dialog.get_by_label('Comparison', exact=True).select_option('gt')
    dialog.get_by_label('Threshold in selected unit', exact=True).fill('0')
    dialog.get_by_label('Target equipment', exact=True).select_option('SIM-DEVICE-0')
    dialog.get_by_label('Proposed change', exact=True).select_option('ENABLE_GRID_CHARGE')
    expect(dialog).to_contain_text('This action takes no parameters.')
    for width in (1600, 1024, 430):
        page.set_viewport_size({'width': width, 'height': 1000})
        assert dialog.evaluate('d=>d.scrollWidth<=d.clientWidth+1')
    with page.expect_response(lambda r: r.url.endswith('/api/rules') and r.request.method == 'POST') as saved:
        dialog.get_by_role('button', name='Save draft', exact=True).click()
    assert saved.value.status == 201
    body = saved.value.request.post_data_json
    assert body['conditions'][0]['threshold'] == 0
    assert body['conditions'][0]['max_age_seconds'] == 300
    assert body['actions'][0]['parameters'] == {}
    assert page.request.get(origin + '/api/commands').json() == []
    page.get_by_role('button', name='Edit', exact=True).click()
    expect(dialog.get_by_label('Name', exact=True)).to_have_value('ISOLATED rule draft')
    expect(dialog.locator('.rule-builder-grid')).to_be_visible()


def test_rule_device_change_cannot_apply_a_late_measurement_response(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    page.goto(origin + '/#operations/main/rules')
    page.get_by_role('button', name='+ Multi-condition rule', exact=True).click()
    dialog = page.get_by_role('dialog')
    pending = []
    page.route('**/api/devices/SIM-DEVICE-0', lambda route: pending.append(route))
    dialog.get_by_label('Monitored equipment', exact=True).select_option('SIM-DEVICE-0')
    page.wait_for_timeout(100)
    dialog.get_by_label('Monitored equipment', exact=True).select_option('')
    pending[0].fulfill(json={'latest': {'samples': [{'metric': 'LATE_ONLY', 'unit': 'W'}]}})
    expect(dialog.get_by_label('Observed metric', exact=True)).to_be_disabled()
    expect(dialog).not_to_contain_text('LATE_ONLY')
    assert page.request.get(origin + '/api/commands').json() == []


def test_schedule_keyboard_resize_touch_friendly_move_and_undo(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    page.goto(origin + '/#operations/main/schedules')
    page.get_by_role('button', name='+ Create draft', exact=True).click()
    dialog = page.get_by_role('dialog')
    dialog.get_by_label('Name', exact=True).fill('ISOLATED resize and move')
    dialog.get_by_role('button', name='+ Add slot', exact=True).click()
    dialog.get_by_label('From', exact=True).fill('06:00')
    dialog.get_by_label('To', exact=True).fill('09:00')
    dialog.get_by_label('Mode', exact=True).select_option('charge')
    dialog.get_by_role('button', name='Update draft slot', exact=True).click()
    handle = dialog.get_by_role('button', name='Monday · Resize end', exact=True)
    handle.focus()
    page.keyboard.press('ArrowDown')
    expect(dialog.get_by_role('status')).to_contain_text('Slot resized in draft')
    expect(dialog.locator('.week-edit[data-day="0"][data-start="06:00"]')).to_have_attribute('aria-label', 'Monday 06:00–09:15 · Edit draft')
    page.set_viewport_size({'width': 430, 'height': 932})
    dialog.locator('.week-edit[data-day="0"][data-start="06:00"]').click()
    dialog.get_by_role('button', name='Choose a cell to move this slot', exact=True).click()
    dialog.get_by_role('button', name='Save draft', exact=True).click()
    expect(dialog.get_by_role('alert')).to_contain_text('Choose a destination')
    dialog.locator('.week-edit[data-day="1"][data-start="06:00"]').click()
    expect(dialog.get_by_role('status')).to_contain_text('Slot moved in draft')
    dialog.get_by_role('button', name='Undo', exact=True).click()
    expect(dialog.locator('.week-edit[data-day="0"] .week-slot')).to_have_count(1)
    with page.expect_response(lambda r: r.url.endswith('/api/schedules') and r.request.method == 'POST') as saved:
        dialog.get_by_role('button', name='Save draft', exact=True).click()
    assert saved.value.status == 201
    slot = saved.value.request.post_data_json['slots'][0]
    assert (slot['day'], slot['start'], slot['end']) == (0, '06:00', '09:15')
    assert page.request.get(origin + '/api/commands').json() == []


def test_schedule_pointer_resize_cancel_and_overlap_preserve_draft(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    page.goto(origin + '/#operations/main/schedules')
    page.get_by_role('button', name='+ Create draft', exact=True).click()
    dialog = page.get_by_role('dialog')
    dialog.get_by_label('Name', exact=True).fill('ISOLATED pointer resize')
    for start, end in [('06:00', '09:00'), ('10:00', '12:00')]:
        dialog.get_by_role('button', name='+ Add slot', exact=True).click()
        dialog.get_by_label('From', exact=True).fill(start)
        dialog.get_by_label('To', exact=True).fill(end)
        dialog.get_by_label('Mode', exact=True).select_option('charge')
        dialog.get_by_role('button', name='Update draft slot', exact=True).click()

    def resize_to(start, fraction, cancel=False):
        handle = dialog.get_by_role('button', name='Monday · Resize end', exact=True).first
        handle.scroll_into_view_if_needed()
        source = handle.bounding_box()
        cell = dialog.locator(f'td[data-day="0"][data-start="{start}"]')
        target = cell.bounding_box()
        page.mouse.move(source['x'] + source['width'] / 2, source['y'] + source['height'] / 2)
        page.mouse.down()
        page.mouse.move(target['x'] + target['width'] / 2, target['y'] + target['height'] * fraction, steps=8)
        if cancel:
            page.keyboard.press('Escape')
        elif start == '10:00':
            expect(handle).to_have_attribute('data-preview', '11:00')
        page.mouse.up()

    resize_to('09:00', 0.5, cancel=True)
    expect(dialog).to_be_visible()
    expect(dialog.locator('td[data-day="0"][data-start="09:00"] .week-slot')).to_have_count(0)
    resize_to('09:00', 0.5)
    expect(dialog.get_by_role('status')).to_contain_text('Slot resized in draft')
    expect(dialog.locator('.week-edit[data-day="0"][data-start="06:00"]')).to_have_attribute('aria-label', 'Monday 06:00–09:30 · Edit draft')
    resize_to('10:00', 0.5)
    expect(dialog.get_by_role('status')).to_contain_text('Time slots overlap')
    expect(dialog.locator('.week-edit[data-day="0"][data-start="06:00"]')).to_have_attribute('aria-label', 'Monday 06:00–09:30 · Edit draft')
    with page.expect_response(lambda r: r.url.endswith('/api/schedules') and r.request.method == 'POST') as saved:
        dialog.get_by_role('button', name='Save draft', exact=True).click()
    assert saved.value.status == 201
    slots = saved.value.request.post_data_json['slots']
    assert [(s['start'], s['end']) for s in slots] == [('06:00', '09:30'), ('10:00', '12:00')]
    assert page.request.get(origin + '/api/commands').json() == []
