import requests
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
import matplotlib.pyplot as plt

BBOX_WGS84 = [103.505, 1.605, 103.545, 1.640]

def fetch_scene_crop(scene_id):
    url = "https://earth-search.aws.element84.com/v1/search"
    payload = {
        "collections": ["sentinel-2-l2a"],
        "ids": [scene_id]
    }
    resp = requests.post(url, json=payload, timeout=20)
    resp.raise_for_status()
    features = resp.json().get("features", [])
    if not features:
        raise ValueError(f"Scene {scene_id} not found")
    
    visual_url = features[0]["assets"]["visual"]["href"]
    date_str = features[0]["properties"]["datetime"][:10]
    
    with rasterio.Env(AWS_NO_SIGN_REQUEST='YES', GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'):
        with rasterio.open(visual_url) as src:
            left, bottom, right, top = transform_bounds('EPSG:4326', src.crs, *BBOX_WGS84)
            window = from_bounds(left, bottom, right, top, transform=src.transform)
            rgb_data = src.read(window=window)
            
    rgb = np.transpose(rgb_data, (1, 2, 0))
    if rgb.max() > 255:
        rgb = (rgb / rgb.max() * 255).astype(np.uint8)
    return rgb, date_str

print("Fetching March 2023 baseline...")
rgb_2023, date_2023 = fetch_scene_crop("S2B_48NUG_20230316_0_L2A")
plt.imsave("kulai_2023.png", rgb_2023)
print(f"Saved kulai_2023.png ({rgb_2023.shape})")

print("Fetching August 2026 current...")
rgb_2026, date_2026 = fetch_scene_crop("S2C_48NUG_20260822_0_L2A")
plt.imsave("kulai_2026.png", rgb_2026)
print(f"Saved kulai_2026.png ({rgb_2026.shape})")
