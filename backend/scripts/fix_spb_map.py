"""
Привести карту Санкт-Петербурга к 18 районам.
- Удалить «муниципальный округ Дворцовый округ» (это внутригородской округ в составе Центрального района).
- Добавить «Петродворцовый муниципальный район» с геометрией из OSM.
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
# СПб bbox
SPB_BBOX = "29.5,59.7,30.5,60.2"

def search_geom(query):
    params = {
        'q': f"{query}, Санкт-Петербург",
        'format': 'json',
        'polygon_geojson': 1,
        'limit': 3,
        'viewbox': SPB_BBOX,
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
                if 'Петербург' in display or 'Saint' in display or 'Санкт' in display:
                    return g
    except Exception:
        pass
    return None

with ENGINE.connect() as c:
    rid = str(c.execute(text("SELECT id FROM regions WHERE name = 'город Санкт-Петербург'")).scalar())

# 1. Удалить «муниципальный округ Дворцовый округ»
with ENGINE.begin() as c:
    c.execute(text("""
        DELETE FROM districts 
        WHERE region_id = :rid AND name = 'муниципальный округ Дворцовый округ'
    """), {'rid': rid})
print("Удалён: муниципальный округ Дворцовый округ")

# 2. Добавить Петродворцовый муниципальный район
name = "Петродворцовый муниципальный район"
geom = search_geom("Петродворцовый район")
if not geom:
    geom = search_geom("Петродворцовый")
if geom:
    with ENGINE.begin() as c:
        c.execute(text("""
            INSERT INTO districts (id, region_id, name, geom)
            VALUES (:id, :rid, :name, ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))))
        """), {'id': str(uuid.uuid4()), 'rid': rid, 'name': name, 'g': json.dumps(geom)})
    with ENGINE.connect() as c:
        area = c.execute(text("""
            SELECT ROUND(ST_Area(geom::geography)/1e6) FROM districts 
            WHERE region_id = :rid AND name = :name
        """), {'rid': rid, 'name': name}).scalar()
    print(f"Добавлен: {name} (~{area} km2)")
else:
    print("Не удалось загрузить геометрию для Петродворцового района")

# 3. Итог
with ENGINE.connect() as c:
    total = c.execute(text("SELECT COUNT(*) FROM districts WHERE region_id = :rid"), {'rid': rid}).scalar()
    sum_area = c.execute(text("""
        SELECT ROUND(SUM(ST_Area(geom::geography))/1e6) FROM districts 
        WHERE region_id = :rid AND geom IS NOT NULL
    """), {'rid': rid}).scalar()
print(f"\nИтого: {total} районов, суммарная площадь ~{sum_area} km2 (СПб ~1439 km2)")
