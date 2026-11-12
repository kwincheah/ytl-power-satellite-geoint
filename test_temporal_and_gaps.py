"""
Automated Test Suite for Multi-Temporal Timeline (2023-2026),
14-Quarter Bursa Financial Series, Thermal Infrared (TIR), TNB Substation, and Bitemporal PIT Quant Engine.
"""

import unittest
from fastapi.testclient import TestClient
from backend.app import app

class TestTemporalAndIndustryGaps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_timeline_epochs_endpoint(self):
        """Verify /api/timeline/epochs returns all 14 quarters and milestone filtering."""
        resp = self.client.get("/api/timeline/epochs")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("epochs", data)
        self.assertEqual(len(data["epochs"]), 14)
        self.assertEqual(data["total_quarters"], 14)
        self.assertEqual(len(data["milestones"]), 5)

        # Test milestone mode filtering
        resp_ms = self.client.get("/api/timeline/epochs?mode=milestones")
        self.assertEqual(resp_ms.status_code, 200)
        data_ms = resp_ms.json()
        self.assertEqual(len(data_ms["epochs"]), 5)
        epoch_ids = [e["id"] for e in data_ms["epochs"]]
        self.assertEqual(epoch_ids, ["2023_03", "2023_12", "2024_05", "2025_11", "2026_08"])

    def test_timeline_epoch_detail_endpoint(self):
        """Verify /api/timeline/epoch/{epoch_id} returns accurate physical metrics and Bursa financials."""
        for eid in ["2023_03", "2023_06", "2023_12", "2024_05", "2025_11", "2026_08"]:
            resp = self.client.get(f"/api/timeline/epoch/{eid}")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["id"], eid)
            self.assertIn("solar_capacity_mw", data)
            self.assertIn("stock_price_myr", data)
            self.assertIn("revenue_myr_m", data)
            self.assertIn("patami_myr_m", data)
            self.assertGreaterEqual(data["critical_it_mw"], 0)

    def test_quarterly_financial_series_endpoint(self):
        """Verify /api/financial/quarterly-series returns 14 quarters with Bursa statements."""
        resp = self.client.get("/api/financial/quarterly-series")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["ticker"], "6742.KL")
        self.assertEqual(data["total_quarters"], 14)
        series = data["historical_and_forecast_series"]
        self.assertEqual(len(series), 14)
        self.assertIn("revenue_myr_m", series[0])
        self.assertIn("patami_myr_m", series[0])
        self.assertIn("powerseraya_profit_m", series[0])
        self.assertIn("kulai_revenue_m", series[-1])
        self.assertGreater(series[-1]["kulai_revenue_m"], 200)

    def test_epoch_layer_images(self):
        """Verify /api/layers/epoch/{epoch_id} streams valid PNG bytes."""
        for eid in ["2023_03", "2023_06", "2023_12", "2024_05", "2025_11", "2026_08"]:
            resp = self.client.get(f"/api/layers/epoch/{eid}")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.headers["content-type"], "image/png")
            self.assertGreater(len(resp.content), 5000)

    def test_thermal_radiometry_layer_and_telemetry(self):
        """Verify Thermal Infrared image stream and physical load factor telemetry."""
        img_resp = self.client.get("/api/layers/thermal")
        self.assertEqual(img_resp.status_code, 200)
        self.assertEqual(img_resp.headers["content-type"], "image/png")
        self.assertGreater(len(img_resp.content), 10000)

        tel_resp = self.client.get("/api/thermal/telemetry")
        self.assertEqual(tel_resp.status_code, 200)
        data = tel_resp.json()
        self.assertIn("operational_thermal_load_mw", data)
        self.assertGreater(data["operational_thermal_load_mw"], 500)
        self.assertGreater(data["operational_load_factor_pct"], 70)
        self.assertGreater(data["max_delta_t_kelvin"], 5.0)

    def test_substation_layer_and_telemetry(self):
        """Verify TNB 275/500kV Main Intake Substation image and grid telemetry."""
        img_resp = self.client.get("/api/layers/substation")
        self.assertEqual(img_resp.status_code, 200)
        self.assertEqual(img_resp.headers["content-type"], "image/png")
        self.assertGreater(len(img_resp.content), 10000)

        tel_resp = self.client.get("/api/substation/telemetry")
        self.assertEqual(tel_resp.status_code, 200)
        data = tel_resp.json()
        self.assertEqual(data["installed_capacity_mva"], 600.0)
        self.assertEqual(data["transformer_bays_energized"], 3)
        self.assertEqual(data["grid_interconnection_status"], "SYNCHRONIZED_ACTIVE")

    def test_bitemporal_pit_quant_feed(self):
        """Verify strict bitemporal separation and 14 quarters in PIT dataset."""
        resp = self.client.get("/api/quant/pit")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("summary", data)
        self.assertIn("series", data)
        self.assertEqual(data["summary"]["bitemporal_rigor"], "STRICT_ZERO_LOOKAHEAD")
        self.assertEqual(len(data["series"]), 14)
        self.assertGreater(data["summary"]["information_coefficient_90d"], 0.20)
        self.assertGreater(data["summary"]["t_statistic"], 3.0)

        csv_resp = self.client.get("/api/quant/export/pit-csv")
        self.assertEqual(csv_resp.status_code, 200)
        self.assertEqual(csv_resp.headers["content-type"], "text/csv; charset=utf-8")
        lines = csv_resp.text.strip().splitlines()
        self.assertEqual(len(lines), 15)  # 1 header + 14 quarters
        self.assertIn("observation_time,knowledge_time,signal_lag_hours", lines[0])

if __name__ == "__main__":
    unittest.main()
