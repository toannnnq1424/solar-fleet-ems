"""Compatibility imports; cloud Eybond and local SOLARMAN are separate protocols."""

from .dessmonitor import Dessmonitor as EybondAdapter
from .solarman_v5 import SolarmanV5Frame, calculate_v5_checksum, crc16_modbus

__all__ = ["EybondAdapter", "SolarmanV5Frame", "calculate_v5_checksum", "crc16_modbus"]
