"""
Comprehensive Automated Test Suite for Institutional Intelligence Platform
Tests Financial Modeling, SAR Radar, Quant Exporter, Alerting, and Mosaic Compliance.
"""

import os
import unittest
from fastapi.testclient import TestClient
from backend.app import app
from backend.financial_model import FinancialValuationEngine
from backend.sar_service import SarRadarService
from backend.quant_service import QuantFeatureStore
from backend.alert_service import AlertDispatcher

class TestInstitutionalIntelligence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_financial_engine_math(self):
        """Test physical-to-financial conversion calculations."""
        engine = FinancialValuationEngine(lease_usd_per_kw=135.0, usd_to_myr=4.45, pue=1.22)
        res = engine.compute_valuation(roof_area_m2=752000.0, solar_area_m2=1035800.0, est_solar_mw=103.6)
        
        self.assertIn("critical_it_load", res)
        self.assertIn("financial_runway", res)
        self.assertIn("consensus_variance", res)
        self.assertGreater(res["critical_it_load"]["critical_it_mw"], 500.0)
        self.assertGreater(res["financial_runway"]["annual_revenue_myr"], 500000000.0)
        self.assertEqual(res["consensus_variance"]["status"], "AHEAD_OF_SCHEDULE")
        self.assertEqual(len(res["sensitivity_matrix"]), 4)

    def test_sar_telemetry_and_layer(self):
        """Test Sentinel-1 SAR telemetry and pseudo-color radar layer."""
        sar = SarRadarService()
        telemetry = sar.get_sar_telemetry()
        self.assertEqual(telemetry["all_weather_capability"], True)
        self.assertEqual(telemetry["cloud_penetration_pct"], 100.0)
        self.assertIn("dihedral_structural_delta_db", telemetry)

        # Test streaming layer
        resp = self.client.get("/api/layers/sar_composite")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("content-type"), "image/png")
        self.assertGreater(len(resp.content), 1000)

    def test_quant_csv_and_mosaic_provenance(self):
        """Test Quant time-series export and SHA-256 Mosaic Theory compliance."""
        quant = QuantFeatureStore()
        csv_text = quant.export_csv()
        self.assertIn("timestamp_utc,ticker", csv_text)
        self.assertIn("solar_capacity_mw", csv_text)
        self.assertIn("critical_it_mw", csv_text)
        self.assertIn("provenance_hash", csv_text)

        dossier = quant.get_compliance_dossier()
        self.assertEqual(dossier["legal_status"], "COMPLIANT_NON_MNPI")
        self.assertEqual(len(dossier["cryptographic_provenance"]["sha256_hash"]), 64)

        # HTTP Endpoint checks
        resp_csv = self.client.get("/api/quant/export/csv")
        self.assertEqual(resp_csv.status_code, 200)
        self.assertEqual(resp_csv.headers.get("content-type"), "text/csv; charset=utf-8")

        resp_prov = self.client.get("/api/quant/provenance")
        self.assertEqual(resp_prov.status_code, 200)
        self.assertIn("cryptographic_provenance", resp_prov.json())

    def test_alert_dispatcher(self):
        """Test institutional alert payload building and dispatch."""
        dispatcher = AlertDispatcher()
        payload = dispatcher.build_alert_payload("TEST_ALERT", {"est_solar_mw": 103.6, "roof_area_m2": 752000.0}, {})
        self.assertIn("[ALPHA ALERT]", payload["title"])
        self.assertEqual(payload["compliance"], "MOSAIC_THEORY_VERIFIED_NON_MNPI")

        os.environ["ADMIN_TOKEN"] = "test-admin-token"
        try:
            resp = self.client.post("/api/alerts/dispatch", headers={"X-Admin-Token": "test-admin-token"})
        finally:
            os.environ.pop("ADMIN_TOKEN", None)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "SIMULATED_SUCCESS")

    def test_financial_routes(self):
        """Test /api/financial/valuation and /api/financial/simulate routes."""
        resp_val = self.client.get("/api/financial/valuation")
        self.assertEqual(resp_val.status_code, 200)
        data = resp_val.json()
        self.assertIn("financial_runway", data)
        self.assertIn("tenant_breakdown", data)
        self.assertIn("sea_ltd", data["tenant_breakdown"])
        self.assertIn("nvidia_dgx", data["tenant_breakdown"])

        sim_params = {"lease_usd_per_kw": 150.0, "usd_to_myr": 4.50, "pue": 1.20}
        resp_sim = self.client.post("/api/financial/simulate", json=sim_params)
        self.assertEqual(resp_sim.status_code, 200)
        sim_data = resp_sim.json()
        self.assertEqual(sim_data["financial_runway"]["monthly_lease_usd_per_kw"], 150.0)

    def test_sotp_valuation_and_endpoints(self):
        """Test institutional Sum-of-the-Parts (SOTP) target price engine and routes."""
        engine = FinancialValuationEngine()
        sotp = engine.compute_sotp_valuation()

        self.assertIn("target_price_myr", sotp)
        self.assertIn("implied_upside_pct", sotp)
        self.assertIn("group_enterprise_value_myr", sotp)
        self.assertGreater(sotp["target_price_myr"], 5.01) # Target price exceeds current Bursa market quote
        self.assertEqual(len(sotp["segments"]), 4)

        # GET /api/financial/sotp
        resp_sotp = self.client.get("/api/financial/sotp")
        self.assertEqual(resp_sotp.status_code, 200)
        sotp_data = resp_sotp.json()
        self.assertIn("target_price_myr", sotp_data)
        self.assertGreater(sotp_data["implied_upside_pct"], 50.0)

        # POST /api/financial/sotp-simulate
        sim_sotp = {"dc_multiple": 20.0, "powerseraya_multiple": 7.5, "wessex_multiple": 1.10}
        resp_sim_sotp = self.client.post("/api/financial/sotp-simulate", json=sim_sotp)
        self.assertEqual(resp_sim_sotp.status_code, 200)
        sim_res = resp_sim_sotp.json()
        self.assertGreater(sim_res["target_price_myr"], sotp_data["target_price_myr"])

    def test_layer_image_caching_headers(self):
        """Test HTTP Cache-Control and ETag headers for CDN/browser edge caching."""
        resp = self.client.get("/api/layers/annotated")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("cache-control", resp.headers)
        self.assertIn("public, max-age=86400", resp.headers["cache-control"])
        self.assertIn("etag", resp.headers)

        resp_epoch = self.client.get("/api/layers/epoch/2026_08")
        self.assertEqual(resp_epoch.status_code, 200)
        self.assertIn("cache-control", resp_epoch.headers)
        self.assertIn("etag", resp_epoch.headers)

if __name__ == "__main__":
    unittest.main()
