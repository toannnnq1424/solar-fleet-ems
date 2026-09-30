"""Shared read transport rejects revoked context before consuming responses."""

import httpx
import pytest

from solar_fleet.adapters.cloud import ReadCloud
from solar_fleet.domain import SafetyError
from solar_fleet.transport_guard import check_transport_guard, guarded_read


@pytest.mark.parametrize("boundary", ["entry", "budget", "response", "unchanged"])
async def test_shared_cloud_read_fence(boundary):
    allowed = boundary != "entry"
    seen = []

    def guard():
        if not allowed:
            raise SafetyError("synthetic_revocation")

    def handler(request):
        nonlocal allowed
        seen.append(request)
        if boundary == "response":
            allowed = False
        return httpx.Response(200, json={"success": True})

    class Cloud(ReadCloud):
        host = "https://synthetic.invalid"

    class Budget:
        async def acquire(self, *args):
            nonlocal allowed
            if boundary == "budget":
                allowed = False

    adapter = Cloud({}, {}, client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
                    budgets=Budget())
    try:
        if boundary == "unchanged":
            assert await guarded_read(guard, adapter.http, "/read") == {"success": True}
        else:
            with pytest.raises(SafetyError, match="synthetic_revocation"):
                await guarded_read(guard, adapter.http, "/read")
        assert len(seen) == (1 if boundary in {"response", "unchanged"} else 0)
        check_transport_guard()
    finally:
        await adapter.close()