"""Load remaining district geometries via Nominatim with region context."""
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
        'limit': 5,
    }
    headers = {'User-Agent': 'ZoneMonitoring/1.0'}
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"    Error: {e}")
    return []


def find_polygon(results, region_hint=None):
    """Find best polygon from results."""
    for r in results:
        geojson = r.get('geojson')
        if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
            # If we have a region hint, prefer results that mention it
            if region_hint:
                display = r.get('display_name', '').lower()
                hint_words = region_hint.lower().replace('область', '').replace('край', '').replace('республика', '').strip().split()
                if any(w in display for w in hint_words if len(w) > 3):
                    return geojson
    
    # Return first polygon if no region match
    for r in results:
        geojson = r.get('geojson')
        if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
            return geojson
    
    return None


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
    print("Загрузка оставшихся районов через Nominatim...")
    
    engine = get_engine()
    
    # Get districts without proper geometry (check for duplicates)
    with engine.connect() as conn:
        missing = conn.execute(text("""
            WITH geom_hashes AS (
                SELECT id, MD5(ST_AsBinary(geom)::text) as hash
                FROM districts WHERE geom IS NOT NULL
            ),
            duplicate_hashes AS (
                SELECT hash FROM geom_hashes GROUP BY hash HAVING COUNT(*) > 1
            )
            SELECT d.id, d.name, r.name as region_name
            FROM districts d
            JOIN regions r ON d.region_id = r.id
            LEFT JOIN geom_hashes gh ON d.id = gh.id
            WHERE d.geom IS NULL 
               OR gh.hash IN (SELECT hash FROM duplicate_hashes)
            ORDER BY r.name, d.name
        """)).fetchall()
    
    print(f"Районов для загрузки: {len(missing)}")
    
    updated = 0
    failed = []
    
    for i, (d_id, d_name, r_name) in enumerate(missing):
        print(f"[{i+1}/{len(missing)}] {d_name[:50]}...", end=" ", flush=True)
        
        clean_name = d_name.replace('муниципальный район', '').replace('городской округ', '').strip()
        
        # Try queries with increasing specificity
        queries = [
            f"{clean_name} район, {r_name}, Россия",
            f"{clean_name}, {r_name}, Россия",
            f"{d_name}, {r_name}",
            f"{clean_name} район, Россия",
            f"{clean_name}, Россия",
        ]
        
        geojson = None
        for q in queries:
            results = search_nominatim(q)
            geojson = find_polygon(results, r_name)
            if geojson:
                break
            time.sleep(1.1)
        
        if geojson:
            try:
                update_geometry(engine, d_id, geojson)
                print("OK")
                updated += 1
            except Exception as e:
                print(f"DB error")
                failed.append((r_name, d_name))
        else:
            print("not found")
            failed.append((r_name, d_name))
    
    print(f"\nОбновлено: {updated}")
    print(f"Не найдено: {len(failed)}")
    
    if failed:
        print("\nНе найдено:")
        for r, d in failed[:30]:
            print(f"  {r} -> {d}")


if __name__ == "__main__":
    main()
