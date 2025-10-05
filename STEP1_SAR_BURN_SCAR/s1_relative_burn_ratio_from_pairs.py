#!/usr/bin/env python3
"""
Compute SAR 'relative burn ratio' per polarization from two S1 rasters (before & after).

RBR = (After - Before) / (After + Before)
- Computed in LINEAR power domain (recommended for SAR).
- If your inputs are in dB, add --inputs-in-db to convert to linear first.

Inputs:
  BEFORE.tif  AFTER.tif   (each may be multi-band [VV,VH] or single-band with VV/VH in name)

Outputs (in --outdir):
  RBR_VV.tiff (if VV present in both)
  RBR_VH.tiff (if VH present in both)

Usage:
  python s1_relative_burn_ratio_from_pairs.py BEFORE.tif AFTER.tif
  python s1_relative_burn_ratio_from_pairs.py BEFORE.tif AFTER.tif --inputs-in-db --outdir rbr_out
"""

import argparse
from pathlib import Path
import math
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

NODATA_OUT = -9999.0
EPS = 1e-12  # protect division by ~zero

# ---------- helpers ----------

def read_band_masked(ds, band_index):
    arr = ds.read(band_index, masked=False).astype("float32")
    mask = ~np.isfinite(arr)
    nd = ds.nodata
    if nd is not None and not (isinstance(nd, float) and math.isnan(nd)):
        mask |= (arr == nd)
    return np.ma.MaskedArray(arr, mask=mask)

def find_pol_indices(ds, filepath: Path):
    """
    Return dict with present polarizations and their 1-based indices, e.g. {'VV':1,'VH':2}.
    Priority: band descriptions/tags -> filename hint for single-band -> fallback [1,2].
    """
    vv = None
    vh = None

    # Descriptions
    if ds.descriptions:
        for i, d in enumerate(ds.descriptions, start=1):
            if not d: continue
            t = d.strip().upper()
            if t == "VV" and vv is None: vv = i
            if t == "VH" and vh is None: vh = i

    # Tags
    for i in range(1, ds.count + 1):
        tags = ds.tags(i)
        for k in ("BAND_NAME", "name", "band_name", "long_name"):
            v = tags.get(k)
            if not v: continue
            t = v.strip().upper()
            if t == "VV" and vv is None: vv = i
            if t == "VH" and vh is None: vh = i

    # Filename hint for single-band
    name = filepath.name.upper()
    if ds.count == 1:
        if "VV" in name and vv is None: vv = 1
        if "VH" in name and vh is None: vh = 1

    # Fallback (common order [VV,VH])
    if ds.count >= 2 and vv is None and vh is None:
        vv, vh = 1, 2

    present = {}
    if vv is not None: present["VV"] = vv
    if vh is not None: present["VH"] = vh
    return present

def grids_match(p1, p2):
    return (
        p1["crs"] == p2["crs"]
        and p1["transform"] == p2["transform"]
        and p1["width"] == p2["width"]
        and p1["height"] == p2["height"]
    )

def reproject_to_ref(ma, src_prof, ref_prof):
    """Reproject masked array to ref grid, returning masked array in ref CRS/transform."""
    src = ma.filled(np.nan).astype("float32")
    src_valid = (~ma.mask).astype("uint8")

    dst_data  = np.full((ref_prof["height"], ref_prof["width"]), np.nan, dtype="float32")
    dst_valid = np.zeros((ref_prof["height"], ref_prof["width"]), dtype="uint8")

    reproject(
        source=src, destination=dst_data,
        src_transform=src_prof["transform"], src_crs=src_prof["crs"],
        dst_transform=ref_prof["transform"], dst_crs=ref_prof["crs"],
        resampling=Resampling.bilinear,
        src_nodata=np.nan, dst_nodata=np.nan,
    )
    reproject(
        source=src_valid, destination=dst_valid,
        src_transform=src_prof["transform"], src_crs=src_prof["crs"],
        dst_transform=ref_prof["transform"], dst_crs=ref_prof["crs"],
        resampling=Resampling.nearest,
    )
    mask = (dst_valid == 0) | ~np.isfinite(dst_data)
    return np.ma.MaskedArray(dst_data, mask=mask)

def to_linear(ma_db: np.ma.MaskedArray) -> np.ma.MaskedArray:
    """dB -> linear power."""
    lin = np.power(10.0, ma_db / 10.0, dtype=np.float32)
    return np.ma.MaskedArray(lin, mask=ma_db.mask)

def compute_rbr(before_lin: np.ma.MaskedArray, after_lin: np.ma.MaskedArray):
    """RBR = (after - before) / (after + before) in linear domain."""
    mask = before_lin.mask | after_lin.mask
    b = np.ma.MaskedArray(before_lin.filled(0.0), mask=mask)
    a = np.ma.MaskedArray(after_lin.filled(0.0), mask=mask)
    num = a - b
    den = a + b
    r = np.ma.divide(num, den + EPS)
    r.mask = mask | ~np.isfinite(r)
    return r

def write_gtiff(path: Path, arr: np.ndarray, ref_prof):
    prof = {
        "driver": "GTiff",
        "width": ref_prof["width"],
        "height": ref_prof["height"],
        "count": 1,
        "dtype": "float32",
        "crs": ref_prof["crs"],
        "transform": ref_prof["transform"],
        "nodata": NODATA_OUT,
        "compress": "deflate",
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(arr.astype("float32"), 1)

# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="Compute RBR per polarization from BEFORE & AFTER S1 rasters.")
    ap.add_argument("before", type=str, help="BEFORE raster (multi- or single-band)")
    ap.add_argument("after",  type=str, help="AFTER raster (multi- or single-band)")
    ap.add_argument("--inputs-in-db", action="store_true",
                    help="Set if inputs are in dB (will convert to linear before computing RBR)")
    ap.add_argument("--outdir", type=str, default=None, help="Output directory (default: AFTER's folder)")
    args = ap.parse_args()

    before_path = Path(args.before)
    after_path  = Path(args.after)
    outdir = Path(args.outdir) if args.outdir else after_path.parent

    with rasterio.open(before_path) as ds_b, rasterio.open(after_path) as ds_a:
        pol_b = find_pol_indices(ds_b, before_path)
        pol_a = find_pol_indices(ds_a, after_path)

        # Reference grid = BEFORE
        ref_prof = {
            "crs": ds_b.crs,
            "transform": ds_b.transform,
            "width": ds_b.width,
            "height": ds_b.height,
        }

        available = []
        for pol in ("VV", "VH"):
            if pol in pol_b and pol in pol_a:
                available.append(pol)
            else:
                print(f"[INFO] Skipping {pol}: not present in both inputs.")

        if not available:
            print("[ERROR] Neither VV nor VH found in both inputs. Nothing to do.")
            return

        for pol in available:
            b_idx = pol_b[pol]
            a_idx = pol_a[pol]

            # Read bands
            b_band = read_band_masked(ds_b, b_idx)
            a_band = read_band_masked(ds_a, a_idx)

            # Align AFTER to BEFORE grid if needed
            if not grids_match(ds_b.profile, ds_a.profile):
                a_band = reproject_to_ref(a_band, ds_a.profile, ref_prof)

            # Convert to linear if inputs are dB
            if args.inputs_in_db:
                b_band = to_linear(b_band)
                a_band = to_linear(a_band)

            # Compute RBR
            rbr = compute_rbr(b_band, a_band)

            # Save
            out_path = outdir / f"RBR_{pol}.tiff"
            out = np.full((ref_prof["height"], ref_prof["width"]), NODATA_OUT, dtype="float32")
            valid = ~rbr.mask
            out[valid] = rbr.filled(0.0)[valid].astype("float32")
            write_gtiff(out_path, out, ref_prof)

            # Quick stats
            vals = rbr.compressed()
            if vals.size:
                print(f"[OK] {out_path}  min={vals.min():.4f}  p5={np.percentile(vals,5):.4f}  "
                      f"med={np.median(vals):.4f}  p95={np.percentile(vals,95):.4f}  max={vals.max():.4f}  n={vals.size}")
            else:
                print(f"[OK] {out_path}  (no valid pixels)")

    print("Done.")

if __name__ == "__main__":
    main()
