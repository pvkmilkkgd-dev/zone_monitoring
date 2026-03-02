"""
Fix the remaining regions:
1. Запорожская, Херсонская - try Nominatim search
2. Check if regions with few districts need more
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

ENGINE = create_engine(settings.DATABASE_URL)

HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

# Known districts for new territories from official sources
NEW_TERRITORIES = {
    "Запорожская область": [
        "Бердянский район", "Васильевский район", "Мелитопольский район",
        "Пологовский район", "Запорожский район",
    ],
    "Херсонская область": [
        "Бериславский район", "Генический район", "Каховский район",
        "Скадовский район", "Херсонский район",
    ],
}


def search_nominatim(query):
    """Search Nominatim."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': query,
        'format': 'json',
        'polygon_geojson': 1,
        'limit': 5,
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return []


def get_region_id(region_name):
    with ENGINE.connect() as conn:
        row = conn.execute(
            text("SELECT id FROM regions WHERE name = :name"),
            {"name": region_name}
        ).fetchone()
    return str(row[0]) if row else None


def insert_district(region_id, name, geojson):
    geojson_str = json.dumps(geojson)
    with ENGINE.connect() as conn:
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
            'name': name,
            'geojson': geojson_str,
        })
        conn.commit()


def main():
    for region_name, districts in NEW_TERRITORIES.items():
        print(f"\n{region_name}")
        region_id = get_region_id(region_name)
        if not region_id:
            print(f"  Region not found in DB!")
            continue
        
        # Clear existing
        with ENGINE.connect() as conn:
            conn.execute(text("DELETE FROM districts WHERE region_id = :rid"), {"rid": region_id})
            conn.commit()
        
        inserted = 0
        for district_name in districts:
            queries = [
                f"{district_name}, {region_name}, Россия",
                f"{district_name}, {region_name}, Украина",
                f"{district_name}, {region_name}",
            ]
            
            found = False
            for q in queries:
                results = search_nominatim(q)
                time.sleep(1.1)
                
                for r in results:
                    geojson = r.get('geojson')
                    if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
                        try:
                            insert_district(region_id, district_name, geojson)
                            inserted += 1
                            found = True
                            print(f"  + {district_name}")
                        except Exception as e:
                            print(f"  ! {district_name}: {e}")
                        break
                
                if found:
                    break
            
            if not found:
                # Insert without geometry
                with ENGINE.connect() as conn:
                    conn.execute(text("""
                        INSERT INTO districts (id, region_id, name, created_at)
                        VALUES (:id, :rid, :name, NOW())
                    """), {
                        'id': str(uuid4()),
                        'rid': region_id,
                        'name': district_name,
                    })
                    conn.commit()
                print(f"  - {district_name} (no geometry)")
        
        print(f"  Total: {inserted}/{len(districts)}")
    
    # Final stats for all regions
    print(f"\n{'='*60}")
    with ENGINE.connect() as conn:
        stats = conn.execute(text("""
            SELECT r.name, 
                   COUNT(d.id) as total,
                   COUNT(d.geom) as with_geom
            FROM regions r
            LEFT JOIN districts d ON d.region_id = r.id
            GROUP BY r.name
            ORDER BY total, r.name
        """)).fetchall()
    
    total_districts = 0
    total_with_geom = 0
    for name, cnt, geom_cnt in stats:
        total_districts += cnt
        total_with_geom += geom_cnt
        if cnt < 5:
            print(f"  {cnt:4d} ({geom_cnt:4d} geom)  {name}")
    
    print(f"\nTotal: {total_districts} districts, {total_with_geom} with geometry")


if __name__ == "__main__":
    main()
