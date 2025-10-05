#!/usr/bin/env python3
"""
Visualize Sentinel-1 GRD VV/VH bands as PNGs with good-looking dB scaling.

- Auto-detects VV/VH (from band descriptions/tags; falls back to band order or filename).
- Converts linear backscatter to dB (10*log10) by default.
- Robust contrast stretch with percentile clipping (default 2..98%).
- Saves one PNG per band with a colorbar labeled in dB.

Usage example:
  python s1_visualize_vv_vh.py "s1_grd_VV-VH" \
      --recursive \
      --outdir "s1_grd_VV-VH_png" \
      --pclip 2 98 \
      --cmap gray

Options:
  --recursive           Recurse into subfolders (default: off)
  --outdir PATH         Output root folder (default: <input>/png)
  --pclip L H           Percentile clip in dB (default: 2 98)
  --sample N            Max samples for percentile calc (default: 5e6)
  --fixed-range L H     Optional fixed dB range (e.g., -25 0) for consistent color scale across images
  --already-db          Skip dB conversion (use if your TIFFs are already in dB)
  --cmap NAME           Matplotlib colormap (default: gray). Try 'magma', 'viridis' if you prefer color.
  --dpi N               PNG DPI (default: 180)

Requires:
  pip install rasterio numpy matplotlib
"""
import argparse
import math
import re
from pathlib import Path

import numpy as np
import rasterio
import matplotlib.pyplot as plt

# ---------------- utilities ----------------

def list_tiffs(root: Path, recursive: bool):
    pats = ["*.tif", "*.tiff", "*.TIF", "*.TIFF"]
    it = root.rglob if recursive else root.glob
    files = []
    for p in pats:
        files.extend(it(p))
    return sorted(set(files))

def read_band_masked(ds, b):
    """Read band b as masked array honoring nodata and NaN/Inf."""
    arr = ds.read(b, masked=False)
    mask = ~np.isfinite(arr)
    nd = ds.nodata
    if nd is not None and not (isinstance(nd, float) and math.isnan(nd)):
        mask |= (arr == nd)
    return np.ma.MaskedArray(arr, mask=mask)

def to_db_safe(ma):
    """Convert linear backscatter to dB; <=0 becomes masked."""
    m = np.ma.masked_less_equal(ma, 0)
    with np.errstate(divide="ignore"):
        return 10.0 * np.ma.log10(m)

def robust_percentiles(ma, plo, phi, sample_max):
    v = ma.compressed()
    if v.size == 0:
        return None, None
    if v.size > sample_max:
        idx = np.random.default_rng(12345).choice(v.size, size=int(sample_max), replace=False)
        v = v[idx]
    lo = np.percentile(v, plo)
    hi = np.percentile(v, phi)
    if not np.isfinite(lo) or not np.isfinite(hi) or lo >= hi:
        lo, hi = float(v.min()), float(v.max())
    if lo == hi:
        hi = lo + 1e-6
    return float(lo), float(hi)

def find_band_indices_for_vv_vh(ds, filepath: Path):
    """
    Return dict like {'VV': index or None, 'VH': index or None}.
    Priority: per-band descriptions/tags -> filename hint -> fallback by position.
    """
    vv_idx = None
    vh_idx = None

    # 1) Descriptions
    if ds.descriptions:
        for i, d in enumerate(ds.descriptions, start=1):
            if not d:
                continue
            t = d.strip().upper()
            if t == "VV":
                vv_idx = vv_idx or i
            if t == "VH":
                vh_idx = vh_idx or i

    # 2) Tags
    for i in range(1, ds.count + 1):
        tags = ds.tags(i)
        for k in ("BAND_NAME", "name", "band_name", "long_name"):
            v = tags.get(k)
            if not v:
                continue
            t = v.strip().upper()
            if t == "VV":
                vv_idx = vv_idx or i
            if t == "VH":
                vh_idx = vh_idx or i

    # 3) Filename hint (single-band files commonly have VV/VH in name)
    name = filepath.name.upper()
    if ds.count == 1:
        if "VV" in name and vv_idx is None:
            vv_idx = 1
        if "VH" in name and vh_idx is None:
            vh_idx = 1

    # 4) Fallback by position for two-band products
    if ds.count >= 2:
        if vv_idx is None and vh_idx is None:
            # Many stacks are [VV, VH]
            vv_idx, vh_idx = 1, 2

    return {"VV": vv_idx, "VH": vh_idx}

def render_band_png(ma_db, out_png: Path, vmin, vmax, cmap="gray", dpi=180, title=None):
    """Save a band image with colorbar in dB."""
    # Turn masked values transparent
    img = np.ma.masked_invalid(ma_db)

    plt.figure(figsize=(8, 6), dpi=dpi)
    ax = plt.gca()
    im = ax.imshow(img, vmin=vmin, vmax=vmax, cmap=cmap, interpolation="nearest")
    ax.set_axis_off()
    if title:
        ax.set_title(title, fontsize=10)
    cbar = plt.colorbar(im, ax=ax, fraction=0.030, pad=0.02)
    cbar.set_label("Backscatter (dB)")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout(pad=0.05)
    plt.savefig(out_png, bbox_inches="tight", pad_inches=0.05)
    plt.close()
    print(f"[OK] {out_png}  (dB range {vmin:.2f}..{vmax:.2f})")

# ---------------- main ----------------

def main():
    ap = argparse.ArgumentParser(description="Visualize S1 VV/VH bands as pretty PNGs with dB color scale.")
    ap.add_argument("folder", type=str, help="Folder with S1 GRD GeoTIFFs (e.g., s1_grd_VV-VH)")
    ap.add_argument("--recursive", action="store_true", help="Recurse into subfolders")
    ap.add_argument("--outdir", type=str, default=None, help="Output root (default: <input>/png)")
    ap.add_argument("--pclip", nargs=2, type=float, default=[2.0, 98.0], metavar=("LOW", "HIGH"),
                    help="Percentile clip for dB scaling (ignored if --fixed-range is set)")
    ap.add_argument("--sample", type=float, default=5e6, help="Max samples for percentile calc")
    ap.add_argument("--fixed-range", nargs=2, type=float, default=None, metavar=("MIN_DB", "MAX_DB"),
                    help="Fixed dB range (e.g., -25 0) for consistent color scaling")
    ap.add_argument("--already-db", action="store_true",
                    help="Skip dB conversion (use if your data are already in dB)")
    ap.add_argument("--cmap", type=str, default="gray", help="Matplotlib colormap (default: gray)")
    ap.add_argument("--dpi", type=int, default=180, help="DPI for PNGs")
    args = ap.parse_args()

    root = Path(args.folder)
    out_root = Path(args.outdir) if args.outdir else (root / "png")

    files = list_tiffs(root, args.recursive)
    if not files:
        print(f"No GeoTIFFs found under {root}")
        return

    print(f"Found {len(files)} file(s). Writing PNGs under: {out_root}")

    for tif in files:
        with rasterio.open(tif) as ds:
            idx = find_band_indices_for_vv_vh(ds, tif)
            file_out_dir = out_root / tif.stem

            for pol in ("VV", "VH"):
                b = idx.get(pol)
                if not b or b > ds.count:
                    # Not present in this file
                    continue

                band = read_band_masked(ds, b)

                # Convert to dB if needed
                if args.already_db:
                    data_db = band.astype("float32")
                else:
                    data_db = to_db_safe(band).astype("float32")

                # Determine display range in dB
                if args.fixed_range:
                    vmin, vmax = float(args.fixed_range[0]), float(args.fixed_range[1])
                else:
                    vmin, vmax = robust_percentiles(data_db, args.pclip[0], args.pclip[1], args.sample)
                    if vmin is None:
                        print(f"[SKIP] {tif.name} {pol}: no valid data.")
                        continue
                    # Clamp to a sensible SAR range to avoid wild outliers
                    vmin = max(vmin, -35.0)
                    vmax = min(vmax, 5.0)
                    if vmin >= vmax:
                        vmax = vmin + 0.1

                # Title & output
                title = f"{tif.name} — {pol}"
                out_png = file_out_dir / f"{tif.stem}_{pol}_dB.png"

                render_band_png(data_db, out_png, vmin=vmin, vmax=vmax,
                                cmap=args.cmap, dpi=args.dpi, title=title)

    print("Done.")

if __name__ == "__main__":
    main()
