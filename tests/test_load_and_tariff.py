"""Tests for load prediction engine and dynamic tariff catalogue.

Tests:
- Load profile calculations (load factor, peak, base)
- Predictors: persistence, similar-day, profile clustering, ensemble, temperature-adjusted
- Prediction accuracy metrics (MAE, RMSE, MAPE, R²)
- Tariff catalogue: pre-built plans, TOU slot evaluation, midnight wrapping
- Dynamic spot pricing feeds (cheapest/expensive hour finders)
- Carbon tracker and greenest hours
- Bill calculator and multi-tariff comparison
"""

import pytest

from solar_fleet.load_predictor import (
    EnsemblePredictor,
    LoadProfile,
    PersistencePredictor,
    ProfileClusterPredictor,
    SimilarDayPredictor,
    TemperatureAdjustedPredictor,
    prediction_metrics,
)
from solar_fleet.tariff_catalogue import (
    TARIFF_CATALOGUE,
    BillCalculator,
    CarbonIntensity,
    CarbonTracker,
    DynamicPricingFeed,
    PriceSlot,
    SpotPrice,
    TariffPlan,
    TariffType,
    TimeSlot,
)

# ---------------------------------------------------------------------------
# Load Predictor Tests
# ---------------------------------------------------------------------------

class TestLoadPredictor:
    def test_load_profile_properties(self):
        values = [1.0, 1.5, 2.0, 3.0] + [2.0] * 20
        profile = LoadProfile(values=values, date="2026-09-27", day_type="weekday")
        assert profile.total_kwh == sum(values)
        assert profile.peak_kw == 3.0
        assert profile.base_kw == 1.0
        assert profile.load_factor > 0.0

    def test_persistence_predictor_fallback(self):
        pred = PersistencePredictor()
        result = pred.predict()
        assert len(result) == 24
        assert result[0] == 2.0  # default baseline

    def test_persistence_predictor_with_history(self):
        pred = PersistencePredictor()
        history_vals = [i * 0.5 for i in range(24)]
        pred.add_history(LoadProfile(values=history_vals))
        result = pred.predict()
        assert result == history_vals

    def test_similar_day_predictor(self):
        pred = SimilarDayPredictor(n_similar=2)
        # Add weekday and weekend
        weekday_vals = [2.0] * 24
        weekend_vals = [1.0] * 24
        pred.add_history(LoadProfile(values=weekday_vals, day_type="weekday"))
        pred.add_history(LoadProfile(values=weekend_vals, day_type="weekend"))
        pred.add_history(LoadProfile(values=weekday_vals, day_type="weekday"))

        pred_weekday = pred.predict(day_type="weekday")
        assert pred_weekday[0] == 2.0

        pred_weekend = pred.predict(day_type="weekend")
        assert pred_weekend[0] == 1.0

    def test_profile_cluster_predictor(self):
        pred = ProfileClusterPredictor(n_clusters=2)
        p1 = LoadProfile(values=[1.0] * 24)
        p2 = LoadProfile(values=[5.0] * 24)
        pred.add_history(p1)
        pred.add_history(p2)
        train_res = pred.train()
        assert train_res["status"] == "trained"
        prediction = pred.predict()
        assert len(prediction) == 24

    def test_ensemble_predictor(self):
        pred = EnsemblePredictor(weights={"persistence": 0.5, "similar_day": 0.5, "profile_cluster": 0.0})
        p = LoadProfile(values=[3.0] * 24)
        pred.add_history(p)
        pred.train()
        res = pred.predict()
        assert len(res) == 24
        assert pytest.approx(res[0], 0.1) == 3.0

    def test_temperature_adjusted_predictor(self):
        base = PersistencePredictor()
        base.add_history(LoadProfile(values=[2.0] * 24))
        adj_pred = TemperatureAdjustedPredictor(base_predictor=base, heating_threshold_c=18.0)
        # Cold temperature (10°C) should increase heating load
        temps = [10.0] * 24
        cold_res = adj_pred.predict_with_temperature(temps)
        assert cold_res[0] > 2.0

    def test_prediction_metrics(self):
        actual = [1.0, 2.0, 3.0, 4.0]
        predicted = [1.1, 1.9, 3.2, 3.8]
        metrics = prediction_metrics(actual, predicted)
        assert metrics["mae"] > 0
        assert metrics["rmse"] > 0
        assert metrics["mape"] > 0
        assert metrics["r2"] > 0.9  # very close fit


# ---------------------------------------------------------------------------
# Tariff Catalogue Tests
# ---------------------------------------------------------------------------

class TestTariffCatalogue:
    def test_price_slot_containment(self):
        slot_normal = PriceSlot(start_hour=9, end_hour=17, price_per_kwh=0.25)
        assert slot_normal.contains_hour(9)
        assert slot_normal.contains_hour(16)
        assert not slot_normal.contains_hour(17)
        assert not slot_normal.contains_hour(8)

        # Midnight wrap (22 to 6)
        slot_midnight = PriceSlot(start_hour=22, end_hour=6, price_per_kwh=0.10)
        assert slot_midnight.contains_hour(23)
        assert slot_midnight.contains_hour(2)
        assert not slot_midnight.contains_hour(12)

    def test_tariff_plan_hourly_rates(self):
        plan = TariffPlan(
            name="Test TOU",
            tariff_type=TariffType.TIME_OF_USE,
            import_slots=[
                PriceSlot(0, 12, 0.10, TimeSlot.OFF_PEAK),
                PriceSlot(12, 24, 0.30, TimeSlot.PEAK),
            ],
            export_slots=[
                PriceSlot(0, 24, 0.05, TimeSlot.SHOULDER),
            ],
        )
        assert plan.import_rate(5) == 0.10
        assert plan.import_rate(15) == 0.30
        assert plan.export_rate(10) == 0.05
        assert len(plan.hourly_import_rates()) == 24

    def test_prebuilt_catalogues_exist(self):
        assert "vn_evn_commercial_tou" in TARIFF_CATALOGUE
        assert "au_amber_spot" in TARIFF_CATALOGUE
        assert "de_awattar" in TARIFF_CATALOGUE
        assert "uk_octopus_agile" in TARIFF_CATALOGUE
        assert "us_tou_residential" in TARIFF_CATALOGUE

        evn = TARIFF_CATALOGUE["vn_evn_commercial_tou"]
        assert evn.currency == "VND"
        assert evn.demand_charge_per_kw > 0

    def test_dynamic_pricing_feed(self):
        feed = DynamicPricingFeed()
        prices = [
            SpotPrice("2026-09-27T00:00:00Z", 0.05),
            SpotPrice("2026-09-27T01:00:00Z", 0.02),
            SpotPrice("2026-09-27T02:00:00Z", 0.15),
            SpotPrice("2026-09-27T03:00:00Z", 0.08),
        ]
        feed.set_prices(prices)
        assert feed.get_current_price().price == 0.05

        cheapest = feed.cheapest_hours(2, window=4)
        assert 1 in cheapest  # 0.02 is hour 1
        assert 0 in cheapest  # 0.05 is hour 0

        expensive = feed.most_expensive_hours(1, window=4)
        assert expensive == [2]  # 0.15 is hour 2

    def test_carbon_tracker(self):
        tracker = CarbonTracker(default_intensity=400.0)
        assert tracker.current_intensity() == 400.0

        data = [
            CarbonIntensity("0h", 500.0),
            CarbonIntensity("1h", 200.0),
            CarbonIntensity("2h", 350.0),
        ]
        tracker.set_forecast(data)
        assert tracker.current_intensity() == 500.0
        greenest = tracker.greenest_hours(1, window=3)
        assert greenest == [1]  # 200g/kWh is hour 1

        savings = tracker.carbon_savings(shifted_kwh=10.0, from_intensity=500.0, to_intensity=200.0)
        assert savings == 3.0  # 10 * 300 / 1000 = 3 kg CO2

    def test_bill_calculator(self):
        plan = TariffPlan(
            name="Simple Plan",
            tariff_type=TariffType.FIXED,
            currency="USD",
            import_slots=[PriceSlot(0, 24, 0.20)],
            export_slots=[PriceSlot(0, 24, 0.05)],
            demand_charge_per_kw=2.0,
            fixed_daily_charge=1.0,
            gst_pct=10.0,
        )
        calc = BillCalculator(plan)
        import_kwh = [1.0] * 24  # 24 kWh * 0.20 = $4.80
        export_kwh = [2.0] * 24  # 48 kWh * 0.05 = $2.40
        bill = calc.calculate_daily(import_kwh, export_kwh, peak_demand_kw=5.0)

        assert bill["import_cost"] == 4.80
        assert bill["export_revenue"] == 2.40
        assert bill["demand_cost"] == 10.00
        assert bill["fixed_charge"] == 1.00
        # Subtotal = 4.80 - 2.40 + 10.00 + 1.00 = 13.40
        assert bill["subtotal"] == 13.40
        assert bill["gst"] == 1.34
        assert bill["total"] == 14.74

    def test_compare_tariffs(self):
        plan = TARIFF_CATALOGUE["vn_evn_commercial_tou"]
        calc = BillCalculator(plan)
        import_kwh = [2.0] * 24
        export_kwh = [1.0] * 24
        comparison = calc.compare_tariffs(import_kwh, export_kwh)
        assert len(comparison) >= 3
        # Comparison should be sorted by total cost ascending
        assert comparison[0]["total"] <= comparison[-1]["total"]
