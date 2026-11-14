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

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "places"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "enrichment_category_audit.csv"
)


def missing(series):

    return (
        series.isna()
        | series.astype("string").str.strip().eq("")
    ).fillna(True)


def main():

    df = pd.read_parquet(INPUT_FILE)

    # Identify missing values
    fields = [
        "opening_hours",
        "fee",
        "description",
        "website"
    ]

    for field in fields:
        df[f"missing_{field}"] = missing(df[field])

    # Fee applicability
    non_entrance_fee_categories = [
        "restaurant",
        "cafe",
        "hotel"
    ]

    df["entrance_fee_applicable"] = (
        ~df["category"].isin(non_entrance_fee_categories)
    )

    # Category-level report
    report = df.groupby("category").agg(

        total_places=("place_id", "count"),

        missing_opening_hours=(
            "missing_opening_hours",
            "sum"
        ),

        missing_fee=("missing_fee", "sum"),

        missing_description=(
            "missing_description",
            "sum"
        ),

        missing_website=("missing_website", "sum"),

        entrance_fee_applicable=(
            "entrance_fee_applicable",
            "sum"
        )

    ).reset_index()

    # Calculate percentages
    for field in fields:

        column = f"missing_{field}"

        report[f"{field}_missing_pct"] = (
            report[column]
            / report["total_places"]
            * 100
        ).round(2)

    report.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    print("=" * 65)
    print("RAHHAL - CATEGORY ENRICHMENT AUDIT")
    print("=" * 65)

    print(report.to_string(index=False))

    print("\nReport saved:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()