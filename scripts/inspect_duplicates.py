from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "places"
    / "cairo_places_pilot.parquet"
)


def main():

    df = pd.read_parquet(INPUT_FILE)

    print("=" * 70)
    print("RAHHAL - DUPLICATE INVESTIGATION")
    print("=" * 70)

    # 1. Duplicate Place IDs

    print("\n[1] DUPLICATE PLACE IDs")

    duplicate_ids = df[
        df.duplicated("place_id", keep=False)
    ].sort_values("place_id")

    if duplicate_ids.empty:
        print("No duplicate IDs found.")

    else:
        columns = [
            "place_id",
            "element",
            "id",
            "name",
            "category",
            "latitude",
            "longitude"
        ]

        print(
            duplicate_ids[columns].to_string(index=False)
        )

    # 2. Duplicate Names

    print("\n[2] DUPLICATE PLACE NAMES")

    normalized_names = (
        df["name"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    duplicate_names = df[
        normalized_names.duplicated(keep=False)
    ].copy()

    duplicate_names["normalized_name"] = (
        normalized_names[
            duplicate_names.index
        ]
    )

    duplicate_names = duplicate_names.sort_values(
        "normalized_name"
    )

    columns = [
        "name",
        "place_id",
        "category",
        "latitude",
        "longitude"
    ]

    print(
        duplicate_names[columns]
        .head(100)
        .to_string(index=False)
    )

    print("\nTotal duplicate ID records:",
          len(duplicate_ids))

    print("Total duplicate name records:",
          len(duplicate_names))

    print("\nInvestigation completed.")


if __name__ == "__main__":
    main()