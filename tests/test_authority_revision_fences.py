"""Persistent ABA fences, synthetic adapters only; no hardware writes."""

import pytest
from test_control import settle, setup

from solar_fleet.control import command_selection
from solar_fleet.domain import SafetyError
from solar_fleet.storage import Store


def test_revision_tombstone_rollback_reopen(tmp_path):
    path = tmp_path / "revision.sqlite"
    store = Store(path)
    original = {"id": "sim", "enabled": True}
    store.put("integration", "sim", original)
    before = store.revisions("integration")
    store.put("integration", "sim", original)
    assert store.revisions("integration") == before
    with pytest.raises(RuntimeError), store.transaction():
        store.put("integration", "sim", original | {"enabled": False})
        raise RuntimeError("rollback")
    assert store.revisions("integration") == before
    store.db.execute("DELETE FROM entities WHERE kind='integration' AND id='sim'")
    store.put("integration", "sim", original)
    after = store.revisions("integration")
    assert after["integration"]["sim"] == before["integration"]["sim"] + 2
    store.close()
    reopened = Store(path)
    try:
        assert reopened.revisions("integration") == after
        assert reopened.get("integration", "sim") == original
    finally:
        reopened.close()


@pytest.mark.parametrize("kind", ["integration", "device", "site", "binding"])
def test_selected_revisions_absence_aba_rollback_reopen(tmp_path, kind):
    path = tmp_path / "selected.sqlite"
    store = Store(path)
    other = Store(path)
    try:
        before = store.object_revisions({kind: ["selected"]})
        assert before == {kind: {"selected": 0}}
        other.put(kind, "unrelated", {"id": "unrelated"})
        assert store.object_revisions(before) == before
        with pytest.raises(RuntimeError), other.transaction():
            other.put(kind, "selected", {"id": "selected"})
            raise RuntimeError("rollback")
        assert store.object_revisions(before) == before
        other.put(kind, "selected", {"id": "selected"})
        other.db.execute("DELETE FROM entities WHERE kind=? AND id=?", (kind, "selected"))
        after = store.object_revisions(before)
        assert after == {kind: {"selected": 2}}
        assert store.get(kind, "selected") is None
    finally:
        other.close()
        store.close()
    reopened = Store(path)
    try:
        assert reopened.object_revisions(before) == after
    finally:
        reopened.close()


@pytest.mark.parametrize("column", ["kind", "id"])
def test_entity_identity_update_aba_migrates_legacy_trigger(tmp_path, column):
    path = tmp_path / "identity.sqlite"
    store = Store(path)
    store.put("device", "selected", {"id": "selected"})
    # Reproduce the installed old trigger, then exercise the reopen migration.
    store.db.executescript("""
        DROP TRIGGER entity_revision_update;
        CREATE TRIGGER entity_revision_update AFTER UPDATE ON entities
        WHEN OLD.body != NEW.body
        BEGIN INSERT INTO entity_revisions VALUES(NEW.kind,NEW.id,1)
        ON CONFLICT(kind,id) DO UPDATE SET revision=revision+1; END;
    """)
    store.close()
    store = Store(path)
    original = "device" if column == "kind" else "selected"
    before = store.object_revisions({"device": ["selected"]})

    def aba():
        store.db.execute(f"UPDATE entities SET {column}=? WHERE kind=? AND id=?",
                         ("moved", "device", "selected"))
        store.db.execute(f"UPDATE entities SET {column}=? WHERE {column}=?", (original, "moved"))

    try:
        with pytest.raises(RuntimeError), store.transaction():
            aba()
            raise RuntimeError("rollback")
        assert store.object_revisions(before) == before
        aba()
        assert store.object_revisions(before)["device"]["selected"] == before["device"]["selected"] + 2
        target = {"moved": ["selected"]} if column == "kind" else {"device": ["moved"]}
        assert next(iter(store.object_revisions(target).values())) == {
            "selected" if column == "kind" else "moved": 2,
        }
        assert store.get("device", "selected") == {"id": "selected"}
    finally:
        store.close()


@pytest.mark.parametrize("kind", ["integration", "device", "site", "binding"])
@pytest.mark.parametrize("phase", ["preview", "confirm", "configuration", "send"])
async def test_command_aba_fence(store, device, operator, capability, kind, phase):
    engine, sim = setup(store, device, operator, capability)
    original = {"id": command_selection(device)[kind][0], "enabled": True}
    store.put(kind, original["id"], original)

    def aba():
        store.put(kind, original["id"], original | {"enabled": False})
        store.put(kind, original["id"], original)

    configuration = sim.configuration

    async def changed_configuration(d):
        result = await configuration(d)
        aba()
        return result

    if phase == "preview":
        sim.configuration = changed_configuration
        with pytest.raises(SafetyError, match="authority_revision_changed"):
            await engine.preview(operator, device.id, capability.intent, {"value": 20})
        assert store.db.execute("SELECT count(*) FROM plans").fetchone()[0] == 0
        return
    plan = await engine.preview(operator, device.id, capability.intent, {"value": 20})
    if phase == "confirm":
        aba()
        with pytest.raises(SafetyError, match="authority_revision_changed"):
            await engine.confirm(operator, plan.id, plan.digest, "sim-revision-key-0001")
        assert store.command(plan.id) is None
        return
    if phase == "configuration":
        sim.configuration = changed_configuration
    else:
        send = sim.send

        async def changed_send(*args, **kwargs):
            ack = await send(*args, **kwargs)
            aba()
            return ack

        sim.send = changed_send
    await engine.confirm(operator, plan.id, plan.digest, "sim-revision-key-0001")
    await settle(engine)
    row = store.command(plan.id)
    assert row["status"] == ("TIMEOUT" if phase == "send" else "FAILED")
    assert sim.sent == (1 if phase == "send" else 0)
    if phase == "send":
        assert row["order_ids"] != "[]"
        replay = await engine.confirm(operator, plan.id, plan.digest, "sim-revision-key-0001")
        assert replay["id"] == row["id"]
        assert replay["status"] == "TIMEOUT"
        assert sim.sent == 1


@pytest.mark.parametrize("kind", ["integration", "device", "site", "binding"])
async def test_command_unrelated_changes_through_network_and_replay(store, device, operator, capability, kind):
    engine, sim = setup(store, device, operator, capability)
    configuration, send = sim.configuration, sim.send
    counter = 0

    def unrelated():
        nonlocal counter
        counter += 1
        store.put(kind, "unrelated", {"id": "unrelated", "revision": counter})

    async def changed_configuration(d):
        result = await configuration(d)
        unrelated()
        return result

    async def changed_send(*args, **kwargs):
        ack = await send(*args, **kwargs)
        unrelated()
        return ack

    sim.configuration, sim.send = changed_configuration, changed_send
    plan = await engine.preview(operator, device.id, capability.intent, {"value": 20})
    assert plan.revision_scope == "selected_objects_v1"
    assert plan.authority_revisions == store.object_revisions(command_selection(device))
    unrelated()
    key = "sim-selected-replay-0001"
    await engine.confirm(operator, plan.id, plan.digest, key)
    await settle(engine)
    assert store.command(plan.id)["status"] == "VERIFIED"
    unrelated()
    replay = await engine.confirm(operator, plan.id, plan.digest, key)
    assert replay["status"] == "VERIFIED"
    assert sim.sent == 1


@pytest.mark.parametrize("kind", ["integration", "device", "site", "binding"])
async def test_command_absent_selected_identity_aba(store, device, operator, capability, kind):
    engine, sim = setup(store, device, operator, capability)
    plan = await engine.preview(operator, device.id, capability.intent, {"value": 20})
    id = command_selection(device)[kind][0]
    assert plan.authority_revisions[kind][id] == 0
    store.put(kind, id, {"id": id})
    store.db.execute("DELETE FROM entities WHERE kind=? AND id=?", (kind, id))
    with pytest.raises(SafetyError, match="authority_revision_changed"):
        await engine.confirm(operator, plan.id, plan.digest, "sim-absence-key-0001")
    assert sim.sent == 0
    assert store.command(plan.id) is None


@pytest.mark.parametrize("change", [False, True])
async def test_legacy_plan_digest_scope_and_non_sending_replay(store, device, operator, capability, change):
    import hashlib

    from solar_fleet.control import fingerprint
    from solar_fleet.storage import encoded

    engine, sim = setup(store, device, operator, capability)
    plan = await engine.preview(operator, device.id, capability.intent, {"value": 20}, persist=False)
    body = plan.model_dump(mode="json", exclude={"digest", "revision_scope"})
    body["authority_revisions"] = store.revisions("integration", "device", "site", "binding")
    # Compute the old format independently, then load the exact persisted JSON.
    body["digest"] = hashlib.sha256(encoded(body).encode()).hexdigest()
    store.db.execute("INSERT INTO plans VALUES(?,?)", (plan.id, encoded(body)))
    legacy = store.plan(plan.id)
    assert legacy.revision_scope == "kind_wide"
    assert fingerprint(legacy) == body["digest"]
    key = "sim-legacy-replay-0001"
    if change:
        store.put("integration", "unrelated", {"id": "unrelated"})
        with pytest.raises(SafetyError, match="authority_revision_changed"):
            await engine.confirm(operator, plan.id, legacy.digest, key)
        assert sim.sent == 0
        return
    await engine.confirm(operator, plan.id, legacy.digest, key)
    await settle(engine)
    store.put("integration", "unrelated", {"id": "unrelated"})
    replay = await engine.confirm(operator, plan.id, legacy.digest, key)
    assert replay["status"] == "VERIFIED"
    assert sim.sent == 1


async def test_selected_scope_is_digest_bound(store, device, operator, capability):
    engine, sim = setup(store, device, operator, capability)
    plan = await engine.preview(operator, device.id, capability.intent, {"value": 20})
    body = plan.model_dump(mode="json")
    body.pop("revision_scope")
    from solar_fleet.storage import encoded

    store.db.execute("UPDATE plans SET body=? WHERE id=?", (encoded(body), plan.id))
    with pytest.raises(SafetyError, match="plan_digest_mismatch"):
        await engine.confirm(operator, plan.id, plan.digest, "sim-scope-key-000001")
    assert sim.sent == 0