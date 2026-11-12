"""
Automated Pipeline Updater Orchestrator
Invoked periodically by Google Cloud Scheduler to check for new Sentinel-2 passes,
execute segmentation, pull live Bursa stock valuation, and commit rows to BigQuery.
"""

import os
from datetime import datetime, timezone
from backend.stac_service import StacService
from backend.geoint_service import GeointService
from backend.stock_service import StockService
from backend.bigquery_service import BigQueryService
from backend.gcp_service import GcpService

class PipelineUpdater:
    def __init__(self):
        self.stac_service = StacService()
        self.geoint_service = GeointService()
        self.stock_service = StockService()
        self.bigquery_service = BigQueryService()
        self.gcp_service = GcpService()

    def run_update_cycle(self, force: bool = False) -> dict:
        """
        Executes end-to-end update cycle:
        1. STAC catalog pass check
        2. Computer Vision / YOLO segmentation
        3. Stock market telemetry sync (6742.KL)
        4. BigQuery commit
        5. Cloud Storage sync
        """
        cycle_start = datetime.now(timezone.utc)
        print(f"[Pipeline Updater] Running automated update cycle at {cycle_start.isoformat()}...")

        # 1. Fetch available scenes
        scenes = self.stac_service.get_scenes()
        latest_scene = scenes[0] if scenes else None
        
        # 2. Run segmentation
        cv_metrics = self.geoint_service.analyze()

        # 3. Pull latest Bursa stock telemetry (forcing fresh pull if requested)
        stock_data = self.stock_service.get_stock_data(refresh=force)

        # 4. Construct telemetry record
        record = self.bigquery_service.build_record(cv_metrics, stock_data)

        # 5. Commit to BigQuery via GCP service
        bq_result = self.bigquery_service.sync_to_bigquery(record)

        # 6. Upload current outputs to GCS if configured
        gcs_result = self.gcp_service.upload_to_gcs(
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kulai_2026.png"),
            f"satellite_crops/kulai_{datetime.now(timezone.utc).strftime('%Y%m%d')}.png"
        )

        cycle_end = datetime.now(timezone.utc)
        duration_s = (cycle_end - cycle_start).total_seconds()

        summary = {
            "status": "COMPLETED",
            "cycle_timestamp": cycle_start.isoformat(),
            "duration_seconds": round(duration_s, 2),
            "latest_satellite_scene": latest_scene["id"] if latest_scene else "N/A",
            "scene_date": latest_scene["date"] if latest_scene else "N/A",
            "quantified_metrics": {
                "solar_area_m2": cv_metrics["solar_area_m2"],
                "est_solar_capacity_mw": cv_metrics["est_solar_mw"],
                "data_hall_roof_m2": cv_metrics["roof_area_m2"],
                "stock_price_myr": stock_data.get("current_price"),
                "stock_gain_pct": stock_data.get("gain_pct")
            },
            "bigquery_commit": bq_result["status"],
            "cloud_storage_sync": gcs_result["status"]
        }

        print(f"[Pipeline Updater] Update cycle completed in {duration_s:.2f}s: BigQuery={bq_result['status']}")
        return summary
