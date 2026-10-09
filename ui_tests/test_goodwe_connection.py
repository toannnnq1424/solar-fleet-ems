"""Local UI contracts; intercepted credentials are synthetic and never sent to GoodWe."""

from conftest import login
from playwright.sync_api import expect


def open_form(page, origin):
    page.goto(origin + '/#settings/main/connections')
    page.get_by_role('button', name='Connection & testing guide', exact=True).click()
    dialog = page.get_by_role('dialog')
    dialog.get_by_role('button', name='View GoodWe requirements', exact=True).click()
    dialog.get_by_label('Your GoodWe app', exact=True).select_option('sems_plus')
    dialog.get_by_role('button', name='I have the connection details', exact=True).click()
    return dialog


def test_semsplus_form_consent_server_password_clear_and_no_fake_inventory(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    dialog = open_form(page, origin)
    expect(dialog.get_by_label('Account server', exact=True)).to_have_value('')
    expect(dialog.get_by_role('checkbox')).not_to_be_checked()
    expect(dialog.locator('input[type="password"]')).to_have_count(1)
    expect(dialog.get_by_label('SEMS+ email', exact=True)).to_have_value('')
    expect(dialog.get_by_label('SEMS+ password', exact=True)).to_have_value('')
    expect(dialog.get_by_label('SEMS+ password', exact=True)).to_have_attribute('autocomplete', 'section-goodwe new-password')
    expect(dialog).to_contain_text('No App ID, App Secret or manual plant ID is required')
    for width in (1600, 1024, 430):
        page.set_viewport_size({'width': width, 'height': 1000})
        assert dialog.evaluate('el => el.scrollWidth <= el.clientWidth + 1')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    calls = []

    def respond(route):
        calls.append(route.request.post_data_json)
        route.fulfill(status=400 if len(calls) == 1 else 201, json=(
            {'detail': 'goodwe_authentication_failed'} if len(calls) == 1 else
            {'id': 'SYNTHETIC-only', 'state': 'AUTHENTICATED', 'inventory_synced': False, 'write_enabled': False}))

    page.route('**/api/connections/goodwe', respond)
    dialog.get_by_label('Account server', exact=True).select_option('hk')
    dialog.get_by_label('SEMS+ email', exact=True).fill('synthetic@example.invalid')
    dialog.get_by_label('SEMS+ password', exact=True).fill('SYNTHETIC-password')
    dialog.get_by_role('button', name='Authenticate & link read-only', exact=True).click()
    assert not calls  # unchecked consent blocks native form submission
    dialog.get_by_role('checkbox').check()
    dialog.get_by_role('button', name='Authenticate & link read-only', exact=True).click()
    expect(dialog.get_by_label('SEMS+ password', exact=True)).to_have_value('')
    expect(dialog).to_contain_text('Not linked. Check the SEMS+ server')
    expect(dialog.get_by_label('Account server', exact=True)).to_be_enabled()
    dialog.get_by_label('SEMS+ password', exact=True).fill('SYNTHETIC-password')
    dialog.get_by_role('button', name='Authenticate & link read-only', exact=True).click()
    expect(dialog).not_to_be_visible()
    assert len(calls) == 2 and all(c['vendor_terms_accepted'] for c in calls)
    assert all(c['region'] == 'hk' and 'app_secret' not in c and 'plant_ids' not in c for c in calls)
    assert page.request.get(origin + '/api/commands').json() == []


def test_semsplus_inflight_freezes_identity_and_no_double_submit(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    dialog = open_form(page, origin)
    calls = []
    page.route('**/api/connections/goodwe', lambda route: calls.append(route))
    dialog.get_by_label('Account server', exact=True).select_option('hk')
    dialog.get_by_label('SEMS+ email', exact=True).fill('synthetic@example.invalid')
    dialog.get_by_label('SEMS+ password', exact=True).fill('SYNTHETIC-password')
    dialog.get_by_role('checkbox').check()
    dialog.get_by_role('button', name='Authenticate & link read-only', exact=True).click()
    expect(dialog.get_by_label('Account server', exact=True)).to_be_disabled()
    expect(dialog.get_by_label('SEMS+ email', exact=True)).to_be_disabled()
    expect(dialog.get_by_role('button', name='Authenticate & link read-only', exact=True)).to_be_disabled()
    assert len(calls) == 1
    calls[0].fulfill(status=429, json={'detail': 'goodwe_login_rate_limited'})
    expect(dialog.get_by_label('SEMS+ password', exact=True)).to_have_value('')
    expect(dialog.get_by_label('Account server', exact=True)).to_be_enabled()
