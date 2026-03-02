"""
Исправить карту ДНР: у крупных городских округов подменить геометрию на границы города
(не района), чтобы убрать перекрытия и фрагментацию.
"""
import sys
import json
import time
import requests
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
NOMINATIM = "https://nominatim.openstreetmap.org/search"
BBOX = "36.5,46.8,39.2,49.2"
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

def search_city_geom(query):
    """Ищем именно город (place=city/town), не район."""
    params = {'q': query, 'format': 'json', 'polygon_geojson': 1, 'limit': 5, 'viewbox': BBOX}
    try:
        time.sleep(1.8)
        r = requests.get(NOMINATIM, params=params, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return None
        for res in r.json():
            g = res.get('geojson')
            if not g or g.get('type') not in ('Polygon', 'MultiPolygon'):
                continue
            typ = res.get('type', '')
            cls = res.get('class', '')
            # Предпочитаем place=city или town, не admin_boundary
            if cls in ('place', 'boundary') and typ in ('city', 'town', 'administrative'):
                disp = res.get('display_name', '')
                if 'Donetsk' in disp or 'Донецк' in disp or 'Ukraine' in disp or 'Украин' in disp:
                    return g
        # Если не нашли по типу — берём первый полигон в bbox
        for res in r.json():
            g = res.get('geojson')
            if g and g.get('type') in ('Polygon', 'MultiPolygon'):
                return g
    except Exception as e:
        print(f"    err: {e}")
    return None

# Крупные ГО, у которых в базе границы района (перекрывают карту)
BIG_CITY_OKRUGS = [
    ("городской округ Донецк", ["Donetsk city Ukraine", "Донецк город"]),
    ("городской округ Краматорск", ["Krasnatorsk city Ukraine", "Краматорск город"]),
    ("городской округ Мариуполь", ["Mariupol city Ukraine", "Мариуполь город"]),
    ("городской округ Горловка", ["Horlivka city Ukraine", "Горловка город"]),
]

with ENGINE.connect() as c:
    rid = str(c.execute(text("SELECT id FROM regions WHERE name = 'Донецкая Народная Республика'")).scalar())

updated = 0
for name, queries in BIG_CITY_OKRUGS:
    geom = None
    for q in queries:
        geom = search_city_geom(q)
        if geom:
            break
    if not geom:
        print(f"  — {name}: не найден полигон города")
        continue
    with ENGINE.begin() as c:
        c.execute(text("""
            UPDATE districts SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))
            WHERE region_id = :rid AND name = :name
        """), {'g': json.dumps(geom), 'rid': rid, 'name': name})
    with ENGINE.connect() as c:
        area = c.execute(text("""
            SELECT ROUND(ST_Area(geom::geography)/1e6) FROM districts
            WHERE region_id = :rid AND name = :name
        """), {'rid': rid, 'name': name}).scalar()
    print(f"  OK {name}: ~{area} km2")
    updated += 1

print(f"\nОбновлено записей: {updated}")

# Итоговая сводка по площадям
with ENGINE.connect() as c:
    rows = c.execute(text("""
        SELECT name, ROUND(ST_Area(geom::geography)/1e6) as km2
        FROM districts WHERE region_id = :rid AND geom IS NOT NULL
        ORDER BY ST_Area(geom::geography) DESC
        LIMIT 15
    """), {'rid': rid}).fetchall()
print("\nТоп-15 по площади после правки:")
for name, km2 in rows:
    print(f"  {km2} km2  {name}")
