"""Tests for timeseries engine, LTTB downsampling, and solar energy/financial calculations."""

import pytest

from solar_fleet.timeseries_engine import (
    calculate_financial_savings,
    calculate_performance_ratio,
    integrate_power_to_energy,
    lttb_downsample,
)


def test_lttb_downsampling_preserves_peaks():
    """Verify LTTB preserves maximum peak when downsampling 100 points to 10 points."""
    # Synthetic curve with a sharp peak at x = 50
    data = [(float(i), float(i % 10)) for i in range(100)]
    data[50] = (50.0, 999.0)  # Extreme peak

    downsampled = lttb_downsample(data, threshold=10)
    assert len(downsampled) == 10
    # The peak at 50.0, 999.0 must be preserved in the downsampled result
    y_values = [pt[1] for pt in downsampled]
    assert 999.0 in y_values
    assert downsampled[0] == data[0]
    assert downsampled[-1] == data[-1]


def test_integrate_power_to_energy():
    """Verify trapezoidal integration from power (W) to energy (kWh)."""
    # 1000 W constant power for 3600 seconds (1 hour) = 1 kWh
    points = [(0.0, 1000.0), (1800.0, 1000.0), (3600.0, 1000.0)]
    energy_kwh = integrate_power_to_energy(points)
    assert energy_kwh == pytest.approx(1.0, rel=1e-3)


def test_calculate_performance_ratio():
    """Verify PR calculation per IEC 61724-1."""
    # 50 kWp plant, 200 kWh generated, 5 kWh/m2 irradiance
    # specific_yield = 200 / 50 = 4.0 h
    # reference_yield = 5.0 / 1.0 = 5.0 h
    # PR = (4.0 / 5.0) * 100 = 80.0%
    pr = calculate_performance_ratio(
        actual_energy_kwh=200.0,
        capacity_kwp=50.0,
        poa_irradiance_kwh_m2=5.0,
    )
    assert pr == pytest.approx(80.0)


def test_calculate_financial_savings():
    """Verify 3-tier tariff financial savings and carbon footprint calculations."""
    result = calculate_financial_savings(
        pv_energy_kwh=1000.0,
        self_consumption_pct=80.0,
    )
    assert result["self_consumed_kwh"] == 800.0
    assert result["exported_kwh"] == 200.0
    assert result["savings_vnd"] > 1_000_000
    assert result["avoided_co2_kg"] == pytest.approx(722.1)
    assert result["avoided_co2_tons"] == pytest.approx(0.722)
