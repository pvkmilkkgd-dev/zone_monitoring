"""
Загрузка геометрии районов Запорожской области из OSM.

Используются relation ID из Overpass (районы и городские общины).
Для МО без текущего района в OSM после реформы 2020 — пробуем поиск по названию.
"""
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

REGION_NAME = "Запорожская область"

# Из Overpass: район = admin_level 6, міська громада = община города (для ГО)
# МО — текущие районы ОСМ (после реформы их 5, но нам нужны соответствия по названию)
DISTRICT_TO_OSM_RELATION = {
    "Васильевский муниципальный округ": 11872898,   # Василівський район
    "Пологовский муниципальный округ": 11857109,   # Пологівський район
    "городской округ Бердянск": 12313138,          # Бердянська міська громада
    "городской округ Мелитополь": 12287604,       # Мелітопольська міська громада
    "городской округ Энергодар": 12207507,        # Енергодарська міська громада
    # Ниже — общины/районы по названию (может не быть полного совпадения с МО)
    "Акимовский муниципальный округ": 12253222,   # Якимівська селищна громада (нет старого района)
    "Веселовский муниципальный округ": 12223010,  # Веселівська селищна громада
    "Каменско-Днепровский муниципальный округ": 12207510,  # Кам'янсько-Дніпровська міська громада
    "Михайловский муниципальный округ": 12219450, # Михайлівська селищна громада
    "Приазовский муниципальный округ": 12287600, # Приазовська селищна громада
    "Приморский муниципальный округ": 12313141,   # Приморська міська громада
    "Токмакский муниципальный округ": 12314755,  # Токмацька міська громада
    "Черниговский муниципальный округ": 12313143,# Чернігівська селищна громада
}
# Куйбышевский МО — в ОСМ может быть Бильмацька громада (Більмак = Куйбышево): R12319203
DISTRICT_TO_OSM_RELATION["Куйбышевский муниципальный округ"] = 12319203


def get_geojson_from_nominatim(relation_id):
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {"osm_ids": f"R{relation_id}", "format": "geojson", "polygon_geojson": 1}
    headers = {"User-Agent": "ZoneMonitoring/1.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=30)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("features") and len(data["features"]) > 0:
            geom = data["features"][0].get("geometry")
            if geom and geom["type"] in ("Polygon", "MultiPolygon"):
                return geom
    except Exception:
        pass
    return None


def main():
    print("Загрузка геометрии районов Запорожской области из OSM")
    print("=" * 60)

    with engine.begin() as conn:
        for district_name, rel_id in DISTRICT_TO_OSM_RELATION.items():
            geom = get_geojson_from_nominatim(rel_id)
            time.sleep(1.1)
            if not geom:
                print(f"  {district_name}: нет геометрии (R{rel_id})")
                continue
            geojson_str = json.dumps(geom)
            updated = conn.execute(
                text("""
                    UPDATE districts d
                    SET geom = ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)
                    FROM regions r
                    WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
                    RETURNING d.id
                """),
                {"geojson": geojson_str, "region": REGION_NAME, "name": district_name},
            ).fetchone()
            if updated:
                area = conn.execute(
                    text("""
                        SELECT ROUND(ST_Area(d.geom::geography)/1000000)
                        FROM districts d
                        JOIN regions r ON d.region_id = r.id
                        WHERE r.name = :region AND d.name = :name
                    """),
                    {"region": REGION_NAME, "name": district_name},
                ).scalar()
                print(f"  OK {district_name}: ~{int(area)} км² (R{rel_id})")
            else:
                print(f"  (запись не найдена в БД: {district_name})")

    print()
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT d.name,
                       CASE WHEN d.geom IS NOT NULL THEN ROUND(ST_Area(d.geom::geography)/1000000) ELSE NULL END
                FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE r.name = :name
                ORDER BY d.name
            """),
            {"name": REGION_NAME},
        ).fetchall()
        print("Итог:")
        for name, area in rows:
            a = f" {int(area)} км²" if area is not None else " (нет геометрии)"
            print(f"  {name}{a}")


if __name__ == "__main__":
    main()
