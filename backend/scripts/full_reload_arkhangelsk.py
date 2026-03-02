"""
FULL reload of Arkhangelsk Oblast from scratch:
1. Re-download region geometry from Nominatim  
2. Re-download ALL district geometries from OSM/Nominatim
3. Clip districts to region boundary
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
REGION_OSM_ID = 140337


def download_polygon(osm_id):
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {'osm_ids': f'R{osm_id}', 'format': 'json', 'polygon_geojson': 1}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return data[0].get('geojson')
    except Exception as e:
        print(f"    Error: {e}")
    return None


def normalize(name):
    n = name.strip().lower()
    for w in ['муниципальный район', 'муниципальный округ', 'городской округ',
              'район', 'округ', 'городской', 'город', 'зато', 'муниципальный']:
        n = n.replace(w, '')
    n = n.replace('ё', 'е').replace('-', '').replace(' ', '').replace('«', '').replace('»', '')
    return n


def main():
    # Step 1: Get region DB id
    with ENGINE.connect() as c:
        rid = str(c.execute(text(
            "SELECT id FROM regions WHERE name = :n"
        ), {"n": REGION_NAME}).fetchone()[0])
    
    # Step 2: Re-download region geometry
    print("Step 1: Re-downloading region geometry...")
    geojson = download_polygon(REGION_OSM_ID)
    if not geojson:
        print("FAILED to download region!")
        return
    
    with ENGINE.connect() as c:
        c.execute(text("""
            UPDATE regions SET
                geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))),
                geom_simplified = ST_SimplifyPreserveTopology(
                    ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))), 0.01)
            WHERE id = :rid
        """), {"g": json.dumps(geojson), "rid": rid})
        c.commit()
        
        rarea = c.execute(text(
            "SELECT ST_Area(geom::geography)/1e6 FROM regions WHERE id = :rid"
        ), {"rid": rid}).fetchone()[0]
    print(f"  Region: {rarea:.0f} km2")
    
    time.sleep(1.1)
    
    # Step 3: Get district OSM IDs from Overpass
    print("\nStep 2: Finding districts in Overpass...")
    area_id = 3600000000 + REGION_OSM_ID
    query = f"""
[out:json][timeout:120];
area({area_id})->.region;
relation["boundary"="administrative"]["admin_level"~"^(5|6)$"](area.region);
out tags;
"""
    resp = requests.post("https://overpass-api.de/api/interpreter",
                        data={'data': query}, timeout=150)
    elements = resp.json().get('elements', [])
    print(f"  Found {len(elements)} relations")
    
    for el in sorted(elements, key=lambda x: x.get('tags', {}).get('name', '')):
        tags = el.get('tags', {})
        print(f"    R{el['id']} level={tags.get('admin_level','')} {tags.get('name','')}")
    
    # Step 4: Delete old districts and reload
    print(f"\nStep 3: Reloading {len(elements)} districts...")
    with ENGINE.connect() as c:
        c.execute(text("DELETE FROM districts WHERE region_id = :rid"), {"rid": rid})
        c.commit()
    
    loaded = 0
    for el in elements:
        name = el.get('tags', {}).get('name', '')
        osm_id = el['id']
        
        geojson = download_polygon(osm_id)
        if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
            try:
                with ENGINE.connect() as c:
                    c.execute(text("""
                        INSERT INTO districts (id, region_id, name, geom, geom_simplified, created_at)
                        VALUES (:id, :rid, :name,
                            ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))),
                            ST_SimplifyPreserveTopology(
                                ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))), 0.005),
                            NOW())
                    """), {
                        'id': str(uuid4()), 'rid': rid,
                        'name': name, 'g': json.dumps(geojson),
                    })
                    c.commit()
                loaded += 1
            except Exception as e:
                print(f"    Error {name}: {e}")
        else:
            print(f"    No polygon: {name}")
        time.sleep(1.1)
    
    print(f"  Loaded: {loaded}/{len(elements)}")
    
    # Step 5: Clip districts to region boundary  
    print("\nStep 4: Clipping districts to region boundary...")
    with ENGINE.connect() as c:
        c.execute(text("""
            UPDATE districts d SET
                geom = ST_Multi(ST_MakeValid(ST_Intersection(d.geom, r.geom))),
                geom_simplified = ST_SimplifyPreserveTopology(
                    ST_Multi(ST_MakeValid(ST_Intersection(d.geom, r.geom))), 0.005)
            FROM regions r
            WHERE d.region_id = r.id AND d.region_id = :rid AND d.geom IS NOT NULL
        """), {"rid": rid})
        c.commit()
    
    # Step 6: Rename via ОКТМО
    print("\nStep 5: Renaming via ОКТМО...")
    resp = requests.get("https://okp-okpd.ru/oktmo.aspx?kod=11", timeout=30)
    resp.encoding = 'windows-1251'
    soup = BeautifulSoup(resp.text, 'html.parser')
    oktmo_names = []
    for tr in soup.find_all('tr'):
        cells = tr.find_all('td')
        if len(cells) >= 2:
            code = cells[0].get_text(strip=True)
            name = cells[1].get_text(strip=True)
            if re.match(r'^\d{11}$', code) and 'ненец' not in name.lower():
                m = re.match(r'^город\s+(.+)$', name)
                if m:
                    name = f"городской округ {m.group(1)}"
                oktmo_names.append(name)
    
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
    print(f"  Renamed: {renames}")
    
    # Final stats
    print(f"\n{'='*60}")
    with ENGINE.connect() as c:
        rows = c.execute(text(
            "SELECT name, ST_Area(geom::geography)/1e6, ST_NPoints(geom) "
            "FROM districts WHERE region_id = :rid AND geom IS NOT NULL ORDER BY name"
        ), {"rid": rid}).fetchall()
        total = sum(r[1] for r in rows)
    
    print(f"Region: {rarea:.0f} km2")
    print(f"Districts: {len(rows)}, Total area: {total:.0f} km2, Coverage: {total/rarea*100:.1f}%")
    for name, area, pts in rows:
        print(f"  {area:>10.0f} km2  {pts:>6d} pts  {name}")
    
    with ENGINE.connect() as c:
        stats = c.execute(text("SELECT COUNT(id), COUNT(geom) FROM districts")).fetchone()
    print(f"\nOverall: {stats[0]} districts, {stats[1]} with geometry")


if __name__ == "__main__":
    main()
