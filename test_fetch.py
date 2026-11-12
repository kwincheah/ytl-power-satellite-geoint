import os
import requests
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
import matplotlib.pyplot as plt

# Bounding box for YTL Green Data Center Park, Kulai, Johor
# [min_lon, min_lat, max_lon, max_lat]
BBOX_WGS84 = [103.505, 1.605, 103.545, 1.640]

print("1. Querying Element84 STAC API for cloud-free Sentinel-2 scenes...")
url = "https://earth-search.aws.element84.com/v1/search"
payload = {
    "collections": ["sentinel-2-l2a"],
    "bbox": BBOX_WGS84,
    "datetime": "2024-01-01T00:00:00Z/2026-11-01T00:00:00Z",
    "query": {"eo:cloud_cover": {"lt": 15}},
    "limit": 10,
    "sortby": [{"field": "properties.datetime", "direction": "desc"}]
}

resp = requests.post(url, json=payload, timeout=20)
resp.raise_for_status()
features = resp.json().get("features", [])
print(f"Found {len(features)} candidate scenes.")

if not features:
    print("No scenes found, exiting.")
    exit(1)

# Pick the best low-cloud scene
selected = features[0]
print(f"Selected scene: {selected['id']}")
print(f"Acquisition date: {selected['properties']['datetime']}")
print(f"Cloud cover: {selected['properties']['eo:cloud_cover']:.2f}%")

visual_url = selected["assets"]["visual"]["href"]
print(f"Visual COG URL: {visual_url}")

print("2. Streaming and cropping ROI via HTTP Range Request (COG)...")
# Open COG with rasterio
with rasterio.Env(AWS_NO_SIGN_REQUEST='YES', GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'):
    with rasterio.open(visual_url) as src:
        print(f"Dataset CRS: {src.crs}, Dimensions: {src.width}x{src.height}")
        # Transform BBOX from WGS84 (EPSG:4326) to dataset CRS (typically UTM Zone 48N, EPSG:32648)
        left, bottom, right, top = transform_bounds('EPSG:4326', src.crs, *BBOX_WGS84)
        print(f"Projected bounds: left={left:.1f}, bottom={bottom:.1f}, right={right:.1f}, top={top:.1f}")
        
        # Calculate pixel window
        window = from_bounds(left, bottom, right, top, transform=src.transform)
        print(f"Window: {window}")
        
        # Read the 3 bands (RGB) for this exact crop
        rgb_data = src.read(window=window)
        print(f"Read shape: {rgb_data.shape}, dtype: {rgb_data.dtype}")

# Convert (bands, height, width) -> (height, width, bands)
rgb = np.transpose(rgb_data, (1, 2, 0))

# Normalize if needed
if rgb.max() > 255:
    rgb = (rgb / rgb.max() * 255).astype(np.uint8)

out_file = "kulai_satellite_crop.png"
plt.imsave(out_file, rgb)
print(f"Saved crop to {out_file} (Resolution: {rgb.shape[1]}x{rgb.shape[0]})")
