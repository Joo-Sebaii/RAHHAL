from pathlib import Path
import requests
import pandas as pd
import json
from datetime import datetime, timezone
from math import radians, sin, cos, sqrt, atan2

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR / "data" / "processed" /
    "places" / "enrichment_pilot_25.csv"
)

OUTPUT_DIR = (
    BASE_DIR / "data" / "raw" / "places"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_OUTPUT = OUTPUT_DIR / "wikidata_enrichment_pilot.csv"
JSON_OUTPUT = OUTPUT_DIR / "wikidata_raw_response.json"

API_URL = "https://www.wikidata.org/w/api.php"

HEADERS = {
    "User-Agent": "RAHHAL-Academic-Project/1.0 (educational research)"
}


def get_claim_value(claim, property_type=None):

    values = []

    for item in claim or []:
        try:
            value = item["mainsnak"]["datavalue"]["value"]

            if property_type == "coordinate":
                values.append({
                    "latitude": value["latitude"],
                    "longitude": value["longitude"]
                })

            elif property_type == "url":
                values.append(value)

            else:
                values.append(value)

        except (KeyError, TypeError):
            continue

    return values


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


def main():

    df = pd.read_csv(INPUT_FILE)

    linked = df[
        df["wikidata"].notna()
        & df["wikidata"].astype(str).str.strip().ne("")
    ].copy()

    if linked.empty:
        print("No Wikidata IDs found.")
        return

    ids = linked["wikidata"].unique().tolist()

    params = {
        "action": "wbgetentities",
        "ids": "|".join(ids),
        "props": "labels|descriptions|claims|sitelinks",
        "languages": "ar|en",
        "format": "json",
        "maxlag": 5
    }

    print("=" * 65)
    print("RAHHAL - WIKIDATA ENRICHMENT")
    print("=" * 65)

    print("Requesting entities:", len(ids))

    response = requests.get(
        API_URL,
        params=params,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    payload = response.json()

    JSON_OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    results = []

    for _, place in linked.iterrows():

        qid = place["wikidata"]
        entity = payload.get("entities", {}).get(qid, {})

        if "missing" in entity:
            print(f"Entity not found: {qid}")
            continue

        labels = entity.get("labels", {})
        descriptions = entity.get("descriptions", {})
        claims = entity.get("claims", {})
        sitelinks = entity.get("sitelinks", {})

        coordinates = get_claim_value(
            claims.get("P625"),
            "coordinate"
        )

        websites = get_claim_value(
            claims.get("P856"),
            "url"
        )

        latitude = None
        longitude = None
        distance = None

        if coordinates:

            latitude = coordinates[0]["latitude"]
            longitude = coordinates[0]["longitude"]

            distance = distance_km(
                float(place["latitude"]),
                float(place["longitude"]),
                latitude,
                longitude
            )

        results.append({

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

            "wikidata_latitude": latitude,
            "wikidata_longitude": longitude,
            "coordinate_distance_km": (
                round(distance, 3)
                if distance is not None else None
            ),

            "official_websites": json.dumps(
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
            "source_url": (
                f"https://www.wikidata.org/wiki/{qid}"
            ),
            "license": "CC0",

            "collected_at": datetime.now(
                timezone.utc
            ).isoformat(),

            "verification_status": "REVIEW_REQUIRED"

        })

    output = pd.DataFrame(results)

    output.to_csv(
        CSV_OUTPUT,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nCollection completed.")
    print("Entities collected:", len(output))

    print("\nResults:")

    if not output.empty:
        print(
            output[
                [
                    "place_name",
                    "wikidata_label_ar",
                    "wikidata_label_en",
                    "coordinate_distance_km"
                ]
            ].to_string(index=False)
        )

    print("\nCSV:", CSV_OUTPUT)
    print("Raw JSON:", JSON_OUTPUT)


if __name__ == "__main__":
    main()