"""
Исправления по аудиту:
1. СПб: удалить Ломоносовский МР (он в Ленобласти, не в СПб).
2. Ингушетия: удалить 7 записей с названиями районов Адыгеи (ошибочно привязаны к Ингушетии).
3. Чечня: загрузить геометрию для Шалинского МР.
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
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

# --- 1. СПб: удалить Ломоносовский МР ---
print("1. Санкт-Петербург: удаляю Ломоносовский муниципальный район (принадлежит Ленобласти)...")
with ENGINE.begin() as c:
    rid = c.execute(text("SELECT id FROM regions WHERE name = 'город Санкт-Петербург'")).scalar()
    r = c.execute(text("""
        DELETE FROM districts 
        WHERE region_id = :rid AND name = 'Ломоносовский муниципальный район'
        RETURNING id
    """), {'rid': str(rid)})
    if r.fetchone():
        print("   Удалён.")
    else:
        print("   Не найден.")

# --- 2. Ингушетия: удалить 7 записей с названиями районов Адыгеи ---
wrong_adygea_names = [
    'Кошехабльский муниципальный район',
    'Гиагинский муниципальный район',
    'Тахтамукайский муниципальный район',
    'Теучежский муниципальный район',
    'Шовгеновский муниципальный район',
    'Красногвардейский муниципальный район',
    'Майкопский муниципальный район',
]
print("\n2. Ингушетия: удаляю 7 записей с названиями районов Адыгеи (ошибочная привязка)...")
with ENGINE.connect() as c:
    rid_ing = c.execute(text("SELECT id FROM regions WHERE name = 'Республика Ингушетия'")).scalar()
if rid_ing:
    with ENGINE.begin() as c:
        for name in wrong_adygea_names:
            c.execute(text("DELETE FROM districts WHERE region_id = :rid AND name = :name"),
                     {'rid': str(rid_ing), 'name': name})
    print(f"   Удалено записей: {len(wrong_adygea_names)}.")
else:
    print("   Регион Ингушетия не найден.")

# --- 3. Чечня: геометрия для Шалинского МР ---
print("\n3. Чечня: загружаю геометрию для Шалинского муниципального района...")
def search_geom(query, bbox="45.5,42.8,46.2,43.5"):
    params = {'q': query, 'format': 'json', 'polygon_geojson': 1, 'limit': 3, 'viewbox': bbox, 'accept-language': 'ru'}
    try:
        time.sleep(1.5)
        r = requests.get(NOMINATIM, params=params, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return None
        for res in r.json():
            g = res.get('geojson')
            if g and g.get('type') in ('Polygon', 'MultiPolygon'):
                if 'Чечн' in res.get('display_name', '') or 'Chechnya' in res.get('display_name', '') or 'Шали' in res.get('display_name', ''):
                    return g
    except Exception:
        pass
    return None

with ENGINE.connect() as c:
    rid_che = c.execute(text("SELECT id FROM regions WHERE name = 'Чеченская Республика'")).scalar()
    row = c.execute(text("SELECT id FROM districts WHERE region_id = :rid AND name = 'Шалинский муниципальный район'"),
                    {'rid': str(rid_che)}).fetchone()
if not row:
    print("   Шалинский МР не найден в базе.")
else:
    did = str(row[0])
    geom = search_geom("Шалинский район Чеченская Республика") or search_geom("Шали Чечня")
    if geom:
        with ENGINE.begin() as c:
            c.execute(text("""
                UPDATE districts SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))
                WHERE id = :id
            """), {'g': json.dumps(geom), 'id': did})
        with ENGINE.connect() as c:
            area = c.execute(text("SELECT ROUND(ST_Area(geom::geography)/1e6) FROM districts WHERE id = :id"), {'id': did}).scalar()
        print(f"   Геометрия загружена, площадь ~{area} km2.")
    else:
        print("   Геометрию по Nominatim не получилось подгрузить.")

# Итог
print("\n--- Итог ---")
with ENGINE.connect() as c:
    no_geom = c.execute(text("SELECT COUNT(*) FROM districts WHERE geom IS NULL OR ST_NPoints(geom) = 0")).scalar()
    spb_cnt = c.execute(text("SELECT COUNT(*) FROM districts d JOIN regions r ON d.region_id = r.id WHERE r.name = 'город Санкт-Петербург'")).scalar()
print(f"Районов без геометрии в базе: {no_geom}")
print(f"Районов в Санкт-Петербурге: {spb_cnt} (ожидается 18)")
