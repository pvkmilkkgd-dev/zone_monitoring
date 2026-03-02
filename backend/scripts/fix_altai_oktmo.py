"""
Fix Алтайский край district names using ОКТМО (official federal classifier).
Source: https://okp-okpd.ru/oktmo.aspx?kod=01
"""
import sys
import os
import json
import time
import requests
from uuid import uuid4

os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

# Official ОКТМО names for Алтайский край (code 01)
# Source: https://okp-okpd.ru/oktmo.aspx?kod=01
OKTMO_DISTRICTS = [
    # Муниципальные районы (59)
    "Алейский муниципальный район",
    "Алтайский муниципальный район",
    "Баевский муниципальный район",
    "Бийский муниципальный район",
    "Благовещенский муниципальный район",
    "Бурлинский муниципальный район",
    "Быстроистокский муниципальный район",
    "Волчихинский муниципальный район",
    "Егорьевский муниципальный район",
    "Ельцовский муниципальный район",
    "Завьяловский муниципальный район",
    "Залесовский муниципальный район",
    "Заринский муниципальный район",
    "Змеиногорский муниципальный район",
    "Зональный муниципальный район",
    "Калманский муниципальный район",
    "Каменский муниципальный район",
    "Ключевский муниципальный район",
    "Косихинский муниципальный район",
    "Красногорский муниципальный район",
    "Краснощёковский муниципальный район",
    "Крутихинский муниципальный район",
    "Кулундинский муниципальный район",
    "Курьинский муниципальный район",
    "Кытмановский муниципальный район",
    "Локтевский муниципальный район",
    "Мамонтовский муниципальный район",
    "Михайловский муниципальный район",
    "Немецкий национальный муниципальный район",
    "Новичихинский муниципальный район",
    "Павловский муниципальный район",
    "Панкрушихинский муниципальный район",
    "Первомайский муниципальный район",
    "Петропавловский муниципальный район",
    "Поспелихинский муниципальный район",
    "Ребрихинский муниципальный район",
    "Родинский муниципальный район",
    "Романовский муниципальный район",
    "Рубцовский муниципальный район",
    "Смоленский муниципальный район",
    "Советский муниципальный район",
    "Солонешенский муниципальный район",
    "Солтонский муниципальный район",
    "Суетский муниципальный район",
    "Табунский муниципальный район",
    "Тальменский муниципальный район",
    "Тогульский муниципальный район",
    "Топчихинский муниципальный район",
    "Третьяковский муниципальный район",
    "Троицкий муниципальный район",
    "Тюменцевский муниципальный район",
    "Угловский муниципальный район",
    "Усть-Калманский муниципальный район",
    "Усть-Пристанский муниципальный район",
    "Хабарский муниципальный район",
    "Целинный муниципальный район",
    "Чарышский муниципальный район",
    "Шелаболихинский муниципальный район",
    "Шипуновский муниципальный район",
    # Городские округа / города (10)
    "город Барнаул",
    "город Алейск",
    "город Белокуриха",
    "город Бийск",
    "город Заринск",
    "город Камень-на-Оби",
    "город Новоалтайск",
    "город Рубцовск",
    "город Славгород",
    "город Яровое",
    # ЗАТО (1)
    "ЗАТО Сибирский",
]

HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}


def normalize(name):
    n = name.strip().lower()
    for w in ['муниципальный район', 'район', 'муниципальный округ', 'округ',
              'городской округ', 'город', 'зато', 'муниципальный']:
        n = n.replace(w, '')
    n = n.replace('ё', 'е').replace('-', '').replace(' ', '')
    return n


def download_polygon_nominatim(name, region="Алтайский край"):
    """Download polygon from Nominatim for a missing district."""
    queries = [
        f"{name}, {region}, Россия",
        f"{name}, Россия",
    ]
    for q in queries:
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={'q': q, 'format': 'json', 'polygon_geojson': 1, 'limit': 5},
                headers=HEADERS, timeout=30
            )
            if resp.status_code == 200:
                for r in resp.json():
                    geojson = r.get('geojson')
                    if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
                        display = r.get('display_name', '')
                        if 'Алтайский' in display or 'Altai' in display:
                            return geojson
        except:
            pass
        time.sleep(1.1)
    return None


def main():
    print(f"Official ОКТМО list: {len(OKTMO_DISTRICTS)} entries")
    
    # Get region ID
    with engine.connect() as conn:
        row = conn.execute(text("SELECT id FROM regions WHERE name = 'Алтайский край'")).fetchone()
        region_id = str(row[0])
    
    # Get current DB entries
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT d.id, d.name, d.geom IS NOT NULL as has_geom
            FROM districts d
            WHERE d.region_id = :rid
            ORDER BY d.name
        """), {"rid": region_id}).fetchall()
    
    db_districts = {str(r[0]): {'name': r[1], 'has_geom': r[2]} for r in rows}
    db_by_norm = {}
    for did, info in db_districts.items():
        norm = normalize(info['name'])
        db_by_norm[norm] = (did, info)
    
    print(f"Current DB entries: {len(db_districts)}")
    
    # Match ОКТМО -> DB
    renames = []
    missing = []
    matched_ids = set()
    
    print(f"\n{'='*70}")
    print("Comparison:")
    print(f"{'='*70}")
    
    for oktmo_name in OKTMO_DISTRICTS:
        oktmo_norm = normalize(oktmo_name)
        
        if oktmo_norm in db_by_norm:
            did, info = db_by_norm[oktmo_norm]
            matched_ids.add(did)
            if info['name'] == oktmo_name:
                print(f"  OK    {oktmo_name}")
            else:
                print(f"  RENAME '{info['name']}' -> '{oktmo_name}'")
                renames.append((did, oktmo_name))
        else:
            print(f"  MISSING {oktmo_name}")
            missing.append(oktmo_name)
    
    # Extra in DB (not in ОКТМО)
    extra_ids = set(db_districts.keys()) - matched_ids
    extra = [(did, db_districts[did]['name']) for did in extra_ids]
    
    if extra:
        print(f"\n  Extra in DB (will remove):")
        for did, name in extra:
            print(f"    - {name}")
    
    # Apply changes
    print(f"\n{'='*70}")
    print(f"Changes: {len(renames)} renames, {len(missing)} missing, {len(extra)} extra")
    print(f"{'='*70}")
    
    # 1. Rename
    if renames:
        print(f"\nRenaming {len(renames)} entries...")
        with engine.connect() as conn:
            for did, new_name in renames:
                conn.execute(text("UPDATE districts SET name = :name WHERE id = :id"),
                           {"name": new_name, "id": did})
            conn.commit()
        print("  Done!")
    
    # 2. Delete extras
    if extra:
        print(f"\nDeleting {len(extra)} extra entries...")
        with engine.connect() as conn:
            for did, name in extra:
                conn.execute(text("DELETE FROM districts WHERE id = :id"), {"id": did})
            conn.commit()
        print("  Done!")
    
    # 3. Add missing (download geometry)
    if missing:
        print(f"\nAdding {len(missing)} missing entries...")
        for name in missing:
            geojson = download_polygon_nominatim(name)
            if geojson:
                geojson_str = json.dumps(geojson)
                with engine.connect() as conn:
                    conn.execute(text("""
                        INSERT INTO districts (id, region_id, name, geom, geom_simplified, created_at)
                        VALUES (:id, :rid, :name,
                                ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                                ST_SimplifyPreserveTopology(
                                    ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))), 0.005),
                                NOW())
                    """), {
                        'id': str(uuid4()), 'rid': region_id,
                        'name': name, 'geojson': geojson_str,
                    })
                    conn.commit()
                print(f"  + {name} (with geometry)")
            else:
                with engine.connect() as conn:
                    conn.execute(text("""
                        INSERT INTO districts (id, region_id, name, created_at)
                        VALUES (:id, :rid, :name, NOW())
                    """), {'id': str(uuid4()), 'rid': region_id, 'name': name})
                    conn.commit()
                print(f"  + {name} (NO geometry)")
    
    # Final list
    print(f"\n{'='*70}")
    print("FINAL list:")
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT d.name, d.geom IS NOT NULL as has_geom
            FROM districts d
            WHERE d.region_id = :rid
            ORDER BY d.name
        """), {"rid": region_id}).fetchall()
    
    for i, (name, has_geom) in enumerate(rows, 1):
        geom_mark = "" if has_geom else " [NO GEOM]"
        print(f"  {i:3d}. {name}{geom_mark}")
    
    print(f"\nTotal: {len(rows)} (ОКТМО: {len(OKTMO_DISTRICTS)})")


if __name__ == "__main__":
    main()
