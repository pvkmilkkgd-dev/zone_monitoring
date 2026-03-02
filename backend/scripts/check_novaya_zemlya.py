"""Check Novaya Zemlya geometry - what OSM relation is being used?"""
import sys, json, requests
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

# Check what's in DB
with e.connect() as c:
    nz = c.execute(text("""
        SELECT d.id, d.name, ST_Area(d.geom::geography)/1e6,
               ST_NPoints(d.geom), ST_GeometryType(d.geom),
               ST_XMin(d.geom), ST_YMin(d.geom), ST_XMax(d.geom), ST_YMax(d.geom),
               ST_NumGeometries(d.geom)
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Архангельская область' AND d.name LIKE '%Новая Земля%'
    """)).fetchone()

print(f"Name: {nz[1]}")
print(f"Area: {nz[2]:.0f} km2")
print(f"Points: {nz[3]}, Type: {nz[4]}, Num geometries: {nz[9]}")
print(f"Bbox: lon {nz[5]:.2f}-{nz[7]:.2f}, lat {nz[6]:.2f}-{nz[8]:.2f}")

# Novaya Zemlya should be at approx:
# lon: 49-69, lat: 70-77
# Two long narrow islands oriented NE-SW
print(f"\nExpected: lon ~49-69, lat ~70-77 (two narrow islands)")
print(f"Got:      lon {nz[5]:.2f}-{nz[7]:.2f}, lat {nz[6]:.2f}-{nz[8]:.2f}")

# Check the OSM relation for Новая Земля
print("\n=== Searching Nominatim for correct Новая Земля ===")
url = "https://nominatim.openstreetmap.org/search"
params = {'q': 'городской округ Новая Земля, Архангельская область', 'format': 'json', 'limit': 5}
resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
for r in resp.json():
    print(f"  {r['osm_type']}{r['osm_id']} {r.get('class','')}/{r.get('type','')} "
          f"bbox={r.get('boundingbox','')} {r.get('display_name','')[:70]}")

import time; time.sleep(1.1)

# Check what R1329568 actually is (what was loaded)
print("\n=== Checking OSM R1329568 (loaded relation) ===")
url = "https://nominatim.openstreetmap.org/lookup"
params = {'osm_ids': 'R1329568', 'format': 'json'}
resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
if resp.json():
    r = resp.json()[0]
    print(f"  Name: {r.get('display_name','')[:80]}")
    print(f"  Bbox: {r.get('boundingbox','')}")
    print(f"  Type: {r.get('class','')}/{r.get('type','')}")

time.sleep(1.1)

# Try to find the actual Novaya Zemlya archipelago
print("\n=== Searching for Новая Земля archipelago ===")
params = {'q': 'Новая Земля', 'format': 'json', 'limit': 10}
resp = requests.get("https://nominatim.openstreetmap.org/search", params=params, headers=HEADERS, timeout=30)
for r in resp.json():
    otype = r.get('osm_type', '')
    oid = r.get('osm_id', '')
    bbox = r.get('boundingbox', [])
    name = r.get('display_name', '')[:70]
    cls = r.get('class', '')
    print(f"  {otype}{oid} {cls}/{r.get('type','')} bbox={bbox} {name}")
