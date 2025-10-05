import json
import openeo
from pathlib import Path

# --- SETTINGS ---
BACKEND_URL = "https://openeo.cloud"          # openEO Platform
COLLECTION_ID = "SENTINEL1_GRD"                # High-resolution GRD collection on openEO Platform
AOI_GEOJSON = "/home/veyza/geodata-toolkit/data/aoi/aoi.geojson"                    # <- your file
TIME_RANGE = ["2023-07-15", "2023-07-20"]
OUT_DIR = Path("s1_grd_2023-07-15_2023-07-20")

# --- CONNECT & AUTH (OIDC opens a browser login) ---
con = openeo.connect(BACKEND_URL).authenticate_oidc()

# --- READ AOI ---
with open(AOI_GEOJSON, "r", encoding="utf-8") as f:
    aoi = json.load(f)   # dict with "type": "Polygon"/"MultiPolygon" (Feature or FeatureCollection also OK)

# --- LOAD S1 GRD ---
# This loads *all* GRD scenes intersecting the AOI and time window.
# We don’t filter polarization/orbit so you get everything.
cube = con.load_collection(
    "SENTINEL1_GRD",
    spatial_extent=aoi,
    temporal_extent=["2023-06-20", "2023-07-03"],
    bands=["VV", "VH"],   # <-- restrict to the VV/VH pair
)

cube = cube.sar_backscatter(
    #coefficient="gamma0_ellipsoid",
    local_incidence_angle=True,
    mask=True,
)


# Optional: keep only common polarizations or set one explicitly
# cube = cube.filter_bands(["VV", "VH"])   # or ["HH", "HV"] depending on what exists in your AOI/time

# Optional: subset by orbit direction (ascending/descending)
# cube = cube.filter_metadata("orbitDirection", "=", "ASCENDING")

# --- SAVE RESULT (GeoTIFF). Most backends split by date/polarization into multiple files. ---
result = cube.save_result(format="GTiff")
job = result.create_job(title="S1 GRD γ0 VV/VH 2023-07-01..20")
job.start_and_wait().get_results().download_files("s1_grd_2023-07-15_2023-07-20_VV-VH")