"""
Upgrade geometry quality for districts by re-downloading from Nominatim
with polygon_threshold=0 for maximum detail.

First test on Arkhangelsk, then can be applied to all regions.
"""
import sys, os, json, time, requests
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}


def get_osm_id_for_district(district_name, region_name):
    """Find OSM relation ID for a district via Nominatim search."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': f'{district_name}, {region_name}',
        'format': 'json',
        'limit': 3,
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            for r in resp.json():
                if r.get('osm_type') == 'relation':
                    return int(r['osm_id'])
    except:
        pass
    return None


def download_hq_polygon(osm_id):
    """Download high-quality polygon from Nominatim with polygon_threshold=0."""
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {
        'osm_ids': f'R{osm_id}',
        'format': 'json',
        'polygon_geojson': 1,
        'polygon_threshold': 0.0,  # Maximum detail!
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                geojson = data[0].get('geojson')
                if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
                    return geojson
    except Exception as e:
        print(f"    Error: {e}")
    return None


def count_geojson_points(geojson):
    """Count points in a GeoJSON geometry."""
    count = 0
    def process(coords):
        nonlocal count
        if isinstance(coords[0], (int, float)):
            count += 1
        else:
            for item in coords:
                process(item)
    process(geojson['coordinates'])
    return count


def upgrade_region(region_name):
    """Upgrade geometry for all districts in a region."""
    print(f"\n{'='*60}")
    print(f"Upgrading: {region_name}")
    
    with ENGINE.connect() as c:
        rid = c.execute(text(
            "SELECT id FROM regions WHERE name = :n"
        ), {"n": region_name}).fetchone()
        if not rid:
            print(f"  Region not found!")
            return
        region_id = str(rid[0])
        
        districts = c.execute(text(
            "SELECT id, name, ST_NPoints(geom) as pts "
            "FROM districts WHERE region_id = :rid AND geom IS NOT NULL "
            "ORDER BY name"
        ), {"rid": region_id}).fetchall()
    
    print(f"  Districts: {len(districts)}")
    
    # First, get OSM relation IDs via Overpass
    # Use the same approach as fix_final_9.py
    from fix_final_9 import KNOWN_REGION_IDS
    
    # Try Overpass to get relation IDs for all districts at once
    region_osm_id = None
    # Search Nominatim for region OSM ID
    url = "https://nominatim.openstreetmap.org/search"
    params = {'q': f'{region_name}, Россия', 'format': 'json', 'limit': 3}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        for r in resp.json():
            if r['osm_type'] == 'relation':
                region_osm_id = int(r['osm_id'])
                break
    except:
        pass
    
    time.sleep(1.1)
    
    osm_ids = {}  # district_name -> osm_id
    
    if region_osm_id:
        area_id = 3600000000 + region_osm_id
        query = f"""
[out:json][timeout:120];
area({area_id})->.region;
relation["boundary"="administrative"]["admin_level"~"^(5|6|7)$"](area.region);
out tags;
"""
        try:
            resp = requests.post("https://overpass-api.de/api/interpreter",
                               data={'data': query}, timeout=150)
            if resp.status_code == 200:
                elements = resp.json().get('elements', [])
                for el in elements:
                    name = el.get('tags', {}).get('name', '')
                    if name:
                        osm_ids[name] = el['id']
                print(f"  Overpass found {len(osm_ids)} relations")
        except Exception as e:
            print(f"  Overpass error: {e}")
    
    # Now upgrade each district
    upgraded = 0
    for did, dname, old_pts in districts:
        did = str(did)
        
        # Find OSM ID
        osm_id = osm_ids.get(dname)
        
        # Try fuzzy match if exact match failed
        if not osm_id:
            dname_lower = dname.lower()
            for oname, oid in osm_ids.items():
                if oname.lower() in dname_lower or dname_lower in oname.lower():
                    osm_id = oid
                    break
        
        if not osm_id:
            # Try Nominatim search as fallback
            osm_id = get_osm_id_for_district(dname, region_name)
            time.sleep(1.1)
        
        if not osm_id:
            print(f"  SKIP {dname} (no OSM ID)")
            continue
        
        # Download HQ polygon
        geojson = download_hq_polygon(osm_id)
        if not geojson:
            print(f"  SKIP {dname} (no HQ polygon)")
            time.sleep(1.1)
            continue
        
        new_pts = count_geojson_points(geojson)
        
        if new_pts <= old_pts:
            print(f"  SAME {dname}: {old_pts} -> {new_pts} pts")
            time.sleep(1.1)
            continue
        
        # Update geometry
        try:
            with ENGINE.connect() as c:
                c.execute(text("""
                    UPDATE districts SET
                        geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                        geom_simplified = ST_SimplifyPreserveTopology(
                            ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))), 0.005)
                    WHERE id = :id
                """), {"geojson": json.dumps(geojson), "id": did})
                c.commit()
            upgraded += 1
            print(f"  OK   {dname}: {old_pts} -> {new_pts} pts (+{new_pts-old_pts})")
        except Exception as e:
            print(f"  ERR  {dname}: {e}")
        
        time.sleep(1.1)
    
    print(f"\n  Upgraded: {upgraded}/{len(districts)}")
    
    # Show new stats
    with ENGINE.connect() as c:
        rows = c.execute(text(
            "SELECT name, ST_NPoints(geom) "
            "FROM districts WHERE region_id = :rid AND geom IS NOT NULL "
            "ORDER BY ST_NPoints(geom)"
        ), {"rid": region_id}).fetchall()
    
    print(f"  New point counts:")
    for name, pts in rows:
        print(f"    {pts:>6d} pts  {name}")


def main():
    # Test on Arkhangelsk first
    upgrade_region("Архангельская область")
    
    # Final check
    with ENGINE.connect() as c:
        stats = c.execute(text("SELECT COUNT(id), COUNT(geom) FROM districts")).fetchone()
    print(f"\nOverall: {stats[0]} districts, {stats[1]} with geometry")


if __name__ == "__main__":
    main()
