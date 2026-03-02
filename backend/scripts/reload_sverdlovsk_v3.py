"""
Reload Sverdlovsk Oblast districts - correct approach:
1. Get all admin_level=6 relation IDs from Overpass (fast, no geometry)
2. Download each polygon from Nominatim by OSM ID (always correct)
"""
import sys
import json
import time
import requests
from uuid import uuid4

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings


def get_relation_ids():
    """Get all admin_level=6 relations within Sverdlovsk Oblast - just IDs and names."""
    print("Step 1: Getting relation IDs from Overpass (no geometry)...")
    
    query = """
[out:json][timeout:60];
area["name"="Свердловская область"]["admin_level"="4"]->.region;
relation["boundary"="administrative"]["admin_level"="6"](area.region);
out tags;
"""
    
    url = "https://overpass-api.de/api/interpreter"
    resp = requests.post(url, data={'data': query}, timeout=90)
    
    if resp.status_code != 200:
        print(f"  Error: {resp.status_code}")
        return None
    
    data = resp.json()
    elements = data.get('elements', [])
    
    result = []
    for el in elements:
        tags = el.get('tags', {})
        name = tags.get('name', '')
        osm_id = el.get('id')
        if name and osm_id:
            result.append({'osm_id': osm_id, 'name': name})
    
    print(f"  Found {len(result)} relations")
    return result


def download_polygon_by_osm_id(osm_id):
    """Download polygon from Nominatim by exact OSM relation ID."""
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {
        'osm_ids': f'R{osm_id}',
        'format': 'json',
        'polygon_geojson': 1,
    }
    headers = {'User-Agent': 'ZoneMonitoring/1.0'}
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                geojson = data[0].get('geojson')
                if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
                    return geojson
    except Exception as e:
        print(f"    Error: {e}")
    
    return None


def main():
    print("=" * 60)
    print("Reload Sverdlovsk Oblast from OSM (by relation IDs)")
    print("=" * 60)
    
    # Step 1: Get relation IDs
    relations = get_relation_ids()
    if not relations:
        print("Failed to get relations!")
        return
    
    print("\nDistricts found in OSM:")
    for r in sorted(relations, key=lambda x: x['name']):
        print(f"  R{r['osm_id']}: {r['name']}")
    
    # Step 2: Connect to DB
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        region = conn.execute(text("SELECT id FROM regions WHERE name LIKE '%Свердлов%'")).fetchone()
        if not region:
            print("Region not found!")
            return
        region_id = str(region[0])
        
        # Clear existing
        conn.execute(text("DELETE FROM districts WHERE region_id = :rid"), {"rid": region_id})
        conn.commit()
        print(f"\nCleared existing districts")
    
    # Step 3: Download and insert each polygon
    print(f"\nStep 2: Downloading {len(relations)} polygons from Nominatim...")
    
    inserted = 0
    failed = []
    
    for i, rel in enumerate(sorted(relations, key=lambda x: x['name'])):
        name = rel['name']
        osm_id = rel['osm_id']
        
        print(f"[{i+1}/{len(relations)}] R{osm_id} {name}...", end=" ", flush=True)
        
        geojson = download_polygon_by_osm_id(osm_id)
        
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
                        'name': name,
                        'geojson': geojson_str,
                    })
                    conn.commit()
                inserted += 1
                print("OK")
            except Exception as e:
                print(f"DB error: {str(e)[:50]}")
                failed.append(name)
        else:
            print("no polygon")
            failed.append(name)
        
        time.sleep(1.1)  # Rate limit
    
    print(f"\n{'='*60}")
    print(f"Inserted: {inserted}/{len(relations)}")
    
    if failed:
        print(f"\nFailed ({len(failed)}):")
        for name in failed:
            print(f"  - {name}")
    
    with engine.connect() as conn:
        count = conn.execute(text(
            "SELECT COUNT(*) FROM districts d JOIN regions r ON d.region_id=r.id WHERE r.name LIKE '%Свердлов%'"
        )).scalar()
        print(f"\nTotal in DB: {count}")


if __name__ == "__main__":
    main()
