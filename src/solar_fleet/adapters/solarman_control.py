"""No accepted solarman control contract is packaged. Never guess native IDs."""

from ..domain import SafetyError

CONTROL_PATHS = {}


def compile_solarman(device, intent, parameters):
    raise SafetyError("intent_mapping_unknown")
