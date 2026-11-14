from pathlib import Path
import json
import pandas as pd

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "places"
    / "cairo_places_pilot.parquet"
)

REPORT_DIR = BASE_DIR / "logs"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_FILE = REPORT_DIR / "places_quality_report.json"


def main():

    print("=" * 60)
    print("RAHHAL - PLACES DATA QUALITY INSPECTION")
    print("=" * 60)

    # 1. Load dataset
    print("\n[1] Loading dataset...")

    df = pd.read_parquet(INPUT_FILE)

    print(f"Loaded successfully: {len(df):,} records")

    # 2. Columns and data types
    print("\n[2] Dataset structure")

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nData types:")
    print(df.dtypes.astype(str).to_dict())

    # 3. Missing values
    print("\n[3] Missing values")

    missing = df.isnull().sum()

    missing_report = {}

    for column, count in missing.items():

        percentage = (
            count / len(df) * 100
            if len(df) > 0 else 0
        )

        missing_report[column] = {
            "count": int(count),
            "percentage": round(percentage, 2)
        }

        print(
            f"{column}: "
            f"{count} missing "
            f"({percentage:.2f}%)"
        )

    # 4. Duplicate IDs
    print("\n[4] Duplicate place IDs")

    if "place_id" in df.columns:

        duplicate_ids = int(
            df["place_id"].duplicated().sum()
        )

    else:
        duplicate_ids = None

    print("Duplicate IDs:", duplicate_ids)

    # 5. Duplicate names
    print("\n[5] Duplicate place names")

    if "name" in df.columns:

        normalized_names = (
            df["name"]
            .astype("string")
            .str.strip()
            .str.lower()
        )

        duplicate_names = int(
            normalized_names.duplicated().sum()
        )

    else:
        duplicate_names = None

    print("Duplicate names:", duplicate_names)

    # 6. Coordinate validation
    print("\n[6] Coordinate validation")

    coordinate_report = {}

    if {"latitude", "longitude"}.issubset(df.columns):

        valid_coordinates = (
            df["latitude"].between(29.5, 30.5)
            & df["longitude"].between(31.0, 32.0)
        )

        invalid_coordinates = int(
            (~valid_coordinates).sum()
        )

        coordinate_report = {
            "valid": int(valid_coordinates.sum()),
            "outside_expected_cairo_range": invalid_coordinates
        }

        print("Valid coordinates:", coordinate_report["valid"])
        print(
            "Outside broad Cairo range:",
            invalid_coordinates
        )

    else:

        print("Latitude/longitude columns not found.")

    # 7. Category distribution
    print("\n[7] Category distribution")

    if "category" in df.columns:

        categories = (
            df["category"]
            .value_counts(dropna=False)
            .to_dict()
        )

        categories = {
            str(key): int(value)
            for key, value in categories.items()
        }

        print(pd.Series(categories))

    else:
        categories = {}

    # 8. Sample records
    print("\n[8] Sample places")

    sample_columns = [
        column
        for column in [
            "place_id",
            "name",
            "category",
            "latitude",
            "longitude"
        ]
        if column in df.columns
    ]

    print(
        df[sample_columns]
        .head(15)
        .to_string(index=False)
    )

    # 9. Final report
    report = {

        "total_records": int(len(df)),

        "columns": df.columns.tolist(),

        "data_types": df.dtypes.astype(str).to_dict(),

        "missing_values": missing_report,

        "duplicate_place_ids": duplicate_ids,

        "duplicate_names": duplicate_names,

        "coordinates": coordinate_report,

        "category_distribution": categories,

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
            indent=4,
            default=str
        )

    print("\n" + "=" * 60)
    print("INSPECTION COMPLETED")
    print("=" * 60)

    print(f"\nReport saved to:\n{REPORT_FILE}")


if __name__ == "__main__":
    main()