"""
Fix remaining 9 regions using direct OSM relation IDs.
Strategy: Find region relation ID via Nominatim, then use Overpass
with relation(id) to find child admin boundaries.
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

REGION_TO_OKTMO = {
    "Еврейская автономная область": "99",
    "Кабардино-Балкарская Республика": "83",
    "Карачаево-Черкесская Республика": "91",
    "Республика Калмыкия": "85",
    "Республика Коми": "87",
    "Республика Саха (Якутия)": "98",
    "Республика Северная Осетия - Алания": "90",
    "Республика Тыва": "93",
    "Чувашская Республика": "97",
}

# Known OSM relation IDs for parent regions
KNOWN_REGION_IDS = {
    "Еврейская автономная область": 1845454,
    "Кабардино-Балкарская Республика": 109879,
    "Карачаево-Черкесская Республика": 109878,
    "Республика Калмыкия": 108083,
    "Республика Коми": 115136,
    "Республика Саха (Якутия)": 151234,
    "Республика Северная Осетия - Алания": 110032,
    "Республика Тыва": 145195,
    "Чувашская Республика": 80513,
}


def find_region_osm_id(region_name):
    """Find region OSM ID via Nominatim."""
    if region_name in KNOWN_REGION_IDS:
        return KNOWN_REGION_IDS[region_name]
    
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': region_name,
        'format': 'json',
        'country': 'Russia',
        'limit': 5,
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


def get_children_by_parent_id(parent_id):
    """Get child admin boundaries using the parent relation ID directly."""
    # Use relation(id) -> map_to_area -> then search inside
    # The relation ID in Overpass area format is 3600000000 + relation_id
    area_id = 3600000000 + parent_id
    
    for levels in ["5|6", "5|6|7", "6", "5|6|7|8"]:
        query = f"""
[out:json][timeout:120];
area({area_id})->.region;
relation["boundary"="administrative"]["admin_level"~"^({levels})$"](area.region);
out tags;
"""
        servers = [
            "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
        ]
        for server in servers:
            try:
                resp = requests.post(server, data={'data': query}, timeout=150)
                if resp.status_code == 200:
                    data = resp.json()
                    result = []
                    for el in data.get('elements', []):
                        tags = el.get('tags', {})
                        name = tags.get('name', '')
                        osm_id = el.get('id')
                        al = tags.get('admin_level', '')
                        if name and osm_id:
                            result.append({
                                'osm_id': osm_id, 'name': name, 'admin_level': al
                            })
                    if result:
                        # Filter: prefer admin_level 6, include 5 for cities
                        # If we have mixed levels, keep only the most relevant
                        levels_found = set(r['admin_level'] for r in result)
                        if '6' in levels_found:
                            # Keep level 5 and 6
                            filtered = [r for r in result if r['admin_level'] in ('5', '6')]
                            if len(filtered) > 3:
                                return filtered
                        return result
            except Exception as e:
                print(f"    Server {server.split('/')[2]} error: {e}")
                continue
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


def normalize(name):
    n = name.strip().lower()
    for w in ['муниципальный район', 'муниципальный округ', 'городской округ',
              'район', 'округ', 'городской', 'город', 'зато', 'муниципальный']:
        n = n.replace(w, '')
    n = n.replace('ё', 'е').replace('-', '').replace(' ', '').replace('«', '').replace('»', '')
    return n


def transform_name(name):
    if 'внутригородское' in name.lower() or 'поселение' in name.lower():
        return name
    m = re.match(r'^город\s+(.+)$', name)
    if m:
        return f"городской округ {m.group(1)}"
    return name


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


def process_region(region_name):
    # Get region DB ID
    with ENGINE.connect() as conn:
        row = conn.execute(text("SELECT id FROM regions WHERE name = :n"), {"n": region_name}).fetchone()
        if not row:
            print(f"    Not in DB!")
            return
        region_id = str(row[0])
    
    # Find OSM ID
    parent_id = find_region_osm_id(region_name)
    if not parent_id:
        print(f"    Could not find OSM ID!")
        return
    print(f"    OSM region ID: {parent_id}")
    
    # Get children
    children = get_children_by_parent_id(parent_id)
    if not children:
        print(f"    No children found!")
        return
    
    print(f"    Found {len(children)} children in OSM")
    
    # Clear and reload
    with ENGINE.connect() as conn:
        conn.execute(text("DELETE FROM districts WHERE region_id = :rid"), {"rid": region_id})
        conn.commit()
    
    loaded = 0
    for child in children:
        geojson = download_polygon(child['osm_id'])
        if geojson:
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
                        'name': child['name'], 'geojson': json.dumps(geojson),
                    })
                    conn.commit()
                loaded += 1
            except Exception as e:
                print(f"    Insert error for {child['name']}: {e}")
        else:
            print(f"    No polygon for {child['name']} (R{child['osm_id']})")
        time.sleep(1.1)
    
    print(f"    Loaded: {loaded}/{len(children)}")
    
    # Rename from ОКТМО
    oktmo_code = REGION_TO_OKTMO.get(region_name)
    if oktmo_code:
        try:
            oktmo_raw = fetch_oktmo_names(oktmo_code)
            oktmo_names = [transform_name(n) for n in oktmo_raw]
            
            with ENGINE.connect() as conn:
                rows = conn.execute(text(
                    "SELECT id, name FROM districts WHERE region_id = :rid"
                ), {"rid": region_id}).fetchall()
            
            db_by_norm = {normalize(dname): (str(did), dname) for did, dname in rows}
            
            renames = 0
            for target in oktmo_names:
                tnorm = normalize(target)
                if tnorm in db_by_norm:
                    did, dname = db_by_norm[tnorm]
                    if dname != target:
                        with ENGINE.connect() as conn:
                            conn.execute(text("UPDATE districts SET name = :n WHERE id = :id"),
                                       {"n": target, "id": did})
                            conn.commit()
                        renames += 1
            
            if renames:
                print(f"    Renamed: {renames}")
        except Exception as e:
            print(f"    ОКТМО error: {e}")
        time.sleep(1)
    
    return loaded


def main():
    with ENGINE.connect() as conn:
        damaged = conn.execute(text("""
            SELECT r.name, COUNT(d.id), COUNT(d.geom)
            FROM regions r LEFT JOIN districts d ON d.region_id = r.id
            GROUP BY r.name
            HAVING COUNT(d.geom) < COUNT(d.id) AND COUNT(d.id) > 0
            ORDER BY r.name
        """)).fetchall()
    
    print(f"Regions to fix: {len(damaged)}")
    for name, cnt, gcnt in damaged:
        print(f"  {name}: {gcnt}/{cnt}")
    
    for name, cnt, gcnt in damaged:
        print(f"\n{name}")
        process_region(name)
        time.sleep(3)
    
    # Final stats
    print(f"\n{'='*60}")
    with ENGINE.connect() as conn:
        stats = conn.execute(text("SELECT COUNT(id), COUNT(geom) FROM districts")).fetchone()
    print(f"Total: {stats[0]} districts, {stats[1]} with geometry")
    
    with ENGINE.connect() as conn:
        still = conn.execute(text("""
            SELECT r.name, COUNT(d.id), COUNT(d.geom)
            FROM regions r LEFT JOIN districts d ON d.region_id = r.id
            GROUP BY r.name
            HAVING COUNT(d.geom) < COUNT(d.id) AND COUNT(d.id) > 0
            ORDER BY r.name
        """)).fetchall()
    
    if still:
        print(f"\nStill missing geometry ({len(still)}):")
        for n, c, g in still:
            print(f"  {n}: {g}/{c}")
    else:
        print("\nAll regions have 100% geometry!")


if __name__ == "__main__":
    main()
