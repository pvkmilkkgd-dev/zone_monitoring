"""
Севастополь: 4 района города федерального значения (не муниципальные районы).
1. Переименовать: X муниципальный район → X район (Балаклавский, Ленинский, Нахимовский).
2. Добавить Гагаринский район с геометрией из OSM.
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
SEV_BBOX = "33.4,44.5,33.6,44.65"

def search_geom(query):
    params = {'q': query, 'format': 'json', 'polygon_geojson': 1, 'limit': 3, 'viewbox': SEV_BBOX, 'accept-language': 'ru'}
    try:
        time.sleep(1.5)
        r = requests.get(NOMINATIM, params=params, headers={'User-Agent': 'ZoneMonitoring/1.0'}, timeout=30)
        if r.status_code != 200:
            return None
        for res in r.json():
            g = res.get('geojson')
            if g and g.get('type') in ('Polygon', 'MultiPolygon'):
                if 'Севастополь' in res.get('display_name', '') or 'Sevastopol' in res.get('display_name', ''):
                    return g
    except Exception:
        pass
    return None

with ENGINE.connect() as c:
    rid = str(c.execute(text("SELECT id FROM regions WHERE name = 'город Севастополь'")).scalar())

# 1. Переименовать существующие три в "район"
with ENGINE.begin() as c:
    c.execute(text("""
        UPDATE districts d SET name = REPLACE(d.name, ' муниципальный район', ' район')
        FROM regions r WHERE d.region_id = r.id AND r.name = 'город Севастополь' AND d.name LIKE '%муниципальный район'
    """))
print("1. Переименованы: Балаклавский, Ленинский, Нахимовский → X район")

# 2. Добавить Гагаринский район
geom = search_geom("Гагаринский район Севастополь") or search_geom("Gagarin district Sevastopol")
if geom:
    new_id = str(uuid.uuid4())
    with ENGINE.begin() as c:
        c.execute(text("""
            INSERT INTO districts (id, region_id, name, geom)
            VALUES (:id, :rid, :name, ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))))
        """), {'id': new_id, 'rid': rid, 'name': 'Гагаринский район', 'g': json.dumps(geom)})
    with ENGINE.connect() as c:
        area = c.execute(text("SELECT ROUND(ST_Area(geom::geography)/1e6) FROM districts WHERE id = :id"), {'id': new_id}).scalar()
    print(f"2. Добавлен: Гагаринский район (~{area} km2)")
else:
    print("2. Геометрию Гагаринского района не удалось загрузить из Nominatim")

# Итог
with ENGINE.connect() as c:
    rows = c.execute(text("SELECT d.name FROM districts d JOIN regions r ON d.region_id = r.id WHERE r.name = 'город Севастополь' ORDER BY d.name")).fetchall()
print("\nИтого по городу Севастополь:", [r[0] for r in rows])
