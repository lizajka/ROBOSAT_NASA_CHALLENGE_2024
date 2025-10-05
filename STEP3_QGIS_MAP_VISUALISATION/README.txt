Please to proceed open https://tuni-my.sharepoint.com/my?id=%2Fpersonal%2Fyelyzaveta%5Fpervysheva%5Ftuni%5Ffi%2FDocuments%2FROBOSAT%2Fqgis&ga=1
🛰️ RoboSat Project – QGIS Documentation
📁 Project Overview

This QGIS project (ROBOSAT.qgz) is focused on terrain and path analysis using high-resolution surface models and path datasets.
The merged DEM (merged.tif) serves as the core elevation dataset for visualization, terrain modeling, and feature extraction.

Contents
File	Description
ROBOSAT.qgz	QGIS project file — open this to view all layers together.
merged.tif	Merged Digital Elevation Model (DEM) created from SwissSurface3D LAZ tiles.
navsatfix_path.geojson	Path recorded during navigation (actual route).
KF2_path.geojson	Secondary or comparison path (planned or reference route).
swisssurface3d_2024_268x_125x_2056_57x.laz	Source SwissSurface3D point cloud tiles used to generate the DEM.
🧭 Coordinate Reference System

All files use  LV95 (EPSG: 2056), which ensures perfect alignment between the DEM and paths.

🪄 How to Open

Start QGIS (≥ 3.30)

Go to File → Open Project…

RoboSat – Step 3: QGIS Visualization (KFargen Forest)
📖 Purpose

This folder contains Step 3 of the RoboSat project — the QGIS visualization and terrain analysis stage for the KFargen Forest area.
It is used to visually inspect surface data, verify navigation paths, and analyze terrain features relevant to autonomous navigation.

📂 Contents
File	Description
ROBOSAT.qgz	QGIS project file. Open this in QGIS to view all layers together.
merged.tif	Digital Elevation Model (DEM) generated from SwissSurface3D data — used for analyzing slopes, inclinations, and terrain profiles.
swisssurface3d_2024_268x_125x_2056_57x.laz	LiDAR point cloud (SwissSurface3D) — used for obstacle detection and avoidance modeling.
navsatfix_path.geojson	Navigation path from Step 2 (actual GPS data).
KF2_path.geojson	Reference or comparison path from Step 2 (planned route).
🧭 Coordinate Reference System

All data are in CH1903+ / LV95 (EPSG:2056), ensuring proper spatial alignment and metric elevation values.

🎯 Data Accuracy

SwissSurface3D (LAZ):

Vertical accuracy: ±0.5 m

Horizontal accuracy: ±0.3 m

Point spacing: ~0.5 m

Ideal for detecting small terrain variations and vegetation or man-made obstacles.

Merged DEM (GeoTIFF):

Derived from SwissSurface3D LAZ tiles.

Effective resolution: 0.5–1.0 m.

Used for inclination, elevation profile, and terrain slope analysis.

GeoJSON paths:

Imported from Step 2 (see Step 2 documentation for details).

Used for path alignment and performance verification.

🪄 How to Open in QGIS

Open QGIS (v3.30 or later).

Go to File → Open Project…

Select ROBOSAT.qgz.

The project will load automatically with:

merged.tif as the elevation raster background.

navsatfix_path.geojson and KF2_path.geojson as path overlays.

Optional LAZ layers (can be loaded via Add → Point Cloud Layer).

🗺️ What You’ll See

DEM (merged.tif) — terrain elevation and slope visualization.

Paths (GeoJSON) — real and planned navigation routes (from Step 2).

LAZ (SwissSurface3D) — dense 3D point cloud for obstacle and vegetation analysis.

💡 Recommended QGIS Tools

Hillshade / Slope Renderer → to visualize terrain relief and inclinations.

Profile Tool Plugin → to check elevation changes along the paths.

Point Cloud Viewer → to explore LAZ data in 3D for obstacle assessment.

📅 Step Summary

Step 3 – QGIS Visualization:
This step focuses on terrain analysis, path validation, and obstacle overview using the processed DEM and point cloud data.
The navigation paths (GeoJSONs) are carried over from Step 2 (Path Generation and Tracking).