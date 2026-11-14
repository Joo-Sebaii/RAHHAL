from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "places"
    / "enrichment_pilot_25.csv"
)

df = pd.read_csv(INPUT_FILE)

def available(column):
    if column not in df.columns:
        return pd.Series(False, index=df.index)

    return (
        df[column].notna()
        & df[column].astype(str).str.strip().ne("")
    )

has_wikidata = available("wikidata")
has_wikipedia = available("wikipedia")

has_website = (
    available("existing_website")
    | available("existing_contact_website")
)

print("=" * 65)
print("RAHHAL - ENRICHMENT PILOT INSPECTION")
print("=" * 65)

print("\n[1] Source availability")

print(f"Wikidata IDs: {has_wikidata.sum()} / {len(df)}")
print(f"Wikipedia links: {has_wikipedia.sum()} / {len(df)}")
print(f"Websites: {has_website.sum()} / {len(df)}")

print("\n[2] Places by category")

print(df.groupby("category").size().to_string())

print("\n[3] Selected places")

print(
    df[["name", "category", "wikidata", "wikipedia"]]
    .to_string(index=False)
)

print("\n[4] Missing source identifiers")

print("Missing Wikidata:", (~has_wikidata).sum())
print("Missing Wikipedia:", (~has_wikipedia).sum())
print("Missing Website:", (~has_website).sum())