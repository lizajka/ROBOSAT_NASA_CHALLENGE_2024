# ROBOSAT_NASA_CHALLENGE_2025
Robosat combines SAR and optical satellite imagery with GIS data to identify forest fire zones in Switzerland. A quadruped robot, guided via joystick and GPS, maps terrain for rescue planning. We optimize routes using ROS, QGIS, and machine learning. Includes data, code, and visualization tools.

# Project workflow summary:
(For detailed description, refer to the README.txt files in the corresponding folders.)

1. Wildfire burn scar mapping: Acquire and preprocess Sentinel-1 SAR imagery, perform backscatter analysis, and delineate the burned area.

2. Robodog data extraction: Process experimental bag files using ROS1 to retrieve navigation and sensor datasets.

3. Terrain and trajectory analysis: Integrate robodog trajectory data with high-resolution DEM and LiDAR point cloud measurements within the QGIS environment (project available on OneDrive https://tuni-my.sharepoint.com/personal/yelyzaveta_pervysheva_tuni_fi/_layouts/15/onedrive.aspx?id=%2Fpersonal%2Fyelyzaveta%5Fpervysheva%5Ftuni%5Ffi%2FDocuments%2FROBOSAT%2Fqgis&ga=1).

4. Obstacle detection: Compute terrain obstacles along the robodog’s path based on elevation and point cloud metrics.
