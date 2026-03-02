"""Fix remaining duplicate districts with exact region search."""
import sys
import time
import json
import requests
from sqlalchemy import create_engine, text

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from app.core.config import settings


def get_engine():
    return create_engine(settings.DATABASE_URL)


def search_nominatim(query):
    """Search Nominatim."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': query,
        'format': 'json',
        'polygon_geojson': 1,
        'limit': 10,
    }
    headers = {'User-Agent': 'ZoneMonitoring/1.0'}
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"    Error: {e}")
    return []


def update_geometry(engine, district_id, geojson):
    """Update district geometry."""
    geojson_str = json.dumps(geojson)
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE districts
            SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                geom_simplified = ST_SimplifyPreserveTopology(
                    ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                    0.01
                )
            WHERE id = :id
        """), {'geojson': geojson_str, 'id': str(district_id)})
        conn.commit()


def main():
    engine = get_engine()
    
    # Get duplicate groups
    with engine.connect() as conn:
        dupes = conn.execute(text("""
            WITH geom_hashes AS (
                SELECT d.id, d.name, r.name as region_name, 
                       MD5(ST_AsBinary(d.geom)::text) as hash
                FROM districts d
                JOIN regions r ON d.region_id = r.id
                WHERE d.geom IS NOT NULL
            ),
            dup_hashes AS (
                SELECT hash FROM geom_hashes GROUP BY hash HAVING COUNT(*) > 1
            )
            SELECT gh.id, gh.name, gh.region_name
            FROM geom_hashes gh
            WHERE gh.hash IN (SELECT hash FROM dup_hashes)
              AND gh.name NOT LIKE '%ЛНР%'
              AND gh.region_name NOT LIKE '%Луганск%'
            ORDER BY gh.region_name, gh.name
        """)).fetchall()
    
    print(f"Дубликатов для исправления: {len(dupes)}")
    
    for d_id, d_name, r_name in dupes:
        print(f"\n{r_name} -> {d_name}")
        
        clean = d_name.replace('муниципальный район', '').strip()
        
        # Very specific search
        queries = [
            f"{clean} район {r_name}",
            f'"{clean}" район "{r_name}"',
        ]
        
        for q in queries:
            print(f"  Trying: {q[:60]}...", end=" ")
            results = search_nominatim(q)
            
            # Find result that matches region
            for r in results:
                geojson = r.get('geojson')
                if not geojson or geojson.get('type') not in ('Polygon', 'MultiPolygon'):
                    continue
                
                display = r.get('display_name', '').lower()
                region_key = r_name.lower().replace('область', '').replace('край', '').replace('республика', '').strip()
                
                # Check if region is in display name
                if any(w in display for w in region_key.split() if len(w) > 3):
                    print("Found!")
                    try:
                        update_geometry(engine, d_id, geojson)
                        print("  -> Updated")
                    except Exception as e:
                        print(f"  -> Error: {e}")
                    break
            else:
                print("no match")
                time.sleep(1.1)
                continue
            break
        else:
            print("  -> NOT FOUND")
        
        time.sleep(1.1)


if __name__ == "__main__":
    main()
