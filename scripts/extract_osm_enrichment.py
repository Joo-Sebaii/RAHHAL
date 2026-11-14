from pathlib import Path
import json
import pandas as pd
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_FILE = BASE_DIR / "data/raw/places/cairo_places_raw.geojson"

PLACES_FILE = (
    BASE_DIR / "data/processed/places/cairo_places_clean.parquet"
)

OUTPUT_DIR = BASE_DIR / "data/raw/places"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "osm_enrichment.csv"
REPORT_FILE = OUTPUT_DIR / "osm_enrichment_report.json"

TAGS = [
    "cuisine",
    "opening_hours",
    "fee",
    "description",
    "website",
    "contact:website",
    "phone",
    "contact:phone",
    "wheelchair",
    "outdoor_seating",
    "takeaway",
    "delivery",
    "internet_access",
    "capacity",
    "reservation",
    "operator",
    "brand",
    "payment:cash",
    "payment:cards",
    "diet:vegetarian",
    "diet:vegan",
    "toilets",
    "access",
    "lit",
    "addr:street",
    "addr:city",
    "wikidata",
    "wikipedia"
]


def main():

    print("=" * 65)
    print("RAHHAL - OSM LOCAL ENRICHMENT")
    print("=" * 65)

    places = pd.read_parquet(PLACES_FILE)

    with open(RAW_FILE, "r", encoding="utf-8") as file:
        geojson = json.load(file)

    print("Clean places:", len(places))
    print("Raw OSM features:", len(geojson["features"]))

    raw_lookup = {}

    for feature in geojson["features"]:

        properties = feature.get("properties", {})

        element = properties.get("element")
        osm_id = properties.get("id")

        if element is None or osm_id is None:
            continue

        place_id = f"osm:{element}:{osm_id}"

        raw_lookup[place_id] = properties

    records = []

    for _, place in places.iterrows():

        place_id = place["place_id"]

        properties = raw_lookup.get(place_id, {})

        record = {
            "place_id": place_id,
            "name": place["name"],
            "category": place["category"]
        }

        for tag in TAGS:
            record[tag] = properties.get(tag)

        record["source"] = "OpenStreetMap"
        record["source_license"] = "ODbL"
        record["collected_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        records.append(record)

    result = pd.DataFrame(records)

    result.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    coverage = {}

    for tag in TAGS:

        available = (
            result[tag].notna()
            & result[tag].astype(str).str.strip().ne("")
        )

        coverage[tag] = {
            "available": int(available.sum()),
            "missing": int((~available).sum()),
            "coverage_pct": round(
                available.mean() * 100, 2
            )
        }

    report = {
        "total_places": len(result),
        "matched_places": int(
            result[TAGS].notna().any(axis=1).sum()
        ),
        "tags": coverage,
        "source": "OpenStreetMap",
        "license": "ODbL"
    }

    REPORT_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("\n[1] Enrichment coverage")

    for tag, stats in coverage.items():

        if stats["available"] > 0:

            print(
                f"{tag}: {stats['available']} "
                f"({stats['coverage_pct']}%)"
            )

    print("\n[2] Results")

    print("Total places:", len(result))
    print(
        "Places with additional OSM tags:",
        report["matched_places"]
    )

    print("\nCSV:", OUTPUT_FILE)
    print("Report:", REPORT_FILE)

    print("\nOSM enrichment completed.")


if __name__ == "__main__":
    main()