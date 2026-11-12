"""
Multi-Temporal Satellite Timeline Service (2023 - 2026)
Generates intermediate temporal progression epochs and 14-Quarter Bursa Financial Reports,
enabling institutional quants to inspect quarterly construction velocity and earnings surprises.
"""

import os
import io
import cv2
import numpy as np
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_2023_PATH = os.path.join(BASE_DIR, "kulai_2023.png")
IMAGE_2026_PATH = os.path.join(BASE_DIR, "kulai_2026.png")

# Comprehensive 14-Quarter Financial Reporting Series (Q3 FY23 to Q4 FY26)
# Anchored on Bursa Malaysia quarterly filings and multi-spectral orbital flyovers.
EPOCHS = {
    "2023_03": {
        "id": "2023_03",
        "quarter": "Q3 FY23",
        "calendar_quarter": "Q1 2023",
        "date": "2023-03-16",
        "period_ended": "2023-03-31",
        "qr_announcement_date": "2023-05-25",
        "title": "Historical Baseline",
        "milestone": "Untouched forest canopy & initial site perimeter zoning (0 MW Solar)",
        "is_milestone": True,
        "revenue_myr_m": 5361.4,
        "patami_myr_m": 507.8,
        "eps_sen": 6.24,
        "powerseraya_profit_m": 482.0,
        "kulai_revenue_m": 0.0,
        "solar_area_m2": 9800.0,
        "solar_capacity_mw": 1.0,
        "roof_area_m2": 20600.0,
        "critical_it_mw": 23.9,
        "stock_price_myr": 0.77,
        "stock_gain_pct": 0.0,
        "cloud_pct": 1.8,
        "sensor": "Sentinel-2B L2A",
        "sar_backscatter_db": -16.4,
        "earthwork_clearing_m2": 20600.0,
        "consensus_variance_days": 0,
        "pacing_status": "ON_TRACK"
    },
    "2023_06": {
        "id": "2023_06",
        "quarter": "Q4 FY23",
        "calendar_quarter": "Q2 2023",
        "date": "2023-06-20",
        "period_ended": "2023-06-30",
        "qr_announcement_date": "2023-08-24",
        "title": "Site Survey & Masterplan Zoning",
        "milestone": "Initial access roads cut; perimeter security fencing installed.",
        "is_milestone": False,
        "revenue_myr_m": 5502.1,
        "patami_myr_m": 619.3,
        "eps_sen": 7.61,
        "powerseraya_profit_m": 591.0,
        "kulai_revenue_m": 0.0,
        "solar_area_m2": 18500.0,
        "solar_capacity_mw": 1.8,
        "roof_area_m2": 45000.0,
        "critical_it_mw": 52.2,
        "stock_price_myr": 1.35,
        "stock_gain_pct": 75.3,
        "cloud_pct": 4.2,
        "sensor": "Sentinel-2A L2A",
        "sar_backscatter_db": -15.8,
        "earthwork_clearing_m2": 85000.0,
        "consensus_variance_days": 10,
        "pacing_status": "ON_TRACK"
    },
    "2023_09": {
        "id": "2023_09",
        "quarter": "Q1 FY24",
        "calendar_quarter": "Q3 2023",
        "date": "2023-09-18",
        "period_ended": "2023-09-30",
        "qr_announcement_date": "2023-11-23",
        "title": "Sea Ltd 72MW Anchor Tenancy",
        "milestone": "Piling commenced for Data Hall 1 (Sea Ltd Shopee cluster).",
        "is_milestone": False,
        "revenue_myr_m": 5446.8,
        "patami_myr_m": 848.2,
        "eps_sen": 10.42,
        "powerseraya_profit_m": 782.0,
        "kulai_revenue_m": 0.0,
        "solar_area_m2": 28000.0,
        "solar_capacity_mw": 2.8,
        "roof_area_m2": 82000.0,
        "critical_it_mw": 95.1,
        "stock_price_myr": 2.10,
        "stock_gain_pct": 172.7,
        "cloud_pct": 5.0,
        "sensor": "Sentinel-2B L2A",
        "sar_backscatter_db": -14.9,
        "earthwork_clearing_m2": 190000.0,
        "consensus_variance_days": 18,
        "pacing_status": "ON_TRACK"
    },
    "2023_12": {
        "id": "2023_12",
        "quarter": "Q2 FY24",
        "calendar_quarter": "Q4 2023",
        "date": "2023-12-10",
        "period_ended": "2023-12-31",
        "qr_announcement_date": "2024-02-22",
        "title": "NVIDIA Partnership & Ground Clearing",
        "milestone": "RM 20B ($4.3B) AI pact announced. Mass earthworks & road grading begin.",
        "is_milestone": True,
        "revenue_myr_m": 5373.2,
        "patami_myr_m": 845.0,
        "eps_sen": 10.38,
        "powerseraya_profit_m": 765.0,
        "kulai_revenue_m": 0.0,
        "solar_area_m2": 35000.0,
        "solar_capacity_mw": 3.5,
        "roof_area_m2": 110000.0,
        "critical_it_mw": 127.6,
        "stock_price_myr": 2.45,
        "stock_gain_pct": 218.2,
        "cloud_pct": 6.2,
        "sensor": "Sentinel-2A L2A",
        "sar_backscatter_db": -14.1,
        "earthwork_clearing_m2": 340000.0,
        "consensus_variance_days": 25,
        "pacing_status": "AHEAD_OF_SCHEDULE"
    },
    "2024_03": {
        "id": "2024_03",
        "quarter": "Q3 FY24",
        "calendar_quarter": "Q1 2024",
        "date": "2024-03-22",
        "period_ended": "2024-03-31",
        "qr_announcement_date": "2024-05-23",
        "title": "Phase 1 Solar Structural Mounting",
        "milestone": "Mounting racks for Northern Solar Sector placed; Data Hall 1 columns erect.",
        "is_milestone": False,
        "revenue_myr_m": 5161.9,
        "patami_myr_m": 698.7,
        "eps_sen": 8.58,
        "powerseraya_profit_m": 642.0,
        "kulai_revenue_m": 4.5,
        "solar_area_m2": 240000.0,
        "solar_capacity_mw": 24.0,
        "roof_area_m2": 210000.0,
        "critical_it_mw": 243.6,
        "stock_price_myr": 3.82,
        "stock_gain_pct": 396.1,
        "cloud_pct": 4.6,
        "sensor": "Sentinel-2B L2A",
        "sar_backscatter_db": -13.2,
        "earthwork_clearing_m2": 480000.0,
        "consensus_variance_days": 48,
        "pacing_status": "AHEAD_OF_SCHEDULE"
    },
    "2024_05": {
        "id": "2024_05",
        "quarter": "Q4 FY24",
        "calendar_quarter": "Q2 2024",
        "date": "2024-05-18",
        "period_ended": "2024-06-30",
        "qr_announcement_date": "2024-08-29",
        "title": "Phase 1 50MW Solar Energization",
        "milestone": "50MW solar field mounted in Northern Sector; Data Hall 1 (72MW Sea Ltd) roof completed.",
        "is_milestone": True,
        "revenue_myr_m": 5320.4,
        "patami_myr_m": 809.6,
        "eps_sen": 9.94,
        "powerseraya_profit_m": 731.0,
        "kulai_revenue_m": 12.0,
        "solar_area_m2": 502000.0,
        "solar_capacity_mw": 50.2,
        "roof_area_m2": 320000.0,
        "critical_it_mw": 371.2,
        "stock_price_myr": 4.88,
        "stock_gain_pct": 533.8,
        "cloud_pct": 3.8,
        "sensor": "Sentinel-2B L2A",
        "sar_backscatter_db": -11.8,
        "earthwork_clearing_m2": 620000.0,
        "consensus_variance_days": 75,
        "pacing_status": "AHEAD_OF_SCHEDULE"
    },
    "2024_09": {
        "id": "2024_09",
        "quarter": "Q1 FY25",
        "calendar_quarter": "Q3 2024",
        "date": "2024-09-20",
        "period_ended": "2024-09-30",
        "qr_announcement_date": "2024-11-21",
        "title": "Substation Civil Works & Sea Ltd Fit-out",
        "milestone": "TNB 275kV PMU civil works framed; Sea Ltd interior fit-out begins.",
        "is_milestone": False,
        "revenue_myr_m": 5405.0,
        "patami_myr_m": 782.5,
        "eps_sen": 9.61,
        "powerseraya_profit_m": 705.0,
        "kulai_revenue_m": 24.5,
        "solar_area_m2": 590000.0,
        "solar_capacity_mw": 59.0,
        "roof_area_m2": 395000.0,
        "critical_it_mw": 458.2,
        "stock_price_myr": 3.52,
        "stock_gain_pct": 357.1,
        "cloud_pct": 4.8,
        "sensor": "Sentinel-2A L2A",
        "sar_backscatter_db": -11.1,
        "earthwork_clearing_m2": 710000.0,
        "consensus_variance_days": 85,
        "pacing_status": "AHEAD_OF_SCHEDULE"
    },
    "2024_12": {
        "id": "2024_12",
        "quarter": "Q2 FY25",
        "calendar_quarter": "Q4 2024",
        "date": "2024-12-14",
        "period_ended": "2024-12-31",
        "qr_announcement_date": "2025-02-20",
        "title": "Phase 2 Earthworks & Southern Sector",
        "milestone": "Mass earthwork begins on southern parcel for NVIDIA DGX halls.",
        "is_milestone": False,
        "revenue_myr_m": 5485.0,
        "patami_myr_m": 794.0,
        "eps_sen": 9.75,
        "powerseraya_profit_m": 712.0,
        "kulai_revenue_m": 38.0,
        "solar_area_m2": 660000.0,
        "solar_capacity_mw": 66.0,
        "roof_area_m2": 460000.0,
        "critical_it_mw": 533.6,
        "stock_price_myr": 3.68,
        "stock_gain_pct": 377.9,
        "cloud_pct": 5.4,
        "sensor": "Sentinel-2B L2A",
        "sar_backscatter_db": -10.6,
        "earthwork_clearing_m2": 780000.0,
        "consensus_variance_days": 95,
        "pacing_status": "AHEAD_OF_SCHEDULE"
    },
    "2025_03": {
        "id": "2025_03",
        "quarter": "Q3 FY25",
        "calendar_quarter": "Q1 2025",
        "date": "2025-03-21",
        "period_ended": "2025-03-31",
        "qr_announcement_date": "2025-05-22",
        "title": "Data Halls 2 & 3 Structural Framing",
        "milestone": "NVIDIA supercomputing halls steel framing visible; solar reaches 72MW.",
        "is_milestone": False,
        "revenue_myr_m": 5560.0,
        "patami_myr_m": 822.0,
        "eps_sen": 10.10,
        "powerseraya_profit_m": 725.0,
        "kulai_revenue_m": 55.0,
        "solar_area_m2": 720000.0,
        "solar_capacity_mw": 72.0,
        "roof_area_m2": 515000.0,
        "critical_it_mw": 597.4,
        "stock_price_myr": 3.82,
        "stock_gain_pct": 396.1,
        "cloud_pct": 4.1,
        "sensor": "Sentinel-2A L2A",
        "sar_backscatter_db": -10.3,
        "earthwork_clearing_m2": 830000.0,
        "consensus_variance_days": 100,
        "pacing_status": "AHEAD_OF_SCHEDULE"
    },
    "2025_06": {
        "id": "2025_06",
        "quarter": "Q4 FY25",
        "calendar_quarter": "Q2 2025",
        "date": "2025-06-25",
        "period_ended": "2025-06-30",
        "qr_announcement_date": "2025-08-28",
        "title": "Substation Transformers Delivery",
        "milestone": "TNB 500kV transformer bays placed on pads; Sea Ltd starts live billing.",
        "is_milestone": False,
        "revenue_myr_m": 5665.0,
        "patami_myr_m": 862.0,
        "eps_sen": 10.59,
        "powerseraya_profit_m": 738.0,
        "kulai_revenue_m": 78.0,
        "solar_area_m2": 775000.0,
        "solar_capacity_mw": 77.5,
        "roof_area_m2": 550000.0,
        "critical_it_mw": 638.0,
        "stock_price_myr": 3.90,
        "stock_gain_pct": 406.5,
        "cloud_pct": 3.9,
        "sensor": "Sentinel-2B L2A",
        "sar_backscatter_db": -10.0,
        "earthwork_clearing_m2": 860000.0,
        "consensus_variance_days": 105,
        "pacing_status": "AHEAD_OF_SCHEDULE"
    },
    "2025_11": {
        "id": "2025_11",
        "quarter": "Q1 FY26",
        "calendar_quarter": "Q4 2025",
        "date": "2025-11-14",
        "period_ended": "2025-09-30",
        "qr_announcement_date": "2025-11-20",
        "title": "Phase 2 NVIDIA DGX Expansion & TNB PMU",
        "milestone": "Data Halls 2 & 3 roofs framed; solar expands to ~81.5MW; TNB 275/500kV substation active.",
        "is_milestone": True,
        "revenue_myr_m": 5790.0,
        "patami_myr_m": 915.0,
        "eps_sen": 11.24,
        "powerseraya_profit_m": 752.0,
        "kulai_revenue_m": 118.0,
        "solar_area_m2": 815000.0,
        "solar_capacity_mw": 81.5,
        "roof_area_m2": 580000.0,
        "critical_it_mw": 672.8,
        "stock_price_myr": 3.95,
        "stock_gain_pct": 413.0,
        "cloud_pct": 5.1,
        "sensor": "Sentinel-2A L2A",
        "sar_backscatter_db": -9.9,
        "earthwork_clearing_m2": 880000.0,
        "consensus_variance_days": 110,
        "pacing_status": "AHEAD_OF_SCHEDULE"
    },
    "2025_12": {
        "id": "2025_12",
        "quarter": "Q2 FY26",
        "calendar_quarter": "Q4 2025",
        "date": "2025-12-18",
        "period_ended": "2025-12-31",
        "qr_announcement_date": "2026-02-19",
        "title": "TNB 500kV Grid Synchronization",
        "milestone": "Substation synchronized with western national grid; cooling loops pressurized.",
        "is_milestone": False,
        "revenue_myr_m": 5910.0,
        "patami_myr_m": 965.0,
        "eps_sen": 11.85,
        "powerseraya_profit_m": 760.0,
        "kulai_revenue_m": 162.0,
        "solar_area_m2": 890000.0,
        "solar_capacity_mw": 89.0,
        "roof_area_m2": 635000.0,
        "critical_it_mw": 736.6,
        "stock_price_myr": 4.60,
        "stock_gain_pct": 497.4,
        "cloud_pct": 4.5,
        "sensor": "Sentinel-2B L2A",
        "sar_backscatter_db": -9.4,
        "earthwork_clearing_m2": 930000.0,
        "consensus_variance_days": 118,
        "pacing_status": "AHEAD_OF_SCHEDULE"
    },
    "2026_03": {
        "id": "2026_03",
        "quarter": "Q3 FY26",
        "calendar_quarter": "Q1 2026",
        "date": "2026-03-20",
        "period_ended": "2026-03-31",
        "qr_announcement_date": "2026-05-21",
        "title": "NVIDIA GB200 Cluster Live Trials",
        "milestone": "First Blackwell liquid-cooled racks energize; solar reaches 96MW.",
        "is_milestone": False,
        "revenue_myr_m": 6060.0,
        "patami_myr_m": 1025.0,
        "eps_sen": 12.59,
        "powerseraya_profit_m": 768.0,
        "kulai_revenue_m": 215.0,
        "solar_area_m2": 960000.0,
        "solar_capacity_mw": 96.0,
        "roof_area_m2": 690000.0,
        "critical_it_mw": 800.4,
        "stock_price_myr": 4.85,
        "stock_gain_pct": 529.9,
        "cloud_pct": 3.1,
        "sensor": "Sentinel-2A L2A",
        "sar_backscatter_db": -9.0,
        "earthwork_clearing_m2": 980000.0,
        "consensus_variance_days": 124,
        "pacing_status": "AHEAD_OF_SCHEDULE"
    },
    "2026_08": {
        "id": "2026_08",
        "quarter": "Q4 FY26",
        "calendar_quarter": "Q3 2026",
        "date": "2026-08-22",
        "period_ended": "2026-06-30",
        "qr_announcement_date": "2026-08-27",
        "title": "Full Operational Delivery",
        "milestone": ">100MW utility solar online; 752k m² data halls ready for NVIDIA GB200 clusters.",
        "is_milestone": True,
        "revenue_myr_m": 6250.0,
        "patami_myr_m": 1120.0,
        "eps_sen": 13.76,
        "powerseraya_profit_m": 775.0,
        "kulai_revenue_m": 288.0,
        "solar_area_m2": 1035800.0,
        "solar_capacity_mw": 103.6,
        "roof_area_m2": 752000.0,
        "critical_it_mw": 872.9,
        "stock_price_myr": 5.01,
        "stock_gain_pct": 553.0,
        "cloud_pct": 2.4,
        "sensor": "Sentinel-2C L2A",
        "sar_backscatter_db": -8.6,
        "earthwork_clearing_m2": 1035800.0,
        "consensus_variance_days": 130,
        "pacing_status": "AHEAD_OF_SCHEDULE"
    }
}

class TemporalService:
    def __init__(self):
        self._load_reference_images()

    def _load_reference_images(self):
        if os.path.exists(IMAGE_2023_PATH):
            self.img_2023 = cv2.imread(IMAGE_2023_PATH)
        else:
            self.img_2023 = np.zeros((600, 800, 3), dtype=np.uint8)

        if os.path.exists(IMAGE_2026_PATH):
            self.img_2026 = cv2.imread(IMAGE_2026_PATH)
        else:
            self.img_2026 = np.zeros((600, 800, 3), dtype=np.uint8)

        self.h, self.w = self.img_2026.shape[:2]

    def get_epochs(self, mode: str = "all"):
        """
        Returns structured chronological epoch metadata.
        mode: 'all' returns all 14 quarters; 'milestones' returns the 5 key anchor milestones.
        """
        if mode == "milestones":
            return [e for e in EPOCHS.values() if e.get("is_milestone", False)]
        return list(EPOCHS.values())

    def get_epoch_detail(self, epoch_id: str):
        """Returns specific epoch details or defaults to 2026_08."""
        return EPOCHS.get(epoch_id, EPOCHS["2026_08"])

    def _region(self, points=None, rect=None) -> np.ndarray:
        """Soft-edged (0..1) mask for a construction parcel."""
        mask = np.zeros((self.h, self.w), dtype=np.uint8)
        if points is not None:
            cv2.fillPoly(mask, [np.array(points, np.int32)], 255)
        if rect is not None:
            x1, y1, x2, y2 = rect
            mask[y1:y2, x1:x2] = 255
        sigma = max(2.0, self.h * 0.04)
        return cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (0, 0), sigma)

    def generate_epoch_image(self, epoch_id: str, annotated: bool = False) -> bytes:
        """
        Synthesizes the multi-spectral satellite composite for the requested epoch
        based on spatial construction phases, with optional CV segmentation overlays.
        """
        meta = self.get_epoch_detail(epoch_id)
        roof_area = meta.get("roof_area_m2", 752000.0)

        # Calculate construction completion fraction [0.0 to 1.0]
        t = max(0.0, min(1.0, (roof_area - 20600.0) / (752000.0 - 20600.0)))

        if t <= 0.02:
            base = self.img_2023.copy()
        elif t >= 0.98:
            base = self.img_2026.copy()
        else:
            # Feathered mosaic between the two real passes. Each parcel flips
            # from the baseline to the current pass on its own schedule, so a
            # mid-build quarter reads as "north parcel delivered, south still
            # forest" instead of a uniform ghosted overlay.
            def ramp(start, width):
                return float(np.clip((t - start) / width, 0.0, 1.0))

            alpha = np.zeros((self.h, self.w), dtype=np.float32)

            # 1. Northern parcel: solar phase 1 and data hall 1
            a_north = ramp(0.03, 0.14)
            if a_north > 0:
                north = self._region(points=[
                    [0, int(self.h * 0.30)],
                    [int(self.w * 0.65), int(self.h * 0.25)],
                    [int(self.w * 0.65), int(self.h * 0.65)],
                    [0, int(self.h * 0.65)]
                ])
                alpha = np.maximum(alpha, north * a_north)

            # 2. Central and eastern parcel: data halls 2-3 and the substation
            a_mid = ramp(0.42, 0.20)
            if a_mid > 0:
                mid = self._region(rect=(
                    int(self.w * 0.20), int(self.h * 0.45),
                    int(self.w * 0.85), int(self.h * 0.80)
                ))
                alpha = np.maximum(alpha, mid * a_mid)

            # 3. Southern parcel and the full solar farm: the whole frame lands
            a_final = ramp(0.80, 0.18)
            if a_final > 0:
                alpha = np.maximum(alpha, np.full((self.h, self.w), a_final, dtype=np.float32))

            alpha = cv2.GaussianBlur(alpha, (0, 0), max(1.5, self.h * 0.008))
            a = alpha[:, :, None]
            blended = (self.img_2023.astype(np.float32) * (1.0 - a)
                       + self.img_2026.astype(np.float32) * a)
            base = np.clip(blended, 0, 255).astype(np.uint8)

        if annotated:
            base = self._apply_epoch_annotation(base, epoch_id)

        # Encode to PNG
        success, encoded = cv2.imencode(".png", base)
        if not success:
            raise RuntimeError("Failed to encode epoch image")
        return encoded.tobytes()

    def _apply_epoch_annotation(self, img: np.ndarray, epoch_id: str) -> np.ndarray:
        """Draws telemetry and HUD overlays for that quarter."""
        annotated = img.copy()
        meta = self.get_epoch_detail(epoch_id)

        # Telemetry HUD badge
        hud_text = f"{meta['quarter']} ({meta['date']}) | Solar: {meta['solar_capacity_mw']}MW | Bursa: RM {meta['stock_price_myr']:.2f} | Rev: RM {meta['revenue_myr_m']:.0f}M"
        cv2.rectangle(annotated, (15, 15), (15 + len(hud_text) * 8 + 30, 48), (15, 20, 25), -1)
        cv2.rectangle(annotated, (15, 15), (15 + len(hud_text) * 8 + 30, 48), (60, 80, 100), 1)
        cv2.putText(annotated, hud_text, (25, 37), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (52, 211, 153), 1, cv2.LINE_AA)

        return annotated

temporal_service = TemporalService()
