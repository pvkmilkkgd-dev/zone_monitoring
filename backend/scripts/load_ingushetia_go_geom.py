"""Загрузить геометрию городских округов Ингушетии из OSM (Nominatim)."""
import os
import json
import time
import requests
import sqlalchemy as sa
from sqlalchemy import text

db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/zone_monitoring")
if db_url.startswith("postgresql+psycopg"):
    db_url = db_url.replace("postgresql+psycopg", "postgresql", 1)
engine = sa.create_engine(db_url)

REGION_NAME = "Республика Ингушетия"

# Название в БД -> запросы для Nominatim (город, чтобы не перепутать с другими регионами)
DISTRICTS_QUERIES = {
    "городской округ город Магас": ["Магас Ингушетия Россия", "Magas Ingushetia Russia"],
    "городской округ город Назрань": ["Назрань Ингушетия Россия", "Nazran Ingushetia Russia"],
    "городской округ город Карабулак": ["Карабулак Ингушетия Россия", "Karabulak Ingushetia Russia"],
    "городской округ город Сунжа": ["Сунжа Ингушетия Россия", "Sunzha Ingushetia Russia"],
    "городской округ город Малгобек": ["Малгобек Ингушетия Россия", "Malgobek Ingushetia Russia"],
}


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
    print("Загрузка геометрии городских округов Ингушетии")
    print("=" * 60)

    with engine.begin() as conn:
        for district_name, queries in DISTRICTS_QUERIES.items():
            geojson = None
            for q in queries:
                time.sleep(1.1)
                results = search_nominatim(q)
                if not results:
                    continue
                for item in results:
                    display = item.get("display_name", "")
                    if "Ингушетия" not in display and "Ingushetia" not in display and "Ingushetiya" not in display:
                        continue
                    g = item.get("geojson")
                    if g and g.get("type") in ("Polygon", "MultiPolygon"):
                        geojson = g
                        break
                if geojson:
                    break

            if not geojson:
                print(f"  {district_name}: геометрия не найдена")
                continue

            conn.execute(
                text("""
                    UPDATE districts d
                    SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)))
                    FROM regions r
                    WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
                """),
                {"geojson": json.dumps(geojson), "region": REGION_NAME, "name": district_name},
            )
            row = conn.execute(
                text("""
                    SELECT ROUND(ST_Area(d.geom::geography)/1000000), ST_NPoints(d.geom)
                    FROM districts d
                    JOIN regions r ON d.region_id = r.id
                    WHERE r.name = :region AND d.name = :name
                """),
                {"region": REGION_NAME, "name": district_name},
            ).fetchone()
            print(f"  OK {district_name}: ~{int(row[0])} км², {row[1]} точек")

    print("\nГотово.")


if __name__ == "__main__":
    main()
