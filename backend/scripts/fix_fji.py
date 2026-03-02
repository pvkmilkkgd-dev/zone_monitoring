"""Find and fix Franz Josef Land island geometry within Primorsky district"""
import sys, json, requests, time
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

# 1. Check current Primorsky district parts
with e.connect() as c:
    row = c.execute(text("""
        SELECT d.id, d.name, ST_NPoints(d.geom), ST_NumGeometries(d.geom),
               ST_AsGeoJSON(d.geom)::text
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Архангельская область' AND d.name LIKE '%Приморский%'
    """)).fetchone()

print(f"District: {row[1]}, id={row[0]}")
print(f"  Total: {row[2]} pts, {row[3]} parts")

geom = json.loads(row[4])
print(f"\nParts breakdown:")
for i, poly in enumerate(geom['coordinates']):
    pts = sum(len(ring) for ring in poly)
    all_coords = [c for ring in poly for c in ring]
    lons = [coord[0] for coord in all_coords]
    lats = [coord[1] for coord in all_coords]
    print(f"  Part {i}: {pts} pts, lat {min(lats):.1f}-{max(lats):.1f}, lon {min(lons):.1f}-{max(lons):.1f}")
    if max(lats) > 78:
        print(f"    ^^^ Franz Josef Land!")
    elif min(lats) > 68:
        print(f"    ^^^ Kolguev Island or similar")
    elif min(lats) < 66:
        print(f"    ^^^ Mainland or coastal islands")

# 2. Search for Franz Josef Land in OSM
print("\n=== Searching for Franz Josef Land ===")
for q in ['Franz Josef Land', 'Zemlya Frantsa-Iosifa', 'Земля Франца-Иосифа']:
    params = {'q': q, 'format': 'json', 'limit': 5}
    resp = requests.get("https://nominatim.openstreetmap.org/search", params=params, headers=HEADERS, timeout=30)
    for r in resp.json():
        ot = r.get('osm_type', '')
        oid = r.get('osm_id', '')
        cls = r.get('class', '')
        bbox = r.get('boundingbox', [])
        name = r.get('display_name', '')[:70]
        print(f"  [{q[:20]}] {ot}{oid} {cls}/{r.get('type','')} bbox={bbox} {name}")
    time.sleep(1.1)

# 3. Search for Kolguev Island  
print("\n=== Searching for Kolguev Island ===")
for q in ['Kolguev Island', 'остров Колгуев']:
    params = {'q': q, 'format': 'json', 'limit': 5}
    resp = requests.get("https://nominatim.openstreetmap.org/search", params=params, headers=HEADERS, timeout=30)
    for r in resp.json():
        ot = r.get('osm_type', '')
        oid = r.get('osm_id', '')
        bbox = r.get('boundingbox', [])
        name = r.get('display_name', '')[:70]
        print(f"  [{q[:20]}] {ot}{oid} {r.get('class','')}/{r.get('type','')} bbox={bbox} {name}")
    time.sleep(1.1)

# 4. Search for Solovetsky Islands
print("\n=== Searching for Solovetsky Islands ===")
for q in ['Соловецкие острова', 'Solovetsky Islands']:
    params = {'q': q, 'format': 'json', 'limit': 5}
    resp = requests.get("https://nominatim.openstreetmap.org/search", params=params, headers=HEADERS, timeout=30)
    for r in resp.json():
        ot = r.get('osm_type', '')
        oid = r.get('osm_id', '')
        bbox = r.get('boundingbox', [])
        name = r.get('display_name', '')[:70]
        print(f"  [{q[:20]}] {ot}{oid} {r.get('class','')}/{r.get('type','')} bbox={bbox} {name}")
    time.sleep(1.1)

# 5. Overpass: find all islands within the Primorsky district bbox
print("\n=== Overpass: island/archipelago relations in Arctic area ===")
query = """
[out:json][timeout:60];
(
  relation["place"="archipelago"](78,40,82,70);
  relation["place"="island"](78,40,82,70);
);
out tags;
"""
resp = requests.post("https://overpass-api.de/api/interpreter", data={'data': query}, headers=HEADERS, timeout=90)
elements = resp.json().get('elements', [])
for el in elements:
    tags = el.get('tags', {})
    print(f"  R{el['id']}: {tags.get('name','')} / {tags.get('name:en','')} "
          f"type={tags.get('place','')} wikidata={tags.get('wikidata','')}")
