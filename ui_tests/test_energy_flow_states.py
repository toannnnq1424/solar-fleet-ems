"""Power directions are tested on isolated fixtures, not customer observations."""

from conftest import login


def test_flow_state_never_animates_unknown_clock_or_missing_values(browser_page):
    page, origin = browser_page
    login(page, origin, 'ui-admin')
    rows = page.evaluate('''async () => {
      const {flowState} = await import('/static/energy-flow.js');
      const now = Date.parse('2026-01-01T00:00:00Z');
      const cases = [
        [2800, 'GOOD', '2026-01-01T00:01:00Z'],
        [-2800, 'GOOD', '2026-01-01T00:01:00Z'],
        [0, 'GOOD', '2026-01-01T00:01:00Z'],
        [null, 'GOOD', '2026-01-01T00:01:00Z'],
        [2800, 'GOOD', '2025-12-31T23:59:00Z'],
        [2800, 'GOOD', null],
        [2800, 'VENDOR_REPORTED', null],
        [2800, 'UNKNOWN', '2026-01-01T00:01:00Z'],
      ];
      return cases.map(([battery_w, quality, valid_until]) => flowState('battery_w', {
        battery_w, channels:{battery_w:{quality, valid_until}}
      }, now));
    }''')
    assert rows[0]['active'] and not rows[0]['reverse']
    assert rows[1]['active'] and rows[1]['reverse']
    assert rows[2]['value'] == 0 and not rows[2]['active']
    assert all(not row['active'] for row in rows[3:])
    assert all(rows[i]['value'] is None for i in (3, 4, 5, 7))
    assert rows[6]['value'] == 2800 and rows[6]['status'] == 'VENDOR_REPORTED'
    assert page.request.get(origin + '/api/commands').json() == []
