"""Empty/real-response UI contracts; all identities/measurements are isolated tests."""
from conftest import login
from playwright.sync_api import expect


def test_engineering_fields_no_seed_or_json_and_clear_stale_results(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    for route in ('operations/main/rules', 'operations/main/control'):
        page.goto(origin + '/#' + route)
        page.locator('.engineering-tools > summary').click()
        expect(page.locator('.engineering-tools textarea')).to_have_count(0)
        assert page.locator('.calculation-fields input').evaluate_all('els => els.every(el => el.value === "")')
        assert page.locator('.calculation-fields select').evaluate_all('els => els.every(el => el.value === "")')
        expect(page.locator('.engineering-tools')).not_to_contain_text('Preset')
        expect(page.locator('.engineering-tools')).not_to_contain_text('Parameter schema')
        for width in (1600, 1024, 430):
            page.set_viewport_size({'width': width, 'height': 1000})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.goto(origin + '/#operations/main/rules')
    page.locator('.engineering-tools > summary').click()
    panel = page.locator('[data-calculator="/thermal/heat-pump-cop"]')
    panel.get_by_role('button', name='Calculate supplied inputs', exact=True).click()
    expect(panel).to_contain_text('Check field:')
    panel.get_by_label('Ambient temperature (°C)', exact=True).fill('7')
    expect(panel.locator('.calculation-result')).to_be_empty()
    panel.get_by_role('button', name='Clear', exact=True).click()
    expect(panel.get_by_label('Ambient temperature (°C)', exact=True)).to_have_value('')
    page.get_by_role('button', name='Add entry', exact=True).click()
    expect(page.locator('.calculation-entry')).to_have_count(1)
    page.get_by_role('button', name='Remove entry', exact=True).click()
    expect(page.locator('.calculation-entry')).to_have_count(0)
    assert page.request.get(origin + '/api/commands').json() == []


def test_multichannel_chart_keeps_zero_rejects_invalid_and_breaks_gaps(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    result = page.evaluate('''async () => {
      const {multiMeasurementChart}=await import('/static/measurement-chart.js');
      const sample=(time,value,unit='W',extra={})=>({source_timestamp:'2026-10-04T00:'+time+':00Z',value,unit,device_id:'TEST',binding_id:'TEST',source:'VENDOR_CLOUD',...extra});
      const plot=multiMeasurementChart([{label:'Test PV',unit:'W',color:0,samples:[
        sample('00',0),sample('01',100),sample('02',null),sample('03',200),sample('20',300),sample('21',400,'kW'),sample('22',500,'W',{quality:'BAD'})]},
        {label:'SOC',unit:'%',color:6,samples:[sample('00',0,'%'),sample('01',101,'%')]}]);
      return {points:plot.querySelectorAll('circle').length,lines:plot.querySelectorAll('.measurement-segment').length,
        empty:multiMeasurementChart([]).querySelectorAll('circle').length,
        ticks:plot.querySelectorAll('.measurement-time-tick').length,
        tickLines:plot.querySelectorAll('.measurement-time-tick tspan').length,
        singleTicks:multiMeasurementChart([{label:'One observation',unit:'W',color:0,samples:[sample('00',0)]}]).querySelectorAll('.measurement-time-tick').length,
        labels:[...plot.querySelectorAll('title')].map(t=>t.textContent)};
    }''')
    assert result['points'] == 5
    assert result['lines'] == 1
    assert result['empty'] == 0
    assert result['ticks'] == 5
    assert result['tickLines'] == 10
    assert result['singleTicks'] == 1
    assert any('0 W' in text for text in result['labels'])


def test_multichannel_and_network_empty_layouts_remain_honest(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    page.get_by_label('Plant scope', exact=True).select_option('SIM-SITE-0')
    page.route('**/telemetry-timeseries?**', lambda route: route.fulfill(json={
        'samples': [], 'total_points': 0, 'reason': 'AMBIGUOUS_SOURCE'}))
    page.goto(origin + '/#overview/main/data')
    expect(page.locator('.measurement-reference-layout')).to_be_visible()
    expect(page.locator('.measurement-selectors input')).to_have_count(7)
    expect(page.locator('.multi-measurement-chart circle')).to_have_count(0)
    expect(page.locator('.measurement-channel-summary').first).to_contain_text('Resolve ambiguous sources')
    page.get_by_label('Battery level', exact=True).check()
    expect(page.locator('.measurement-channel-summary')).to_have_count(3)
    page.set_viewport_size({'width': 430, 'height': 932})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    assert page.locator('.measurement-plot-scroll').evaluate('el => el.scrollWidth > el.clientWidth')
    assert page.locator('.measurement-reference-layout .card > h2').first.evaluate('el => parseFloat(getComputedStyle(el).fontSize) >= 16')
    page.goto(origin + '/#overview/main/network')
    expect(page.locator('.network-reference')).to_contain_text('Unknown')
    expect(page.locator('.network-reference')).not_to_contain_text('0 ms')
    expect(page.locator('.network-reference')).to_contain_text('RS485 bus')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
