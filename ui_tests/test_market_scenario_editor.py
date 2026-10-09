from conftest import login
from playwright.sync_api import expect


def open_editor(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    page.goto(origin + '/#reports/analytics')
    page.get_by_text('Engineering tools · market scenarios', exact=True).click()
    return page, origin, page.locator('.market-scenario-editor')


def add_scenario(editor, name='SYNTHETIC scenario', hour='12', price='-10', clearing='0'):
    editor.get_by_role('button', name='Add scenario', exact=True).click()
    row=editor.locator('.market-bid-row').last
    row.get_by_label('Scenario name', exact=True).fill(name)
    row.get_by_label('Market', exact=True).select_option('day_ahead')
    row.get_by_label('Direction', exact=True).select_option('sell_discharge')
    row.get_by_label('Delivery hour', exact=True).select_option(hour)
    row.get_by_label('Quantity (MW)', exact=True).fill('1')
    row.get_by_label('Bid price (EUR/MWh)', exact=True).fill(price)
    row.get_by_label('Assumed market price (EUR/MWh)', exact=True).fill(clearing)
    return row


def test_market_blank_conflicts_capacity_and_zero_prices(browser_page):
    page, origin, editor=open_editor(browser_page)
    sent=[]
    page.on('request',lambda request:sent.append(request) if request.url.endswith('/market-trader/submit-and-clear') else None)
    calculate=editor.get_by_role('button',name='Calculate supplied market scenario',exact=True)
    expect(editor.locator('textarea')).to_have_count(0)
    expect(editor.locator('.market-bid-row')).to_have_count(0)
    calculate.click()
    expect(editor.get_by_role('alert')).to_contain_text('Enter a valid number')
    editor.get_by_label('Available capacity (MW)',exact=True).fill('2')
    calculate.click()
    expect(editor.get_by_role('alert')).to_contain_text('Add at least one')
    first=add_scenario(editor)
    second=add_scenario(editor)
    calculate.click()
    expect(editor.get_by_role('alert')).to_contain_text('unique')
    second.get_by_label('Scenario name',exact=True).fill('SYNTHETIC second')
    second.get_by_label('Assumed market price (EUR/MWh)',exact=True).fill('1')
    calculate.click()
    expect(editor.get_by_role('alert')).to_contain_text('same assumed market price')
    second.get_by_label('Assumed market price (EUR/MWh)',exact=True).fill('0')
    second.get_by_label('Quantity (MW)',exact=True).fill('2')
    calculate.click()
    expect(editor.get_by_role('alert')).to_contain_text('exceed available capacity')
    assert sent == []
    second.get_by_role('button',name='Remove scenario',exact=True).click()
    with page.expect_response('**/api/market-trader/submit-and-clear') as response:
        calculate.click()
    assert response.value.status==200
    payload=response.value.request.post_data_json
    assert payload['clearing_prices']=={'12':0}
    assert payload['bids'][0]['price_eur_per_mwh']==-10
    assert response.value.json()['submitted_to_market'] is False
    expect(editor.locator('.metric-tile')).to_have_count(4)
    first.get_by_label('Bid price (EUR/MWh)',exact=True).fill('20')
    expect(editor.locator('.metric-tile')).to_have_count(0)
    expect(editor.get_by_role('status')).to_contain_text('Inputs changed')
    page.route('**/api/market-trader/submit-and-clear',lambda route:route.fulfill(status=422,json={'detail':'SYNTHETIC rejected request'}))
    calculate.click()
    expect(editor.get_by_role('alert')).to_contain_text('SYNTHETIC rejected request')
    expect(first.get_by_label('Bid price (EUR/MWh)',exact=True)).to_have_value('20')
    expect(calculate).to_be_enabled()
    assert page.request.get(origin+'/api/commands').json()==[]


def test_market_responsive_translated_fields_and_chart_gaps(browser_page):
    page, origin, editor=open_editor(browser_page)
    editor.get_by_role('button',name='Add scenario',exact=True).click()
    for item in editor.locator('.market-bid-row input,.market-bid-row select').all():
        expect(item).to_have_value('')
    for width in (1600,1024,430):
        page.set_viewport_size({'width':width,'height':1000})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        assert editor.evaluate('e=>e.scrollWidth<=e.clientWidth+1')
    result=page.evaluate("""async()=>{
      const {dailyEnergyChart}=await import('/static/ui-visuals.js');
      const options={lineKeys:['pv_kwh']};
      const rows=[{date:'2026-10-01',pv_kwh:0},{date:'2026-10-02',pv_kwh:null},{date:'2026-10-03',pv_kwh:10}];
      const gap=dailyEnergyChart(rows,options),continuous=dailyEnergyChart([rows[0],{...rows[1],pv_kwh:2},rows[2]],options);
      return {gap:gap.querySelectorAll('.energy-line').length,points:gap.querySelectorAll('.energy-point').length,
        continuous:continuous.querySelectorAll('.energy-line').length};
    }""")
    assert result=={'gap':0,'points':2,'continuous':1}
    page.get_by_label('Language / Ngôn ngữ',exact=True).select_option('vi')
    page.get_by_text('Công cụ kỹ sư · kịch bản thị trường',exact=True).click()
    expect(page.get_by_label('Tổng công suất tham gia (MW)',exact=True)).to_have_value('')
    assert 'JSON' not in editor.inner_text()
