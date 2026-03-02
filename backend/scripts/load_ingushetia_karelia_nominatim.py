"""
Загрузка геометрии районов Ингушетии и Карелии из Nominatim/OSM (не GADM).
"""
import sys
import io
import json
import time
import urllib.request
import urllib.parse
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlalchemy as sa
from sqlalchemy import text
from app.core.config import settings

engine = sa.create_engine(settings.DATABASE_URL)

# Специальные запросы для сложных названий
CUSTOM_QUERIES = {
    "Республика Ингушетия": {
        "городской округ г. Карабулак": ["Карабулак, Ингушетия, Россия", "городской округ Карабулак, Ингушетия"],
        "городской округ г. Магас": ["Магас, Ингушетия, Россия", "городской округ Магас, Ингушетия"],
        "городской округ г. Малгобек": ["Малгобек, Ингушетия, Россия", "городской округ Малгобек, Ингушетия"],
        "городской округ г. Назрань": ["Назрань, Ингушетия, Россия", "городской округ Назрань, Ингушетия"],
        "городской округ г. Сунжа": ["Сунжа, Ингушетия, Россия", "городской округ Сунжа, Ингушетия"],
        "Джейрахский муниципальный район": ["Джейрахский район, Ингушетия, Россия", "Джейрахский район, Ингушетия"],
        "Малгобекский муниципальный район": ["Малгобекский район, Ингушетия, Россия"],
        "Назрановский муниципальный район": ["Назрановский район, Ингушетия, Россия"],
        "Сунженский муниципальный район": ["Сунженский район, Ингушетия, Россия"],
    },
    "Республика Карелия": {
        "городской округ г. Костомукша": ["Костомукша, Карелия, Россия", "городской округ Костомукша, Карелия"],
        "городской округ г. Петрозаводск": ["Петрозаводск, Карелия, Россия", "городской округ Петрозаводск, Карелия"],
        "городской округ г. Сортавала": ["Сортавала, Карелия, Россия", "городской округ Сортавала, Карелия"],
        "Костомукшский муниципальный округ": ["Костомукшский район, Карелия, Россия"],
        "Сортавальский муниципальный округ": ["Сортавальский район, Карелия, Россия"],
    },
}


def nominatim_search(query):
    base = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 5,
        "polygon_geojson": 1,
    }
    url = f"{base}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "ZoneMonitoring/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_geojson(results):
    for r in results:
        g = r.get("geojson")
        if g and g.get("type") in ("Polygon", "MultiPolygon"):
            return g, r.get("display_name", "")
    return None, None


def build_queries(region_name, district_name):
    if region_name in CUSTOM_QUERIES and district_name in CUSTOM_QUERIES[region_name]:
        return CUSTOM_QUERIES[region_name][district_name]
    short = district_name.replace("муниципальный район", "район").replace("муниципальный округ", "округ")
    return [
        f"{short}, {region_name}, Россия",
        f"{district_name}, {region_name}",
    ]


def load_region(conn, region_name, region_id):
    r = conn.execute(
        text("SELECT id, name FROM districts WHERE region_id = :rid ORDER BY name"),
        {"rid": region_id},
    )
    districts = [(str(row[0]), row[1]) for row in r]
    print(f"\n{region_name}: {len(districts)} районов")

    loaded = 0
    failed = []
    for d_id, d_name in districts:
        queries = build_queries(region_name, d_name)
        geojson = None
        for q in queries:
            try:
                results = nominatim_search(q)
                geojson, _ = get_geojson(results)
                if geojson:
                    break
            except Exception as e:
                print(f"  [ERR] {d_name}: {e}")
            time.sleep(1.2)

        if geojson:
            g = json.dumps(geojson)
            conn.execute(
                text("""
                UPDATE districts
                SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))
                WHERE id = :id
                """),
                {"g": g, "id": d_id},
            )
            r2 = conn.execute(
                text("SELECT ROUND((ST_Area(geom::geography)/1e6)::numeric, 1) FROM districts WHERE id = :id"),
                {"id": d_id},
            )
            area = r2.scalar()
            print(f"  OK   {d_name:<55} {area:>8.1f} km²")
            loaded += 1
        else:
            failed.append(d_name)
            print(f"  [!]  {d_name:<55} не найден")
        time.sleep(1.2)

    return loaded, failed


def main():
    print("=" * 70)
    print("ЗАГРУЗКА ИНГУШЕТИИ И КАРЕЛИИ ИЗ NOMINATIM")
    print("=" * 70)

    with engine.begin() as conn:
        for region_name in ["Республика Ингушетия", "Республика Карелия"]:
            r = conn.execute(
                text("SELECT id FROM regions WHERE name = :name"),
                {"name": region_name},
            )
            rid = r.scalar()
            if not rid:
                print(f"Регион не найден: {region_name}")
                continue
            load_region(conn, region_name, str(rid))

    print("\nГотово!")


if __name__ == "__main__":
    main()
