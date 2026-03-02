"""
Восстановить корректную карту Москвы:
1. Удалить 97 муниципальных округов (неверные геометрии от Nominatim).
2. Вставить 9 административных округов с границами из OSM (Nominatim по имени АО).
Троицк и поселение Московский не трогаем (уже есть).
"""
import sys
import json
import time
import requests
import uuid

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
NOMINATIM = "https://nominatim.openstreetmap.org/search"
MOSCOW_BBOX = "37.3,55.5,37.9,55.9"

# 12 административных округов Москвы (включая Зеленоградский, Троицкий, Новомосковский)
AO_NAMES = [
    "Центральный административный округ",
    "Северный административный округ",
    "Северо-Восточный административный округ",
    "Восточный административный округ",
    "Юго-Восточный административный округ",
    "Южный административный округ",
    "Юго-Западный административный округ",
    "Западный административный округ",
    "Северо-Западный административный округ",
    "Зеленоградский административный округ",
    "Троицкий административный округ",
    "Новомосковский административный округ",
]

def search_geom(query):
    params = {
        'q': f"{query}, Москва",
        'format': 'json',
        'polygon_geojson': 1,
        'limit': 3,
        'viewbox': MOSCOW_BBOX,
        'accept-language': 'ru',
    }
    try:
        time.sleep(1.5)
        r = requests.get(NOMINATIM, params=params, headers={'User-Agent': 'ZoneMonitoring/1.0'}, timeout=30)
        if r.status_code != 200:
            return None
        for res in r.json():
            g = res.get('geojson')
            if g and g.get('type') in ('Polygon', 'MultiPolygon'):
                display = res.get('display_name', '')
                if 'Москва' in display or 'Moscow' in display:
                    return g
    except Exception:
        pass
    return None

def main():
    with ENGINE.connect() as c:
        rid = c.execute(text("SELECT id FROM regions WHERE name = 'город Москва'")).scalar()
        if not rid:
            print("Регион Москва не найден")
            return
        moscow_region_id = str(rid)

    # 1. Удалить все 97 муниципальных округов (name LIKE 'муниципальный округ %')
    with ENGINE.begin() as c:
        result = c.execute(text("""
            DELETE FROM districts 
            WHERE region_id = :rid AND name LIKE 'муниципальный округ %'
            RETURNING name
        """), {'rid': moscow_region_id})
        deleted = list(result)
    print(f"Удалено муниципальных округов: {len(deleted)}")

    # 2. Удалить дубликаты Новой Москвы (они войдут в Троицкий/Новомосковский АО)
    with ENGINE.begin() as c:
        c.execute(text("""
            DELETE FROM districts 
            WHERE region_id = :rid AND name IN ('городской округ Троицк', 'поселение Московский')
        """), {'rid': moscow_region_id})
    print("Удалены городской округ Троицк и поселение Московский (входят в АО).")

    # 3. Добавить 12 АО с геометрией
    inserted = 0
    for name in AO_NAMES:
        geom = search_geom(name)
        if not geom:
            print(f"  Нет геометрии: {name}")
            continue
        geojson_str = json.dumps(geom)
        new_id = str(uuid.uuid4())
        with ENGINE.begin() as c:
            c.execute(text("""
                INSERT INTO districts (id, region_id, name, geom)
                VALUES (:id, :rid, :name, ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))))
            """), {'id': new_id, 'rid': moscow_region_id, 'name': name, 'g': geojson_str})
        inserted += 1
        area = None
        with ENGINE.connect() as conn:
            area = conn.execute(text("""
                SELECT ROUND(ST_Area(geom::geography)/1e6) FROM districts WHERE id = :id
            """), {'id': new_id}).scalar()
        print(f"  + {name}: {area} km2")
    print(f"Добавлено АО: {inserted}")

    # 4. Итог
    with ENGINE.connect() as c:
        total = c.execute(text("SELECT COUNT(*) FROM districts WHERE region_id = :rid"), {'rid': moscow_region_id}).scalar()
        sum_area = c.execute(text("""
            SELECT ROUND(SUM(ST_Area(geom::geography))/1e6) FROM districts 
            WHERE region_id = :rid AND geom IS NOT NULL
        """), {'rid': moscow_region_id}).scalar()
    print(f"\nИтого по городу Москва: {total} единиц, суммарная площадь ~{sum_area} km2 (ожидается ~2561)")

if __name__ == '__main__':
    main()
