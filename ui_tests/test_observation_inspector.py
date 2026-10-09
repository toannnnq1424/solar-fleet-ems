"""Synthetic history belongs only in isolated browser response fixtures."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from conftest import login
from playwright.sync_api import expect


def test_history_comparison_quality_time_and_source_identity(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    now = datetime.now(UTC)

    def sample(minutes, value, **extra):
        return {'device_id': 'SIM-DEVICE-0', 'metric': 'grid_voltage_v', 'unit': 'V',
                'value': value, 'source_timestamp': (now - timedelta(minutes=minutes)).isoformat(),
                'source': 'VENDOR_CLOUD', 'binding_id': 'TEST-A', 'quality': 'GOOD', **extra}

    rows = [sample(2880, 5), sample(20, 0), sample(10, 10),
            sample(5, 99, quality='UNVERIFIED'), sample(3, 999, quality='INVALID'),
            sample(-60, 999), sample(1, '123'), sample(1, 123, quality=None),
            sample(8, 20, binding_id='TEST-B'),
            sample(8, 30, device_id='SIM-DEVICE-OTHER'),
            sample(8, 2, metric='TEST.current', unit='A')]
    page.route('**/api/devices/*/history', lambda route: route.fulfill(json={'samples': rows}))
    page.goto(origin + '/#devices/main')
    page.get_by_role('button', name='Detail & native readings', exact=True).first.click()
    history = page.locator('.device-history')
    chart = history.locator('.measurement-plot-scroll svg')
    expect(history.get_by_label('Observed metric', exact=True).locator('option')).to_have_count(5)
    expect(chart.locator('circle')).to_have_count(3)
    expect(history.locator('.observation-summary')).to_contain_text('0 V')
    comparison = history.get_by_label('Compare same-unit channel', exact=True)
    expect(comparison.locator('option')).to_have_count(3)
    comparison.select_option('1')
    expect(chart.locator('.comparison-point')).to_have_count(1)
    history.get_by_label('Time range', exact=True).select_option('1')
    expect(chart.locator('circle')).to_have_count(3)
    history.get_by_label('Data quality', exact=True).select_option('native')
    expect(chart.locator('circle')).to_have_count(4)
    expect(chart.locator('.unverified-point')).to_have_count(1)
    expect(history.get_by_role('status')).to_contain_text('not control inputs')
    history.locator('.measurement-table > summary').click()
    expect(history.locator('.measurement-table')).to_contain_text('TEST-B')
    expect(history.locator('.measurement-table')).not_to_contain_text('999')
    output = Path('work/qa-audit')
    output.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(output / 'observation-inspector-desktop.png'), full_page=True)
    for width in (1024, 430):
        page.set_viewport_size({'width': width, 'height': 932})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    history.get_by_label('Observed metric', exact=True).select_option('3')
    expect(comparison).to_be_disabled()
    expect(chart.locator('.comparison-point')).to_have_count(0)
    assert page.request.get(origin + '/api/commands').json() == []


def test_single_chart_rejects_coercion_and_requires_explicit_native_opt_in(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    result = page.evaluate('''async () => {
      const {measurementChart}=await import('/static/measurement-chart.js');
      const s=(value,unit='V',quality='GOOD')=>({value,unit,quality,source_timestamp:new Date().toISOString()});
      const rows=[s(0),s(false),s('1'),s(null),s(3,'A'),s(5,'V','INVALID'),s(6,'V','UNVERIFIED')];
      return {normal:measurementChart(rows,'Test','V').querySelectorAll('circle').length,
        native:measurementChart(rows,'Test','V',{allowUnverified:true}).querySelectorAll('.unverified-point').length,
        comparison:measurementChart(rows,'Test','V',{comparison:[s(1),s(2,'A')]}).querySelectorAll('.comparison-point').length};
    }''')
    assert result == {'normal': 1, 'native': 1, 'comparison': 1}


def test_specialist_panels_require_explicit_channels_and_keep_unit_boundaries(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    stamp = datetime.now(UTC).isoformat()
    rows = [
        {'device_id': 'SIM-DEVICE-0', 'binding_id': 'TEST-A', 'source': 'SIMULATOR',
         'source_timestamp': stamp, 'quality': 'GOOD', 'metric': metric, 'unit': unit, 'value': value}
        for metric, unit, value in [('TEST_PV_OR_AC_UNKNOWN', 'V', 220), ('battery_charge_w', 'W', 0),
                                    ('soc_pct', '%', 25), ('TEST_LATENCY', 'ms', 12)]
    ]
    page.route('**/api/devices/*/history', lambda route: route.fulfill(json={'samples': rows}))
    page.goto(origin + '/#devices/main')
    page.get_by_role('button', name='Detail & native readings', exact=True).first.click()
    panels = page.locator('.device-mini-charts')
    expect(panels.locator('circle')).to_have_count(0)
    ac = panels.locator('[data-observation-panel="ac"]')
    ac.get_by_label('AC electricity · phase channels · Primary channel', exact=True).select_option('0')
    expect(ac.locator('circle')).to_have_count(1)
    expect(ac).not_to_contain_text('Phase A ·')
    ac.get_by_label('AC electricity · phase channels · Unit', exact=True).select_option('A')
    expect(ac.locator('circle')).to_have_count(0)
    battery = panels.locator('[data-observation-panel="battery"]')
    battery.get_by_label('Battery · charge, discharge and level · Primary channel', exact=True).select_option('1')
    expect(battery.locator('circle')).to_have_count(1)
    battery.get_by_label('Battery · charge, discharge and level · Unit', exact=True).select_option('%')
    expect(battery.locator('circle')).to_have_count(0)
    latency = panels.locator('[data-observation-panel="latency"]')
    latency.get_by_label('Communication latency · Primary channel', exact=True).select_option('3')
    expect(latency.locator('circle')).to_have_count(1)
    page.set_viewport_size({'width': 430, 'height': 932})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    assert page.request.get(origin + '/api/commands').json() == []
