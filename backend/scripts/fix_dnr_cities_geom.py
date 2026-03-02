"""
Подгрузить корректные границы городов Донецк, Мариуполь, Горловка по OSM relation id
(у них после замены получилась площадь 0 — нужен нормальный полигон).
"""
import sys
import json
import time
import requests
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
# Nominatim lookup по relation id
LOOKUP = "https://nominatim.openstreetmap.org/lookup"
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

# OSM relation id для городов (административная граница города)
CITY_RELATIONS = {
    "городской округ Донецк": 1413957,   # Donetsk
    "городской округ Мариуполь": 1748539,  # Mariupol Ukraine
    "городской округ Горловка": 3862199,  # Horlivka Ukraine
}

with ENGINE.connect() as c:
    rid = str(c.execute(text("SELECT id FROM regions WHERE name = 'Донецкая Народная Республика'")).scalar())

for name, rel_id in CITY_RELATIONS.items():
    time.sleep(2)
    try:
        r = requests.get(LOOKUP, params={
            'osm_ids': f'R{rel_id}',
            'format': 'json',
            'polygon_geojson': 1,
        }, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"  {name}: HTTP {r.status_code}")
            continue
        data = r.json()
        if not data:
            print(f"  {name}: пустой ответ")
            continue
        g = data[0].get('geojson')
        if not g or g.get('type') not in ('Polygon', 'MultiPolygon'):
            print(f"  {name}: нет полигона")
            continue
        with ENGINE.begin() as c:
            c.execute(text("""
                UPDATE districts SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))
                WHERE region_id = :rid AND name = :name
            """), {'g': json.dumps(g), 'rid': rid, 'name': name})
        with ENGINE.connect() as c:
            area = c.execute(text("SELECT ROUND(ST_Area(geom::geography)/1e6) FROM districts WHERE region_id = :rid AND name = :name"), {'rid': rid, 'name': name}).scalar()
        print(f"  OK {name}: ~{area} km2 (R{rel_id})")
    except Exception as e:
        print(f"  {name}: {e}")
