"""
Reload Sverdlovsk Oblast districts - download from Overpass by individual districts.
Uses lighter queries - just getting the relation by name, then geometry.
"""
import sys
import json
import time
import requests
from uuid import uuid4

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

# Official list with OSM search names
DISTRICTS = [
    # (official_name, osm_search_name)
    # 30 rayonov
    ("Алапаевский район", "Алапаевский район"),
    ("Артёмовский район", "Артёмовский район"),
    ("Артинский район", "Артинский район"),
    ("Ачитский район", "Ачитский район"),
    ("Байкаловский район", "Байкаловский район"),
    ("Белоярский район", "Белоярский район"),
    ("Богдановичский район", "Богдановичский район"),
    ("Верхнесалдинский район", "Верхнесалдинский район"),
    ("Верхотурский район", "Верхотурский район"),
    ("Гаринский район", "Гаринский район"),
    ("Ирбитский район", "Ирбитский район"),
    ("Каменский район", "Каменский район"),
    ("Камышловский район", "Камышловский район"),
    ("Красноуфимский район", "Красноуфимский район"),
    ("Невьянский район", "Невьянский район"),
    ("Нижнесергинский район", "Нижнесергинский район"),
    ("Новолялинский район", "Новолялинский район"),
    ("Пригородный район", "Пригородный район"),
    ("Пышминский район", "Пышминский район"),
    ("Режевский район", "Режевский район"),
    ("Серовский район", "Серовский район"),
    ("Слободо-Туринский район", "Слободо-Туринский район"),
    ("Сухоложский район", "Сухоложский район"),
    ("Сысертский район", "Сысертский район"),
    ("Таборинский район", "Таборинский район"),
    ("Тавдинский район", "Тавдинский район"),
    ("Талицкий район", "Талицкий район"),
    ("Тугулымский район", "Тугулымский район"),
    ("Туринский район", "Туринский район"),
    ("Шалинский район", "Шалинский район"),
    # 25 gorodov
    ("город Алапаевск", "Алапаевск"),
    ("город Асбест", "Асбест"),
    ("город Берёзовский", "Берёзовский"),
    ("город Верхняя Пышма", "Верхняя Пышма"),
    ("город Екатеринбург", "Екатеринбург"),
    ("город Заречный", "Заречный"),
    ("город Ивдель", "Ивдель"),
    ("город Ирбит", "Ирбит"),
    ("город Каменск-Уральский", "Каменск-Уральский"),
    ("город Камышлов", "Камышлов"),
    ("город Карпинск", "Карпинск"),
    ("город Качканар", "Качканар"),
    ("город Кировград", "Кировград"),
    ("город Краснотурьинск", "Краснотурьинск"),
    ("город Красноуральск", "Красноуральск"),
    ("город Красноуфимск", "Красноуфимск"),
    ("город Кушва", "Кушва"),
    ("город Нижний Тагил", "Нижний Тагил"),
    ("город Нижняя Салда", "Нижняя Салда"),
    ("город Нижняя Тура", "Нижняя Тура"),
    ("город Первоуральск", "Первоуральск"),
    ("город Полевской", "Полевской"),
    ("город Ревда", "Ревда"),
    ("город Североуральск", "Североуральск"),
    ("город Серов", "Серов"),
    # 4 ZATO
    ("ЗАТО город Лесной", "Лесной"),
    ("ЗАТО город Новоуральск", "Новоуральск"),
    ("ЗАТО посёлок Свободный", "Свободный"),
    ("ЗАТО посёлок Уральский", "Уральский"),
]


def search_nominatim(name, region="Свердловская область"):
    """Search Nominatim for district boundary."""
    url = "https://nominatim.openstreetmap.org/search"
    headers = {'User-Agent': 'ZoneMonitoring/1.0'}
    
    # Try different queries
    queries = [
        f"{name}, {region}, Россия",
        f"{name} район, {region}",
        f"{name}, {region}",
    ]
    
    for q in queries:
        params = {
            'q': q,
            'format': 'json',
            'polygon_geojson': 1,
            'limit': 5,
        }
        
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            if resp.status_code == 200:
                results = resp.json()
                
                for r in results:
                    geojson = r.get('geojson')
                    if not geojson:
                        continue
                    
                    gtype = geojson.get('type', '')
                    if gtype not in ('Polygon', 'MultiPolygon'):
                        continue
                    
                    # Verify it's in Sverdlovsk
                    display = r.get('display_name', '').lower()
                    if 'свердлов' in display or 'ekaterinburg' in display:
                        return geojson
                    
                    # For cities/ZATO, accept if class matches
                    rclass = r.get('class', '')
                    if rclass == 'boundary' and 'свердлов' not in display:
                        continue
                    
                    return geojson
        except Exception as e:
            print(f"    Error: {e}")
        
        time.sleep(1.1)
    
    return None


def main():
    print("=" * 60)
    print(f"Reload Sverdlovsk Oblast: {len(DISTRICTS)} districts")
    print("=" * 60)
    
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Get region ID
        region = conn.execute(text(
            "SELECT id FROM regions WHERE name LIKE '%Свердлов%'"
        )).fetchone()
        
        if not region:
            print("Region not found!")
            return
        
        region_id = str(region[0])
        
        # Clear existing districts
        conn.execute(text("DELETE FROM districts WHERE region_id = :rid"), {"rid": region_id})
        conn.commit()
        print("Cleared existing districts\n")
    
    # Download and insert each district
    inserted = 0
    failed = []
    
    for i, (official_name, search_name) in enumerate(DISTRICTS):
        pct = (i + 1) * 100 // len(DISTRICTS)
        print(f"[{i+1}/{len(DISTRICTS)} {pct}%] {official_name}...", end=" ", flush=True)
        
        geojson = search_nominatim(search_name)
        
        if geojson:
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
                    """), {
                        'id': str(uuid4()),
                        'rid': region_id,
                        'name': official_name,
                        'geojson': geojson_str,
                    })
                    conn.commit()
                inserted += 1
                print("OK")
            except Exception as e:
                err = str(e)[:50]
                print(f"DB error: {err}")
                failed.append((official_name, err))
        else:
            print("NOT FOUND")
            failed.append((official_name, "not found"))
    
    print(f"\n{'='*60}")
    print(f"Inserted: {inserted}/{len(DISTRICTS)}")
    
    if failed:
        print(f"\nFailed ({len(failed)}):")
        for name, reason in failed:
            print(f"  {name}: {reason}")


if __name__ == "__main__":
    main()
