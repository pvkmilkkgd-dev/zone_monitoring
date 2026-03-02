"""
Подгрузка геометрии для районов ДНР без геометрии (Nominatim/OSM).
"""
import sys
import json
import time
import requests
import re

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
NOMINATIM = "https://nominatim.openstreetmap.org/search"
# Донбасс bbox
BBOX = "36.5,46.8,39.2,49.2"
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

def search_geom(query, bbox=BBOX):
    params = {'q': query, 'format': 'json', 'polygon_geojson': 1, 'limit': 5, 'viewbox': bbox, 'accept-language': 'ru'}
    try:
        time.sleep(1.5)
        r = requests.get(NOMINATIM, params=params, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return None
        for res in r.json():
            g = res.get('geojson')
            if not g or g.get('type') not in ('Polygon', 'MultiPolygon'):
                continue
            disp = res.get('display_name', '')
            # Донецк, Украина или Donetsk
            if 'Donetsk' in disp or 'Донецк' in disp or 'Donets' in disp or 'Украин' in disp or 'Ukraine' in disp:
                return g
    except Exception as e:
        print(f"    err: {e}")
    return None

# Варианты запросов для МО (район) и ГО (город)
QUERIES = {
    "Александровский муниципальный округ": ["Александровка Донецкая область", "Oleksandrivka Donetsk"],
    "Амвросиевский муниципальный округ": ["Амвросиевка Донецк", "Amvrosiivka Donetsk"],
    "Великоновоселковский муниципальный округ": ["Великая Новосёлка Донецк", "Velyka Novosilka Donetsk"],
    "Володарский муниципальный округ": ["Володарский район Донецк", "Volodarske Donetsk"],
    "Добропольский муниципальный округ": ["Доброполье Донецк", "Dobropillia Donetsk"],
    "Константиновский муниципальный округ": ["Константиновка Донецк", "Kostiantynivka Donetsk"],
    "Краснолиманский муниципальный округ": ["Красный Лиман Донецк", "Krasnii Lyman Donetsk"],
    "Кураховский муниципальный округ": ["Курахово Донецк", "Kurakhove Donetsk"],
    "Мангушский муниципальный округ": ["Мангуш Донецк", "Manhush Donetsk"],
    "Новоазовский муниципальный округ": ["Новоазовск Донецк", "Novoazovsk Donetsk"],
    "Славянский муниципальный округ": ["Славянск Донецк", "Sloviansk Donetsk"],
    "Старобешевский муниципальный округ": ["Старобешево Донецк", "Starobesheve Donetsk"],
    "Тельмановский муниципальный округ": ["Тельманово Донецк", "Telmanove Donetsk"],
    "Шахтерский муниципальный округ": ["Шахтёрск Донецк", "Shakhtarsk Donetsk"],
    "Ясиноватский муниципальный округ": ["Ясиноватая Донецк", "Yasynuvata Donetsk"],
    "городской округ Дебальцево": ["Дебальцево Донецк", "Debaltseve Donetsk"],
    "городской округ Докучаевск": ["Докучаевск Донецк", "Dokuchaievsk Donetsk"],
    "городской округ Енакиево": ["Енакиево Донецк", "Yenakiieve Donetsk"],
    "городской округ Иловайск": ["Иловайск Донецк", "Ilovaisk Donetsk"],
    "городской округ Макеевка": ["Макеевка Донецк", "Makiivka Donetsk"],
    "городской округ Снежное": ["Снежное Донецк", "Snizhne Donetsk"],
    "городской округ Торез": ["Торез Донецк", "Torez Donetsk"],
    "городской округ Харцызск": ["Харцызск Донецк", "Khartsyzsk Donetsk"],
}

with ENGINE.connect() as c:
    rid = str(c.execute(text("SELECT id FROM regions WHERE name = 'Донецкая Народная Республика'")).scalar())
    no_geom = c.execute(text("""
        SELECT id, name FROM districts
        WHERE region_id = :rid AND (geom IS NULL OR ST_NPoints(geom) = 0)
        ORDER BY name
    """), {'rid': rid}).fetchall()

print(f"Без геометрии: {len(no_geom)} записей\n")
loaded = 0
for did, name in no_geom:
    did = str(did)
    queries = QUERIES.get(name, [name.replace('муниципальный округ', '').replace('городской округ', '').strip() + ' Донецк'])
    geom = None
    for q in queries:
        geom = search_geom(q)
        if geom:
            break
    if geom:
        with ENGINE.begin() as c:
            c.execute(text("""
                UPDATE districts SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))
                WHERE id = :id
            """), {'g': json.dumps(geom), 'id': did})
        with ENGINE.connect() as c:
            area = c.execute(text("SELECT ROUND(ST_Area(geom::geography)/1e6) FROM districts WHERE id = :id"), {'id': did}).scalar()
        print(f"  OK {name} (~{area} km2)")
        loaded += 1
    else:
        print(f"  -- {name} (геометрия не найдена)")
print(f"\nЗагружено геометрий: {loaded} из {len(no_geom)}")

with ENGINE.connect() as c:
    still = c.execute(text("""
        SELECT COUNT(*) FROM districts WHERE region_id = :rid AND (geom IS NULL OR ST_NPoints(geom) = 0)
    """), {'rid': rid}).scalar()
    total_geom = c.execute(text("""
        SELECT COUNT(*) FROM districts WHERE region_id = :rid AND geom IS NOT NULL AND ST_NPoints(geom) > 0
    """), {'rid': rid}).scalar()
print(f"По ДНР: с геометрией {total_geom}, без геометрии {still}")
