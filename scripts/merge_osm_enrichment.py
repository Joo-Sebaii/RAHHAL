from pathlib import Path
import pandas as pd
import json

BASE_DIR = Path(__file__).resolve().parent.parent

PLACES_FILE = (
    BASE_DIR / "data/processed/places/cairo_places_clean.parquet"
)

ENRICHMENT_FILE = (
    BASE_DIR / "data/raw/places/osm_enrichment.csv"
)

OUTPUT_DIR = BASE_DIR / "data/processed/places"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "cairo_places_osm_enriched.parquet"
CSV_FILE = OUTPUT_DIR / "cairo_places_osm_enriched.csv"
REPORT_FILE = BASE_DIR / "logs/osm_merge_report.json"

NEW_FIELDS = [
    "cuisine",
    "phone",
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
    "lit"
]


def main():

    print("=" * 65)
    print("RAHHAL - OSM ENRICHMENT MERGE")
    print("=" * 65)

    places = pd.read_parquet(PLACES_FILE)
    enrichment = pd.read_csv(ENRICHMENT_FILE)

    result = places.merge(
        enrichment[["place_id"] + NEW_FIELDS],
        on="place_id",
        how="left",
        validate="one_to_one"
    )

    coverage = {}

    for field in NEW_FIELDS:

        available = (
            result[field].notna()
            & result[field].astype(str).str.strip().ne("")
        )

        coverage[field] = {
            "available": int(available.sum()),
            "missing": int((~available).sum()),
            "coverage_pct": round(
                available.mean() * 100, 2
            )
        }

    result.to_parquet(OUTPUT_FILE, index=False)
    result.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

    report = {
        "total_places": len(result),
        "original_columns": len(places.columns),
        "new_columns": len(NEW_FIELDS),
        "final_columns": len(result.columns),
        "new_fields_coverage": coverage,
        "source": "OpenStreetMap",
        "license": "ODbL"
    }

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("\n[1] Merge summary")
    print("Places:", len(result))
    print("Original columns:", len(places.columns))
    print("Added columns:", len(NEW_FIELDS))
    print("Final columns:", len(result.columns))

    print("\n[2] New fields coverage")

    for field, stats in coverage.items():
        if stats["available"] > 0:
            print(
                f"{field}: {stats['available']} "
                f"({stats['coverage_pct']}%)"
            )

    print("\n[3] Output files")
    print(OUTPUT_FILE)
    print(CSV_FILE)
    print(REPORT_FILE)

    print("\nOSM merge completed successfully.")


if __name__ == "__main__":
    main()