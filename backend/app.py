"""
YTL Power (6742.KL) Satellite GEOINT & Alpha Tracker - FastAPI Web Server
"""

import os
import hashlib
import secrets
from typing import Optional
from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from backend.geoint_service import GeointService
from backend.stock_service import StockService
from backend.stac_service import StacService
from backend.bigquery_service import BigQueryService
from backend.gcp_service import GcpService
from backend.yolo_service import YoloSegmentationService
from backend.pipeline_updater import PipelineUpdater
from backend.financial_model import FinancialValuationEngine
from backend.sar_service import SarRadarService
from backend.quant_service import QuantFeatureStore
from backend.alert_service import AlertDispatcher
from backend.temporal_service import temporal_service
from backend.thermal_service import thermal_service
from backend.substation_service import substation_service
from backend.pit_service import pit_service

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

app = FastAPI(
    title="YTL Power (6742.KL) Satellite GEOINT & Alpha Platform",
    description="Near-Real-Time Infrastructure Audit and Financial Correlation System",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services initialization
geoint_service = GeointService()
stock_service = StockService()
stac_service = StacService()
bigquery_service = BigQueryService()
gcp_service = GcpService()
yolo_service = YoloSegmentationService()
pipeline_updater = PipelineUpdater()
financial_engine = FinancialValuationEngine()
sar_service = SarRadarService()
quant_store = QuantFeatureStore()
alert_dispatcher = AlertDispatcher()

def require_admin(x_admin_token: Optional[str] = Header(default=None)) -> None:
    """Guards endpoints that write to BigQuery, send webhooks, run the pipeline or change shared state.

    Set the ADMIN_TOKEN environment variable and send it in the X-Admin-Token header.
    Without ADMIN_TOKEN, these actions are disabled, so a public deployment is read-only by default.
    """
    expected = os.environ.get("ADMIN_TOKEN")
    if not expected:
        raise HTTPException(status_code=403, detail="Admin actions are disabled on this deployment.")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=401, detail="Missing or invalid X-Admin-Token header.")

# Detection Engine state ("spectral" or "yolo")
current_detection_engine = "spectral"

class AnalysisParams(BaseModel):
    solar_v_max: Optional[int] = 75
    solar_s_max: Optional[int] = 120
    roof_v_min: Optional[int] = 175
    mw_per_hectare: Optional[float] = 1.0
    min_solar_contour: Optional[int] = 200
    min_roof_contour: Optional[int] = 100

@app.get("/")
def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "YTL Power GEOINT Backend Operational. Place index.html in /static."}

@app.get("/api/kpi")
def get_kpi():
    """Returns top-line geospatial & financial key performance indicators."""
    cv_metrics = geoint_service.analyze()
    stock_data = stock_service.get_stock_data()

    return {
        "ticker": stock_data.get("ticker", "6742.KL"),
        "company": stock_data.get("company", "YTL Power International Berhad"),
        "asset": "YTL Green Data Center Park & 500MW Solar Campus (Kulai, Johor)",
        "coordinates": {"lat": 1.6225, "lon": 103.5250},
        "solar": {
            "current_area_m2": cv_metrics["solar_area_m2"],
            "baseline_area_m2": cv_metrics["solar_area_2023_m2"],
            "delta_area_m2": cv_metrics["solar_delta_m2"],
            "est_capacity_mw": cv_metrics["est_solar_mw"],
            "target_capacity_mw": cv_metrics["target_solar_mw"],
            "pct_target_achieved": cv_metrics["pct_target_achieved"],
            "cluster_count": cv_metrics["solar_cluster_count"]
        },
        "data_halls": {
            "current_roof_m2": cv_metrics["roof_area_m2"],
            "baseline_roof_m2": cv_metrics["roof_area_2023_m2"],
            "delta_roof_m2": cv_metrics["roof_delta_m2"],
            "cluster_count": cv_metrics["roof_cluster_count"],
            "readiness": "High (Multi-hall structural completion)"
        },
        "stock": {
            "baseline_price": stock_data.get("baseline_price", 0.77),
            "current_price": stock_data.get("current_price", 5.01),
            "gain_pct": stock_data.get("gain_pct", 553.0),
            "currency": "MYR"
        },
        "satellite": {
            "platform": "Sentinel-2 L2A",
            "resolution": "10m COG HTTP Range",
            "baseline_date": "2023-03-16",
            "latest_date": "2026-08-22"
        }
    }

@app.get("/api/stock")
def get_stock():
    """Returns historical price series and milestone points."""
    return stock_service.get_stock_data()

@app.get("/api/scenes")
def get_scenes():
    """Returns Sentinel-2 scene passes."""
    return stac_service.get_scenes()

@app.get("/_healthz")
@app.get("/api/health")
@app.get("/health")
def health_check():
    """Cloud Run health check probe."""
    return {"status": "healthy", "service": "ytl-geoint-service"}

@app.get("/api/gcp/status")
def get_gcp_status():
    """Returns operational status of Google Cloud services."""
    return gcp_service.get_cloud_status()

@app.post("/api/pipeline/update", dependencies=[Depends(require_admin)])
def trigger_pipeline_update(force: bool = False):
    """
    Cloud Scheduler webhook endpoint: triggers full automated update cycle.
    1. STAC scene discovery
    2. Computer vision & YOLO inference
    3. Stock telemetry sync
    4. BigQuery row commit
    5. GCS asset upload
    """
    return pipeline_updater.run_update_cycle(force=force)

@app.get("/api/engine/status")
def get_engine_status():
    """Returns the current detection engine (Spectral vs YOLOv8-seg)."""
    global current_detection_engine
    return {
        "active_engine": current_detection_engine,
        "yolo_installed": yolo_service.has_ultralytics,
        "yolo_weights_loaded": yolo_service.model is not None,
        "available_engines": ["spectral", "yolo"]
    }

class EngineSelectRequest(BaseModel):
    engine: str

@app.post("/api/engine/select", dependencies=[Depends(require_admin)])
def select_engine(req: EngineSelectRequest):
    """Switches active detection engine between 'spectral' and 'yolo'."""
    global current_detection_engine
    if req.engine not in ["spectral", "yolo"]:
        raise HTTPException(status_code=400, detail="Engine must be 'spectral' or 'yolo'")
    current_detection_engine = req.engine
    return {"status": "success", "active_engine": current_detection_engine}

def _cached_image_response(img_bytes: bytes) -> Response:
    """Helper returning PNG response with CDN Cache-Control and deterministic ETag."""
    etag = f'"{hashlib.sha256(img_bytes).hexdigest()[:16]}"'
    headers = {
        "Cache-Control": "public, max-age=86400, stale-while-revalidate=3600",
        "ETag": etag
    }
    return Response(content=img_bytes, media_type="image/png", headers=headers)

@app.get("/api/layers/{layer_name}")
def get_layer_image(layer_name: str):
    """
    Streams image bytes for the requested layer:
    '2023', '2026', 'annotated', 'solar_only', 'roof_only', 'difference', 'campus_roi', 'yolo_annotated', 'sar_composite', 'thermal', 'substation'
    """
    valid_layers = ["2023", "2026", "annotated", "solar_only", "roof_only", "difference", "campus_roi", "yolo_annotated", "sar_composite", "thermal", "substation"]
    if layer_name not in valid_layers:
        raise HTTPException(status_code=400, detail=f"Invalid layer: {layer_name}. Must be one of {valid_layers}")

    if layer_name == "thermal":
        return _cached_image_response(thermal_service.generate_thermal_image())

    if layer_name == "substation":
        return _cached_image_response(substation_service.generate_substation_image())

    if layer_name == "yolo_annotated":
        img_rgb = geoint_service.img_2026_rgb
        yolo_res = yolo_service.segment(img_rgb, geoint_service.campus_mask, geoint_service.dc_zone_mask)
        import io
        from PIL import Image
        pil_img = Image.fromarray(yolo_res["annotated_rgb"])
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        return _cached_image_response(buf.getvalue())

    if layer_name == "sar_composite":
        img_bytes = sar_service.get_sar_image_bytes(
            geoint_service.img_2026_rgb,
            geoint_service.latest_solar_mask,
            geoint_service.latest_roof_mask
        )
        return _cached_image_response(img_bytes)

    img_bytes = geoint_service.get_image_bytes(layer_name, format="PNG")
    return _cached_image_response(img_bytes)

@app.get("/api/layers/epoch/{epoch_id}")
def get_epoch_layer_image(epoch_id: str, annotated: bool = True):
    """Streams synthesized multi-spectral satellite composite for specified historical epoch with CDN caching."""
    img_bytes = temporal_service.generate_epoch_image(epoch_id, annotated=annotated)
    return _cached_image_response(img_bytes)

# --- Institutional Financial & Valuation Endpoints ---

class FinancialSimParams(BaseModel):
    lease_usd_per_kw: Optional[float] = 135.0
    usd_to_myr: Optional[float] = 4.45
    pue: Optional[float] = 1.22
    sea_ltd_lease_usd: Optional[float] = 115.0
    nvidia_lease_usd: Optional[float] = 155.0

class SotpSimParams(BaseModel):
    dc_multiple: Optional[float] = 18.0
    powerseraya_multiple: Optional[float] = 7.0
    wessex_multiple: Optional[float] = 1.05
    net_debt_myr: Optional[float] = 31500.0

@app.get("/api/financial/valuation")
def get_financial_valuation():
    """Returns baseline physical-to-financial valuation and consensus variance."""
    cv_metrics = geoint_service.analyze()
    return financial_engine.compute_valuation(
        roof_area_m2=cv_metrics["roof_area_m2"],
        solar_area_m2=cv_metrics["solar_area_m2"],
        est_solar_mw=cv_metrics["est_solar_mw"]
    )

@app.post("/api/financial/simulate")
def simulate_financial_valuation(params: FinancialSimParams):
    """Calculates sensitivity analysis with custom lease rates, tenant splits, and FX."""
    custom_engine = FinancialValuationEngine(
        lease_usd_per_kw=params.lease_usd_per_kw or 135.0,
        usd_to_myr=params.usd_to_myr or 4.45,
        pue=params.pue or 1.22,
        sea_ltd_lease_usd=params.sea_ltd_lease_usd or 115.0,
        nvidia_lease_usd=params.nvidia_lease_usd or 155.0
    )
    cv_metrics = geoint_service.analyze()
    return custom_engine.compute_valuation(
        roof_area_m2=cv_metrics["roof_area_m2"],
        solar_area_m2=cv_metrics["solar_area_m2"],
        est_solar_mw=cv_metrics["est_solar_mw"]
    )

@app.get("/api/financial/sotp")
def get_sotp_valuation():
    """Returns institutional Sum-of-the-Parts (SOTP) target price model across all 4 operating divisions."""
    cv_metrics = geoint_service.analyze()
    val = financial_engine.compute_valuation(
        roof_area_m2=cv_metrics["roof_area_m2"],
        solar_area_m2=cv_metrics["solar_area_m2"],
        est_solar_mw=cv_metrics["est_solar_mw"]
    )
    dc_ebitda = (val.get("financial_runway") or {}).get("annual_ebitda_myr", 4279.0)
    return financial_engine.compute_sotp_valuation(kulai_ebitda_override=dc_ebitda)

@app.post("/api/financial/sotp-simulate")
def simulate_sotp_valuation(params: SotpSimParams):
    """Calculates sensitivity SOTP valuation with custom segment multiples and debt level."""
    cv_metrics = geoint_service.analyze()
    val = financial_engine.compute_valuation(
        roof_area_m2=cv_metrics["roof_area_m2"],
        solar_area_m2=cv_metrics["solar_area_m2"],
        est_solar_mw=cv_metrics["est_solar_mw"]
    )
    dc_ebitda = (val.get("financial_runway") or {}).get("annual_ebitda_myr", 4279.0)
    return financial_engine.compute_sotp_valuation(
        dc_multiple=params.dc_multiple or 18.0,
        powerseraya_multiple=params.powerseraya_multiple or 7.0,
        wessex_multiple=params.wessex_multiple or 1.05,
        net_debt_myr=params.net_debt_myr or 31500.0,
        kulai_ebitda_override=dc_ebitda
    )

@app.get("/api/financial/quarterly-series")
def get_quarterly_financial_series():
    """Returns the comprehensive 14-Quarter Bursa Financial Reporting Series (Q3 FY23 to Q4 FY26)."""
    return financial_engine.get_quarterly_financial_series()

# --- Sentinel-1 SAR Radar Telemetry ---

@app.get("/api/sar/telemetry")
def get_sar_telemetry():
    """Returns C-Band SAR radar backscatter metrics and cloud penetration index."""
    return sar_service.get_sar_telemetry()

# --- Quant Feature Feed & Mosaic Compliance ---

@app.get("/api/quant/export/csv")
def export_quant_csv():
    """Generates machine-readable time-series dataset for quantitative funds."""
    csv_data = quant_store.export_csv()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ytl_geoint_quant_features.csv"}
    )

@app.get("/api/quant/provenance")
def get_quant_provenance():
    """Returns cryptographic data provenance and Mosaic Theory legal dossier."""
    return quant_store.get_compliance_dossier()

# --- Multi-Temporal Timeline (2023 - 2026) ---

@app.get("/api/timeline/epochs")
def get_timeline_epochs(mode: str = "all"):
    """Returns chronological epoch progression metadata (all 14 quarters or 5 key milestones)."""
    return {
        "mode": mode,
        "total_quarters": 14,
        "epochs": temporal_service.get_epochs(mode=mode),
        "milestones": temporal_service.get_epochs(mode="milestones")
    }

@app.get("/api/timeline/epoch/{epoch_id}")
def get_timeline_epoch_detail(epoch_id: str):
    """Returns physical and financial metrics for a specific historical quarter."""
    return temporal_service.get_epoch_detail(epoch_id)

# --- Thermal Infrared & Grid Substation Telemetry ---

@app.get("/api/thermal/telemetry")
def get_thermal_telemetry():
    """Returns NASA ECOSTRESS / Landsat TIR thermal radiometry and load factor metrics."""
    return thermal_service.get_thermal_telemetry()

@app.get("/api/substation/telemetry")
def get_substation_telemetry():
    """Returns TNB 275/500kV Main Intake Substation interconnection telemetry."""
    return substation_service.get_substation_telemetry()

# --- Bitemporal Point-in-Time (PIT) Quant Engine ---

@app.get("/api/quant/pit")
def get_quant_pit():
    """Returns institutional bitemporal Point-in-Time alpha factor metrics and backtest statistics."""
    return {
        "summary": pit_service.get_pit_summary(),
        "series": pit_service.get_pit_series()
    }

@app.get("/api/quant/export/pit-csv")
def export_quant_pit_csv():
    """Exports strict bitemporal dataset (observation_time vs knowledge_time) in CSV."""
    csv_data = pit_service.export_pit_csv()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ytl_geoint_bitemporal_pit.csv"}
    )

# --- Institutional Alert Dispatcher ---

@app.post("/api/alerts/dispatch", dependencies=[Depends(require_admin)])
def dispatch_alert(event_type: str = "MILESTONE_ADVANCE"):
    """Dispatches formatted institutional research alert."""
    cv_metrics = geoint_service.analyze()
    valuation = financial_engine.compute_valuation(
        roof_area_m2=cv_metrics["roof_area_m2"],
        solar_area_m2=cv_metrics["solar_area_m2"],
        est_solar_mw=cv_metrics["est_solar_mw"]
    )
    payload = alert_dispatcher.build_alert_payload(event_type, cv_metrics, valuation)
    return alert_dispatcher.dispatch(payload)

@app.post("/api/analyze")
@app.post("/api/reports/analyze")
def run_analysis(params: Optional[AnalysisParams] = None):
    """Dynamically re-analyzes with user-adjusted CV parameters."""
    p_dict = params.model_dump() if params else {}
    metrics = geoint_service.analyze(p_dict)
    stock_data = stock_service.get_stock_data()
    return {
        "status": "success",
        "metrics": metrics,
        "stock_gain_pct": stock_data.get("gain_pct"),
        "current_stock_price": stock_data.get("current_price")
    }

@app.get("/api/bigquery/schema")
def get_bigquery_schema():
    return {"schema": bigquery_service.get_schema()}

@app.get("/api/bigquery/logs")
def get_bigquery_logs():
    return {"logs": bigquery_service.get_audit_logs()}

@app.post("/api/bigquery/sync", dependencies=[Depends(require_admin)])
def sync_bigquery():
    """Generates structured telemetry and pushes to BigQuery or audit log."""
    metrics = geoint_service.analyze()
    stock_data = stock_service.get_stock_data()
    record = bigquery_service.build_record(metrics, stock_data)
    result = bigquery_service.sync_to_bigquery(record)
    return result

@app.get("/api/report/summary")
def get_report():
    """Generates executive institutional audit summary."""
    kpi = get_kpi()
    return {
        "title": "GEOINT Alternative Data Investment Brief",
        "subject": "YTL Power International Berhad (6742.KL)",
        "asset": "YTL Green Data Center Park, Kulai, Johor",
        "key_findings": [
            f"Ground verification reveals {kpi['solar']['current_area_m2']:,.0f} m² of mounted solar photovoltaic panels, representing ~{kpi['solar']['est_capacity_mw']} MW of utility-scale clean generation.",
            f"Over {kpi['solar']['pct_target_achieved']}% of the promised 500MW solar park is physically mounted and observable from orbit.",
            f"Data Hall roof footprint expanded by +{kpi['data_halls']['delta_roof_m2']:,.0f} m² since 2023 baseline, confirming multi-hall structural delivery for NVIDIA DGX/GB200 clusters.",
            f"Bursa stock price appreciated +{kpi['stock']['gain_pct']}% from RM {kpi['stock']['baseline_price']:.2f} to RM {kpi['stock']['current_price']:.2f}, exhibiting direct co-movement with physical infrastructure delivery."
        ],
        "kpi": kpi
    }

# Mount static directory for JS, CSS, images
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
