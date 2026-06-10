"""
ETL Script: Import Foody CSV → PostgreSQL locations table.
Run once after DB is up:  python scripts/import_foody_csv.py
"""
import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

POSTGRES_URL = os.getenv(
    "POSTGRES_URL",
    "postgresql://weatherise:weatherise@localhost:5432/weatherise"
)
CSV_PATH = os.path.join(os.path.dirname(__file__), "../data/raw/foody_danang_restaurants_20260610_110653.csv")


def classify_indoor(categories: str, name: str) -> bool:
    """Heuristic indoor/outdoor classification."""
    outdoor_keywords = ["vỉa hè", "ngoài trời", "xe đẩy", "food truck", "lề đường"]
    combined = (categories or "").lower() + " " + (name or "").lower()
    return not any(kw in combined for kw in outdoor_keywords)


def classify_price_tier(price_min, price_max) -> str:
    try:
        avg = (float(price_min or 0) + float(price_max or 0)) / 2
        if avg < 80000:
            return "budget"
        elif avg < 250000:
            return "medium"
        else:
            return "premium"
    except Exception:
        return "medium"


def map_vibe_tags(categories: str, cuisines: str) -> list:
    tags = []
    combined = (categories or "").lower() + " " + (cuisines or "").lower()
    if "hải sản" in combined or "seafood" in combined:
        tags.append("seafood")
    if "vỉa hè" in combined or "ăn vặt" in combined:
        tags.append("street_food")
    if "café" in combined or "cafe" in combined or "dessert" in combined:
        tags.append("cafe")
    if "nhà hàng" in combined:
        tags.append("restaurant")
    if "quán ăn" in combined:
        tags.append("local_food")
    if "miền trung" in combined or "quảng" in combined:
        tags.append("central_vietnamese")
    return tags or ["restaurant"]


def main():
    print(f"[ETL] Reading CSV: {CSV_PATH}")
    try:
        df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(CSV_PATH, encoding="utf-8")

    print(f"[ETL] Loaded {len(df)} rows. Columns: {list(df.columns)}")

    # Filter rows with valid coordinates
    df = df.dropna(subset=["Latitude", "Longitude"])
    df = df[df["Latitude"].between(15.8, 16.4)]  # Da Nang bounding box
    df = df[df["Longitude"].between(107.8, 108.5)]
    print(f"[ETL] After geo filter: {len(df)} rows")

    conn = psycopg2.connect(POSTGRES_URL)
    cur = conn.cursor()

    rows = []
    for _, row in df.iterrows():
        try:
            rid = f"foody_{str(row.get('Id', '')).strip()}"
            name_vi = str(row.get("Name", "")).strip()
            if not name_vi or not rid:
                continue

            is_indoor = classify_indoor(
                str(row.get("Categories", "")),
                name_vi
            )
            price_tier = classify_price_tier(
                row.get("PriceMin"), row.get("PriceMax")
            )
            vibe_tags = map_vibe_tags(
                str(row.get("Categories", "")),
                str(row.get("Cuisines", ""))
            )
            bad_weather_rules = {}
            if not is_indoor:
                bad_weather_rules = {
                    "max_precipitation_mm": 1.5,
                    "max_rain_prob_pct": 60
                }

            rows.append((
                rid,                                    # id
                "foody_csv",                            # source
                name_vi,                                # name_vi
                None,                                   # name_en
                "restaurant",                           # category
                str(row.get("Categories", ""))[:80],   # sub_category
                str(row.get("Address", "")),            # address
                str(row.get("District", "")),           # district
                "Da Nang",                              # city
                "Vietnam",                              # country
                float(row["Latitude"]),                 # latitude
                float(row["Longitude"]),                # longitude
                min(float(row.get("AvgRating") or 0), 9.99),  # avg_rating
                int(row.get("TotalReviews") or 0),     # total_reviews
                price_tier,                             # price_tier
                60,                                     # avg_duration_minutes
                is_indoor,                              # is_indoor
                not is_indoor,                          # rain_sensitive
                False,                                  # uv_sensitive
                psycopg2.extras.Json(bad_weather_rules), # bad_weather_rules
                vibe_tags,                              # vibe_tags
                bool(row.get("IsOpening", True)),       # is_opening
                bool(row.get("HasDelivery", False)),    # has_delivery
                bool(row.get("HasBooking", False)),     # has_booking
                str(row.get("PhotoUrl", "") or ""),    # photo_url
                str(row.get("FoodyUrl", "") or ""),    # foody_url
                str(row.get("Phone", "") or "")[:30],       # phone
            ))
        except Exception as e:
            print(f"[ETL] Skip row {row.get('Id')}: {e}")
            continue

    print(f"[ETL] Inserting {len(rows)} records...")

    sql = """
        INSERT INTO locations (
            id, source, name_vi, name_en, category, sub_category,
            address, district, city, country,
            latitude, longitude,
            avg_rating, total_reviews, price_tier, avg_duration_minutes,
            is_indoor, rain_sensitive, uv_sensitive, bad_weather_rules,
            vibe_tags, is_opening, has_delivery, has_booking,
            photo_url, foody_url, phone
        ) VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            avg_rating = EXCLUDED.avg_rating,
            total_reviews = EXCLUDED.total_reviews,
            updated_at = NOW()
    """

    execute_values(cur, sql, rows, page_size=200)
    conn.commit()
    cur.close()
    conn.close()
    print(f"[ETL] ✅ Imported {len(rows)} Foody restaurants into PostgreSQL.")


if __name__ == "__main__":
    main()
