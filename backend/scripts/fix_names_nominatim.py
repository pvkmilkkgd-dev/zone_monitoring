"""Fix short district names using Nominatim display_name as reference"""
import sys, requests, time, re
from collections import defaultdict
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

# Get all districts with short names
with e.connect() as c:
    rows = c.execute(text("""
        SELECT d.id, d.name, r.name as region_name, r.id as region_id
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE d.name NOT LIKE '%%район%%'
          AND d.name NOT LIKE '%%округ%%'
          AND d.name NOT LIKE '%%город%%'
          AND d.name NOT LIKE '%%ЗАТО%%'
          AND d.name NOT LIKE '%%поселение%%'
          AND d.name NOT LIKE '%%улус%%'
          AND d.name NOT LIKE '%%участок%%'
        ORDER BY r.name, d.name
    """)).fetchall()

print(f"Found {len(rows)} districts with short names (excluding улус/участок)\n")

# Group by region
by_region = defaultdict(list)
for r in rows:
    by_region[r[2]].append({'id': r[0], 'name': r[1], 'region_name': r[2]})

# For each region, use Overpass to get the relation names with admin_level
fixed = 0
failed = 0

for region_name, districts in sorted(by_region.items()):
    print(f"\n=== {region_name} ({len(districts)} to fix) ===")
    
    # Search Nominatim for each district
    for d in districts:
        search_q = f"{d['name']}, {region_name}"
        try:
            params = {
                'q': search_q,
                'format': 'json',
                'limit': 5,
                'addressdetails': 1
            }
            resp = requests.get("https://nominatim.openstreetmap.org/search", 
                              params=params, headers=HEADERS, timeout=30)
            results = resp.json()
            
            # Find the best match - look for administrative boundary
            best_name = None
            for r in results:
                display = r.get('display_name', '')
                osm_type = r.get('osm_type', '')
                cls = r.get('class', '')
                rtype = r.get('type', '')
                
                # We want administrative boundaries
                if cls == 'boundary' and rtype == 'administrative':
                    name_from_display = display.split(',')[0].strip()
                    if name_from_display != d['name'] and d['name'].lower() in name_from_display.lower():
                        best_name = name_from_display
                        break
            
            if best_name:
                print(f"  {d['name']} -> {best_name}")
                with e.begin() as conn:
                    conn.execute(text("UPDATE districts SET name = :new_name WHERE id = :did"),
                               {'new_name': best_name, 'did': d['id']})
                fixed += 1
            else:
                # Try lookup by relation if we can find it
                if results:
                    first = results[0]
                    disp = first.get('display_name', '').split(',')[0].strip()
                    if disp != d['name'] and d['name'].lower() in disp.lower():
                        print(f"  {d['name']} -> {disp} (from first result)")
                        with e.begin() as conn:
                            conn.execute(text("UPDATE districts SET name = :new_name WHERE id = :did"),
                                       {'new_name': disp, 'did': d['id']})
                        fixed += 1
                    else:
                        print(f"  {d['name']} -> NOT FOUND (first result: {disp})")
                        failed += 1
                else:
                    print(f"  {d['name']} -> NO RESULTS")
                    failed += 1
            
            time.sleep(1.1)  # Nominatim rate limit
            
        except Exception as ex:
            print(f"  {d['name']} -> ERROR: {ex}")
            failed += 1
            time.sleep(1.1)

print(f"\n\nSummary: Fixed {fixed}, Failed {failed}, Total {fixed + failed}")
