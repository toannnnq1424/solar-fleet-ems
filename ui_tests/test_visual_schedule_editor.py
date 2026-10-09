"""Visual draft editing and report interactions, isolated fixtures only."""

from conftest import login
from playwright.sync_api import expect


def open_draft(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    page.goto(origin + '/#operations/main/schedules')
    page.get_by_role('button', name='+ Create draft', exact=True).click()
    dialog = page.get_by_role('dialog')
    dialog.get_by_label('Name', exact=True).fill('SYNTHETIC visual draft')
    return page, origin, dialog


def add_slot(dialog, day='0', start='06:00', end='09:00', mode='charge'):
    dialog.get_by_role('button', name='+ Add slot', exact=True).click()
    dialog.get_by_label('Day', exact=True).select_option(day)
    dialog.get_by_label('From', exact=True).fill(start)
    dialog.get_by_label('To', exact=True).fill(end)
    dialog.get_by_label('Mode', exact=True).select_option(mode)
    dialog.get_by_label('Target battery level (%)', exact=True).fill('75')
    dialog.get_by_role('button', name='Update draft slot', exact=True).click()


def test_copy_move_undo_save_and_reload_are_only_draft_changes(browser_page):
    page, origin, dialog = open_draft(browser_page)
    expect(dialog.locator('.week-slot')).to_have_count(0)
    add_slot(dialog)
    expect(dialog.locator('.week-slot')).to_have_count(1)
    assert page.request.get(origin + '/api/operations').json()['schedule'] == []
    dialog.locator('.schedule-copy-panel summary').click()
    dialog.get_by_label('Tuesday', exact=True).check()
    dialog.get_by_role('button', name='Copy selected day', exact=True).click()
    expect(dialog.locator('.week-slot')).to_have_count(2)
    dialog.get_by_role('button', name='Undo', exact=True).click()
    expect(dialog.locator('.week-slot')).to_have_count(1)
    dialog.get_by_role('button', name='Copy selected day', exact=True).click()
    source = dialog.locator('.week-edit[data-day="1"][data-start="06:00"]')
    target = dialog.locator('.week-edit[data-day="2"][data-start="06:00"]')
    source.drag_to(target)
    expect(dialog.get_by_role('status')).to_contain_text('Slot moved in draft')
    expect(dialog.locator('.week-edit[data-day="1"] .week-slot')).to_have_count(0)
    with page.expect_response(lambda r: r.url.endswith('/api/schedules') and r.request.method == 'POST') as saved:
        dialog.get_by_role('button', name='Save draft', exact=True).click()
    assert saved.value.status == 201
    assert [s['day'] for s in saved.value.json()['slots']] == [0, 2]
    assert saved.value.json()['slots'][0]['target_soc'] == 75
    page.reload()
    expect(page.get_by_role('heading', name='SYNTHETIC visual draft', exact=True)).to_be_visible()
    page.get_by_role('button', name='Edit draft', exact=True).click()
    dialog.locator('.week-edit[data-day="0"][data-start="06:00"]').click()
    dialog.get_by_label('Target battery level (%)', exact=True).fill('80')
    dialog.get_by_role('button', name='Update draft slot', exact=True).click()
    with page.expect_response(lambda r: '/schedules/' in r.url and r.url.endswith('/edit')) as edited:
        dialog.get_by_role('button', name='Save draft', exact=True).click()
    assert edited.value.status == 200
    assert page.request.get(origin + '/api/operations').json()['schedule'][0]['slots'][0]['target_soc'] == 80
    assert page.request.get(origin + '/api/commands').json() == []


def test_copy_collision_requires_explicit_replace_and_can_undo(browser_page):
    page, origin, dialog = open_draft(browser_page)
    add_slot(dialog)
    add_slot(dialog, day='1', start='07:00', end='10:00', mode='hold')
    dialog.locator('.schedule-copy-panel summary').click()
    dialog.get_by_label('Tuesday', exact=True).check()
    dialog.get_by_role('button', name='Copy selected day', exact=True).click()
    expect(dialog.get_by_role('status')).to_contain_text('Time slots overlap')
    expect(dialog.locator('.week-slot.mode-hold')).not_to_have_count(0)
    dialog.get_by_label('Replace all slots on the selected target days', exact=True).check()
    dialog.get_by_role('button', name='Copy selected day', exact=True).click()
    expect(dialog.locator('.week-slot.mode-hold')).to_have_count(0)
    expect(dialog.locator('.week-slot.mode-charge')).to_have_count(2)
    dialog.get_by_role('button', name='Undo', exact=True).click()
    expect(dialog.locator('.week-slot.mode-hold')).not_to_have_count(0)
    assert page.request.get(origin + '/api/operations').json()['schedule'] == []


def test_unapplied_slot_and_conflict_do_not_lose_draft(browser_page):
    page, origin, dialog = open_draft(browser_page)
    dialog.get_by_role('button', name='+ Add slot', exact=True).click()
    expect(dialog.get_by_label('From', exact=True)).to_have_value('')
    expect(dialog.get_by_label('Mode', exact=True)).to_have_value('')
    dialog.get_by_role('button', name='Save draft', exact=True).click()
    expect(dialog.get_by_role('alert')).to_contain_text('Update or cancel')
    dialog.get_by_role('button', name='Cancel slot edit', exact=True).click()
    add_slot(dialog)
    dialog.get_by_role('button', name='Save draft', exact=True).click()
    expect(dialog).not_to_be_visible()
    page.get_by_role('button', name='Edit draft', exact=True).click()
    page.route('**/api/schedules/*/edit', lambda route: route.fulfill(status=409, json={'detail':'revision_conflict'}))
    dialog.get_by_label('Name', exact=True).fill('Keep unsaved name')
    dialog.get_by_role('button', name='Save draft', exact=True).click()
    expect(dialog.get_by_role('alert')).not_to_be_empty()
    expect(dialog.get_by_label('Name', exact=True)).to_have_value('Keep unsaved name')
    expect(dialog.locator('.week-slot')).to_have_count(1)
    dialog.get_by_role('button', name='Save draft', exact=True).click()
    expect(dialog.get_by_role('alert')).to_contain_text('Close and reopen')
    assert page.request.get(origin + '/api/commands').json() == []


def test_editor_reflows_keyboard_cells_and_keeps_viewer_read_only(browser_page):
    page, origin, dialog = open_draft(browser_page)
    for width in (1600, 1024, 430):
        page.set_viewport_size({'width':width,'height':1000})
        expect(dialog.locator('.schedule-editor-matrix')).to_be_visible()
        assert dialog.evaluate('d=>d.scrollWidth<=d.clientWidth+1')
        cell=dialog.locator('.week-edit').first
        cell.focus()
        page.keyboard.press('Enter')
        expect(dialog.get_by_label('From',exact=True)).to_have_value('00:00')
        expect(dialog.get_by_label('Mode',exact=True)).to_have_value('')
        dialog.get_by_role('button',name='Cancel slot edit',exact=True).click()
    page.keyboard.press('Escape')
    page.get_by_role('button',name='Account menu',exact=True).click()
    page.get_by_role('button',name='Sign out',exact=True).click()
    login(page,origin,'ui-viewer')
    page.goto(origin+'/#operations/main/schedules')
    expect(page.locator('.schedule-week-grid')).to_be_visible()
    expect(page.locator('.week-edit')).to_have_count(0)
    expect(page.get_by_role('button',name='+ Create draft',exact=True)).to_have_count(0)


def test_report_panels_use_real_channels_and_legend_toggle(browser_page):
    page, origin = browser_page
    login(page,origin,'ui-admin')
    page.route('**/api/reports/analytics/timeseries?*',lambda route:route.fulfill(json={
        'main_chart':[{'date':'2026-10-03','pv_kwh':10,'load_kwh':5,'self_consumption_kwh':None,'grid_export_kwh':0}],
        'battery_bars':[{'date':'2026-10-03','cycles':None}],
        'grid_bars':[{'date':'2026-10-03','import_kwh':2,'export_kwh':0}],
        'incident_bars':[{'date':'2026-10-03','count':3}],
        'self_consumption_donut':{'rate_pct':None,'self_consumption_kwh':None},
    }))
    page.goto(origin+'/#reports/analytics')
    expect(page.locator('.report-mini-grid > .card')).to_have_count(4)
    plot=page.locator('.report-main-plot')
    expect(plot.locator('.energy-bar,.energy-point')).to_have_count(3)
    expect(page.get_by_role('img',name='Daily battery cycles',exact=True).locator('rect')).to_have_count(0)
    expect(page.get_by_role('img',name='Grid energy exchange',exact=True).locator('.energy-bar')).to_have_count(2)
    page.locator('.report-chart-toggles').get_by_role('button',name='Generation',exact=True).click()
    expect(plot.locator('.energy-bar,.energy-point')).to_have_count(2)
    plot.locator('.energy-point').first.focus()
    expect(page.locator('.chart-reading')).to_contain_text('5 kWh')
    page.locator('.report-data-table summary').click()
    expect(page.locator('.report-data-table tbody')).to_contain_text('10')
    for width in (1024,430):
        page.set_viewport_size({'width':width,'height':1000})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')


def test_draft_validator_rejects_invalid_boundaries_and_values(browser_page):
    page, origin = browser_page
    login(page,origin,'ui-admin')
    result=page.evaluate("""async()=>{
      const {validateDraftSlots}=await import('/static/schedule-editor.js');
      const slot={day:0,start:'06:00',end:'09:00',mode:'charge',target_soc:null,power_kw:null};
      return [[],[{...slot,start:'24:00'}],[{...slot,end:'25:00'}],[{...slot,target_soc:30.5}],
        [{...slot,power_kw:-1}],Array(169).fill(slot),[slot,{...slot,start:'08:00'}]].map(slots=>{
          try{validateDraftSlots(slots);return false;}catch{return true;}
        });
    }""")
    assert result == [True]*7
