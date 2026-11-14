
from pathlib import Path
import json
import pandas as pd
import osmnx as ox

# ==========================================
# 1. PROJECT CONFIGURATION
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = PROJECT_DIR / "data" / "raw" / "places"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed" / "places"
CACHE_DIR = RAW_DIR / "osmnx_cache"

for folder in [RAW_DIR, PROCESSED_DIR, CACHE_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

PLACE_QUERY = "Cairo Governorate, Egypt"

# ==========================================
# 2. OPENSTREETMAP CONFIGURATION
# ==========================================

ox.settings.use_cache = True
ox.settings.cache_folder = str(CACHE_DIR)
ox.settings.log_console = True
ox.settings.requests_timeout = 180

# Categories to collect.
# OSMnx combines these tags using UNION logic.
TAGS = {
    "tourism": [
        "attraction",
        "museum",
        "gallery",
        "viewpoint",
        "zoo",
        "aquarium",
        "theme_park"
    ],
    "historic": True,
    "amenity": [
        "restaurant",
        "cafe"
    ],
    "leisure": [
        "park",
        "garden"
    ]
}

# ==========================================
# 3. RETRIEVE CAIRO BOUNDARY
# ==========================================

print("\n" + "=" * 60)
print("RAHHAL - CAIRO PLACES DATA COLLECTION")
print("=" * 60)

print("\n[1/4] Retrieving Cairo boundary...")

boundary = ox.geocoder.geocode_to_gdf(PLACE_QUERY)

if boundary.empty:
    raise RuntimeError("Could not retrieve Cairo boundary.")

boundary_path = RAW_DIR / "cairo_boundary.geojson"

boundary.to_file(
    boundary_path,
    driver="GeoJSON"
)

print("Boundary retrieved successfully.")
print("Boundary information:")
print(boundary[["display_name"]].to_string(index=False)
      if "display_name" in boundary.columns
      else boundary[["name"]].to_string(index=False)
      if "name" in boundary.columns
      else boundary.index)

# ==========================================
# 4. DOWNLOAD PLACES
# ==========================================

print("\n[2/4] Downloading places from OpenStreetMap...")
print("This may take several minutes.")

polygon = boundary.geometry.union_all()

places = ox.features.features_from_polygon(
    polygon,
    TAGS
)

if places.empty:
    raise RuntimeError("No places were returned by OpenStreetMap.")

print(f"\nRetrieved OSM records: {len(places):,}")

# ==========================================
# 5. SAVE RAW DATA
# ==========================================

print("\n[3/4] Saving raw data...")

raw = places.reset_index()

raw_geojson = RAW_DIR / "cairo_places_raw.geojson"
raw_csv = RAW_DIR / "cairo_places_raw.csv"

raw.to_file(
    raw_geojson,
    driver="GeoJSON"
)

raw_csv_df = raw.copy()
raw_csv_df["geometry"] = raw_csv_df.geometry.to_wkt()

raw_csv_df.to_csv(
    raw_csv,
    index=False,
    encoding="utf-8-sig"
)

# ==========================================
# 6. BASIC STRUCTURING
# ==========================================

print("\n[4/4] Creating preliminary places dataset...")

# Keep named places in the preliminary dataset.
# Raw data remains untouched.

if "name" not in raw.columns:
    raise RuntimeError("The downloaded dataset has no name column.")

clean = raw[
    raw["name"].notna()
].copy()

# Generate stable source identifiers.
clean["place_id"] = (
    "osm:"
    + clean["element"].astype(str)
    + ":"
    + clean["id"].astype(str)
)

# Calculate representative coordinates.
projected_geometry = clean.to_crs(epsg=32636).geometry
representative_points = projected_geometry.centroid.to_crs(epsg=4326)

clean["latitude"] = representative_points.y
clean["longitude"] = representative_points.x

# Determine a preliminary category.
def classify_place(row):

    if pd.notna(row.get("tourism")):
        return str(row["tourism"])

    if pd.notna(row.get("historic")):
        return "historic_site"

    if pd.notna(row.get("amenity")):
        return str(row["amenity"])

    if pd.notna(row.get("leisure")):
        return str(row["leisure"])

    return "other"


clean["category"] = clean.apply(classify_place, axis=1)

# Preserve useful fields when available.
selected_columns = [
    "place_id",
    "element",
    "id",
    "name",
    "category",
    "tourism",
    "historic",
    "amenity",
    "leisure",
    "latitude",
    "longitude",
    "addr:street",
    "addr:city",
    "website",
    "contact:website",
    "opening_hours",
    "fee",
    "description",
    "wikidata",
    "wikipedia"
]

available_columns = [
    column for column in selected_columns
    if column in clean.columns
]

final_df = clean[available_columns].copy()

final_df["source"] = "OpenStreetMap"
final_df["source_license"] = "ODbL-1.0"

# Save processed pilot dataset.
output_csv = PROCESSED_DIR / "cairo_places_pilot.csv"
output_parquet = PROCESSED_DIR / "cairo_places_pilot.parquet"

final_df.to_csv(
    output_csv,
    index=False,
    encoding="utf-8-sig"
)

final_df.to_parquet(
    output_parquet,
    index=False
)

# ==========================================
# 7. COLLECTION REPORT
# ==========================================

report = {
    "source": "OpenStreetMap",
    "query": PLACE_QUERY,
    "raw_records": int(len(raw)),
    "named_places": int(len(final_df)),
    "categories": {
        str(key): int(value)
        for key, value in final_df["category"].value_counts().items()
    },
    "files": {
        "raw_geojson": str(raw_geojson),
        "raw_csv": str(raw_csv),
        "processed_csv": str(output_csv),
        "processed_parquet": str(output_parquet)
    }
}

report_path = RAW_DIR / "collection_report.json"

with open(report_path, "w", encoding="utf-8") as file:
    json.dump(report, file, indent=4, ensure_ascii=False)

print("\n" + "=" * 60)
print("COLLECTION COMPLETED")
print("=" * 60)

print(f"Raw OSM records: {len(raw):,}")
print(f"Named places: {len(final_df):,}")

print("\nCategory distribution:")
print(final_df["category"].value_counts().to_string())

print("\nSaved files:")
print(f"Raw GeoJSON: {raw_geojson}")
print(f"Raw CSV: {raw_csv}")
print(f"Processed CSV: {output_csv}")
print(f"Processed Parquet: {output_parquet}")
print(f"Report: {report_path}")

print("\nNext step: inspect data quality and coverage.")
