from pathlib import Path
import pandas as pd
import json

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "raw"
    / "places"
    / "wikidata_enrichment_pilot.csv"
)

df = pd.read_csv(INPUT_FILE)

print("=" * 70)
print("RAHHAL - WIKIDATA RESULTS INSPECTION")
print("=" * 70)

for _, row in df.iterrows():

    print("\n" + "-" * 70)

    print("Original place:", row["place_name"])
    print("Wikidata ID:", row["wikidata_id"])

    print("\n[1] Names")

    print("Arabic:", row["wikidata_label_ar"])
    print("English:", row["wikidata_label_en"])

    print("\n[2] Descriptions")

    print("Arabic:", row["description_ar"])
    print("English:", row["description_en"])

    print("\n[3] Coordinates")

    print("Latitude:", row["wikidata_latitude"])
    print("Longitude:", row["wikidata_longitude"])

    print("Distance (km):", row["coordinate_distance_km"])

    print("\n[4] Official Websites")

    websites = row["official_websites"]

    try:
        websites = json.loads(websites)
    except (ValueError, TypeError):
        websites = []

    print(websites)

    print("\n[5] Wikipedia")

    print("Arabic:", row["ar_wikipedia"])
    print("English:", row["en_wikipedia"])

    print("\nVerification:", row["verification_status"])

print("\n" + "=" * 70)
print("INSPECTION COMPLETED")
print("=" * 70)