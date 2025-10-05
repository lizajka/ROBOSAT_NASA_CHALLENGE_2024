SAR burn‑scar workflow (Sentinel‑1)
===============================================

SAR essentials (Sentinel‑1 GRD)
- Active microwave, C‑band (~5.4 GHz; ~5.6 cm). Day/night, largely weather‑independent.
- Pixel value: backscatter (σ⁰/γ⁰). Controlled by surface roughness, dielectric 
  (moisture), geometry (incidence angle/topography), and vegetation volume scattering.
- Polarizations: VV (co‑pol; surface/geometry) and VH (cross‑pol; vegetation/volume).
- Speckle: multiplicative noise inherent to SAR.
- VV and VH polarizations
- GRD files are pre-processed and analysis ready (no despeckling is performed)

Burn‑scar idea with SAR
- Fire removes/damages vegetation leading to decrease in backscattered signal, 
  the change is more pronounced in VH polarization but also detectable in VV.
- Compare pre-fire and post-fire images.
- Compute normalized change in linear domain:
  RBR = (After − Before) / (After + Before)     # expect in [−1, +1]; burn negative
- Smooth/average to reduce speckle; mask confounders (water, layover/shadow, extreme incidence).
- Threshold + morphology to produce a clean burn mask.


Scripts and how to run
---------------------------------

1) Downloads Sentinel‑1 GRD (VV,VH) over an AOI and time window; optionally daily mosaics.
   Area of interest (AOI) and the time window are set inside the script. Uses openEO.
- openEO is an open API and client libraries to run Earth‑observation processing on cloud backends.
  You describe a process graph in Python/R/JS; the backend (e.g., VITO/Sentinel Hub on openeo.cloud)
  executes it server‑side and returns results (e.g., GeoTIFF, CSV).
   File: s1_download_openeo.py

   Basic run:
   python3 s1_download_openeo.py

2) Recursively scan a folder for Sentinel-1 GRD GeoTIFFs, auto-detects VV/VH bands 
   from metadata (or filename/order), reads them with NoData masking, converts linear 
   to dB (unless --already-db), applies a robust percentile stretch (default 2–98%, capped to [-35, +5] dB), 
   and saves one PNG per band with a dB colorbar. 
   Output layout: <outdir>/<tif_stem>/<tif_stem>_VV_dB.png (and _VH_dB.png).
   File: python s1_extract_images.py
   Basic run:
   python3 s1_extract_images.py /path/to/s1_grd_VV-VH --recursive --outdir /path/to/s1_png


3) Average scenes into pre/post stacks (split at 2023‑07‑18; before=exclusive, after=inclusive)
   File: s1_avg_before_after.py
   Outputs: VV_before.tiff, VH_before.tiff, VV_after.tiff, VH_after.tiff
   Run:
   python3 s1_avg_before_after.py "s1_grd_VV-VH" --recursive --outdir "s1_averages"


4) RBR directly from two rasters
   File: s1_relative_burn_ratio_from_pairs.py
   Outputs: RBR_VV.tiff / RBR_VH.tiff (if present in both)
   Run (linear):
   python s1_relative_burn_ratio_from_pairs.py before.tif after.tif --outdir rbr_out
   Run (inputs in dB):
   python s1_relative_burn_ratio_from_pairs.py before_db.tif after_db.tif --inputs-in-db --outdir rbr_out

5) Quick one‑off plotting of any GeoTIFF
   File: tiff_to_png.py
   Run (auto‑stretch):
   python tiff_to_png.py /path/to/file.tif
   Run (SAR dB with fixed scale):
   python tiff_to_png.py /path/to/s1_vv.tif --db --fixed-range -25 0 --cmap magma


Practical notes
- Keep pre/post on the same relative orbit & pass (ASC/DESC) to reduce geometry effects.
- Prefer linear domain for math (convert dB→linear when computing RBR/averages).
- Expect RBR≈[−1,+1]; spatially coherent negative patches (especially in VH) are typical burn signatures.
