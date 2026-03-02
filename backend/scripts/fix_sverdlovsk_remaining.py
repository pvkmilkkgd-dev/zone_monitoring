"""Fix remaining 9 Sverdlovsk districts."""
import sys
import json
import time
import requests
from uuid import uuid4

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

REMAINING = [
    ("Ачитский район", ["Ачитский городской округ Свердловская", "Ачитский муниципальный округ"]),
    ("Верхотурский район", ["Верхотурский городской округ Свердловская", "Верхотурский район Свердловская"]),
    ("Красноуфимский район", ["Красноуфимский округ Свердловская", "Муниципальное образование Красноуфимский округ"]),
    ("Новолялинский район", ["Новолялинский городской округ Свердловская", "Новолялинский район Свердловская"]),
    ("Пригородный район", ["Горноуральский городской округ", "Пригородный район Свердловская"]),
    ("Сысертский район", ["Сысертский городской округ Свердловская", "Сысертский район Свердловская"]),
    ("Тавдинский район", ["Тавдинский городской округ Свердловская", "Тавдинский район Свердловская"]),
    ("Тугулымский район", ["Тугулымский городской округ Свердловская", "Тугулымский район Свердловская"]),
    ("Шалинский район", ["Шалинский городской округ Свердловская", "Шалинский район Свердловская"]),
]


def search_nominatim(query):
    url = "https://nominatim.openstreetmap.org/search"
    params = {'q': query, 'format': 'json', 'polygon_geojson': 1, 'limit': 5}
    headers = {'User-Agent': 'ZoneMonitoring/1.0'}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"    Error: {e}")
    return []


def main():
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        region = conn.execute(text("SELECT id FROM regions WHERE name LIKE '%Свердлов%'")).fetchone()
        region_id = str(region[0])
    
    inserted = 0
    
    for official_name, queries in REMAINING:
        print(f"\n{official_name}:")
        
        found = False
        for q in queries:
            print(f"  Trying: {q}...", end=" ", flush=True)
            results = search_nominatim(q)
            
            for r in results:
                geojson = r.get('geojson')
                if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
                    display = r.get('display_name', '').lower()
                    if 'свердлов' in display:
                        print("Found!")
                        geojson_str = json.dumps(geojson)
                        try:
                            with engine.connect() as conn:
                                conn.execute(text("""
                                    INSERT INTO districts (id, region_id, name, geom, geom_simplified, created_at)
                                    VALUES (:id, :rid, :name,
                                            ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                                            ST_SimplifyPreserveTopology(
                                                ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))), 0.005),
                                            NOW())
                                """), {'id': str(uuid4()), 'rid': region_id, 'name': official_name, 'geojson': geojson_str})
                                conn.commit()
                            inserted += 1
                            print(f"  -> Saved!")
                        except Exception as e:
                            print(f"  -> DB error: {str(e)[:50]}")
                        found = True
                        break
            
            if found:
                break
            print("no match")
            time.sleep(1.1)
        
        if not found:
            print("  -> NOT FOUND")
        
        time.sleep(1.1)
    
    print(f"\nInserted: {inserted}/{len(REMAINING)}")
    
    with engine.connect() as conn:
        count = conn.execute(text(
            "SELECT COUNT(*) FROM districts d JOIN regions r ON d.region_id = r.id WHERE r.name LIKE '%Свердлов%'"
        )).scalar()
        print(f"Total Sverdlovsk districts: {count}")


if __name__ == "__main__":
    main()
