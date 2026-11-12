"""
Pushes YTL Kulai Geospatial Telemetry directly into Google Cloud BigQuery.
Dataset: <your-gcp-project>.traffic_analytics.ytl_satellite_telemetry
"""

import json
import subprocess
from datetime import datetime

def push_to_bigquery():
    with open("telemetry.json", "r") as f:
        data = json.load(f)

    timestamp = data["timestamp"]
    ticker = data["ticker"]
    company = data["company"].replace("'", "\\'")
    asset_name = data["asset"].replace("'", "\\'")
    solar_m2 = data["solar_farm"]["area_2026_m2"]
    solar_mw = data["solar_farm"]["est_capacity_mw"]
    roof_m2 = data["data_halls"]["roof_area_2026_m2"]
    stock_price = data["financials"]["price_2026_myr"]
    gain_pct = data["financials"]["gain_pct"]

    sql = f"""
    INSERT INTO traffic_analytics.ytl_satellite_telemetry 
    (timestamp, ticker, company, asset_name, solar_area_m2, est_solar_capacity_mw, data_hall_roof_m2, stock_price_myr, stock_gain_pct)
    VALUES (
        CURRENT_TIMESTAMP(),
        '{ticker}',
        '{company}',
        '{asset_name}',
        {solar_m2},
        {solar_mw},
        {roof_m2},
        {stock_price},
        {gain_pct}
    );
    """

    sql_single_line = " ".join(sql.split())
    print("Executing BigQuery SQL Insert...")
    cmd = ["bq.cmd", "query", "--use_legacy_sql=false", sql_single_line]
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    
    if result.returncode == 0:
        print("[SUCCESS] Telemetry row successfully committed to BigQuery table: traffic_analytics.ytl_satellite_telemetry")
        print(result.stdout)
    else:
        print(f"[ERROR] Failed to push to BigQuery (code {result.returncode}):")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

if __name__ == "__main__":
    push_to_bigquery()
