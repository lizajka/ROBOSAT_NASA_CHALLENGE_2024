#!/usr/bin/env python3
"""
Average Sentinel-1 VV/VH before/after a threshold date.

- BEFORE group:  strictly earlier than 2023-07-18
- AFTER  group:  on/after           2023-07-18

Outputs (in --outdir):
  VV_before.tiff, VH_before.tiff, VV_after.tiff, VH_after.tiff

Usage examples:
  python s1_avg_before_after.py "s1_grd_VV-VH"
  python s1_avg_before_after.py "s1_grd_VV-VH" --recursive --outdir "s1_averages"

Notes:
- Averages are done in the **native units** of the GeoTIFFs. If your files are in linear γ0,
  this is the correct way to average. If they’re already in dB, consider averaging in linear
  by converting to linear first; or add a flag to average in dB if you really need that.
"""

import argparse
import math
import re
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

THRESHOLD = date(2023, 7, 18)
NODATA_OUT = -9999.0  # output nodata for GeoTIFFs (float32)

# ---------------------- helpers ----------------------

def list_tiffs(root: Path, recursive: bool):
    pats = ("*.tif", "*.tiff", "*.TIF", "*.TIFF")
    files = []
    it = root.rglob if recursive else root.glob
    for p in pats:
        files.extend(it(p))
    return sorted(set(files))

def extract_date_from_name(name: str):
    """
    Extract acquisition date from filename.
    Tries patterns like 20230712T..., 2023-07-12, 2023_07_12, 20230712.
    Returns datetime.date or None.
    """
    # 1) YYYYMMDD followed by T
    m = re.search(r"(20\d{2})([01]\d)([0-3]\d)T", name)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    # 2) YYYY[-_]MM[-_]DD
    m = re.search(r"(20\d{2})[-_]?([01]\d)[-_]?([0-3]\d)", name)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None

def read_band_masked(ds, band_index):
    """Read band as masked array honoring NoData & NaN/Inf."""
    arr = ds.read(band_index, masked=False)
    mask = ~np.isfinite(arr)
    nd = ds.nodata
    if nd is not None and not (isinstance(nd, float) and math.isnan(nd)):
        mask |= (arr == nd)
    return np.ma.MaskedArray(arr, mask=mask)

def find_vv_vh_indices(ds, filepath: Path):
    """
    Return {'VV': idx_or_None, 'VH': idx_or_None}.
    Priority: per-band descriptions/tags -> filename hint -> fallback [1,2].
    """
    vv = None
    vh = None

    # descriptions
    if ds.descriptions:
        for i, d in enumerate(ds.descriptions, start=1):
            if not d:
                continue
            t = d.strip().upper()
            if t == "VV" and vv is None:
                vv = i
            if t == "VH" and vh is None:
                vh = i

    # tags
    for i in range(1, ds.count + 1):
        tags = ds.tags(i)
        for k in ("BAND_NAME", "name", "band_name", "long_name"):
            v = tags.get(k)
            if not v:
                continue
            t = v.strip().upper()
            if t == "VV" and vv is None:
                vv = i
            if t == "VH" and vh is None:
                vh = i

    # filename hint for single-band
    name = filepath.name.upper()
    if ds.count == 1:
        if "VV" in name and vv is None:
            vv = 1
        if "VH" in name and vh is None:
            vh = 1

    # fallback by position for 2-band products
    if ds.count >= 2 and vv is None and vh is None:
        vv, vh = 1, 2

    return {"VV": vv, "VH": vh}

def same_grid(ds, ref):
    return (
        ds.crs == ref["crs"]
        and ds.transform == ref["transform"]
        and ds.width == ref["width"]
        and ds.height == ref["height"]
    )

def reproject_to_ref(data_ma, src_profile, ref):
    """
    Reproject masked array to reference grid.
    Returns (data_float32, valid_mask_bool) in ref grid.
    """
    src_data = data_ma.filled(np.nan).astype("float32")
    src_valid = (~data_ma.mask).astype("uint8")

    dst_h, dst_w = ref["height"], ref["width"]
    dst_data = np.full((dst_h, dst_w), np.nan, dtype="float32")
    dst_valid = np.zeros((dst_h, dst_w), dtype="uint8")

    reproject(
        source=src_data,
        destination=dst_data,
        src_transform=src_profile.transform,
        src_crs=src_profile.crs,
        dst_transform=ref["transform"],
        dst_crs=ref["crs"],
        resampling=Resampling.bilinear,
        src_nodata=np.nan,
        dst_nodata=np.nan,
        num_threads=2,
    )
    reproject(
        source=src_valid,
        destination=dst_valid,
        src_transform=src_profile.transform,
        src_crs=src_profile.crs,
        dst_transform=ref["transform"],
        dst_crs=ref["crs"],
        resampling=Resampling.nearest,
        num_threads=2,
    )
    valid_bool = (dst_valid == 1) & np.isfinite(dst_data)
    return dst_data, valid_bool

def write_geotiff(path: Path, array, ref, nodata=NODATA_OUT):
    prof = {
        "driver": "GTiff",
        "width": ref["width"],
        "height": ref["height"],
        "count": 1,
        "dtype": "float32",
        "crs": ref["crs"],
        "transform": ref["transform"],
        "nodata": nodata,
        "compress": "deflate",
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(array.astype("float32"), 1)

# ---------------------- main ----------------------

def main():
    ap = argparse.ArgumentParser(description="Average S1 VV/VH before/after 2023-07-18.")
    ap.add_argument("folder", type=str, help="Folder with S1 GRD GeoTIFFs (multi- or single-band).")
    ap.add_argument("--recursive", action="store_true", help="Recurse into subfolders.")
    ap.add_argument("--outdir", type=str, default=None, help="Output directory (default: <input>/averages)")
    args = ap.parse_args()

    root = Path(args.folder)
    outdir = Path(args.outdir) if args.outdir else (root / "averages")

    files = list_tiffs(root, args.recursive)
    if not files:
        print(f"No GeoTIFFs found under {root}")
        return

    # Accumulators: for each polarization and group, keep sum & count arrays
    groups = {
        "before": {"VV": None, "VH": None, "count": {"VV": None, "VH": None}},
        "after":  {"VV": None, "VH": None, "count": {"VV": None, "VH": None}},
    }
    # Reference grid (taken from first file encountered)
    ref = None

    total_used = {"before": {"VV": 0, "VH": 0}, "after": {"VV": 0, "VH": 0}}

    for tif in files:
        acq = extract_date_from_name(tif.name)
        if acq is None:
            print(f"[WARN] Skipping (no date in name): {tif.name}")
            continue

        which = "before" if acq < THRESHOLD else "after"

        with rasterio.open(tif) as ds:
            if ref is None:
                ref = {
                    "crs": ds.crs,
                    "transform": ds.transform,
                    "width": ds.width,
                    "height": ds.height,
                }

            idx = find_vv_vh_indices(ds, tif)
            for pol in ("VV", "VH"):
                b = idx.get(pol)
                if not b or b > ds.count:
                    continue

                band = read_band_masked(ds, b)

                # Align to reference grid if needed
                if same_grid(ds, ref):
                    data = band.filled(np.nan).astype("float32")
                    valid = (~band.mask) & np.isfinite(data)
                else:
                    data, valid = reproject_to_ref(band, ds.profile, ref)

                # Initialize accumulators
                if groups[which][pol] is None:
                    groups[which][pol] = np.zeros((ref["height"], ref["width"]), dtype="float64")
                    groups[which]["count"][pol] = np.zeros((ref["height"], ref["width"]), dtype="uint32")

                groups[which][pol][valid] += data[valid].astype("float64")
                groups[which]["count"][pol][valid] += 1
                total_used[which][pol] += 1

    # Write outputs
    outputs = {
        ("before", "VV"): outdir / "VV_before.tiff",
        ("before", "VH"): outdir / "VH_before.tiff",
        ("after",  "VV"): outdir / "VV_after.tiff",
        ("after",  "VH"): outdir / "VH_after.tiff",
    }

    for (which, pol), path in outputs.items():
        sum_arr = groups[which][pol]
        cnt_arr = groups[which]["count"][pol]
        if ref is None or sum_arr is None or cnt_arr is None or cnt_arr.max() == 0:
            print(f"[INFO] No data for {pol} {which}; skipping {path.name}.")
            continue

        avg = np.full_like(sum_arr, NODATA_OUT, dtype="float32")
        valid = cnt_arr > 0
        avg[valid] = (sum_arr[valid] / cnt_arr[valid]).astype("float32")

        write_geotiff(path, avg, ref, nodata=NODATA_OUT)
        n_pix = int(valid.sum())
        n_imgs = total_used[which][pol]
        print(f"[OK] {path}  (contributing images: {n_imgs}, valid pixels: {n_pix})")

    print("Done.")

if __name__ == "__main__":
    main()
