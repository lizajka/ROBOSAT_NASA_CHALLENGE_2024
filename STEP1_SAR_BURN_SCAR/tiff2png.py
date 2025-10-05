#!/usr/bin/env python3
# pip install rasterio numpy matplotlib
import argparse, math
from pathlib import Path
import numpy as np
import rasterio
import matplotlib.pyplot as plt

def read_band_masked(path: Path):
    with rasterio.open(path) as ds:
        arr = ds.read(1, masked=False)
        nd  = ds.nodata
        mask = ~np.isfinite(arr)
        if nd is not None and not (isinstance(nd, float) and math.isnan(nd)):
            mask |= (arr == nd)
    return np.ma.MaskedArray(arr, mask=mask)

def to_db(ma):
    m = np.ma.masked_less_equal(ma, 0)
    with np.errstate(divide="ignore"): return 10.0 * np.ma.log10(m)

def percentiles(ma, lo, hi):
    v = ma.compressed()
    if v.size == 0: return None, None
    return float(np.percentile(v, lo)), float(np.percentile(v, hi))

def main():
    ap = argparse.ArgumentParser(description="Plot a GeoTIFF (band 1) as a nice PNG.")
    ap.add_argument("tif", type=str, help="Input GeoTIFF")
    ap.add_argument("--out", type=str, help="Output PNG path (default: alongside input)")
    ap.add_argument("--db", action="store_true", help="Convert values to dB (10*log10), for SAR")
    ap.add_argument("--pclip", nargs=2, type=float, default=[2.0, 98.0], metavar=("LOW","HIGH"),
                    help="Percentile clip for display stretch (default 2 98)")
    ap.add_argument("--fixed-range", nargs=2, type=float, metavar=("MIN","MAX"),
                    help="Fixed display range (skips percentile stretch)")
    ap.add_argument("--cmap", default="gray", help="Matplotlib colormap (default: gray)")
    ap.add_argument("--dpi", type=int, default=180, help="PNG DPI (default 180)")
    args = ap.parse_args()

    tif = Path(args.tif)
    out = Path(args.out) if args.out else tif.with_suffix(".png")
    title = tif.stem

    band = read_band_masked(tif)
    data = to_db(band) if args.db else band

    if args.fixed_range:
        vmin, vmax = map(float, args.fixed_range)
    else:
        vmin, vmax = percentiles(data, *args.pclip)
        if vmin is None:
            print("No valid data to plot."); return
        if vmin >= vmax: vmax = vmin + 1e-6

    plt.figure(figsize=(8,6), dpi=args.dpi)
    ax = plt.gca()
    im = ax.imshow(data, vmin=vmin, vmax=vmax, cmap=args.cmap, interpolation="nearest")
    ax.set_title(title, fontsize=11)
    ax.set_axis_off()
    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("Value (dB)" if args.db else "Value")
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout(pad=0.05)
    plt.savefig(out, bbox_inches="tight", pad_inches=0.05)
    plt.close()
    print(f"[OK] {out}  range={vmin:.4f}..{vmax:.4f}")

if __name__ == "__main__":
    main()
