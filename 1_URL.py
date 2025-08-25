# ==========================================================
# Import libraries 
# ==========================================================
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, LineString
from geopy.distance import geodesic
from pathlib import Path

# ==========================================================
# Global Configuration
# ==========================================================
output_folder = Path("C:/GSV/")
output_folder.mkdir(parents=True, exist_ok=True)

angles = [0, 90, 180, 270]
url_log_file = ('C:/GSV/lisbon_streetview_urls.csv')

# Load the roads shapefile
gdf = gpd.read_file('C:/GSV/roads/roads_lisbon.shp')

# Create the 'dissolve' field and assign the value 1 to all the rows
gdf['dissolve'] = 1

# Perform the dissolve based on the 'dissolve' field (all roads will be combined into a single geometry)
gdf_dissolved = gdf.dissolve(by='dissolve')

# Save the result to a new shapefile
gdf_dissolved.to_file('C:/GSV/roads/roads_lisbon_dissolved.shp')

shapefile_path = "C:/GSV/roads/roads_lisbon_dissolved.shp"

# ==========================================================
# Helper Functions
# ==========================================================
def generate_image_url(lat, lon, angle):
    return f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lon}&heading={angle}"

def point_is_near(lat, lon, captured_coords, threshold_distance):
    new_point = (lat, lon)
    for existing in captured_coords:
        if geodesic(existing, new_point).meters < threshold_distance:
            return True
    return False

def interpolate_points(line, distance):
    points = []
    total_length = line.length
    num_segments = int(total_length // distance)
    
    for i in range(num_segments + 1):
        point = line.interpolate(i * distance)
        points.append(point)
    return points

def save_urls_to_csv(lat, lon, angle, image_url, df_urls):
    # Check for duplicates
    duplicate = ((df_urls['Latitude'] == lat) & 
                 (df_urls['Longitude'] == lon) & 
                 (df_urls['Angle'] == angle)).any()
    
    if not duplicate:
        image_name = 1 if df_urls.empty else df_urls['Image_Name'].max() + 1
        new_row = {
            "Latitude": lat,
            "Longitude": lon,
            "Angle": angle,
            "Image_URL": image_url,
            "Image_Name": image_name
        }
        df_urls = pd.concat([df_urls, pd.DataFrame([new_row])], ignore_index=True)
        print(f"URL saved: {image_url} (Image_Name: {image_name})")
    else:
        print(f"URL already registered: {image_url}")
    
    return df_urls

# ==========================================================
# Main Logic
# ==========================================================
print("Loading shapefile...")
gdf = gpd.read_file(shapefile_path)
gdf = gdf.to_crs(epsg=3857)  # reproject to meters
point_distance = 30  # meters

captured_coords = []

# Load existing CSV or create a new one
url_log_file = Path("C:/GSV/lisbon_streetview_urls.csv")
if url_log_file.exists():
    df_urls = pd.read_csv(url_log_file)
else:
    df_urls = pd.DataFrame(columns=["Latitude", "Longitude", "Angle", "Image_URL", "Image_Name"])

# Iterate over each row in the shapefile
for idx, row in gdf.iterrows():
    geometry = row.geometry
    if geometry.is_empty:
        continue
    lines = geometry.geoms if geometry.geom_type == 'MultiLineString' else [geometry]
    for line in lines:
        if line.length == 0:
            continue
        points = interpolate_points(line, point_distance)
        for point in points:
            # Convert back to WGS84 to generate URL (lat/lon)
            point_wgs84 = gpd.GeoSeries([point], crs=gdf.crs).to_crs(epsg=4326).geometry[0]
            lat, lon = point_wgs84.y, point_wgs84.x
            if point_is_near(lat, lon, captured_coords, threshold_distance=point_distance):
                print(f"Coordinates ({lat:.6f}, {lon:.6f}) too close to a previously captured point. Skipping.")
                continue
            captured_coords.append((lat, lon))
            for angle in angles:
                image_url = generate_image_url(lat, lon, angle)
                df_urls = save_urls_to_csv(lat, lon, angle, image_url, df_urls)
                

# Save CSV
df_urls.to_csv(url_log_file, index=False)
print("Processing completed! URLs have been saved to the CSV file.")

