"""Standardize district names: ensure they match OSM admin_level=6 relation names exactly.
Rule: adjective form (X-ский) = suffix ("Губкинский городской округ")
      proper noun = prefix ("городской округ Белгород")
The OSM names are already grammatically correct - use them as source of truth."""
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


def normalize(name):
    n = name.strip().lower()
    for w in ['муниципальный район', 'муниципальный округ', 'городской округ',
              'район', 'округ', 'городской', 'город', 'зато', 'муниципальный',
              'муниципальное образование', 'поселение']:
        n = n.replace(w, '')
    n = re.sub(r'[«»"\'\-\s]', '', n)
    n = n.replace('ё', 'е')
    return n.strip()


def get_osm_names(osm_id):
    """Get admin_level 6 names from Overpass."""
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
        time.sleep(2)
    return {}


# Get regions that have naming inconsistencies
# Focus on regions where "городской округ" or "муниципальный округ" names exist
with ENGINE.connect() as c:
    # Find regions with inconsistent naming
    rows = c.execute(text("""
        SELECT DISTINCT r.id, r.name
        FROM regions r
        JOIN districts d ON d.region_id = r.id
        WHERE (d.name LIKE 'городской округ %%' OR d.name LIKE '%% городской округ'
            OR d.name LIKE 'муниципальный округ %%' OR d.name LIKE '%% муниципальный округ')
        ORDER BY r.name
    """)).fetchall()

regions_to_check = [(str(r[0]), r[1]) for r in rows]
print(f"Regions with городской/муниципальный округ: {len(regions_to_check)}")

# For each region, find its OSM ID and compare names
total_fixed = 0
total_checked = 0

for region_id, region_name in regions_to_check:
    # Find OSM ID
    params = {'q': f"{region_name}, Россия", 'format': 'json', 'limit': 5}
    try:
        resp = requests.get("https://nominatim.openstreetmap.org/search",
                           params=params, headers=HEADERS, timeout=30)
        osm_id = None
        for r in resp.json():
            if r.get('osm_type') == 'relation' and r.get('class') == 'boundary':
                osm_id = int(r['osm_id'])
                break
    except:
        osm_id = None
    
    time.sleep(1.1)
    
    if not osm_id:
        continue
    
    osm_names = get_osm_names(osm_id)
    time.sleep(2)
    
    if not osm_names:
        continue
    
    # Get DB districts for this region
    with ENGINE.connect() as c:
        db_districts = c.execute(text("""
            SELECT id, name FROM districts WHERE region_id = :rid
        """), {'rid': region_id}).fetchall()
    
    fixes = []
    for did, dname in db_districts:
        d_norm = normalize(dname)
        if d_norm in osm_names:
            osm_name = osm_names[d_norm]
            if osm_name != dname:
                fixes.append((str(did), dname, osm_name))
    
    if fixes:
        print(f"\n{region_name}: {len(fixes)} to fix")
        with ENGINE.begin() as c:
            for did, old, new in fixes:
                print(f"  {old} -> {new}")
                c.execute(text("UPDATE districts SET name = :new WHERE id = :id"),
                         {'new': new, 'id': did})
        total_fixed += len(fixes)
    
    total_checked += 1
    if total_checked % 10 == 0:
        print(f"  ... checked {total_checked}/{len(regions_to_check)} regions, fixed {total_fixed}")

print(f"\n\nDone! Checked {total_checked} regions, fixed {total_fixed} names")
