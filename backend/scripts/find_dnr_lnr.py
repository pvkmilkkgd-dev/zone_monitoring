"""Find DNR/LNR region names and OSM IDs"""
import sys, requests, time
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

# DB names
with e.connect() as c:
    rows = c.execute(text("""
        SELECT name FROM regions 
        WHERE name LIKE '%%онецк%%' OR name LIKE '%%уганск%%' 
           OR name LIKE '%%Запорож%%' OR name LIKE '%%Херсон%%'
    """)).fetchall()
    for r in rows:
        print(f"DB region: {r[0]}")

# Search OSM
print()
for q in ['Донецкая область', 'Donetsk Oblast', 'Луганская область', 'Luhansk Oblast',
          'Донецкая область, Украина', 'Луганская область, Украина']:
    resp = requests.get('https://nominatim.openstreetmap.org/search',
                       params={'q': q, 'format': 'json', 'limit': 3},
                       headers=HEADERS, timeout=30)
    for r in resp.json():
        if r.get('osm_type') == 'relation':
            disp = r.get('display_name', '')[:80]
            print(f"  [{q}] R{r['osm_id']} {disp}")
    time.sleep(1.1)

# Try known IDs
print("\nChecking known IDs:")
for rid, name in [(71973, 'Donetsk'), (71971, 'Luhansk')]:
    resp = requests.get('https://nominatim.openstreetmap.org/lookup',
                       params={'osm_ids': f'R{rid}', 'format': 'json'},
                       headers=HEADERS, timeout=30)
    if resp.json():
        r = resp.json()[0]
        print(f"  R{rid}: {r.get('display_name', '')[:80]}")
    time.sleep(1.1)
