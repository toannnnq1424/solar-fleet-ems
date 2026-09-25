from concurrent.futures import ThreadPoolExecutor

from solar_fleet.domain import Role
from solar_fleet.security import create_user, new_session, session_user


def test_concurrent_valid_session_reads_never_lose_or_mix_identity(store):
    tokens = []
    for i in range(3):
        uid = f"SIM-concurrent-{i}"
        create_user(store, uid, "SIMULATOR-concurrency-password", Role.VIEWER, [f"site-{i}"])
        token, csrf = new_session(store, uid)
        tokens.append((token, uid, csrf))

    def read(i):
        token, uid, csrf = tokens[i % 3]
        result = session_user(store, token)
        assert result is not None
        assert result[0].id == uid
        assert result[1] == csrf
        assert result[0].site_ids == [f"site-{i % 3}"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(read, range(1200)))
    assert session_user(store, "invalid-session") is None
