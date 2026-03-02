"""Get actual island geometry for Novaya Zemlya from OSM"""
import sys, json, requests, time
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

# 1. Check archipelago relation R4263184
print("=== Checking archipelago R4263184 ===")
url = "https://nominatim.openstreetmap.org/lookup"
params = {
    'osm_ids': 'R4263184',
    'format': 'geojson',
    'polygon_geojson': 1,
    'polygon_threshold': 0
}
resp = requests.get(url, params=params, headers=HEADERS, timeout=60)
data = resp.json()
if data['features']:
    feat = data['features'][0]
    geom = feat['geometry']
    print(f"  Type: {geom['type']}")
    if geom['type'] == 'MultiPolygon':
        total_pts = 0
        for i, poly in enumerate(geom['coordinates']):
            pts = sum(len(ring) for ring in poly)
            total_pts += pts
            if pts > 10:
                all_coords = [c for ring in poly for c in ring]
                lons = [c[0] for c in all_coords]
                lats = [c[1] for c in all_coords]
                print(f"    Polygon {i}: {len(poly)} rings, {pts} coords, "
                      f"lon: {min(lons):.2f}-{max(lons):.2f}, lat: {min(lats):.2f}-{max(lats):.2f}")
        print(f"  Total: {len(geom['coordinates'])} polygons, {total_pts} points")
    elif geom['type'] == 'Polygon':
        total_pts = sum(len(ring) for ring in geom['coordinates'])
        print(f"  Polygon: {len(geom['coordinates'])} rings, {total_pts} coords")
    elif geom['type'] == 'GeometryCollection':
        print(f"  GeometryCollection with {len(geom['geometries'])} geometries")
else:
    print("  No result!")
    
time.sleep(1.1)

# 2. Search for individual islands
print("\n=== Searching for North and South Islands ===")
for name in ['Северный остров Новая Земля', 'Южный остров Новая Земля']:
    params = {'q': name, 'format': 'json', 'limit': 5}
    resp = requests.get("https://nominatim.openstreetmap.org/search", params=params, headers=HEADERS, timeout=30)
    for r in resp.json():
        print(f"  {r['osm_type']}{r['osm_id']} {r.get('class','')}/{r.get('type','')} "
              f"bbox={r.get('boundingbox','')} {r.get('display_name','')[:80]}")
    time.sleep(1.1)

# 3. Try Overpass to find island relations within the area
print("\n=== Overpass: islands in Novaya Zemlya area ===")
query = """
[out:json][timeout:60];
(
  relation["place"="island"]["name"~"Новая Земля|Северный|Южный"](70,49,78,70);
  relation["place"="archipelago"]["name"~"Новая Земля"](70,49,78,70);
);
out tags;
"""
resp = requests.post("https://overpass-api.de/api/interpreter", data={'data': query}, headers=HEADERS, timeout=90)
elements = resp.json().get('elements', [])
for el in elements:
    tags = el.get('tags', {})
    print(f"  R{el['id']}: {tags.get('name','')} type={tags.get('place','')} "
          f"admin_level={tags.get('admin_level','')}")

time.sleep(1.1)

# 4. Try specific Nominatim searches
print("\n=== Nominatim search for Novaya Zemlya islands ===")
for q in ['Novaya Zemlya North Island', 'Novaya Zemlya South Island', 
          'Severny Island', 'Yuzhny Island Novaya Zemlya']:
    params = {'q': q, 'format': 'json', 'limit': 3}
    resp = requests.get("https://nominatim.openstreetmap.org/search", params=params, headers=HEADERS, timeout=30)
    for r in resp.json():
        otype = r.get('osm_type', '')
        oid = r.get('osm_id', '')
        cls = r.get('class', '')
        print(f"  [{q}] {otype}{oid} {cls}/{r.get('type','')} "
              f"{r.get('display_name','')[:70]}")
    time.sleep(1.1)
