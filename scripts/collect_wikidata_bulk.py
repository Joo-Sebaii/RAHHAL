from pathlib import Path
import pandas as pd
import requests
import json
import re
import time
from datetime import datetime, timezone
from math import radians, sin, cos, sqrt, atan2

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data/processed/places/cairo_places_clean.parquet"

OUTPUT_DIR = BASE_DIR / "data/raw/places"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "wikidata_bulk_enrichment.csv"
OUTPUT_JSONL = OUTPUT_DIR / "wikidata_bulk_raw.jsonl"
MISSING_CSV = OUTPUT_DIR / "places_without_wikidata.csv"

API_URL = "https://www.wikidata.org/w/api.php"

BATCH_SIZE = 50
DELAY_SECONDS = 0.5

session = requests.Session()
session.headers.update({
    "User-Agent": "RAHHAL-Academic-Research/1.0"
})


def distance_km(lat1, lon1, lat2, lon2):
    radius = 6371

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    return 2 * radius * atan2(
        sqrt(a),
        sqrt(1 - a)
    )


def get_claims(claims, property_id):

    values = []

    for item in claims.get(property_id, []):

        try:
            value = item["mainsnak"]["datavalue"]["value"]
            values.append(value)

        except (KeyError, TypeError):
            continue

    return values


def get_entity_coordinates(claims):

    coordinates = get_claims(claims, "P625")

    if not coordinates:
        return None, None

    value = coordinates[0]

    return value.get("latitude"), value.get("longitude")


def collect_batch(ids):

    params = {
        "action": "wbgetentities",
        "ids": "|".join(ids),
        "props": "labels|descriptions|claims|sitelinks",
        "languages": "ar|en",
        "format": "json",
        "maxlag": 5
    }

    response = session.get(
        API_URL,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    return response.json()


def main():

    print("=" * 70)
    print("RAHHAL - BULK WIKIDATA COLLECTION")
    print("=" * 70)

    df = pd.read_parquet(INPUT_FILE)

    df["wikidata"] = df["wikidata"].astype("string").str.strip()

    valid_ids = df[
        df["wikidata"].str.fullmatch(r"Q\d+", na=False)
    ].copy()

    missing = df[
        ~df["wikidata"].str.fullmatch(r"Q\d+", na=False)
    ].copy()

    missing.to_csv(
        MISSING_CSV,
        index=False,
        encoding="utf-8-sig"
    )

    # Keep one place per Wikidata ID for API collection.
    linked = valid_ids.drop_duplicates(
        subset=["wikidata"]
    )

    ids = linked["wikidata"].tolist()

    print("Total places:", len(df))
    print("Places with Wikidata IDs:", len(valid_ids))
    print("Unique Wikidata entities:", len(ids))
    print("Places without Wikidata IDs:", len(missing))

    if not ids:
        print("\nNo Wikidata entities found.")
        return

    place_lookup = {}

    for _, row in valid_ids.iterrows():
        place_lookup.setdefault(
            row["wikidata"], []
        ).append(row)

    records = []
    raw_count = 0
    failed_batches = []

    # Fresh output files for this run.
    OUTPUT_JSONL.write_text("", encoding="utf-8")

    batches = [
        ids[i:i + BATCH_SIZE]
        for i in range(0, len(ids), BATCH_SIZE)
    ]

    print("\nBatches to process:", len(batches))

    for batch_number, batch in enumerate(batches, start=1):

        print(
            f"\nProcessing batch {batch_number}/{len(batches)} "
            f"({len(batch)} entities)"
        )

        try:
            payload = collect_batch(batch)

            with OUTPUT_JSONL.open(
                "a",
                encoding="utf-8"
            ) as file:

                file.write(
                    json.dumps(
                        payload,
                        ensure_ascii=False
                    ) + "\n"
                )

            entities = payload.get("entities", {})

            for qid in batch:

                entity = entities.get(qid, {})

                if "missing" in entity:
                    continue

                labels = entity.get("labels", {})
                descriptions = entity.get("descriptions", {})
                claims = entity.get("claims", {})
                sitelinks = entity.get("sitelinks", {})

                lat, lon = get_entity_coordinates(claims)

                websites = get_claims(claims, "P856")

                for place in place_lookup.get(qid, []):

                    distance = None

                    if lat is not None and lon is not None:

                        distance = distance_km(
                            float(place["latitude"]),
                            float(place["longitude"]),
                            lat,
                            lon
                        )

                    records.append({

                        "place_id": place["place_id"],
                        "place_name": place["name"],
                        "category": place["category"],

                        "wikidata_id": qid,

                        "wikidata_label_ar": (
                            labels.get("ar", {}).get("value")
                        ),

                        "wikidata_label_en": (
                            labels.get("en", {}).get("value")
                        ),

                        "description_ar": (
                            descriptions.get("ar", {}).get("value")
                        ),

                        "description_en": (
                            descriptions.get("en", {}).get("value")
                        ),

                        "wikidata_latitude": lat,
                        "wikidata_longitude": lon,

                        "coordinate_distance_km": (
                            round(distance, 3)
                            if distance is not None else None
                        ),

                        "wikidata_websites": json.dumps(
                            websites,
                            ensure_ascii=False
                        ),

                        "ar_wikipedia": (
                            sitelinks.get("arwiki", {}).get("title")
                        ),

                        "en_wikipedia": (
                            sitelinks.get("enwiki", {}).get("title")
                        ),

                        "source": "Wikidata",
                        "source_license": "CC0",

                        "collected_at": datetime.now(
                            timezone.utc
                        ).isoformat(),

                        "verification_status": "REVIEW_REQUIRED"

                    })

            raw_count += len(entities)

        except requests.RequestException as error:

            failed_batches.append({
                "batch": batch_number,
                "ids": batch,
                "error": str(error)
            })

            print("Batch failed:", error)

        time.sleep(DELAY_SECONDS)

    result = pd.DataFrame(records)

    if not result.empty:

        result.to_csv(
            OUTPUT_CSV,
            index=False,
            encoding="utf-8-sig"
        )

    report = {
        "total_places": len(df),
        "places_with_wikidata_ids": len(valid_ids),
        "unique_entities_requested": len(ids),
        "entities_returned": raw_count,
        "enrichment_records": len(result),
        "failed_batches": failed_batches,
        "collected_at": datetime.now(
            timezone.utc
        ).isoformat()
    }

    report_file = OUTPUT_DIR / "wikidata_bulk_report.json"

    report_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("\n" + "=" * 70)
    print("BULK COLLECTION COMPLETED")
    print("=" * 70)

    print("Places:", len(df))
    print("Linked places:", len(valid_ids))
    print("Unique entities:", len(ids))
    print("Enrichment records:", len(result))
    print("Failed batches:", len(failed_batches))

    print("\nOutput files:")
    print(OUTPUT_CSV)
    print(OUTPUT_JSONL)
    print(MISSING_CSV)
    print(report_file)


if __name__ == "__main__":
    main()