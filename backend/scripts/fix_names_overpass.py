"""Fix short district names using Overpass API to get official OSM relation names.
One query per region to get ALL admin_level 6 relations with their names."""
import sys, os, requests, time, re
from collections import defaultdict

os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}


def normalize(name):
    """Normalize for matching."""
    n = name.strip().lower()
    for w in ['муниципальный район', 'муниципальный округ', 'городской округ',
              'район', 'округ', 'городской', 'город', 'зато', 'муниципальный',
              'муниципальное образование', 'внутригородской', 'внутригородское',
              'поселение', 'национальный', 'эвенкийский', 'улус', 'кожуун']:
        n = n.replace(w, '')
    n = re.sub(r'[«»"\'\-\s]', '', n)
    n = n.replace('ё', 'е')
    return n.strip()


def get_osm_names_for_region(region_name):
    """Use Overpass to get all admin_level 6 relation names within a region."""
    # First find the region's OSM relation ID via Nominatim
    params = {'q': f"{region_name}, Россия", 'format': 'json', 'limit': 5}
    resp = requests.get("https://nominatim.openstreetmap.org/search",
                       params=params, headers=HEADERS, timeout=30)
    
    region_osm_id = None
    for r in resp.json():
        if r.get('osm_type') == 'relation' and r.get('class') == 'boundary':
            region_osm_id = int(r['osm_id'])
            break
    
    if not region_osm_id:
        return []
    
    time.sleep(1.1)
    
    # Get all admin_level 6 relations within this region
    area_id = 3600000000 + region_osm_id
    query = f"""
[out:json][timeout:60];
area({area_id})->.searchArea;
(
  relation["boundary"="administrative"]["admin_level"="6"](area.searchArea);
);
out tags;
"""
    resp = requests.post("https://overpass-api.de/api/interpreter",
                        data={'data': query}, headers=HEADERS, timeout=90)
    
    if resp.status_code != 200:
        return []
    
    names = []
    for el in resp.json().get('elements', []):
        tags = el.get('tags', {})
        name = tags.get('name', '')
        if name:
            names.append(name)
    
    return names


# Get all districts with short names
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
    by_region[r[2]].append({'id': str(r[0]), 'name': r[1]})

print(f"Found {len(rows)} districts with short names across {len(by_region)} regions\n")

total_fixed = 0
total_failed = 0

for region_name, districts in sorted(by_region.items()):
    print(f"\n=== {region_name} ({len(districts)} to fix) ===")
    
    osm_names = get_osm_names_for_region(region_name)
    time.sleep(1.5)
    
    if not osm_names:
        print(f"  Could not fetch OSM names")
        total_failed += len(districts)
        continue
    
    print(f"  Got {len(osm_names)} OSM admin_level=6 names")
    
    # Build normalized lookup
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
                print(f"  {d['name']} - same in OSM")
                total_failed += 1
        else:
            # Try partial match
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
