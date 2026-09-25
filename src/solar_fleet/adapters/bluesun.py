"""Bluesun hardware identity placeholder, not a transport selection by name prefix."""

from ..domain import VendorError


class BluesunAdapter:
    evidence_ids = ["BLUESUN_BSM_001"]

    def __init__(self, integration, credentials):
        self.integration, self.credentials = integration, credentials

    def resolve_oem(self):
        return "UNKNOWN_COMMISSIONING_REQUIRED"

    def build_query(self, slave_id, start_reg, qty):
        raise VendorError("bluesun_exact_logger_protocol_required")

    def decode_registers(self, start_reg, values):
        raise VendorError("uncommissioned_bluesun_model")
