"""
Reload ALL districts for ALL regions from OpenStreetMap.
Approach:
  1. For each region, get admin_level=6 relation IDs from Overpass (fast, no geometry)
  2. Download each polygon from Nominatim by OSM relation ID (always correct)

Usage:
  python scripts/reload_all_districts_osm.py          # all regions
  python scripts/reload_all_districts_osm.py --skip=N  # skip first N regions
  python scripts/reload_all_districts_osm.py --only="Название"  # only one region
"""
import sys
import json
import time
import requests
import argparse
from uuid import uuid4

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

# Regions that need special OSM area names (different from DB name)
REGION_OSM_NAMES = {
    "город Москва": "Москва",
    "город Санкт-Петербург": "Санкт-Петербург",
    "город Севастополь": "Севастополь",
    "Ханты-Мансийский автономный округ — Югра": "Ханты-Мансийский автономный округ — Югра",
    "Ямало-Ненецкий автономный округ": "Ямало-Ненецкий автономный округ",
    "Ненецкий автономный округ": "Ненецкий автономный округ",
    "Чукотский автономный округ": "Чукотский автономный округ",
}

# Regions where admin_level might differ
REGION_ADMIN_LEVELS = {
    "город Москва": "5|6|8",
    "город Санкт-Петербург": "5|6|8",
    "город Севастополь": "5|6|8",
}

ENGINE = None

def get_engine():
    global ENGINE
    if ENGINE is None:
        ENGINE = create_engine(settings.DATABASE_URL)
    return ENGINE


def get_all_regions():
    """Get all regions from DB."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, name FROM regions ORDER BY name")).fetchall()
    return [(str(r[0]), r[1]) for r in rows]


def get_osm_relations(region_name):
    """Get admin_level=6 relation IDs within a region from Overpass."""
    osm_name = REGION_OSM_NAMES.get(region_name, region_name)
    admin_levels = REGION_ADMIN_LEVELS.get(region_name, "6")
    
    query = f"""
[out:json][timeout:60];
area["name"="{osm_name}"]["admin_level"="4"]->.region;
relation["boundary"="administrative"]["admin_level"~"^({admin_levels})$"](area.region);
out tags;
"""
    
    url = "https://overpass-api.de/api/interpreter"
    
    try:
        resp = requests.post(url, data={'data': query}, timeout=90)
        if resp.status_code != 200:
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
        
        return result
    except Exception as e:
        print(f"    Overpass error: {e}")
        return None


def download_polygon(osm_id):
    """Download polygon from Nominatim by OSM relation ID."""
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
        pass
    
    return None


def insert_district(region_id, name, geojson):
    """Insert district into DB."""
    engine = get_engine()
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
            'id': str(uuid4()),
            'rid': region_id,
            'name': name,
            'geojson': geojson_str,
        })
        conn.commit()


def clear_districts(region_id):
    """Clear existing districts for region."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM districts WHERE region_id = :rid"), {"rid": region_id})
        conn.commit()


def process_region(region_id, region_name):
    """Process one region: get relations, download geometry, insert."""
    
    # Step 1: Get relation IDs from Overpass
    relations = get_osm_relations(region_name)
    
    if relations is None:
        print(f"    Overpass failed!")
        return 0, -1
    
    if not relations:
        # Try with admin_level 5 as fallback (for federal cities, etc.)
        print(f"    No level 6, trying level 5...")
        osm_name = REGION_OSM_NAMES.get(region_name, region_name)
        query = f"""
[out:json][timeout:60];
area["name"="{osm_name}"]["admin_level"="4"]->.region;
relation["boundary"="administrative"]["admin_level"~"^(5|7|8)$"](area.region);
out tags;
"""
        try:
            url = "https://overpass-api.de/api/interpreter"
            resp = requests.post(url, data={'data': query}, timeout=90)
            if resp.status_code == 200:
                data = resp.json()
                for el in data.get('elements', []):
                    tags = el.get('tags', {})
                    name = tags.get('name', '')
                    osm_id = el.get('id')
                    if name and osm_id:
                        if not relations:
                            relations = []
                        relations.append({'osm_id': osm_id, 'name': name})
        except:
            pass
    
    if not relations:
        print(f"    No districts found in OSM!")
        return 0, 0
    
    print(f"    Found {len(relations)} districts in OSM")
    
    # Step 2: Clear existing districts
    clear_districts(region_id)
    
    # Step 3: Download and insert
    inserted = 0
    
    for rel in relations:
        geojson = download_polygon(rel['osm_id'])
        
        if geojson:
            try:
                insert_district(region_id, rel['name'], geojson)
                inserted += 1
            except Exception as e:
                pass
        
        time.sleep(1.1)  # Rate limit
    
    return inserted, len(relations)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip', type=int, default=0, help='Skip first N regions')
    parser.add_argument('--only', type=str, default=None, help='Process only this region')
    args = parser.parse_args()
    
    regions = get_all_regions()
    print(f"Total regions in DB: {len(regions)}")
    
    if args.only:
        regions = [(rid, rname) for rid, rname in regions if args.only.lower() in rname.lower()]
        if not regions:
            print(f"Region '{args.only}' not found!")
            return
    
    if args.skip > 0:
        print(f"Skipping first {args.skip} regions")
        regions = regions[args.skip:]
    
    print(f"Processing {len(regions)} regions\n")
    print("=" * 70)
    
    total_inserted = 0
    total_osm = 0
    failed_regions = []
    
    for i, (region_id, region_name) in enumerate(regions):
        print(f"\n[{i+1}/{len(regions)}] {region_name}")
        
        inserted, osm_count = process_region(region_id, region_name)
        
        if osm_count < 0:
            print(f"    FAILED (Overpass error)")
            failed_regions.append((region_name, "overpass error"))
        elif osm_count == 0:
            print(f"    EMPTY (no districts in OSM)")
            failed_regions.append((region_name, "empty"))
        else:
            print(f"    OK: {inserted}/{osm_count}")
            total_inserted += inserted
            total_osm += osm_count
        
        # Small pause between regions to not overload Overpass
        time.sleep(2)
    
    print(f"\n{'='*70}")
    print(f"TOTAL: {total_inserted}/{total_osm} districts loaded")
    
    if failed_regions:
        print(f"\nFailed regions ({len(failed_regions)}):")
        for name, reason in failed_regions:
            print(f"  {name}: {reason}")
    
    # Final stats
    engine = get_engine()
    with engine.connect() as conn:
        stats = conn.execute(text("""
            SELECT r.name, COUNT(d.id) as cnt
            FROM regions r
            LEFT JOIN districts d ON d.region_id = r.id
            GROUP BY r.name
            ORDER BY cnt, r.name
        """)).fetchall()
    
    print(f"\nRegions with fewest districts:")
    for name, cnt in stats[:10]:
        print(f"  {name}: {cnt}")


if __name__ == "__main__":
    main()
