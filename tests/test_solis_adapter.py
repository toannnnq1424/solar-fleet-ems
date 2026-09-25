import base64
import hashlib
import hmac

import pytest

from solar_fleet.adapters.solis import Solis, signed_headers
from solar_fleet.domain import VendorError


def test_signature_uses_exact_serialized_bytes_and_content_type():
    payload = b'{"sn":"fixture-SN"}'
    path = "/v1/api/inverterDetail"
    date = "Mon, 21 Sep 2026 01:00:00 GMT"
    headers = signed_headers(path, payload, "fixture-key", "fixture-secret", date)
    md5 = base64.b64encode(hashlib.md5(payload).digest()).decode()
    canonical = "POST\n" + md5 + "\n" + headers["Content-Type"] + "\n" + date + "\n" + path
    signature = base64.b64encode(
        hmac.new(b"fixture-secret", canonical.encode(), hashlib.sha1).digest()
    ).decode()
    assert headers["Authorization"] == "API fixture-key:" + signature
    assert headers["Content-MD5"] == md5


def test_solis_no_region_fallback():
    with pytest.raises(VendorError):
        Solis({"region": "unknown"}, {"key_id": "fixture", "key_secret": "fixture"})
