"""Fix DNR and LNR district geometry - reload from Overpass/Nominatim"""
import sys, os, json, requests, time

os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def find_region_osm_id(region_name):
    """Find OSM relation ID for a region via Nominatim."""
    params = {'q': f"{region_name}, Россия", 'format': 'json', 'limit': 5}
    resp = requests.get("https://nominatim.openstreetmap.org/search",
                       params=params, headers=HEADERS, timeout=30)
    for r in resp.json():
        if r.get('osm_type') == 'relation' and r.get('class') == 'boundary':
            return int(r['osm_id'])
    return None


def get_children_relations(parent_osm_id):
    """Get all admin_level 6 children via Overpass."""
    area_id = 3600000000 + parent_osm_id
    query = f"""
[out:json][timeout:120];
area({area_id})->.searchArea;
(
  relation["boundary"="administrative"]["admin_level"="6"](area.searchArea);
);
out tags;
"""
    for server in OVERPASS_SERVERS:
        try:
            resp = requests.post(server, data={'data': query}, headers=HEADERS, timeout=120)
            if resp.status_code == 200:
                return resp.json().get('elements', [])
        except:
            pass
        time.sleep(3)
    return []


def download_geometry(osm_id):
    """Download geometry for an OSM relation via Nominatim."""
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {
        'osm_ids': f'R{osm_id}',
        'format': 'geojson',
        'polygon_geojson': 1,
        'polygon_threshold': 0
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('features'):
                geom = data['features'][0]['geometry']
                return geom
    except Exception as e:
        print(f"      Download error: {e}")
    return None


def reload_region_districts(region_name):
    """Full reload of districts for a region."""
    print(f"\n{'='*60}")
    print(f"Processing: {region_name}")
    print(f"{'='*60}")
    
    # Find region in DB
    with ENGINE.connect() as c:
        row = c.execute(text("SELECT id FROM regions WHERE name = :name"),
                       {'name': region_name}).fetchone()
    if not row:
        print(f"  Region not found in DB!")
        return
    region_id = str(row[0])
    
    # Find OSM ID
    osm_id = find_region_osm_id(region_name)
    print(f"  OSM ID: R{osm_id}")
    time.sleep(1.1)
    
    if not osm_id:
        print(f"  Could not find OSM ID!")
        return
    
    # Get children
    children = get_children_relations(osm_id)
    print(f"  Found {len(children)} admin_level=6 districts")
    time.sleep(2)
    
    if not children:
        print(f"  No children found!")
        return
    
    # Delete old districts
    with ENGINE.begin() as c:
        deleted = c.execute(text("DELETE FROM districts WHERE region_id = :rid"),
                          {'rid': region_id}).rowcount
        print(f"  Deleted {deleted} old districts")
    
    # Download and insert each district
    from uuid import uuid4
    
    loaded = 0
    failed = 0
    for el in children:
        tags = el.get('tags', {})
        name = tags.get('name', '')
        rel_id = el['id']
        
        if not name:
            continue
        
        # Transform name
        import re
        if name.startswith('город '):
            name = 'городской округ ' + name[6:]
        
        print(f"  Loading R{rel_id}: {name}...", end=' ')
        
        geom = download_geometry(rel_id)
        time.sleep(1.1)
        
        if geom:
            geom_type = geom['type']
            if geom_type == 'Polygon':
                geom = {'type': 'MultiPolygon', 'coordinates': [geom['coordinates']]}
            
            geom_json = json.dumps(geom)
            
            with ENGINE.begin() as c:
                c.execute(text("""
                    INSERT INTO districts (id, region_id, name, geom, geom_simplified, created_at)
                    VALUES (:id, :rid, :name,
                            ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326))),
                            ST_SimplifyPreserveTopology(
                                ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326))), 0.005),
                            NOW())
                """), {'id': str(uuid4()), 'rid': region_id, 'name': name, 'gj': geom_json})
            
            loaded += 1
            print("OK")
        else:
            # Insert without geometry
            with ENGINE.begin() as c:
                c.execute(text("""
                    INSERT INTO districts (id, region_id, name, created_at)
                    VALUES (:id, :rid, :name, NOW())
                """), {'id': str(uuid4()), 'rid': region_id, 'name': name})
            failed += 1
            print("NO GEOM")
    
    print(f"\n  Result: {loaded} loaded, {failed} no geometry")
    
    # Verify
    with ENGINE.connect() as c:
        total_area = c.execute(text("""
            SELECT COUNT(*), COALESCE(SUM(ST_Area(geom::geography)/1e6), 0)
            FROM districts WHERE region_id = :rid
        """), {'rid': region_id}).fetchone()
        print(f"  Total: {total_area[0]} districts, {total_area[1]:.0f} km2")


# Fix both regions with known OSM IDs
KNOWN_IDS = {
    'Донецкая Народная Республика': 71973,
    'Луганская Народная Республика': 71971,
}

def reload_with_known_id(region_name, osm_id):
    """Reload using known OSM ID."""
    print(f"\n{'='*60}")
    print(f"Processing: {region_name} (R{osm_id})")
    print(f"{'='*60}")
    
    with ENGINE.connect() as c:
        row = c.execute(text("SELECT id FROM regions WHERE name = :name"),
                       {'name': region_name}).fetchone()
    if not row:
        print(f"  Region not found in DB!")
        return
    region_id = str(row[0])
    
    children = get_children_relations(osm_id)
    print(f"  Found {len(children)} admin_level=6 districts")
    time.sleep(2)
    
    if not children:
        print(f"  No children found!")
        return
    
    with ENGINE.begin() as c:
        deleted = c.execute(text("DELETE FROM districts WHERE region_id = :rid"),
                          {'rid': region_id}).rowcount
        print(f"  Deleted {deleted} old districts")
    
    from uuid import uuid4
    import re as re_mod
    
    loaded = 0
    failed = 0
    for el in children:
        tags = el.get('tags', {})
        name = tags.get('name', '')
        rel_id = el['id']
        
        if not name:
            continue
        
        if name.startswith('город '):
            name = 'городской округ ' + name[6:]
        
        print(f"  Loading R{rel_id}: {name}...", end=' ', flush=True)
        
        geom = download_geometry(rel_id)
        time.sleep(1.1)
        
        if geom:
            if geom['type'] == 'Polygon':
                geom = {'type': 'MultiPolygon', 'coordinates': [geom['coordinates']]}
            
            geom_json = json.dumps(geom)
            
            with ENGINE.begin() as c:
                c.execute(text("""
                    INSERT INTO districts (id, region_id, name, geom, geom_simplified, created_at)
                    VALUES (:id, :rid, :name,
                            ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326))),
                            ST_SimplifyPreserveTopology(
                                ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326))), 0.005),
                            NOW())
                """), {'id': str(uuid4()), 'rid': region_id, 'name': name, 'gj': geom_json})
            
            loaded += 1
            print("OK")
        else:
            with ENGINE.begin() as c:
                c.execute(text("""
                    INSERT INTO districts (id, region_id, name, created_at)
                    VALUES (:id, :rid, :name, NOW())
                """), {'id': str(uuid4()), 'rid': region_id, 'name': name})
            failed += 1
            print("NO GEOM")
    
    print(f"\n  Result: {loaded} loaded, {failed} no geometry")
    
    with ENGINE.connect() as c:
        total_area = c.execute(text("""
            SELECT COUNT(*), COALESCE(SUM(ST_Area(geom::geography)/1e6), 0)
            FROM districts WHERE region_id = :rid
        """), {'rid': region_id}).fetchone()
        print(f"  Total: {total_area[0]} districts, {total_area[1]:.0f} km2")


for region_name, osm_id in KNOWN_IDS.items():
    reload_with_known_id(region_name, osm_id)
    time.sleep(5)

print("\nAll done!")
