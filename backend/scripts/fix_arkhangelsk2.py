"""
Fix Arkhangelsk Oblast: find correct OSM ID and reload districts.
"""
import sys, os, json, time, re, requests
from uuid import uuid4

os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings
from bs4 import BeautifulSoup

ENGINE = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

REGION_NAME = "Архангельская область"

def download_polygon_by_id(osm_id):
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


def normalize(name):
    n = name.strip().lower()
    for w in ['муниципальный район', 'муниципальный округ', 'городской округ',
              'район', 'округ', 'городской', 'город', 'зато', 'муниципальный']:
        n = n.replace(w, '')
    n = n.replace('ё', 'е').replace('-', '').replace(' ', '').replace('«', '').replace('»', '')
    return n


def transform_name(name):
    m = re.match(r'^город\s+(.+)$', name)
    if m:
        return f"городской округ {m.group(1)}"
    return name


def main():
    print("Step 1: Find correct OSM relation ID for Архангельская область")
    
    # Search Nominatim for the region
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': 'Архангельская область, Россия',
        'format': 'json',
        'limit': 5,
    }
    resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
    region_osm_id = None
    for r in resp.json():
        print(f"  {r['osm_type']}{r['osm_id']} {r.get('display_name','')[:80]}")
        if r['osm_type'] == 'relation':
            region_osm_id = int(r['osm_id'])
            break
    
    if not region_osm_id:
        print("ERROR: Could not find OSM ID!")
        return
    
    print(f"\nOSM relation ID: {region_osm_id}")
    area_id = 3600000000 + region_osm_id
    
    # Step 2: Get child relations  
    print(f"\nStep 2: Query Overpass with area({area_id})")
    
    query = f"""
[out:json][timeout:120];
area({area_id})->.region;
relation["boundary"="administrative"]["admin_level"~"^(5|6)$"](area.region);
out tags;
"""
    elements = []
    for server in [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]:
        print(f"  Trying {server.split('/')[2]}...")
        try:
            resp = requests.post(server, data={'data': query}, timeout=150)
            if resp.status_code == 200:
                data = resp.json()
                elements = data.get('elements', [])
                if elements:
                    print(f"  Found {len(elements)} elements")
                    break
        except Exception as e:
            print(f"  Error: {e}")
    
    if not elements:
        # Fallback: use name-based area search
        print("\n  Trying name-based search...")
        query = """
[out:json][timeout:120];
area["name"="Архангельская область"]["admin_level"="4"]->.region;
relation["boundary"="administrative"]["admin_level"~"^(5|6)$"](area.region);
out tags;
"""
        for server in [
            "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
        ]:
            try:
                resp = requests.post(server, data={'data': query}, timeout=150)
                if resp.status_code == 200:
                    data = resp.json()
                    elements = data.get('elements', [])
                    if elements:
                        print(f"  Found {len(elements)} elements")
                        break
            except Exception as e:
                print(f"  Error: {e}")
    
    if not elements:
        print("\nOverpass failed! Using Nominatim direct search.")
        elements = []
    
    # Show found districts
    for el in sorted(elements, key=lambda x: x.get('tags', {}).get('name', '')):
        tags = el.get('tags', {})
        print(f"    R{el['id']} level={tags.get('admin_level','')} {tags.get('name','')}")
    
    # Verify these are actually Arkhangelsk districts (not from another region)
    # Check by looking for known Arkhangelsk district names
    arkh_known = {'Вельский', 'Верхнетоемский', 'Котласский', 'Плесецкий', 
                  'Пинежский', 'Мезенский', 'Каргопольский', 'Холмогорский'}
    found_names = {el.get('tags', {}).get('name', '') for el in elements}
    match_count = sum(1 for k in arkh_known if any(k in n for n in found_names))
    
    if match_count < 3 and elements:
        print(f"\nWARNING: Only {match_count}/8 known Arkhangelsk districts found!")
        print("This might be wrong data. Aborting Overpass approach.")
        elements = []
    
    if elements:
        # Filter out Nenets AO districts
        with ENGINE.connect() as c:
            nen = c.execute(text("SELECT id FROM regions WHERE name LIKE '%Ненец%'")).fetchone()
            nen_names = set()
            if nen:
                nen_d = c.execute(text(
                    "SELECT name FROM districts WHERE region_id = :rid"
                ), {"rid": str(nen[0])}).fetchall()
                nen_names = {n[0].lower() for n in nen_d}
        
        filtered = []
        for el in elements:
            name = el.get('tags', {}).get('name', '')
            if name.lower() not in nen_names and 'ненец' not in name.lower():
                filtered.append(el)
            else:
                print(f"  Skipping Nenets: {name}")
        
        print(f"\nFiltered: {len(filtered)} districts for Arkhangelsk")
        
        # Reload
        with ENGINE.connect() as c:
            rid = str(c.execute(text(
                "SELECT id FROM regions WHERE name = :n"
            ), {"n": REGION_NAME}).fetchone()[0])
            c.execute(text("DELETE FROM districts WHERE region_id = :rid"), {"rid": rid})
            c.commit()
        
        loaded = 0
        for el in filtered:
            tags = el.get('tags', {})
            name = tags.get('name', '')
            osm_id = el['id']
            
            geojson = download_polygon_by_id(osm_id)
            if geojson:
                try:
                    with ENGINE.connect() as c:
                        c.execute(text("""
                            INSERT INTO districts (id, region_id, name, geom, geom_simplified, created_at)
                            VALUES (:id, :rid, :name,
                                    ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                                    ST_SimplifyPreserveTopology(
                                        ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))), 0.005),
                                    NOW())
                        """), {
                            'id': str(uuid4()), 'rid': rid,
                            'name': name, 'geojson': json.dumps(geojson),
                        })
                        c.commit()
                    loaded += 1
                except Exception as e:
                    print(f"  Error: {name}: {e}")
            else:
                print(f"  No polygon: {name} (R{osm_id})")
            time.sleep(1.1)
        
        print(f"\nLoaded: {loaded}/{len(filtered)}")
    else:
        # Fallback: Nominatim individual search for each known district
        print("\nUsing ОКТМО + Nominatim individual search")
        
        with ENGINE.connect() as c:
            rid = str(c.execute(text(
                "SELECT id FROM regions WHERE name = :n"
            ), {"n": REGION_NAME}).fetchone()[0])
        
        # Fetch ОКТМО
        resp = requests.get("https://okp-okpd.ru/oktmo.aspx?kod=11", timeout=30)
        resp.encoding = 'windows-1251'
        soup = BeautifulSoup(resp.text, 'html.parser')
        oktmo_names = []
        for tr in soup.find_all('tr'):
            cells = tr.find_all('td')
            if len(cells) >= 2:
                code_text = cells[0].get_text(strip=True)
                name_text = cells[1].get_text(strip=True)
                if re.match(r'^\d{11}$', code_text):
                    if 'ненец' not in name_text.lower():
                        oktmo_names.append(transform_name(name_text))
        
        print(f"ОКТМО districts: {len(oktmo_names)}")
        for n in oktmo_names:
            print(f"  {n}")
        
        # Delete and reload
        with ENGINE.connect() as c:
            c.execute(text("DELETE FROM districts WHERE region_id = :rid"), {"rid": rid})
            c.commit()
        
        loaded = 0
        for name in oktmo_names:
            search_q = f"{name}, Архангельская область"
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
                    for r in resp.json():
                        geojson = r.get('geojson')
                        if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
                            try:
                                with ENGINE.connect() as c:
                                    c.execute(text("""
                                        INSERT INTO districts (id, region_id, name, geom, geom_simplified, created_at)
                                        VALUES (:id, :rid, :name,
                                                ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                                                ST_SimplifyPreserveTopology(
                                                    ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))), 0.005),
                                                NOW())
                                    """), {
                                        'id': str(uuid4()), 'rid': rid,
                                        'name': name, 'geojson': json.dumps(geojson),
                                    })
                                    c.commit()
                                loaded += 1
                                print(f"  OK {name}")
                            except Exception as e:
                                print(f"  Error: {name}: {e}")
                            break
                    else:
                        print(f"  No polygon: {name}")
                else:
                    print(f"  HTTP {resp.status_code}: {name}")
            except Exception as e:
                print(f"  Error: {name}: {e}")
            time.sleep(1.1)
        
        print(f"\nLoaded: {loaded}/{len(oktmo_names)}")
    
    # Step 3: Rename via ОКТМО (if loaded from Overpass)
    if elements:
        print("\nStep 3: Rename via ОКТМО")
        resp = requests.get("https://okp-okpd.ru/oktmo.aspx?kod=11", timeout=30)
        resp.encoding = 'windows-1251'
        soup = BeautifulSoup(resp.text, 'html.parser')
        oktmo_names = []
        for tr in soup.find_all('tr'):
            cells = tr.find_all('td')
            if len(cells) >= 2:
                code_text = cells[0].get_text(strip=True)
                name_text = cells[1].get_text(strip=True)
                if re.match(r'^\d{11}$', code_text):
                    if 'ненец' not in name_text.lower():
                        oktmo_names.append(transform_name(name_text))
        
        with ENGINE.connect() as c:
            rows = c.execute(text(
                "SELECT id, name FROM districts WHERE region_id = :rid"
            ), {"rid": rid}).fetchall()
        
        db_by_norm = {normalize(n): (str(did), n) for did, n in rows}
        
        renames = 0
        for target in oktmo_names:
            tnorm = normalize(target)
            if tnorm in db_by_norm:
                did, dname = db_by_norm[tnorm]
                if dname != target:
                    with ENGINE.connect() as c:
                        c.execute(text("UPDATE districts SET name = :n WHERE id = :id"),
                                {"n": target, "id": did})
                        c.commit()
                    renames += 1
        print(f"Renamed: {renames}")
    
    # Final stats
    print(f"\n{'='*60}")
    with ENGINE.connect() as c:
        rid_q = c.execute(text(
            "SELECT id FROM regions WHERE name = :n"
        ), {"n": REGION_NAME}).fetchone()
        rid = str(rid_q[0])
        
        rows = c.execute(text(
            "SELECT name, ST_Area(geom::geography)/1e6 as area, "
            "ST_AsText(ST_Centroid(geom)) "
            "FROM districts WHERE region_id = :rid ORDER BY name"
        ), {"rid": rid}).fetchall()
        
        total = sum(r[1] for r in rows)
        has_geom = sum(1 for r in rows if r[1] > 0)
    
    print(f"Districts: {len(rows)} ({has_geom} with geometry)")
    for name, area, centroid in rows:
        print(f"  {area:>10.0f} km2  {name}")
    print(f"\nTotal area: {total:.0f} km2")
    
    # Overall DB check
    with ENGINE.connect() as c:
        stats = c.execute(text("SELECT COUNT(id), COUNT(geom) FROM districts")).fetchone()
    print(f"\nOverall: {stats[0]} districts, {stats[1]} with geometry")


if __name__ == "__main__":
    main()
