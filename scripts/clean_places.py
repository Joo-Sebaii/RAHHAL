from pathlib import Path
import pandas as pd
import json

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "places"
    / "cairo_places_pilot.parquet"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "places"
)

OUTPUT_FILE = OUTPUT_DIR / "cairo_places_clean.parquet"
OUTPUT_CSV = OUTPUT_DIR / "cairo_places_clean.csv"

REPORT_DIR = BASE_DIR / "logs"
REPORT_FILE = REPORT_DIR / "places_cleaning_report.json"


def main():

    print("=" * 60)
    print("RAHHAL - PLACES DATA CLEANING")
    print("=" * 60)

    df = pd.read_parquet(INPUT_FILE)

    original_count = len(df)

    print(f"\nOriginal records: {original_count}")

    # 1. Remove exact duplicate Place IDs
    duplicate_id_count = int(
        df["place_id"].duplicated().sum()
    )

    df = df.drop_duplicates(
        subset=["place_id"],
        keep="first"
    ).copy()

    print(f"Duplicate IDs removed: {duplicate_id_count}")

    # 2. Normalize text fields without changing original meaning
    text_columns = [
        "name",
        "category",
        "tourism",
        "historic",
        "amenity",
        "leisure",
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

    for column in text_columns:

        if column in df.columns:

            df[column] = (
                df[column]
                .astype("string")
                .str.strip()
            )

            df[column] = df[column].replace(
                "",
                pd.NA
            )

    # 3. Validate essential fields
    invalid_records = df[
        df["name"].isna()
        | df["latitude"].isna()
        | df["longitude"].isna()
        | df["category"].isna()
    ]

    print(
        "Records missing essential fields:",
        len(invalid_records)
    )

    # 4. Preserve duplicate names
    duplicate_names = int(
        df["name"]
        .str.lower()
        .duplicated()
        .sum()
    )

    # 5. Save clean dataset
    df.to_parquet(
        OUTPUT_FILE,
        index=False
    )

    df.to_csv(
        OUTPUT_CSV,
        index=False,
        encoding="utf-8-sig"
    )

    # 6. Cleaning report
    report = {
        "original_records": original_count,
        "final_records": len(df),
        "duplicate_ids_removed": duplicate_id_count,
        "duplicate_names_preserved": duplicate_names,
        "invalid_essential_records": len(invalid_records),
        "removed_records": original_count - len(df),
        "output_file": str(OUTPUT_FILE)
    }

    with open(
        REPORT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=4
        )

    print("\n" + "=" * 60)
    print("CLEANING COMPLETED")
    print("=" * 60)

    print(f"Final records: {len(df)}")
    print(f"Parquet: {OUTPUT_FILE}")
    print(f"CSV: {OUTPUT_CSV}")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()