"""
Fix Еврейская автономная область specifically.
Try multiple approaches to find its districts.
"""
import sys, os, re, json, time, requests
from uuid import uuid4

os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings
from bs4 import BeautifulSoup

ENGINE = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

REGION_NAME = "Еврейская автономная область"
REGION_OSM_ID = 1845454
AREA_ID = 3600000000 + REGION_OSM_ID  # = 3601845454

def try_overpass(query, server="https://overpass-api.de/api/interpreter"):
    try:
        resp = requests.post(server, data={'data': query}, timeout=180)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"    Error: {e}")
    return None


def download_polygon(osm_id):
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {'osm_ids': f'R{osm_id}', 'format': 'json', 'polygon_geojson': 1}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                geojson = data[0].get('geojson')
                if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
                    return geojson
    except:
        pass
    return None


def main():
    print("Fixing Еврейская автономная область")
    
    # Get current state
    with ENGINE.connect() as conn:
        row = conn.execute(text("SELECT id FROM regions WHERE name = :n"), {"n": REGION_NAME}).fetchone()
        region_id = str(row[0])
        
        current = conn.execute(text(
            "SELECT name, geom IS NOT NULL as has_geom FROM districts WHERE region_id = :rid ORDER BY name"
        ), {"rid": region_id}).fetchall()
    
    print(f"Current districts: {len(current)}")
    for name, has_geom in current:
        print(f"  {'OK' if has_geom else 'NO GEOM'} {name}")
    
    # Try approach 1: Direct area query with different admin levels
    print("\nApproach 1: area(id) query")
    for levels in ["6", "5|6", "5|6|7", "4|5|6|7"]:
        query = f"""
[out:json][timeout:120];
area({AREA_ID})->.region;
relation["boundary"="administrative"]["admin_level"~"^({levels})$"](area.region);
out tags;
"""
        print(f"  Trying admin_level={levels}...")
        data = try_overpass(query)
        if data and data.get('elements'):
            print(f"  Found {len(data['elements'])} elements")
            for el in data['elements']:
                tags = el.get('tags', {})
                print(f"    R{el['id']} level={tags.get('admin_level','')} {tags.get('name','')}")
            break
        else:
            print(f"  No results")
    
    # Try approach 2: Direct name search
    print("\nApproach 2: name search")
    query = f"""
[out:json][timeout:120];
area["name"="Еврейская автономная область"]["admin_level"="4"]->.region;
relation["boundary"="administrative"]["admin_level"~"^(5|6|7)$"](area.region);
out tags;
"""
    data = try_overpass(query)
    if data and data.get('elements'):
        print(f"  Found {len(data['elements'])} elements")
        for el in data['elements']:
            tags = el.get('tags', {})
            print(f"    R{el['id']} level={tags.get('admin_level','')} {tags.get('name','')}")
    else:
        print(f"  No results")
    
    # Try approach 3: Search by bbox (EAO is roughly 130-135E, 47-49N)
    print("\nApproach 3: bbox search")
    query = """
[out:json][timeout:120];
relation["boundary"="administrative"]["admin_level"="6"](47.0,130.0,49.5,135.5);
out tags;
"""
    data = try_overpass(query)
    if data and data.get('elements'):
        # Filter to only those within EAO
        eao_elements = []
        for el in data['elements']:
            tags = el.get('tags', {})
            name = tags.get('name', '')
            # Check if it's in EAO by checking if the parent relation is EAO
            if 'район' in name.lower() or 'округ' in name.lower():
                eao_elements.append(el)
        
        print(f"  Found {len(data['elements'])} total, {len(eao_elements)} likely EAO")
        for el in data['elements']:
            tags = el.get('tags', {})
            print(f"    R{el['id']} level={tags.get('admin_level','')} {tags.get('name','')}")
    else:
        print("  No results")
    
    # Try approach 4: Search Nominatim for districts of EAO
    print("\nApproach 4: Nominatim search for known districts")
    # Known districts of EAO from ОКТМО
    known_districts = [
        "Биробиджанский район",
        "Ленинский район",
        "Облученский район",
        "Октябрьский район",
        "Смидовичский район",
        "городской округ Биробиджан",
    ]
    
    found = []
    for dist_name in known_districts:
        search_q = f"{dist_name}, Еврейская автономная область"
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': search_q,
            'format': 'json',
            'polygon_geojson': 1,
            'limit': 3,
        }
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                results = resp.json()
                for r in results:
                    geojson = r.get('geojson')
                    if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
                        print(f"  Found: {dist_name} -> {r.get('display_name','')[:60]}")
                        found.append({'name': dist_name, 'geojson': geojson})
                        break
                else:
                    print(f"  No polygon: {dist_name}")
            else:
                print(f"  HTTP {resp.status_code}: {dist_name}")
        except Exception as e:
            print(f"  Error: {dist_name}: {e}")
        time.sleep(1.1)
    
    if found:
        print(f"\n  Loading {len(found)} districts from Nominatim")
        
        # Clear and reload
        with ENGINE.connect() as conn:
            conn.execute(text("DELETE FROM districts WHERE region_id = :rid"), {"rid": region_id})
            conn.commit()
        
        loaded = 0
        for item in found:
            try:
                with ENGINE.connect() as conn:
                    conn.execute(text("""
                        INSERT INTO districts (id, region_id, name, geom, geom_simplified, created_at)
                        VALUES (:id, :rid, :name,
                                ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                                ST_SimplifyPreserveTopology(
                                    ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))), 0.005),
                                NOW())
                    """), {
                        'id': str(uuid4()), 'rid': region_id,
                        'name': item['name'], 'geojson': json.dumps(item['geojson']),
                    })
                    conn.commit()
                loaded += 1
            except Exception as e:
                print(f"  Insert error: {item['name']}: {e}")
        
        print(f"  Loaded: {loaded}/{len(found)}")
    
    # Final check
    print(f"\n{'='*60}")
    with ENGINE.connect() as conn:
        stats = conn.execute(text("SELECT COUNT(id), COUNT(geom) FROM districts")).fetchone()
    print(f"Total: {stats[0]} districts, {stats[1]} with geometry")
    
    with ENGINE.connect() as conn:
        final = conn.execute(text(
            "SELECT name, geom IS NOT NULL as has_geom FROM districts WHERE region_id = :rid ORDER BY name"
        ), {"rid": region_id}).fetchall()
    print(f"\nЕврейская АО:")
    for name, has_geom in final:
        print(f"  {'OK' if has_geom else 'NO'} {name}")


if __name__ == "__main__":
    main()
