"""Durable local authorization ABA regressions; synthetic identities only."""

import sqlite3

import pytest
from test_control import settle, setup

from solar_fleet.domain import Role, SafetyError
from solar_fleet.security import create_user, new_session, principal, require_session_principal, session_user
from solar_fleet.storage import Store


def security_aba(store, user_id, change):
    if change == "session_aba":
        rows = store.db.execute("SELECT * FROM sessions WHERE user_id=?", (user_id,)).fetchall()
        store.db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        store.db.executemany("INSERT INTO sessions VALUES(?,?,?,?)", [tuple(row) for row in rows])
    else:
        column = {"role_aba": "role", "scope_aba": "sites", "permission_aba": "permissions",
                  "active_aba": "active", "password_aba": "password_hash"}[change]
        old = store.db.execute(f"SELECT {column} FROM users WHERE id=?", (user_id,)).fetchone()[0]
        changed = {"role": "Viewer", "sites": "[]", "permissions": '["changed"]',
                   "active": 0, "password_hash": "synthetic-replaced"}[column]
        store.db.execute(f"UPDATE users SET {column}=? WHERE id=?", (changed, user_id))
        store.db.execute(f"UPDATE users SET {column}=? WHERE id=?", (old, user_id))


@pytest.mark.parametrize("change", ["role_aba", "scope_aba", "permission_aba", "active_aba",
                                    "password_aba", "session_aba"])
def test_session_detects_aba_without_serializing_internal_state(store, change):
    create_user(store, "sim", "synthetic-password", Role.INSTALLER, ["sim-site"])
    token, _ = new_session(store, "sim")
    before = session_user(store, token)[0]
    security_aba(store, "sim", change)
    after = session_user(store, token)[0]
    assert before.model_dump() == after.model_dump()
    assert before != after
    with pytest.raises(SafetyError, match="session_authority_changed"):
        require_session_principal(store, token, before)
    require_session_principal(store, token, after)


def test_security_revisions_second_connection_rollback_reopen(tmp_path):
    path = tmp_path / "security.sqlite"
    first, second = Store(path), Store(path)
    try:
        create_user(first, "sim", "synthetic-password", Role.INSTALLER, ["sim-site"])
        token, _ = new_session(first, "sim")
        before = session_user(first, token)[0]
        with pytest.raises(RuntimeError), second.transaction():
            security_aba(second, "sim", "role_aba")
            security_aba(second, "sim", "session_aba")
            raise RuntimeError("rollback")
        assert session_user(first, token)[0] == before
        second.db.execute("UPDATE users SET role=role WHERE id='sim'")
        second.db.execute("UPDATE sessions SET csrf=csrf")
        assert session_user(first, token)[0] == before
        security_aba(second, "sim", "role_aba")
        security_aba(second, "sim", "session_aba")
        after = session_user(first, token)[0]
        assert after != before
    finally:
        first.close()
        second.close()
    reopened = Store(path)
    try:
        assert session_user(reopened, token)[0] == after
    finally:
        reopened.close()


def test_security_revision_migration_existing_users(tmp_path):
    path = tmp_path / "legacy.sqlite"
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE users(id TEXT PRIMARY KEY,password_hash TEXT NOT NULL,
            role TEXT NOT NULL,sites TEXT NOT NULL,permissions TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL,
            csrf TEXT NOT NULL,expires TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id));
        INSERT INTO users VALUES('sim','synthetic','Installer','["sim-site"]','[]',1);
    """)
    db.close()
    store = Store(path)
    try:
        before = principal(store, "sim")
        assert before._authority_revision == 0
        security_aba(store, "sim", "permission_aba")
        assert principal(store, "sim")._authority_revision == 2
        assert principal(store, "sim").model_dump() == before.model_dump()
        store.db.execute("DELETE FROM users WHERE id='sim'")
        store.db.execute("INSERT INTO users VALUES('sim','synthetic','Installer','[\"sim-site\"]','[]',1)")
        assert principal(store, "sim")._authority_revision == 4
    finally:
        store.close()


def test_unrelated_user_and_session_do_not_invalidate_authority(store):
    create_user(store, "sim", "synthetic-password", Role.INSTALLER, ["sim-site"])
    token, _ = new_session(store, "sim")
    before = session_user(store, token)[0]
    create_user(store, "other", "synthetic-password", Role.VIEWER, [])
    new_session(store, "other")
    new_session(store, "sim")
    security_aba(store, "other", "scope_aba")
    security_aba(store, "other", "session_aba")
    assert session_user(store, token)[0] == before


@pytest.mark.parametrize("phase", ["preview", "confirm", "configuration", "send"])
@pytest.mark.parametrize("change", ["role_aba", "scope_aba", "permission_aba", "active_aba", "password_aba"])
async def test_command_user_aba(store, device, operator, capability, phase, change):
    create_user(store, operator.id, "synthetic-password", operator.role, operator.site_ids)
    operator = principal(store, operator.id)
    engine, sim = setup(store, device, operator, capability)
    engine.principal = lambda id: principal(store, id)
    configuration = sim.configuration

    async def changed_configuration(d):
        result = await configuration(d)
        security_aba(store, operator.id, change)
        return result

    if phase == "preview":
        sim.configuration = changed_configuration
        with pytest.raises(SafetyError, match="operator_authority_changed"):
            await engine.preview(operator, device.id, capability.intent, {"value": 20})
        assert store.db.execute("SELECT count(*) FROM plans").fetchone()[0] == 0
        return
    plan = await engine.preview(operator, device.id, capability.intent, {"value": 20})
    if phase == "confirm":
        security_aba(store, operator.id, change)
        with pytest.raises(SafetyError, match="operator_authority_changed"):
            await engine.confirm(principal(store, operator.id), plan.id, plan.digest, "security-aba-key-001")
        assert store.command(plan.id) is None
        return
    if phase == "configuration":
        sim.configuration = changed_configuration
    else:
        send = sim.send

        async def changed_send(*args, **kwargs):
            ack = await send(*args, **kwargs)
            security_aba(store, operator.id, change)
            return ack

        sim.send = changed_send
    await engine.confirm(operator, plan.id, plan.digest, "security-aba-key-001")
    await settle(engine)
    row = store.command(plan.id)
    assert row["status"] == ("TIMEOUT" if phase == "send" else "FAILED")
    assert sim.sent == (1 if phase == "send" else 0)
    assert row["error"] == "operator_authority_changed"
    if phase == "send":
        assert row["order_ids"] != "[]"
        replay = await engine.confirm(principal(store, operator.id), plan.id, plan.digest, "security-aba-key-001")
        assert replay["id"] == row["id"]
        assert sim.sent == 1