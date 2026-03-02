"""Restore OSM names (which reflect current admin divisions) for all regions.
OSM is more up-to-date than the ОКТМО data on okp-okpd.ru."""
import sys, os, re, requests, time
from collections import defaultdict

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

# Known region OSM IDs for regions where Nominatim search fails
KNOWN_REGION_IDS = {
    'Архангельская область': 140337,
    'Кабардино-Балкарская Республика': 109879,
    'Калининградская область': 103906,
    'Карачаево-Черкесская Республика': 109877,
    'Оренбургская область': 77687,
    'Пермский край': 115135,
    'Республика Коми': 115136,
    'Самарская область': 72194,
    'Сахалинская область': 394235,
    'Свердловская область': 79379,
    'Тюменская область': 140296,
    'Кемеровская область': 144763,
}

SKIP = {
    'Донецкая Народная Республика',
    'Луганская Народная Республика',
    'Запорожская область',
    'Херсонская область',
}


def normalize(name):
    n = name.strip().lower()
    for w in ['муниципальный район', 'муниципальный округ', 'городской округ',
              'район', 'округ', 'городской', 'город', 'зато', 'муниципальный',
              'муниципальное образование', 'поселение',
              'национальный', 'эвенкийский']:
        n = n.replace(w, '')
    n = re.sub(r'[«»"\'\-\s]', '', n)
    n = n.replace('ё', 'е')
    return n.strip()


def find_region_osm_id(region_name):
    if region_name in KNOWN_REGION_IDS:
        return KNOWN_REGION_IDS[region_name]
    params = {'q': f"{region_name}, Россия", 'format': 'json', 'limit': 5}
    try:
        resp = requests.get("https://nominatim.openstreetmap.org/search",
                           params=params, headers=HEADERS, timeout=30)
        for r in resp.json():
            if r.get('osm_type') == 'relation' and r.get('class') == 'boundary':
                return int(r['osm_id'])
    except:
        pass
    return None


def get_osm_names(osm_id):
    area_id = 3600000000 + osm_id
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
                names = {}
                for el in resp.json().get('elements', []):
                    tags = el.get('tags', {})
                    name = tags.get('name', '')
                    if name:
                        names[normalize(name)] = name
                return names
        except:
            pass
        time.sleep(3)
    return {}


# Get all regions
with ENGINE.connect() as c:
    all_regions = c.execute(text("SELECT id, name FROM regions ORDER BY name")).fetchall()

total_fixed = 0
total_regions = 0

for region_id, region_name in all_regions:
    if region_name in SKIP:
        continue
    
    region_id = str(region_id)
    
    osm_id = find_region_osm_id(region_name)
    time.sleep(1.1)
    
    if not osm_id:
        print(f"{region_name}: NO OSM ID")
        continue
    
    osm_names = get_osm_names(osm_id)
    time.sleep(2)
    
    if not osm_names:
        print(f"{region_name}: NO OSM NAMES (R{osm_id})")
        continue
    
    # Get DB districts
    with ENGINE.connect() as c:
        db_rows = c.execute(text("""
            SELECT id, name FROM districts WHERE region_id = :rid
        """), {'rid': region_id}).fetchall()
    
    fixes = []
    for did, dname in db_rows:
        d_norm = normalize(dname)
        if d_norm in osm_names:
            osm_name = osm_names[d_norm]
            if osm_name != dname:
                fixes.append((str(did), dname, osm_name))
    
    if fixes:
        print(f"\n{region_name} (R{osm_id}): {len(fixes)} to fix")
        with ENGINE.begin() as c:
            for did, old, new in fixes:
                print(f"  {old} -> {new}")
                c.execute(text("UPDATE districts SET name = :new WHERE id = :id"),
                         {'new': new, 'id': did})
        total_fixed += len(fixes)
    
    total_regions += 1
    if total_regions % 10 == 0:
        print(f"  ... processed {total_regions} regions, fixed {total_fixed}")

print(f"\n\nDone! Processed {total_regions} regions, fixed {total_fixed} names")
