from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "places"
    / "cairo_places_clean.parquet"
)

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "places"
    / "enrichment_pilot_25.csv"
)

CATEGORIES = [
    "restaurant",
    "cafe",
    "museum",
    "historic_site",
    "park"
]

SAMPLE_SIZE = 5
RANDOM_STATE = 42


def is_missing(value):
    return pd.isna(value) or str(value).strip() == ""


def main():

    df = pd.read_parquet(INPUT_FILE)

    print("=" * 65)
    print("RAHHAL - ENRICHMENT PILOT")
    print("=" * 65)

    pilot_parts = []

    for category in CATEGORIES:

        category_df = df[
            df["category"] == category
        ].copy()

        if len(category_df) < SAMPLE_SIZE:
            raise ValueError(
                f"Not enough places in category: {category}"
            )

        sample = category_df.sample(
            n=SAMPLE_SIZE,
            random_state=RANDOM_STATE
        )

        pilot_parts.append(sample)

    pilot = pd.concat(
        pilot_parts,
        ignore_index=True
    )

    # Keep original data fields for reference
    output = pd.DataFrame({

        "place_id": pilot["place_id"],
        "name": pilot["name"],
        "category": pilot["category"],
        "latitude": pilot["latitude"],
        "longitude": pilot["longitude"],

        "existing_opening_hours": pilot["opening_hours"],
        "existing_fee": pilot["fee"],
        "existing_description": pilot["description"],
        "existing_website": pilot["website"],

        "wikidata": pilot["wikidata"],
        "wikipedia": pilot["wikipedia"],

        "addr:street": pilot["addr:street"],
        "addr:city": pilot["addr:city"],

        "tourism": pilot["tourism"],
        "historic": pilot["historic"],
        "amenity": pilot["amenity"],
        "leisure": pilot["leisure"],

        "existing_contact_website": pilot["contact:website"],

    })
    output["has_wikidata_id"] = (
        output["wikidata"].notna()
        & output["wikidata"].astype(str).str.strip().ne("")
    )

    output["has_wikipedia_link"] = (
        output["wikipedia"].notna()
        & output["wikipedia"].astype(str).str.strip().ne("")
    )

    output["has_website"] = (
        output["existing_website"].notna()
        & output["existing_website"].astype(str).str.strip().ne("")
    ) | (
        output["existing_contact_website"].notna()
        & output["existing_contact_website"].astype(str).str.strip().ne("")
    )

    # Enrichment fields
    output["new_opening_hours"] = ""
    output["entrance_fee_status"] = ""
    output["entrance_fee_amount"] = ""
    output["currency"] = "EGP"
    output["average_cost_per_person"] = ""
    output["visit_duration_minutes"] = ""
    output["new_description"] = ""
    output["official_website"] = ""

    # Provenance fields
    output["source_name"] = ""
    output["source_url"] = ""
    output["source_access_date"] = ""
    output["verification_status"] = "NOT_STARTED"
    output["confidence"] = ""
    output["notes"] = ""

    # Initial status for entrance fee
    non_entrance_fee = [
        "restaurant",
        "cafe",
        "hotel"
    ]

    output.loc[
        output["category"].isin(non_entrance_fee),
        "entrance_fee_status"
    ] = "NOT_APPLICABLE"

    output.loc[
        ~output["category"].isin(non_entrance_fee),
        "entrance_fee_status"
    ] = "UNKNOWN"

    # Export
    output.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nSelected places:")

    print(
        output.groupby("category")
        .size()
        .to_string()
    )

    print("\nTotal places:", len(output))

    print("\nOutput:")
    print(OUTPUT_FILE)

    print("\nPilot created successfully.")


if __name__ == "__main__":
    main()