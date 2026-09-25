import pytest

from solar_fleet.adapters.goodwe_control import compile_goodwe
from solar_fleet.adapters.growatt_control import compile_growatt
from solar_fleet.adapters.solarman_control import compile_solarman
from solar_fleet.adapters.solis_control import compile_solis
from solar_fleet.adapters.sungrow_control import compile_sungrow
from solar_fleet.domain import SafetyError


@pytest.mark.parametrize(
    "compiler", [compile_goodwe, compile_growatt, compile_sungrow, compile_solis, compile_solarman]
)
@pytest.mark.parametrize("intent", ["SET_WORK_MODE", "SET_TOU", "SET_RESERVE_SOC", "SET_GRID_CODE"])
def test_no_guessed_control_packet_without_exact_contract(compiler, intent, device):
    with pytest.raises(SafetyError):
        compiler(device, intent, {"value": 30})
