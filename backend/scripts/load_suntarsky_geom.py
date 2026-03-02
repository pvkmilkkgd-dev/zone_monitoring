"""Загрузить геометрию Сунтарского муниципального района (Якутия) из OSM (Nominatim)."""
import os
import json
import time
import requests
import sqlalchemy as sa
from sqlalchemy import text

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
except ImportError:
    pass
db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/zone_monitoring")
if db_url.startswith("postgresql+psycopg"):
    db_url = db_url.replace("postgresql+psycopg", "postgresql", 1)
engine = sa.create_engine(db_url)

REGION_NAME = "Республика Саха (Якутия)"
DISTRICT_NAME = "Сунтарский муниципальный район"
QUERIES = [
    "Сунтарский район Якутия Россия",
    "Suntarsky District Sakha Russia",
    "Suntarski ulus Yakutia",
]


def search_nominatim(q):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": q, "format": "json", "polygon_geojson": 1, "limit": 5}
    headers = {"User-Agent": "ZoneMonitoring/1.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=30)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def main():
    print(f"Загрузка геометрии: {DISTRICT_NAME} ({REGION_NAME})")
    print("=" * 60)

    with engine.begin() as conn:
        geojson = None
        for q in QUERIES:
            time.sleep(1.1)
            results = search_nominatim(q)
            if not results:
                continue
            for item in results:
                display = item.get("display_name", "")
                if "Якутия" not in display and "Sakha" not in display and "Yakutia" not in display and "Саха" not in display:
                    continue
                g = item.get("geojson")
                if g and g.get("type") in ("Polygon", "MultiPolygon"):
                    geojson = g
                    break
            if geojson:
                break

        if not geojson:
            print("  Геометрия не найдена в Nominatim.")
            return

        conn.execute(
            text("""
                UPDATE districts d
                SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)))
                FROM regions r
                WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
            """),
            {"geojson": json.dumps(geojson), "region": REGION_NAME, "name": DISTRICT_NAME},
        )
        row = conn.execute(
            text("""
                SELECT ROUND(ST_Area(d.geom::geography)/1000000), ST_NPoints(d.geom)
                FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = :name
            """),
            {"region": REGION_NAME, "name": DISTRICT_NAME},
        ).fetchone()
        print(f"  OK {DISTRICT_NAME}: ~{int(row[0])} км², {row[1]} точек")

    print("\nГотово.")


if __name__ == "__main__":
    main()
