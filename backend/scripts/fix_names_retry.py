"""Retry fixing short names for regions that failed due to Overpass timeouts."""
import sys, os, requests, time, re
from collections import defaultdict

os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

# Regions to retry + fallback Overpass servers
REGION_OSM_IDS = {
    'Кабардино-Балкарская Республика': 109879,
    'Калининградская область': 103906,
    'Республика Коми': 115136,
    'Сахалинская область': 394235,
    'Свердловская область': 79379,
}

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


def get_districts(osm_id):
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
                names = []
                for el in resp.json().get('elements', []):
                    name = el.get('tags', {}).get('name', '')
                    if name:
                        names.append(name)
                return names
            print(f"  {server}: {resp.status_code}")
        except Exception as e:
            print(f"  {server}: {e}")
        time.sleep(3)
    return []


# Get remaining short-named districts
with ENGINE.connect() as c:
    rows = c.execute(text("""
        SELECT d.id, d.name, r.name as region_name
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE d.name NOT LIKE '%%район%%'
          AND d.name NOT LIKE '%%округ%%'
          AND d.name NOT LIKE '%%город%%'
          AND d.name NOT LIKE '%%ЗАТО%%'
          AND d.name NOT LIKE '%%поселение%%'
          AND d.name NOT LIKE '%%улус%%'
          AND d.name NOT LIKE '%%участок%%'
          AND d.name NOT LIKE '%%кожуун%%'
          AND d.name NOT LIKE '%%образование%%'
        ORDER BY r.name, d.name
    """)).fetchall()

by_region = defaultdict(list)
for r in rows:
    if r[2] in REGION_OSM_IDS:
        by_region[r[2]].append({'id': str(r[0]), 'name': r[1]})

print(f"Retrying {sum(len(v) for v in by_region.values())} districts in {len(by_region)} regions\n")

total_fixed = 0
total_failed = 0

for region_name, districts in sorted(by_region.items()):
    osm_id = REGION_OSM_IDS[region_name]
    print(f"\n=== {region_name} (R{osm_id}, {len(districts)}) ===")
    
    osm_names = get_districts(osm_id)
    time.sleep(5)
    
    if not osm_names:
        print(f"  FAILED - no names returned")
        total_failed += len(districts)
        continue
    
    print(f"  Got {len(osm_names)} names")
    
    osm_by_norm = {}
    for oname in osm_names:
        norm = normalize(oname)
        osm_by_norm[norm] = oname
    
    for d in districts:
        d_norm = normalize(d['name'])
        
        if d_norm in osm_by_norm:
            new_name = osm_by_norm[d_norm]
            if new_name != d['name']:
                print(f"  {d['name']} -> {new_name}")
                with ENGINE.begin() as conn:
                    conn.execute(text("UPDATE districts SET name = :new WHERE id = :id"),
                               {'new': new_name, 'id': d['id']})
                total_fixed += 1
            else:
                total_failed += 1
        else:
            found = False
            for norm_key, full_name in osm_by_norm.items():
                if d_norm and len(d_norm) > 3 and (d_norm in norm_key or norm_key in d_norm):
                    if full_name != d['name']:
                        print(f"  {d['name']} -> {full_name} (partial)")
                        with ENGINE.begin() as conn:
                            conn.execute(text("UPDATE districts SET name = :new WHERE id = :id"),
                                       {'new': full_name, 'id': d['id']})
                        total_fixed += 1
                        found = True
                        break
            if not found:
                print(f"  {d['name']} -> NO MATCH")
                total_failed += 1

print(f"\n\nDone! Fixed: {total_fixed}, Failed: {total_failed}")
