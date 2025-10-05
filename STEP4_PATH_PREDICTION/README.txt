README: Combined DEM and COPC Terrain Map (Obstacles)
Overview

This project combines DEM (Digital Elevation Model) and COPC (Classified Point Cloud) data into a single GeoTIFF file to create an obstacle map. The result helps autonomous systems identify safer walking or driving areas and where more caution or sensing is required.

Methodology

We processed and merged the datasets using QGIS as follows:

Loaded the Data:

Imported both the DEM and COPC layers into QGIS.

Ensured both datasets used the same coordinate reference system (CRS).

Rasterization (if needed):

Converted the COPC (point cloud) data into a raster layer representing surface height or obstacle intensity.

Combining Layers:

Used Raster Calculator in QGIS to combine the DEM and COPC rasters.

The formula added or weighted the obstacle (COPC) layer on top of the DEM to produce a single .tif file representing both elevation and obstacle density.

Output:

Exported the final combined raster as a GeoTIFF named obstacles.tif.

Additional Scenario (JPG Visualization)

In one scenario, we also generated a JPG visualization that shows all potential walking paths.

The darker regions in this image represent possible areas where the system could safely navigate, even when performing an exhaustive search — for example, when it needs to “check every single corner.”

This JPG provides a quick visual reference for pathfinding and full coverage exploration without requiring full GIS tools.

Interpretation

Dark colors → Safer and flatter areas, suitable for autonomous walking or driving.

Lighter (white) areas → Steeper or obstacle-heavy zones, requiring more laser scanning or caution.

Purpose

This combined raster and visualization support autonomous mobility and environmental awareness by making it easier to identify both optimal paths and possible exploration areas within complex terrain.
