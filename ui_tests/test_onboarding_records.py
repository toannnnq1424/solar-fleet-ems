"""Onboarding renders actual records, not a fictitious electrical discovery graph."""
import re

from conftest import login
from playwright.sync_api import expect


def test_onboarding_exposes_platforms_actual_details_and_responsive_frames(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    page.goto(origin + '/#settings/main/device_onboarding')
    expect(page.get_by_role('button', name='Bluesun', exact=True)).to_be_visible()
    expect(page.get_by_role('button', name='Eybond / SmartESS', exact=True)).to_be_visible()
    inspector = page.locator('.onboarding-inspector')
    expect(inspector).to_contain_text('Select equipment to inspect')
    page.get_by_role('button', name='Inspect equipment', exact=True).first.click()
    expect(inspector).to_contain_text('SIMULATOR Deye')
    expect(inspector).to_contain_text('TEST')
    expect(inspector).to_contain_text('not a DC/AC wiring diagram')
    expect(inspector).not_to_contain_text('Successfully connected')
    expect(page.locator('.onboarding-workspace')).not_to_contain_text(re.compile(r'\b(?:null|undefined)\b'))
    sources = inspector.locator('details')
    expect(sources).not_to_have_attribute('open', '')
    sources.locator('summary').click()
    expect(sources).to_contain_text('Vendor cloud')
    sources.locator('summary').click()
    for width in (1600, 1024, 430):
        page.set_viewport_size({'width': width, 'height': 932})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.get_by_label('Find equipment', exact=True).fill('SIM-DEVICE-1')
    expect(page.get_by_role('button', name='Inspect equipment', exact=True)).to_have_count(1)
    expect(inspector).to_contain_text('Select equipment to inspect')
    assert page.request.get(origin + '/api/commands').json() == []


def test_onboarding_oem_brand_uses_declared_record_not_transport_name(browser_page):
    page, origin = browser_page

    def with_declared_brand(route):
        response = route.fetch()
        data = response.json()
        device = next(d for d in data['devices'] if d['id'] == 'SIM-DEVICE-2')
        device['metadata']['declared_equipment_brand'] = 'Bluesun'
        route.fulfill(response=response, json=data)

    page.route('**/api/fleet', with_declared_brand)
    login(page, origin, 'ui-admin')
    page.goto(origin + '/#settings/main/device_onboarding')
    page.get_by_role('button', name='Bluesun', exact=True).click()
    expect(page.get_by_role('button', name='Inspect equipment', exact=True)).to_have_count(1)
    expect(page.locator('.onboarding-layout')).to_contain_text('SIMULATOR SOLARMAN')
    page.get_by_role('button', name='Eybond / SmartESS', exact=True).click()
    expect(page.locator('.onboarding-layout')).to_contain_text('No matching equipment')
    assert page.request.get(origin + '/api/commands').json() == []


def test_onboarding_late_details_cannot_replace_filtered_empty_state(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    page.goto(origin + '/#settings/main/device_onboarding')
    pending = []
    page.route('**/api/devices/SIM-DEVICE-0', lambda route: pending.append(route))
    page.get_by_role('button', name='Inspect equipment', exact=True).first.click()
    expect(page.locator('.onboarding-inspector')).to_contain_text('Reading stored details')
    page.get_by_role('button', name='Huawei', exact=True).click()
    assert len(pending) == 1
    pending[0].fulfill(json={'device': {'name': 'LATE_RESPONSE', 'identity': {}}})
    expect(page.locator('.onboarding-inspector')).to_contain_text('Select equipment to inspect')
    expect(page.locator('.onboarding-inspector')).not_to_contain_text('LATE_RESPONSE')
    assert page.request.get(origin + '/api/commands').json() == []
