"""Подгрузить геометрию для городского округа Дзержинский (Московская область) из OSM."""
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

DISTRICT_NAME = "городской округ Дзержинский"
REGION_NAME = "Московская область"

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
    queries = [
        "Дзержинский Московская область Россия",
        "Dzerzhinsky Moscow Oblast Russia",
        "городской округ Дзержинский Московская область",
    ]
    geojson = None
    for q in queries:
        time.sleep(1.1)
        results = search_nominatim(q)
        if not results:
            continue
        for item in results:
            display = item.get("display_name", "")
            # Берём результат в Московской области (не Калужской и не Нижегородской)
            if "Московск" not in display and "Moscow" not in display:
                continue
            if "Калуж" in display or "Калуга" in display or "Nizhny" in display:
                continue
            g = item.get("geojson")
            if g and g.get("type") in ("Polygon", "MultiPolygon"):
                geojson = g
                print(f"Найдена геометрия по запросу: {q}")
                break
        if geojson:
            break

    if not geojson:
        print("Геометрия не найдена в Nominatim.")
        return

    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE districts d
                SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)))
                FROM regions r
                WHERE d.region_id = r.id
                  AND r.name = :region
                  AND d.name = :name
            """),
            {"geojson": json.dumps(geojson), "region": REGION_NAME, "name": DISTRICT_NAME},
        )
        row = conn.execute(
            text("""
                SELECT d.name, ROUND(ST_Area(d.geom::geography)/1000000) as area_km2, ST_NPoints(d.geom)
                FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = :name
            """),
            {"region": REGION_NAME, "name": DISTRICT_NAME},
        ).fetchone()
    if row:
        print(f"Обновлено: {row[0]}, площадь ~{int(row[1])} км², точек {row[2]}.")
    else:
        print("Запись не найдена в БД.")


if __name__ == "__main__":
    main()
