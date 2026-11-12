"""
Comprehensive Automated Test Suite for YTL Power GEOINT Webapp
"""

import os
import unittest
from fastapi.testclient import TestClient
from backend.app import app

TEST_TOKEN = "test-admin-token"
ADMIN = {"X-Admin-Token": TEST_TOKEN}

class TestGeointWebapp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._old_token = os.environ.get("ADMIN_TOKEN")
        os.environ["ADMIN_TOKEN"] = TEST_TOKEN
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        if cls._old_token is None:
            os.environ.pop("ADMIN_TOKEN", None)
        else:
            os.environ["ADMIN_TOKEN"] = cls._old_token

    def test_root_index_html(self):
        """Verify root endpoint serves the HTML interface."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("YTL Power (6742.KL) Satellite GEOINT", resp.text)
        self.assertIn("Multi-Temporal Satellite Studio", resp.text)
        self.assertIn("Consolidated SOTP Target Price Model", resp.text)

    def test_kpi_endpoint(self):
        """Verify /api/kpi returns correct quantitative structure."""
        resp = self.client.get("/api/kpi")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["ticker"], "6742.KL")
        self.assertIn("solar", data)
        self.assertIn("data_halls", data)
        self.assertIn("stock", data)
        self.assertGreater(data["solar"]["current_area_m2"], 1000000)
        self.assertGreater(data["solar"]["est_capacity_mw"], 100)
        self.assertGreater(data["stock"]["current_price"], 0)

    def test_stock_endpoint(self):
        """Verify /api/stock returns series and milestones."""
        resp = self.client.get("/api/stock")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("series", data)
        self.assertIn("milestones", data)
        self.assertGreater(len(data["series"]), 10)

    def test_scenes_endpoint(self):
        """Verify /api/scenes returns Sentinel-2 passes."""
        resp = self.client.get("/api/scenes")
        self.assertEqual(resp.status_code, 200)
        scenes = resp.json()
        self.assertIsInstance(scenes, list)
        self.assertGreater(len(scenes), 0)

    def test_layer_images_endpoint(self):
        """Verify all image layers stream valid PNG data."""
        layers = ["2023", "2026", "annotated", "solar_only", "roof_only", "difference", "campus_roi", "yolo_annotated", "sar_composite", "thermal", "substation"]
        for layer in layers:
            resp = self.client.get(f"/api/layers/{layer}")
            self.assertEqual(resp.status_code, 200, f"Layer {layer} failed")
            self.assertEqual(resp.headers.get("content-type"), "image/png")
            self.assertGreater(len(resp.content), 1000)

    def test_invalid_layer_400(self):
        """Verify invalid layer returns 400 Bad Request."""
        resp = self.client.get("/api/layers/unknown_layer")
        self.assertEqual(resp.status_code, 400)

    def test_analyze_endpoint(self):
        """Verify /api/analyze handles dynamic parameter tuning."""
        params = {
            "solar_v_max": 80,
            "solar_s_max": 130,
            "roof_v_min": 170,
            "mw_per_hectare": 1.1,
            "min_solar_contour": 250,
            "min_roof_contour": 120
        }
        resp = self.client.post("/api/analyze", json=params)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("metrics", data)
        self.assertGreater(data["metrics"]["solar_area_m2"], 0)

        # Test reports/analyze alias
        resp_alias = self.client.post("/api/reports/analyze")
        self.assertEqual(resp_alias.status_code, 200)

    def test_gcp_and_scheduler_endpoints(self):
        """Verify Cloud Run health check and GCP status."""
        health_resp = self.client.get("/_healthz")
        self.assertEqual(health_resp.status_code, 200)
        self.assertEqual(health_resp.json()["status"], "healthy")

        gcp_resp = self.client.get("/api/gcp/status")
        self.assertEqual(gcp_resp.status_code, 200)
        self.assertIn("platform", gcp_resp.json())

        # Test Cloud Scheduler webhook
        pipeline_resp = self.client.post("/api/pipeline/update", headers=ADMIN)
        self.assertEqual(pipeline_resp.status_code, 200)
        self.assertEqual(pipeline_resp.json()["status"], "COMPLETED")

    def test_yolo_engine_endpoints(self):
        """Verify YOLO detection engine status and selection."""
        status_resp = self.client.get("/api/engine/status")
        self.assertEqual(status_resp.status_code, 200)
        self.assertIn("active_engine", status_resp.json())

        select_resp = self.client.post("/api/engine/select", json={"engine": "yolo"}, headers=ADMIN)
        self.assertEqual(select_resp.status_code, 200)
        self.assertEqual(select_resp.json()["active_engine"], "yolo")

        # Switch back to spectral
        select_resp2 = self.client.post("/api/engine/select", json={"engine": "spectral"}, headers=ADMIN)
        self.assertEqual(select_resp2.status_code, 200)
        self.assertEqual(select_resp2.json()["active_engine"], "spectral")

    def test_bigquery_endpoints(self):
        """Verify BigQuery schema, sync and audit log endpoints."""
        schema_resp = self.client.get("/api/bigquery/schema")
        self.assertEqual(schema_resp.status_code, 200)
        self.assertIn("schema", schema_resp.json())

        sync_resp = self.client.post("/api/bigquery/sync", headers=ADMIN)
        self.assertEqual(sync_resp.status_code, 200)
        sync_data = sync_resp.json()
        self.assertIn("status", sync_data)
        self.assertIn("record", sync_data)

        logs_resp = self.client.get("/api/bigquery/logs")
        self.assertEqual(logs_resp.status_code, 200)
        self.assertGreater(len(logs_resp.json()["logs"]), 0)

    def test_report_summary(self):
        """Verify executive report generation."""
        resp = self.client.get("/api/report/summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("key_findings", data)
        self.assertIn("kpi", data)


class TestAdminGuard(unittest.TestCase):
    """Admin-only endpoints must reject requests without a valid token."""

    PROTECTED = [
        ("/api/pipeline/update", None),
        ("/api/bigquery/sync", None),
        ("/api/alerts/dispatch", None),
        ("/api/engine/select", {"engine": "spectral"}),
    ]

    def setUp(self):
        self._old_token = os.environ.get("ADMIN_TOKEN")
        self.client = TestClient(app)

    def tearDown(self):
        if self._old_token is None:
            os.environ.pop("ADMIN_TOKEN", None)
        else:
            os.environ["ADMIN_TOKEN"] = self._old_token

    def test_disabled_when_token_not_configured(self):
        os.environ.pop("ADMIN_TOKEN", None)
        for url, body in self.PROTECTED:
            resp = self.client.post(url, json=body, headers={"X-Admin-Token": "anything"})
            self.assertEqual(resp.status_code, 403, url)

    def test_missing_or_wrong_token_rejected(self):
        os.environ["ADMIN_TOKEN"] = TEST_TOKEN
        for url, body in self.PROTECTED:
            self.assertEqual(self.client.post(url, json=body).status_code, 401, url)
            wrong = self.client.post(url, json=body, headers={"X-Admin-Token": "wrong"})
            self.assertEqual(wrong.status_code, 401, url)

    def test_public_endpoints_need_no_token(self):
        os.environ.pop("ADMIN_TOKEN", None)
        self.assertEqual(self.client.get("/api/kpi").status_code, 200)
        self.assertEqual(self.client.post("/api/analyze").status_code, 200)

if __name__ == "__main__":
    unittest.main()
