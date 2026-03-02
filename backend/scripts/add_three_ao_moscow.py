"""Добавить 3 АО Москвы (Зеленоградский, Троицкий, Новомосковский) и убрать дубликаты."""
import sys, json, time, requests, uuid
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
NOMINATIM = "https://nominatim.openstreetmap.org/search"
MOSCOW_BBOX = "37.3,55.5,37.9,55.9"

def search_geom(query):
    params = {'q': f"{query}, Москва", 'format': 'json', 'polygon_geojson': 1, 'limit': 3, 'viewbox': MOSCOW_BBOX, 'accept-language': 'ru'}
    try:
        time.sleep(1.5)
        r = requests.get(NOMINATIM, params=params, headers={'User-Agent': 'ZoneMonitoring/1.0'}, timeout=30)
        if r.status_code != 200:
            return None
        for res in r.json():
            g = res.get('geojson')
            if g and g.get('type') in ('Polygon', 'MultiPolygon'):
                if 'Москва' in res.get('display_name', '') or 'Moscow' in res.get('display_name', ''):
                    return g
    except Exception:
        pass
    return None

with ENGINE.connect() as c:
    rid = str(c.execute(text("SELECT id FROM regions WHERE name = 'город Москва'")).scalar())

# Удалить: Савелки (часть Зеленограда), городской округ Троицк и поселение Московский (входят в Троицкий/Новомосковский АО)
with ENGINE.begin() as c:
    c.execute(text("""
        DELETE FROM districts WHERE region_id = :rid AND name IN (
            'Муниципальный округ Савелки', 'городской округ Троицк', 'поселение Московский'
        )
    """), {'rid': rid})
print("Удалены 3 дубликата.")

# Добавить 3 АО
for name in ["Зеленоградский административный округ", "Троицкий административный округ", "Новомосковский административный округ"]:
    geom = search_geom(name)
    if not geom:
        print(f"  Нет геометрии: {name}")
        continue
    with ENGINE.begin() as c:
        c.execute(text("""
            INSERT INTO districts (id, region_id, name, geom)
            VALUES (:id, :rid, :name, ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))))
        """), {'id': str(uuid.uuid4()), 'rid': rid, 'name': name, 'g': json.dumps(geom)})
    with ENGINE.connect() as c:
        area = c.execute(text("SELECT ROUND(ST_Area(geom::geography)/1e6) FROM districts WHERE region_id = :rid AND name = :name"), {'rid': rid, 'name': name}).scalar()
    print(f"  + {name}: {area} km2")

with ENGINE.connect() as c:
    total = c.execute(text("SELECT COUNT(*) FROM districts WHERE region_id = :rid"), {'rid': rid}).scalar()
    sum_area = c.execute(text("SELECT ROUND(SUM(ST_Area(geom::geography))/1e6) FROM districts WHERE region_id = :rid AND geom IS NOT NULL"), {'rid': rid}).scalar()
print(f"\nИтого: {total} единиц, суммарная площадь ~{sum_area} km2")
