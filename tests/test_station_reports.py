"""Synthetic, outbound-blocked station aggregate contracts; no real accounts."""

from datetime import timedelta

import httpx
import pytest
from pydantic import ValidationError
from test_goodwe_connection import BODY, transport
from test_goodwe_plus import CONFIG, CREDENTIALS, envelope, reply
from test_workspaces import local as local
from test_workspaces import login

from solar_fleet.adapters.goodwe_plus import FLOW, STATISTICS, GoodWePlus, energy_rows, period_energy
from solar_fleet.domain import VendorError, utcnow
from solar_fleet.integration import StationReport


async def test_station_report_scope_sign_units_clock_and_totals():
    calls = []
    def handler(req):
        calls.append(req)
        return reply(req)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        a = GoodWePlus(CONFIG, CREDENTIALS, client=client)
        with pytest.raises(VendorError, match='station_discovery_required'):
            await a.station_report('unrelated')
        assert calls == []
        await a.stations()
        r = await a.station_report('fixture-plant')
        assert r.power == {'pv_w': 0, 'load_w': 1200, 'battery_w': 500, 'grid_w': 1700, 'battery_soc': 40}
        assert r.source_clock == '2026-10-08T06:45:00'
        assert r.periods['today'].export_kwh is None
        assert r.periods['month'].start_date == '2026-10-01'
        assert r.daily_energy[0].generation_kwh == 12
        assert len([c for c in calls if c.url.path == STATISTICS]) == 4


@pytest.mark.parametrize('dimension,bucket,start', [('day', '2026-10-08', '2026-10-08'),
                                                  ('month', '2026-10', '2026-10-01'),
                                                  ('year', '2026', '2026-01-01')])
def test_unit_bearing_calendar_bucket_wins_over_different_flat_summary(dimension, bucket, start):
    data = {'production': 99, 'dataList': [{'item': 'proSystemTotalStats', 'unit': 'kWh',
                                           'statisticsList': [{'date': bucket, 'val': 0}]}]}
    r = period_energy(data, start, '2026-10-08', dimension)
    assert r.generation_kwh == 0 and r.consumption_kwh is None
    data['dataList'][0]['statisticsList'].append({'date': bucket, 'val': 5})
    with pytest.raises(VendorError, match='vendor_invalid_statistics'):
        period_energy(data, start, '2026-10-08', dimension)


@pytest.mark.parametrize('bad', [None, '', 'NaN', 'Infinity', True, [], {}, -1])
async def test_invalid_pv_never_falls_back_to_inverter_ac(bad):
    def handler(req):
        if req.url.path == FLOW:
            return envelope({'pSystem': bad, 'pAc': 123, 'soc': 101, 'refreshTime': 'invalid'})
        return reply(req)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        a = GoodWePlus(CONFIG, CREDENTIALS, client=client)
        await a.stations()
        r = await a.station_report('fixture-plant')
        assert 'pv_w' not in r.power and 'battery_soc' not in r.power
        assert r.source_clock is None and r.periods == {}


async def test_statistics_failure_is_partial_but_quota_stops_reads():
    count = 0
    def handler(req):
        nonlocal count
        if req.url.path == STATISTICS:
            count += 1
            return envelope(None, code='unavailable' if count < 2 else 'GY0429')
        return reply(req)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        a = GoodWePlus(CONFIG, CREDENTIALS, client=client)
        await a.stations()
        with pytest.raises(VendorError, match='vendor_rate_limited'):
            await a.station_report('fixture-plant')
        assert count == 2


@pytest.mark.parametrize('unit,dates', [('Wh', ['2026-10-01']), ('kWh', ['2026-10-01', '2026-10-01']),
                                      ('kWh', ['2026-09-30']), ('kWh', ['2026-10-32'])])
def test_energy_rejects_wrong_units_duplicates_and_out_of_range(unit, dates):
    data = {'dataList': [{'item': 'proSystemTotalStats', 'unit': unit,
                         'statisticsList': [{'date': d, 'val': 1} for d in dates]}]}
    with pytest.raises(VendorError, match='vendor_invalid_statistics'):
        energy_rows(data, '2026-10-01', '2026-10-08')


@pytest.mark.parametrize('power', [{'pv_w': float('nan')}, {'grid_w': float('inf')}, {'battery_soc': 101.0}, {'pv_w': -1.0}])
def test_common_contract_rejects_nonfinite_and_invalid_ranges(power):
    with pytest.raises(ValidationError):
        StationReport(station_id='synthetic', power=power)


def test_report_reader_rechecks_scope_binding_credentials_and_failure(local, monkeypatch):
    client, ctl = local
    headers = login(local)
    transport(monkeypatch, ctl)
    integration_id = client.post('/api/connections/goodwe', json=BODY, headers=headers).json()['id']
    client.post('/api/sync', json={}, headers=headers)
    site = next(s for s in ctl.store.list('site') if s.get('integration_id') == integration_id)
    url = '/api/sites/' + site['id'] + '/vendor-report'
    assert client.get(url).json()['report']['power']['pv_w'] == 0
    config = ctl.store.get('integration', integration_id)
    ctl.store.put('integration', integration_id, {**config, 'enabled': False})
    assert client.get(url).json()['report'] is None
    ctl.store.put('integration', integration_id, {**config, 'credential_revision': 'changed'})
    assert client.get(url).json()['report'] is None
    ctl.store.put('integration', integration_id, config)
    assert ctl.reported_station(site['id']) is not None
    record = ctl.store.get('station_report', site['id'])
    ctl.store.put('station_report', site['id'], {**record, 'report': {**record['report'], 'station_id': 'other-site'}})
    assert ctl.reported_station(site['id']) is None
    ctl.store.put('station_report', site['id'], record)
    for binding in ctl.store.list('binding'):
        if binding['integration_id'] == integration_id:
            ctl.store.put('binding', binding['id'], {**binding, 'telemetry_enabled': False})
    assert ctl.reported_station(site['id']) is None
    assert client.get('/api/sites/unrelated/vendor-report').status_code in (403, 404)
    assert ctl.store.commands() == []


def test_station_refreshes_at_account_cadence_not_fifteen_minutes(local, monkeypatch):
    client, ctl = local
    headers = login(local)
    calls, _ = transport(monkeypatch, ctl)
    integration_id = client.post('/api/connections/goodwe', json=BODY, headers=headers).json()['id']
    assert client.post('/api/sync', json={}, headers=headers).status_code == 200
    site = next(s for s in ctl.store.list('site') if s.get('integration_id') == integration_id)
    report = ctl.store.get('station_report', site['id'])
    state = ctl.store.get('integration_state', integration_id)
    age = (utcnow() - timedelta(seconds=301)).isoformat()
    ctl.store.put('station_report', site['id'], {**report, 'received_at': age})
    ctl.store.put('integration_state', integration_id, {**state, 'last_attempt': age})
    ctl.last_poll = 0
    before = len([c for c in calls if c.url.path == FLOW])
    assert client.post('/api/sync', json={}, headers=headers).status_code == 200
    assert len([c for c in calls if c.url.path == FLOW]) == before + 1
    assert ctl.reported_station(site['id'])['collection_interval_seconds'] == 60
    ctl.last_poll = 0
    assert client.post('/api/sync', json={}, headers=headers).status_code == 200
    assert len([c for c in calls if c.url.path == FLOW]) == before + 1  # no quota bypass
    device = next(d for d in ctl.devices() if d.integration_id == integration_id)
    assert ctl.latest(device)['collection_interval_seconds'] == 60
    assert ctl.store.commands() == []
