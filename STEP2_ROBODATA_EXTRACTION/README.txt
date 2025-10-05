Description of ROS bag data and exported GeoJSONs
-------------------------------------------------

* A ROS bag is a file that stores recorded data streams from a robot or sensor system running under the Robot Operating System (ROS).
  - ROS is an open-source framework that connects multiple software modules (called nodes) through topics that carry messages such as sensor readings or navigation data.
  - A bag file captures these topics in real time, allowing playback or offline analysis later without the actual robot.
  - Collections of bag files from each experiment make up approximately 100 GB each and can be downloaded from https://grand-tour.leggedrobotics.com/dataset after receiving the access (ANYMALD).

* The bag files we used in our project come from the CPT7 Inertial Explorer unit used during the Kaferberg Forest experiments.
  - The file "2024-11-14-14-36-02_cpt7_ie_tc.bag" (and a similar one from KaferbergForest2) contains synchronized data topics such as:
    • /boxi/inertial_explorer/tc/navsatfix  –  GNSS positions (latitude, longitude, altitude)
    • /boxi/inertial_explorer/tc/odometry   –  Local odometry estimates from inertial sensors
  - These datasets describe how the robot moved through space during a test run of about eight minutes.

* Since ROS messages are not directly readable by GIS software, the data were converted to GeoJSON, a widely supported geospatial text format.
  - The extraction process used ROS tools (rosbag, rostopic echo) and simple Python scripts inside a ROS1 Docker container.
  - The main steps were:
    1. Read the /navsatfix topic from the bag.
    2. Save all GNSS fixes to a CSV file.
    3. Convert the CSV to two GeoJSON files:
       • One containing individual GNSS points.
       • One containing a LineString path of the trajectory.
    4. Read the /odometry topic, convert local coordinates to global ones using the GNSS origin, and export a third GeoJSON.

* The final output consists of three GeoJSON layers:
  1. navsatfix_points.geojson  –  all recorded GNSS positions.
  2. navsatfix_path.geojson    –  continuous GNSS trajectory line.
  3. odom_path.geojson         –  odometry-based trajectory in global coordinates.

* These GeoJSON files can be opened in QGIS, geojson.io, or any mapping software to visualize and compare the robot’s measured GNSS path and its odometry-based motion in the Kaferberg Forest test area. The two sets of GeoJSON files extracted from bag-files and used in our project are in this folder.

===ROS bag to GeoJSON conversion - requirements list
-------------------------------------------------

System:
* Ubuntu-based Docker container with ROS1 (e.g., ROS Noetic)
* Python 3 (included in most ROS images)

Required packages:
* rosbag (part of ROS1 installation)
* rostopic (part of ROS1 installation)
* python3 (>=3.6)
* core Python libraries: json, math, argparse, csv
* pv  –  for progress bar during data export

Optional packages:
* python3-pyproj  –  for coordinate transformations (not used; replaced by pure Python formulas)
* gdal-bin  –  provides ogr2ogr for converting GeoJSON to Shapefile or GeoPackage
* awk, tee, head  –  standard command-line tools used for filtering and preview
* pluma or any text editor  –  to view and edit exported text files

Network setup:
* Working DNS resolution in the container (can use nameserver 8.8.8.8 / 1.1.1.1 in /etc/resolv.conf)

No external Python dependencies (pip installs) were required.
All conversions and exports were performed using built-in Python modules and ROS utilities.


===Commands (execute with ROS1 running):

1. Confirm topics & (optionally) message count
rosbag info data/KaferbergForest2/2024-11-14-15-22-43_cpt7_ie_tc.bag
# Expect to see /boxi/inertial_explorer/tc/navsatfix and /boxi/inertial_explorer/tc/odometry

2. /navsatfix → CSV with progress (pv)
# If you know the exact message count, set MSGS and use -s $((MSGS+1)); otherwise omit -s.
rostopic echo -b data/KaferbergForest2/2024-11-14-15-22-43_cpt7_ie_tc.bag \
  -p /boxi/inertial_explorer/tc/navsatfix \
| pv -l > navsatfix_KF2.csv

3. CSV → GeoJSON (points + path)
python3 - <<'PY'
import csv, json, math
pts, line = [], []
with open("navsatfix_KF2.csv", newline="") as f:
    r = csv.DictReader(f)
    for row in r:
        try:
            lat=float(row["latitude"]); lon=float(row["longitude"])
            alt=row.get("altitude"); alt=float(alt) if alt not in (None,"","nan") else None
        except Exception: continue
        if math.isnan(lat) or math.isnan(lon): continue
        coords=[lon,lat] if alt is None else [lon,lat,alt]
        pts.append({"type":"Feature","geometry":{"type":"Point","coordinates":coords},"properties":row})
        line.append(coords)
with open("navsatfix_KF2_points.geojson","w") as f:
    json.dump({"type":"FeatureCollection","features":pts}, f)
if len(line)>=2:
    with open("navsatfix_KF2_path.geojson","w") as f:
        json.dump({"type":"FeatureCollection","features":[
            {"type":"Feature","geometry":{"type":"LineString","coordinates":line},
             "properties":{"source":"/boxi/inertial_explorer/tc/navsatfix"}}
        ]}, f)
print("Wrote navsatfix_KF2_points.geojson and navsatfix_KF2_path.geojson (if ≥2 pts).")
PY

4. /odometry → GeoJSON (georeference using NavSatFix)
# Using the robust script you already have
python3 data/export_local_to_geojson.py \
  data/KaferbergForest2/2024-11-14-15-22-43_cpt7_ie_tc.bag \
  /boxi/inertial_explorer/tc/odometry \
  --navsatfix /boxi/inertial_explorer/tc/navsatfix \
  --out odom_KF2_path.geojson

5. Exporting navsatfix_KF2_path.geojson from the bag.
python3 - <<'PY'
import json, math, rosbag
bag="data/KaferbergForest2/2024-11-14-15-22-43_cpt7_ie_tc.bag"
topic="/boxi/inertial_explorer/tc/navsatfix"
coords=[]
with rosbag.Bag(bag,'r') as b:
    for _, m, _ in b.read_messages(topics=[topic]):
        lat=getattr(m,'latitude',float('nan')); lon=getattr(m,'longitude',float('nan'))
        if not (math.isnan(lat) or math.isnan(lon)):
            alt=getattr(m,'altitude',None)
            coords.append([float(lon), float(lat)] if (alt is None or (isinstance(alt,float) and math.isnan(alt)))
                          else [float(lon), float(lat), float(alt)])
if len(coords) < 2:
    raise SystemExit("Not enough valid GNSS points to build a LineString.")
geo={"type":"FeatureCollection","features":[
    {"type":"Feature","geometry":{"type":"LineString","coordinates":coords},"properties":{"source":topic}}
]}
with open("navsatfix_KF2_path.geojson","w") as f: json.dump(geo,f)
print("Wrote navsatfix_KF2_path.geojson")
PY

