"""Read-only refresh uses the existing collector; synthetic accounts only."""

from datetime import timedelta

from test_goodwe_connection import BODY, CREDENTIALS, transport
from test_workspaces import local as local
from test_workspaces import login

from solar_fleet.data_workspace import minimum_collection_interval
from solar_fleet.domain import utcnow


def test_scoped_refresh_account_label_cadence_and_no_quota_bypass(local, monkeypatch):
    client, ctl = local
    headers = login(local)
    calls, _ = transport(monkeypatch, ctl)
    integration_id = client.post('/api/connections/goodwe', json=BODY, headers=headers).json()['id']
    result = client.post('/api/readings/refresh', json={}, headers=headers)
    assert result.status_code == 200 and result.json()['state'] == 'UPDATED'
    site = next(s for s in client.get('/api/fleet').json()['sites'] if s.get('integration_id') == integration_id)
    assert site['account_label'] == CREDENTIALS['account']
    assert CREDENTIALS['password'] not in client.get('/api/fleet').text
    device = next(d for d in ctl.devices() if d.integration_id == integration_id)
    payload = {'device_id': device.id, 'site_id': site['id']}
    before = len(calls)
    assert client.post('/api/readings/refresh', json=payload, headers=headers).json()['state'] == 'BUSY'
    ctl.last_poll = 0
    assert client.post('/api/readings/refresh', json=payload, headers=headers).json()['state'] == 'WAITING'
    assert len(calls) == before
    state = ctl.store.get('integration_state', integration_id)
    ctl.store.put('integration_state', integration_id, {**state, 'last_attempt': (utcnow() - timedelta(seconds=61)).isoformat()})
    assert client.post('/api/readings/refresh', json=payload, headers=headers).json()['state'] == 'UPDATED'
    assert len(calls) > before
    assert client.post('/api/readings/refresh', json={'site_id': 'outside'}, headers=headers).status_code == 404
    assert client.post('/api/readings/refresh', json={**payload, 'site_id': 'outside'}, headers=headers).status_code == 422
    assert client.post('/api/readings/refresh', json=payload).status_code == 403
    assert client.get('/api/devices/' + device.id).json()['can_refresh'] is True
    assert ctl.store.commands() == []


def test_classic_goodwe_and_explicit_policy_are_not_accelerated(local):
    _, ctl = local
    registration = ctl.registry.require('GoodWe').registration
    assert minimum_collection_interval({'platform': 'sems_plus'}, registration) == 60
    assert minimum_collection_interval({'platform': 'sems'}, registration) == 300
    ctl.store.put('collection_policy', 'synthetic', {'interval_seconds': 900})
    assert ctl.collection_cadence({'id': 'synthetic', 'vendor': 'GoodWe', 'platform': 'sems_plus'}) == 900


def test_viewer_cannot_trigger_vendor_reads_or_see_login_identity(local, monkeypatch):
    client, ctl = local
    headers = login(local)
    calls, _ = transport(monkeypatch, ctl)
    client.post('/api/connections/goodwe', json=BODY, headers=headers)
    client.post('/api/readings/refresh', json={}, headers=headers)
    before = len(calls)
    # Existing isolated fixture user, not a real user's account.
    from solar_fleet.domain import Role
    from solar_fleet.security import create_user
    create_user(ctl.store, 'refresh-viewer', 'test-only-long-password', Role.VIEWER, ['*'])
    client.post('/api/login', json={'username': 'refresh-viewer', 'password': 'test-only-long-password'},
                headers={'Origin': 'http://127.0.0.1:8765'})
    csrf = client.get('/api/me').json()['csrf']
    assert client.post('/api/readings/refresh', json={}, headers={**headers, 'X-CSRF-Token': csrf}).status_code == 403
    assert len(calls) == before
    assert CREDENTIALS['account'] not in client.get('/api/fleet').text
