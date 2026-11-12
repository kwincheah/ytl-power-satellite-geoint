"""
YTL Power (Bursa: 6742.KL) Satellite Geospatial Intelligence (GEOINT) Tracker
Monitors the YTL Green Data Center Park & 500MW Solar Farm in Kulai, Johor.
"""

import os
import json
import requests
import numpy as np
import cv2
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
import yfinance as yf
from datetime import datetime

# Coordinate Bounding Box for YTL Green Data Center Park, Kulai, Johor
# [min_lon, min_lat, max_lon, max_lat]
KULAI_BBOX = [103.505, 1.605, 103.545, 1.640]
PIXEL_AREA_M2 = 100.0  # Sentinel-2 10m resolution = 100 m^2 per pixel
MW_PER_HECTARE = 1.0   # Standard utility-scale solar density ~1 MW per 10,000 m^2

class KulaiSatelliteTracker:
    def __init__(self, bbox=KULAI_BBOX):
        self.bbox = bbox
        self.stac_endpoint = "https://earth-search.aws.element84.com/v1/search"

    def search_scenes(self, start_date, end_date, max_cloud=15, limit=5):
        """Query open STAC catalog for cloud-free Sentinel-2 L2A scenes."""
        payload = {
            "collections": ["sentinel-2-l2a"],
            "bbox": self.bbox,
            "datetime": f"{start_date}T00:00:00Z/{end_date}T00:00:00Z",
            "query": {"eo:cloud_cover": {"lt": max_cloud}},
            "limit": limit,
            "sortby": [{"field": "properties.datetime", "direction": "desc"}]
        }
        resp = requests.post(self.stac_endpoint, json=payload, timeout=20)
        resp.raise_for_status()
        features = resp.json().get("features", [])
        return features

    def fetch_crop(self, scene_feature):
        """Fetch cropped visual window over HTTP Range Request from Cloud-Optimized GeoTIFF."""
        visual_url = scene_feature["assets"]["visual"]["href"]
        date_str = scene_feature["properties"]["datetime"][:10]
        cloud_pct = scene_feature["properties"]["eo:cloud_cover"]
        scene_id = scene_feature["id"]

        with rasterio.Env(AWS_NO_SIGN_REQUEST='YES', GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'):
            with rasterio.open(visual_url) as src:
                left, bottom, right, top = transform_bounds('EPSG:4326', src.crs, *self.bbox)
                window = from_bounds(left, bottom, right, top, transform=src.transform)
                rgb_data = src.read(window=window)

        rgb = np.transpose(rgb_data, (1, 2, 0))
        if rgb.max() > 255:
            rgb = (rgb / rgb.max() * 255).astype(np.uint8)

        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        return {
            "scene_id": scene_id,
            "date": date_str,
            "cloud_pct": cloud_pct,
            "rgb": rgb,
            "bgr": bgr
        }

    def analyze_scene(self, img_bgr):
        """Perform computer vision segmentation to quantify solar arrays and data hall roofs."""
        h, w, _ = img_bgr.shape
        b, g, r = img_bgr[:, :, 0], img_bgr[:, :, 1], img_bgr[:, :, 2]

        # Spatial campus ROI polygon (focuses on development sectors)
        campus_mask = np.zeros((h, w), dtype=np.uint8)
        campus_polygon = np.array([
            [0, int(h * 0.40)],
            [int(w * 0.52), int(h * 0.35)],
            [int(w * 0.52), h],
            [0, h]
        ], np.int32)
        cv2.fillPoly(campus_mask, [campus_polygon], 255)

        # 1. Solar Array Segmentation
        # Distinguish neutral grey/charcoal PV panels from green oil palm trees
        is_forest = (g > 35) & (g > r.astype(float) * 1.2) & (r < 65)
        is_solar = (r >= 85) & (r <= 160) & (g >= 80) & (g <= 155) & (b >= 80) & (b <= 150) & (~is_forest)
        is_solar = is_solar & (campus_mask > 0)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        solar_mask = cv2.morphologyEx(is_solar.astype(np.uint8) * 255, cv2.MORPH_OPEN, kernel)

        # 2. Data Center Building Roof Segmentation
        # High-reflectance metallic/membrane roofs
        dc_zone_mask = np.zeros((h, w), dtype=np.uint8)
        dc_zone_mask[int(h * 0.40):int(h * 0.75), int(w * 0.20):int(w * 0.52)] = 255

        is_roof = (r > 185) & (g > 185) & (b > 180) & (dc_zone_mask > 0)
        roof_mask = cv2.morphologyEx(is_roof.astype(np.uint8) * 255, cv2.MORPH_OPEN, kernel)

        solar_pixels = int(np.count_nonzero(solar_mask))
        roof_pixels = int(np.count_nonzero(roof_mask))

        solar_area_m2 = solar_pixels * PIXEL_AREA_M2
        roof_area_m2 = roof_pixels * PIXEL_AREA_M2
        est_solar_mw = (solar_area_m2 / 10000.0) * MW_PER_HECTARE

        return {
            "solar_area_m2": solar_area_m2,
            "est_solar_mw": round(est_solar_mw, 1),
            "roof_area_m2": roof_area_m2,
            "solar_mask": solar_mask,
            "roof_mask": roof_mask
        }

    def fetch_stock_telemetry(self, ticker_symbol="6742.KL", start_date="2023-01-01"):
        """Fetch stock market metrics from Bursa Malaysia for YTL Power."""
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(start=start_date)
        return hist


if __name__ == "__main__":
    tracker = KulaiSatelliteTracker()
    print("Testing Kulai Satellite Tracker Pipeline...")
    scenes = tracker.search_scenes("2026-01-01", "2026-11-01", max_cloud=15, limit=2)
    print(f"Found {len(scenes)} scenes in 2026.")
    if scenes:
        crop_data = tracker.fetch_crop(scenes[0])
        print(f"Fetched {crop_data['scene_id']} for {crop_data['date']}.")
        results = tracker.analyze_scene(crop_data["bgr"])
        print(f"Detected Solar Area: {results['solar_area_m2']:,.0f} m² (~{results['est_solar_mw']} MW)")
        print(f"Detected Roof Area:  {results['roof_area_m2']:,.0f} m²")
