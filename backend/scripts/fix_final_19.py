"""
Fix the final 19 regions with missing geometry.
These are mostly republics where OSM uses different names.
Strategy: Overpass with correct OSM name mappings + Nominatim by ID.
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

# OSM name mappings for regions that fail with standard names
REGION_OSM_CONFIG = {
    "Еврейская автономная область": {"osm_name": "Еврейская автономная область", "levels": "6"},
    "Забайкальский край": {"osm_name": "Забайкальский край", "levels": "6"},
    "Кабардино-Балкарская Республика": {"osm_name": "Кабардино-Балкарская Республика", "levels": "5|6|7"},
    "Карачаево-Черкесская Республика": {"osm_name": "Карачаево-Черкесская Республика", "levels": "5|6|7"},
    "Ненецкий автономный округ": {"osm_name": "Ненецкий автономный округ", "levels": "5|6|7"},
    "Республика Адыгея": {"osm_name": "Адыгея", "levels": "5|6|7"},
    "Республика Башкортостан": {"osm_name": "Башкортостан", "levels": "5|6|7"},
    "Республика Дагестан": {"osm_name": "Дагестан", "levels": "5|6|7"},
    "Республика Калмыкия": {"osm_name": "Калмыкия", "levels": "5|6|7"},
    "Республика Карелия": {"osm_name": "Карелия", "levels": "5|6|7"},
    "Республика Коми": {"osm_name": "Коми", "levels": "5|6|7"},
    "Республика Марий Эл": {"osm_name": "Марий Эл", "levels": "5|6|7"},
    "Республика Мордовия": {"osm_name": "Мордовия", "levels": "5|6|7"},
    "Республика Саха (Якутия)": {"osm_name": "Саха (Якутия)", "levels": "5|6|7"},
    "Республика Северная Осетия - Алания": {"osm_name": "Северная Осетия — Алания", "levels": "5|6|7"},
    "Республика Татарстан": {"osm_name": "Татарстан", "levels": "5|6|7"},
    "Республика Тыва": {"osm_name": "Тыва", "levels": "5|6|7"},
    "Удмуртская Республика": {"osm_name": "Удмуртия", "levels": "5|6|7"},
    "Чувашская Республика": {"osm_name": "Чувашия", "levels": "5|6|7"},
}

# ОКТМО config
REGION_TO_OKTMO = {
    "Еврейская автономная область": "99",
    "Забайкальский край": "76",
    "Кабардино-Балкарская Республика": "83",
    "Карачаево-Черкесская Республика": "91",
    "Республика Адыгея": "79",
    "Республика Башкортостан": "80",
    "Республика Дагестан": "82",
    "Республика Калмыкия": "85",
    "Республика Карелия": "86",
    "Республика Коми": "87",
    "Республика Марий Эл": "88",
    "Республика Мордовия": "89",
    "Республика Саха (Якутия)": "98",
    "Республика Северная Осетия - Алания": "90",
    "Республика Татарстан": "92",
    "Республика Тыва": "93",
    "Удмуртская Республика": "94",
    "Чувашская Республика": "97",
}


def get_osm_relations(config):
    """Get admin_level relations from Overpass."""
    osm_name = config["osm_name"]
    levels = config["levels"]
    
    for region_al in ["4", "3", "2"]:
        query = f"""
[out:json][timeout:120];
area["name"="{osm_name}"]["admin_level"="{region_al}"]->.region;
relation["boundary"="administrative"]["admin_level"~"^({levels})$"](area.region);
out tags;
"""
        try:
            resp = requests.post("https://overpass-api.de/api/interpreter",
                               data={'data': query}, timeout=150)
            if resp.status_code == 200:
                data = resp.json()
                result = []
                for el in data.get('elements', []):
                    tags = el.get('tags', {})
                    name = tags.get('name', '')
                    osm_id = el.get('id')
                    if name and osm_id:
                        result.append({'osm_id': osm_id, 'name': name})
                if result:
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
    config = REGION_OSM_CONFIG.get(region_name)
    if not config:
        print(f"    No config!")
        return
    
    # Get region ID
    with ENGINE.connect() as conn:
        row = conn.execute(text("SELECT id FROM regions WHERE name = :n"), {"n": region_name}).fetchone()
        if not row:
            print(f"    Not in DB!")
            return
        region_id = str(row[0])
    
    # Step 1: Load from OSM
    relations = get_osm_relations(config)
    if not relations:
        print(f"    Overpass FAILED")
        return
    
    print(f"    Found {len(relations)} in OSM")
    
    # Clear and reload
    with ENGINE.connect() as conn:
        conn.execute(text("DELETE FROM districts WHERE region_id = :rid"), {"rid": region_id})
        conn.commit()
    
    inserted = 0
    for rel in relations:
        geojson = download_polygon(rel['osm_id'])
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
                        'name': rel['name'], 'geojson': json.dumps(geojson),
                    })
                    conn.commit()
                inserted += 1
            except:
                pass
        time.sleep(1.1)
    
    print(f"    Loaded: {inserted}/{len(relations)}")
    
    # Step 2: Rename from ОКТМО
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
        except:
            pass
        time.sleep(1)
    
    return inserted


def main():
    # Get regions with missing geometry
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
