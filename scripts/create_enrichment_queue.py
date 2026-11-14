from pathlib import Path
import pandas as pd
import json

# ==========================================
# RAHHAL - PLACE ENRICHMENT QUEUE
# ==========================================

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

LOG_DIR = BASE_DIR / "logs"

OUTPUT_FILE = OUTPUT_DIR / "places_enrichment_queue.csv"
REPORT_FILE = LOG_DIR / "enrichment_queue_report.json"


def is_missing(series):
    return (
        series.isna()
        | series.astype("string").str.strip().eq("")
    ).fillna(True)


def main():

    print("=" * 65)
    print("RAHHAL - PLACE ENRICHMENT QUEUE")
    print("=" * 65)

    # 1. Load clean places
    df = pd.read_parquet(INPUT_FILE)

    print(f"\nLoaded places: {len(df):,}")

    # 2. Identify missing fields
    df["missing_opening_hours"] = is_missing(
        df["opening_hours"]
    )

    df["missing_fee"] = is_missing(
        df["fee"]
    )

    df["missing_description"] = is_missing(
        df["description"]
    )

    # Consider contact:website as an alternative
    website_missing = is_missing(df["website"])
    contact_website_missing = is_missing(
        df["contact:website"]
    )

    df["missing_website"] = (
        website_missing & contact_website_missing
    )

    # 3. Create enrichment queue
    queue_columns = [
        "place_id",
        "name",
        "category",
        "latitude",
        "longitude",
        "addr:street",
        "addr:city",
        "wikidata",
        "website",
        "contact:website",
        "missing_opening_hours",
        "missing_fee",
        "missing_description",
        "missing_website"
    ]

    queue = df[queue_columns].copy()

    # 4. Count missing fields
    missing_flags = [
        "missing_opening_hours",
        "missing_fee",
        "missing_description",
        "missing_website"
    ]

    queue["missing_fields_count"] = (
        queue[missing_flags].sum(axis=1)
    )

    # 5. Define enrichment priority
    def get_priority(row):

        if (
            row["missing_opening_hours"]
            or row["missing_fee"]
        ):
            return "HIGH"

        if row["missing_description"]:
            return "MEDIUM"

        if row["missing_website"]:
            return "LOW"

        return "COMPLETE"

    queue["priority"] = queue.apply(
        get_priority,
        axis=1
    )

    # 6. Suggest potential sources
    def suggest_sources(row):

        sources = [
            "OpenStreetMap",
            "Official Website"
        ]

        if pd.notna(row["wikidata"]):
            sources.append("Wikidata")

        sources.append("OpenTripMap")

        return " | ".join(sources)

    queue["suggested_sources"] = queue.apply(
        suggest_sources,
        axis=1
    )

    # 7. Keep only places needing enrichment
    queue = queue[
        queue["missing_fields_count"] > 0
    ].copy()

    # Sort by priority and number of missing fields
    priority_order = {
        "HIGH": 1,
        "MEDIUM": 2,
        "LOW": 3,
        "COMPLETE": 4
    }

    queue["priority_order"] = (
        queue["priority"].map(priority_order)
    )

    queue = queue.sort_values(
        ["priority_order", "missing_fields_count"],
        ascending=[True, False]
    )

    queue = queue.drop(
        columns=["priority_order"]
    )

    # 8. Save CSV
    queue.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    # 9. Generate report
    total_places = len(df)

    report = {
        "total_places": total_places,
        "places_needing_enrichment": len(queue),
        "places_with_all_target_fields": (
            total_places - len(queue)
        ),
        "missing_fields": {
            "opening_hours": int(
                df["missing_opening_hours"].sum()
            ),
            "fee": int(
                df["missing_fee"].sum()
            ),
            "description": int(
                df["missing_description"].sum()
            ),
            "website": int(
                df["missing_website"].sum()
            )
        },
        "priority_distribution": {
            str(k): int(v)
            for k, v in queue["priority"].value_counts().items()
        },
        "output_file": str(OUTPUT_FILE)
    }

    with open(
        REPORT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=4
        )

    # 10. Display summary
    print("\n[1] Missing fields")

    for field, count in report["missing_fields"].items():

        percentage = count / total_places * 100

        print(
            f"{field}: {count:,} "
            f"({percentage:.2f}%)"
        )

    print("\n[2] Enrichment queue")

    print(
        "Places requiring enrichment:",
        len(queue)
    )

    print("\n[3] Priority distribution")

    print(
        queue["priority"].value_counts().to_string()
    )

    print("\n[4] Sample records")

    print(
        queue[
            [
                "name",
                "category",
                "missing_opening_hours",
                "missing_fee",
                "missing_description",
                "missing_website",
                "priority"
            ]
        ].head(15).to_string(index=False)
    )

    print("\n" + "=" * 65)
    print("ENRICHMENT QUEUE CREATED")
    print("=" * 65)

    print(f"\nCSV: {OUTPUT_FILE}")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()