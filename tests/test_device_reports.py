"""Per-inverter reports: synthetic-only identifiers and transport."""

import httpx
import pytest
from test_goodwe_connection import BODY, transport
from test_goodwe_plus import CONFIG, CREDENTIALS, envelope, reply
from test_workspaces import local as local
from test_workspaces import login

from solar_fleet.adapters.goodwe_plus import GoodWePlus, device_report


def point(code, value, unit, group='ac'):
    return {'key': 'telemetry:' + group + ':' + code, 'value': value, 'unit': unit}


def test_device_report_separates_ac_dc_and_rejects_ambiguous_units_missing_zero():
    report = device_report('fixture', [point('pAc', 5, 'kW'), point('pDc', 0, 'kW'),
                                      point('Temperature', 34, '℃')],
                           [point('proPvStatsToday', '12.5', 'kWh'), point('proCharStatsToday', 0, 'kWh'),
                            point('proDischarStatsToday', 1, 'Wh'), point('ratedPower', 10, 'kW')], counters_available=True)
    assert report.ac_kw == 5 and report.pv_dc_kw == 0 and report.rated_kw == 10
    assert report.periods['today'].charge_kwh == 0 and report.periods['today'].discharge_kwh is None
    assert report.source_clock is None and report.temperature_c == 34
    bad = device_report('fixture', [point('pAc', 5, 'kW'), point('pAc', 2, 'kW', 'other')], [], counters_available=False)
    assert bad.ac_kw is None and bad.pv_dc_kw is None and bad.periods == {}


async def test_counter_error_keeps_telemetry_without_reusing_previous_counts():
    def handler(req):
        if req.url.path.endswith('/telecounting'):
            return envelope(None, 'DENIED')
        return reply(req)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        a = GoodWePlus(CONFIG, CREDENTIALS, client=client)
        await a.stations()
        await a.devices('fixture-plant')
        rows = await a.latest(['fixture-inverter'])
        assert rows[0]['reported']['ac_kw'] == 0
        assert rows[0]['reported']['periods'] == {}
        assert rows[0]['reported']['counters_available'] is False


def test_device_scoped_report_persists_without_becoming_good_sample(local, monkeypatch):
    client, ctl = local
    headers = login(local)
    transport(monkeypatch, ctl)
    iid = client.post('/api/connections/goodwe', json=BODY, headers=headers).json()['id']
    client.post('/api/sync', json={}, headers=headers)
    device = next(d for d in ctl.devices() if d.integration_id == iid and d.type == 'INVERTER')
    report = ctl.latest(device)['reported']
    assert report['serial'] == device.vendor_id and report['periods']['today']['generation_kwh'] == 7.5
    assert all(s['quality'] != 'GOOD' for s in ctl.latest(device)['samples'])
    inventory = client.get('/api/fleet/devices-overview').json()['devices']
    assert next(d for d in inventory if d['id'] == device.id)['vendor_report'] == report
    row = ctl.store.get('latest', device.id)
    ctl.store.put('latest', device.id, {**row, 'reported': {**report, 'serial': 'unrelated'}})
    assert ctl.latest(device)['reported'] is None
    assert ctl.store.commands() == []


@pytest.mark.parametrize('value', ['NaN', 'Infinity', -1, None, True])
def test_invalid_device_counters_stay_missing(value):
    report = device_report('fixture', [], [point('proPvStatsToday', value, 'kWh')], counters_available=True)
    assert report.periods == {}
