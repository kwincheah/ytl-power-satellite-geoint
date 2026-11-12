"""
Geospatial Intelligence (GEOINT) Computer Vision Service
Processes Sentinel-2 satellite crops, executes morphological segmentation,
and quantifies photovoltaic (PV) arrays and data hall roofs.
"""

import os
import io
import base64
import cv2
import numpy as np
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_2023_PATH = os.path.join(BASE_DIR, "kulai_2023.png")
IMAGE_2026_PATH = os.path.join(BASE_DIR, "kulai_2026.png")

# Sentinel-2 10m L2A resolution = 100 m² per pixel
DEFAULT_PIXEL_AREA_M2 = 100.0
DEFAULT_MW_PER_HECTARE = 1.0  # ~1 MW per 10,000 m² utility solar
TARGET_CAMPUS_SOLAR_MW = 500.0

# Geographic Coordinates & Bounding Box for Kulai Data Center Park
ROI_INFO = {
    "campus_name": "YTL Green Data Center Park & Solar Campus",
    "location": "Kulai, Johor, Malaysia",
    "coordinates": {"lat": 1.6225, "lon": 103.5250},
    "bbox_wgs84": [103.505, 1.605, 103.545, 1.640],
    "resolution_m": 10.0,
    "satellite": "Sentinel-2 L2A (Multispectral 10m bands)"
}

class GeointService:
    def __init__(self):
        self._load_base_images()

    def _load_base_images(self):
        """Loads cached baseline and current satellite crops."""
        if os.path.exists(IMAGE_2023_PATH):
            self.img_2023_bgr = cv2.imread(IMAGE_2023_PATH)
            self.img_2023_rgb = cv2.cvtColor(self.img_2023_bgr, cv2.COLOR_BGR2RGB)
        else:
            raise FileNotFoundError(f"Missing {IMAGE_2023_PATH}")

        if os.path.exists(IMAGE_2026_PATH):
            self.img_2026_bgr = cv2.imread(IMAGE_2026_PATH)
            self.img_2026_rgb = cv2.cvtColor(self.img_2026_bgr, cv2.COLOR_BGR2RGB)
        else:
            raise FileNotFoundError(f"Missing {IMAGE_2026_PATH}")

        self.h, self.w, _ = self.img_2026_bgr.shape
        self._init_campus_roi()

    def _init_campus_roi(self):
        """Creates polygon masks covering the authorized development sectors."""
        self.campus_mask = np.zeros((self.h, self.w), dtype=np.uint8)
        campus_polygon = np.array([
            [0, int(self.h * 0.40)],
            [int(self.w * 0.62), int(self.h * 0.32)],
            [int(self.w * 0.62), self.h],
            [0, self.h]
        ], np.int32)
        cv2.fillPoly(self.campus_mask, [campus_polygon], 255)

        # Designated Data Center Zone inside the campus
        self.dc_zone_mask = np.zeros((self.h, self.w), dtype=np.uint8)
        self.dc_zone_mask[int(self.h * 0.40):int(self.h * 0.78), int(self.w * 0.18):int(self.w * 0.58)] = 255

    def analyze(self, params: dict = None):
        """
        Executes computer vision segmentation on the 2026 scene with optional dynamic thresholds.
        Also computes comparison against 2023 baseline.
        """
        if params is None:
            params = {}

        # Extraction parameters with institutional defaults
        solar_v_max = int(params.get("solar_v_max", 75))
        solar_s_max = int(params.get("solar_s_max", 120))
        roof_v_min = int(params.get("roof_v_min", 175))
        mw_per_ha = float(params.get("mw_per_hectare", DEFAULT_MW_PER_HECTARE))
        min_solar_area = int(params.get("min_solar_contour", 200))
        min_roof_area = int(params.get("min_roof_contour", 100))

        # HSV spaces
        hsv_2026 = cv2.cvtColor(self.img_2026_bgr, cv2.COLOR_BGR2HSV)
        hsv_2023 = cv2.cvtColor(self.img_2023_bgr, cv2.COLOR_BGR2HSV)

        # 1. Solar Array Segmentation (Dark, neutral/low saturation PV panels)
        solar_lower = np.array([0, 0, 15], dtype=np.uint8)
        solar_upper = np.array([180, solar_s_max, solar_v_max], dtype=np.uint8)

        solar_raw_2026 = cv2.inRange(hsv_2026, solar_lower, solar_upper)
        solar_mask_2026 = cv2.bitwise_and(solar_raw_2026, self.campus_mask)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        solar_mask_2026 = cv2.morphologyEx(solar_mask_2026, cv2.MORPH_OPEN, kernel)
        solar_mask_2026 = cv2.morphologyEx(solar_mask_2026, cv2.MORPH_CLOSE, kernel)

        # 2023 Solar baseline
        solar_raw_2023 = cv2.inRange(hsv_2023, solar_lower, solar_upper)
        solar_mask_2023 = cv2.bitwise_and(solar_raw_2023, self.campus_mask)
        solar_mask_2023 = cv2.morphologyEx(solar_mask_2023, cv2.MORPH_OPEN, kernel)

        # 2. Data Hall Roof Segmentation (High reflectance metallic/membrane roofs)
        roof_lower = np.array([0, 0, roof_v_min], dtype=np.uint8)
        roof_upper = np.array([180, 75, 255], dtype=np.uint8)

        roof_raw_2026 = cv2.inRange(hsv_2026, roof_lower, roof_upper)
        roof_mask_2026 = cv2.bitwise_and(roof_raw_2026, self.dc_zone_mask)
        roof_mask_2026 = cv2.morphologyEx(roof_mask_2026, cv2.MORPH_OPEN, kernel)

        roof_raw_2023 = cv2.inRange(hsv_2023, roof_lower, roof_upper)
        roof_mask_2023 = cv2.bitwise_and(roof_raw_2023, self.dc_zone_mask)
        roof_mask_2023 = cv2.morphologyEx(roof_mask_2023, cv2.MORPH_OPEN, kernel)

        # Count pixels and compute physical areas
        solar_pixels_2023 = int(np.count_nonzero(solar_mask_2023))
        solar_pixels_2026 = int(np.count_nonzero(solar_mask_2026))
        roof_pixels_2023 = int(np.count_nonzero(roof_mask_2023))
        roof_pixels_2026 = int(np.count_nonzero(roof_mask_2026))

        solar_area_2023_m2 = solar_pixels_2023 * DEFAULT_PIXEL_AREA_M2
        solar_area_2026_m2 = solar_pixels_2026 * DEFAULT_PIXEL_AREA_M2
        solar_delta_m2 = solar_area_2026_m2 - solar_area_2023_m2

        roof_area_2023_m2 = roof_pixels_2023 * DEFAULT_PIXEL_AREA_M2
        roof_area_2026_m2 = roof_pixels_2026 * DEFAULT_PIXEL_AREA_M2
        roof_delta_m2 = roof_area_2026_m2 - roof_area_2023_m2

        est_mw_2023 = round((solar_area_2023_m2 / 10000.0) * mw_per_ha, 1)
        est_mw_2026 = round((solar_area_2026_m2 / 10000.0) * mw_per_ha, 1)
        pct_target = round((est_mw_2026 / TARGET_CAMPUS_SOLAR_MW) * 100.0, 1)

        # Contour extraction & clustering
        solar_contours, _ = cv2.findContours(solar_mask_2026, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        solar_boxes = []
        for c in solar_contours:
            if cv2.contourArea(c) >= min_solar_area:
                x, y, bw, bh = cv2.boundingRect(c)
                solar_boxes.append({"x": int(x), "y": int(y), "w": int(bw), "h": int(bh), "area_m2": int(cv2.contourArea(c) * DEFAULT_PIXEL_AREA_M2)})

        roof_contours, _ = cv2.findContours(roof_mask_2026, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        roof_boxes = []
        for c in roof_contours:
            if cv2.contourArea(c) >= min_roof_area:
                x, y, bw, bh = cv2.boundingRect(c)
                roof_boxes.append({"x": int(x), "y": int(y), "w": int(bw), "h": int(bh), "area_m2": int(cv2.contourArea(c) * DEFAULT_PIXEL_AREA_M2)})

        # Difference analysis (Detect transformed terrain)
        # 2023 vs 2026 structural footprint changes
        diff_mask = np.zeros((self.h, self.w), dtype=np.uint8)
        diff_mask[(solar_mask_2026 > 0) & (solar_mask_2023 == 0)] = 255
        diff_mask[(roof_mask_2026 > 0) & (roof_mask_2023 == 0)] = 255

        metrics = {
            "solar_area_m2": solar_area_2026_m2,
            "solar_area_2023_m2": solar_area_2023_m2,
            "solar_delta_m2": solar_delta_m2,
            "est_solar_mw": est_mw_2026,
            "est_solar_mw_2023": est_mw_2023,
            "target_solar_mw": TARGET_CAMPUS_SOLAR_MW,
            "pct_target_achieved": pct_target,
            "roof_area_m2": roof_area_2026_m2,
            "roof_area_2023_m2": roof_area_2023_m2,
            "roof_delta_m2": roof_delta_m2,
            "solar_cluster_count": len(solar_boxes),
            "roof_cluster_count": len(roof_boxes),
            "solar_boxes": solar_boxes,
            "roof_boxes": roof_boxes,
            "roi": ROI_INFO
        }

        # Cache latest masks for fast layer rendering
        self.latest_solar_mask = solar_mask_2026
        self.latest_roof_mask = roof_mask_2026
        self.latest_diff_mask = diff_mask
        self.latest_solar_boxes = solar_boxes
        self.latest_roof_boxes = roof_boxes
        self.latest_metrics = metrics

        return metrics

    def generate_layer_image(self, layer_type: str = "annotated"):
        """
        Generates an RGB/BGR visual image for a requested layer type:
        - '2023': baseline raw 2023
        - '2026': current raw 2026
        - 'annotated': composite with cyan solar, amber roof, and bounding boxes
        - 'solar_only': transparent or overlay showing solar arrays in cyan
        - 'roof_only': transparent or overlay showing roofs in amber
        - 'difference': heatmap of new developments
        - 'campus_roi': satellite with campus perimeter highlighted
        """
        if not hasattr(self, "latest_metrics"):
            self.analyze()

        if layer_type == "2023":
            return self.img_2023_rgb

        elif layer_type == "2026":
            return self.img_2026_rgb

        elif layer_type == "solar_only":
            out = self.img_2026_rgb.copy()
            out[self.latest_solar_mask > 0] = (
                out[self.latest_solar_mask > 0] * 0.35 + np.array([0, 225, 255]) * 0.65
            ).astype(np.uint8)
            return out

        elif layer_type == "roof_only":
            out = self.img_2026_rgb.copy()
            out[self.latest_roof_mask > 0] = (
                out[self.latest_roof_mask > 0] * 0.30 + np.array([255, 160, 0]) * 0.70
            ).astype(np.uint8)
            return out

        elif layer_type == "difference":
            out = self.img_2026_rgb.copy()
            # Heatmap glow for changes
            out[self.latest_diff_mask > 0] = (
                out[self.latest_diff_mask > 0] * 0.30 + np.array([16, 185, 129]) * 0.70
            ).astype(np.uint8)
            return out

        elif layer_type == "campus_roi":
            out = self.img_2026_rgb.copy()
            contours, _ = cv2.findContours(self.campus_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(out, contours, -1, (56, 189, 248), 2)
            dc_contours, _ = cv2.findContours(self.dc_zone_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(out, dc_contours, -1, (245, 158, 11), 2)
            return out

        else:  # 'annotated' default
            annotated = self.img_2026_rgb.copy()
            # Solar tint (Cyan)
            annotated[self.latest_solar_mask > 0] = (
                annotated[self.latest_solar_mask > 0] * 0.45 + np.array([0, 225, 255]) * 0.55
            ).astype(np.uint8)

            # Roof tint (Amber)
            annotated[self.latest_roof_mask > 0] = (
                annotated[self.latest_roof_mask > 0] * 0.35 + np.array([255, 160, 0]) * 0.65
            ).astype(np.uint8)

            # Draw bounding boxes
            for box in self.latest_solar_boxes:
                cv2.rectangle(
                    annotated,
                    (box["x"], box["y"]),
                    (box["x"] + box["w"], box["y"] + box["h"]),
                    (0, 255, 255),
                    1
                )

            for box in self.latest_roof_boxes:
                cv2.rectangle(
                    annotated,
                    (box["x"], box["y"]),
                    (box["x"] + box["w"], box["y"] + box["h"]),
                    (255, 120, 0),
                    2
                )
            return annotated

    def get_image_bytes(self, layer_type: str = "annotated", format: str = "PNG") -> bytes:
        """Encodes requested layer to in-memory image bytes."""
        img_rgb = self.generate_layer_image(layer_type)
        pil_img = Image.fromarray(img_rgb)
        buf = io.BytesIO()
        pil_img.save(buf, format=format, optimize=True)
        return buf.getvalue()

    def get_image_base64(self, layer_type: str = "annotated") -> str:
        """Returns data URI base64 string for direct HTML image src embedding."""
        b = self.get_image_bytes(layer_type)
        encoded = base64.b64encode(b).decode("utf-8")
        return f"data:image/png;base64,{encoded}"
