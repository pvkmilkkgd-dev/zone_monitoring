"""Restore 6 damaged regions by reloading from OSM, then fix names from ОКТМО."""
import sys
import os
import re
import json
import time
import requests
from uuid import uuid4
from bs4 import BeautifulSoup

os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

DAMAGED_REGIONS = [
    'Краснодарский край',
    'Красноярский край', 
    'Приморский край',
    'Ставропольский край',
    'Хабаровский край',
    'Амурская область',
]

# --- Step 1: Reload from OSM (same approach as reload_all_districts_osm.py) ---

def get_osm_relations(region_name):
    osm_name = region_name
    query = f"""
[out:json][timeout:60];
area["name"="{osm_name}"]["admin_level"="4"]->.region;
relation["boundary"="administrative"]["admin_level"="6"](area.region);
out tags;
"""
    try:
        resp = requests.post("https://overpass-api.de/api/interpreter",
                           data={'data': query}, timeout=90)
        if resp.status_code == 200:
            data = resp.json()
            result = []
            for el in data.get('elements', []):
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
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {'osm_ids': f'R{osm_id}', 'format': 'json', 'polygon_geojson': 1}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                geojson = data[0].get('geojson')
                if geojson and geojson.get('type') in ('Polygon', 'MultiPolygon'):
                    return geojson
    except:
        pass
    return None


def restore_region(region_name):
    """Restore a region: delete bad data, reload from OSM."""
    # Get region ID
    with ENGINE.connect() as conn:
        row = conn.execute(text("SELECT id FROM regions WHERE name = :name"),
                         {"name": region_name}).fetchone()
        if not row:
            print(f"  Region not found!")
            return 0
        region_id = str(row[0])
    
    # Get OSM relations
    relations = get_osm_relations(region_name)
    if not relations:
        print(f"  No OSM relations found!")
        return 0
    
    print(f"  Found {len(relations)} districts in OSM")
    
    # Clear old data
    with ENGINE.connect() as conn:
        conn.execute(text("DELETE FROM districts WHERE region_id = :rid"), {"rid": region_id})
        conn.commit()
    
    # Download and insert
    inserted = 0
    for rel in relations:
        geojson = download_polygon(rel['osm_id'])
        if geojson:
            geojson_str = json.dumps(geojson)
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
                        'name': rel['name'], 'geojson': geojson_str,
                    })
                    conn.commit()
                inserted += 1
            except Exception as e:
                print(f"  Error inserting {rel['name']}: {e}")
        time.sleep(1.1)
    
    return inserted


# --- Step 2: Fix names from ОКТМО ---

OKTMO_CODES = {
    'Краснодарский край': '03',
    'Красноярский край': '04',
    'Приморский край': '05',
    'Ставропольский край': '07',
    'Хабаровский край': '08',
    'Амурская область': '10',
}


def fetch_oktmo_names(code):
    url = f"https://okp-okpd.ru/oktmo.aspx?kod={code}"
    resp = requests.get(url, timeout=30)
    resp.encoding = 'windows-1251'
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    names = []
    for tr in soup.find_all('tr'):
        cells = tr.find_all('td')
        if len(cells) >= 2:
            code_text = cells[0].get_text(strip=True)
            name_text = cells[1].get_text(strip=True)
            if re.match(r'^\d{11}$', code_text):
                names.append(name_text)
    return names


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


def fix_names(region_name, oktmo_code):
    """Fix DB names to match ОКТМО."""
    region_id_row = None
    with ENGINE.connect() as conn:
        region_id_row = conn.execute(text("SELECT id FROM regions WHERE name = :name"),
                                    {"name": region_name}).fetchone()
    if not region_id_row:
        return
    region_id = str(region_id_row[0])
    
    oktmo_names = fetch_oktmo_names(oktmo_code)
    print(f"  ОКТМО: {len(oktmo_names)} entries")
    
    # Get DB districts
    with ENGINE.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, name FROM districts WHERE region_id = :rid ORDER BY name"
        ), {"rid": region_id}).fetchall()
    
    db_by_norm = {}
    for did, dname in rows:
        db_by_norm[normalize(dname)] = (str(did), dname)
    
    renames = 0
    for oktmo_name in oktmo_names:
        target = transform_name(oktmo_name)
        target_norm = normalize(target)
        
        if target_norm in db_by_norm:
            did, dname = db_by_norm[target_norm]
            if dname != target:
                with ENGINE.connect() as conn:
                    conn.execute(text("UPDATE districts SET name = :name WHERE id = :id"),
                               {"name": target, "id": did})
                    conn.commit()
                renames += 1
    
    if renames:
        print(f"  Renamed {renames} districts")
    else:
        print(f"  No renames needed")
    
    time.sleep(1)


def main():
    print("=== Step 1: Restore geometry from OSM ===\n")
    
    for region_name in DAMAGED_REGIONS:
        print(f"\n{region_name}")
        inserted = restore_region(region_name)
        print(f"  Loaded: {inserted}")
        time.sleep(3)
    
    print(f"\n\n=== Step 2: Fix names from ОКТМО ===\n")
    
    for region_name in DAMAGED_REGIONS:
        code = OKTMO_CODES[region_name]
        print(f"\n{region_name} (ОКТМО={code})")
        fix_names(region_name, code)
    
    # Final check
    print(f"\n\n=== Final check ===\n")
    with ENGINE.connect() as conn:
        for rname in DAMAGED_REGIONS:
            row = conn.execute(text("""
                SELECT COUNT(d.id), COUNT(d.geom)
                FROM districts d JOIN regions r ON r.id = d.region_id
                WHERE r.name = :rname
            """), {"rname": rname}).fetchone()
            print(f"  {rname}: {row[0]} districts, {row[1]} with geom")


if __name__ == "__main__":
    main()
