import sys, os, json, time, requests
from uuid import uuid4
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

# Try multiple approaches for Камень-на-Оби
queries = [
    "Камень-на-Оби городской округ, Алтайский край",
    "Каменский район, Алтайский край",  # the city might be part of a district
    "Камень-на-Оби, Алтайский край, Россия",
]

# First try Overpass to find the OSM relation
print("Searching Overpass for Камень-на-Оби...")
overpass_q = """
[out:json][timeout:30];
area["name"="Алтайский край"]["admin_level"="4"]->.region;
relation["name"~"Камень"]["boundary"="administrative"](area.region);
out tags;
"""
try:
    resp = requests.post("https://overpass-api.de/api/interpreter", data={'data': overpass_q}, timeout=60)
    if resp.status_code == 200:
        data = resp.json()
        for el in data.get('elements', []):
            tags = el.get('tags', {})
            name = tags.get('name', '')
            al = tags.get('admin_level', '')
            print(f"  R{el['id']}: {name} (admin_level={al})")
except Exception as e:
    print(f"  Overpass error: {e}")

time.sleep(2)

# Try Nominatim searches
for q in queries:
    print(f"\nSearching: {q}")
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={'q': q, 'format': 'json', 'polygon_geojson': 1, 'limit': 5},
            headers=HEADERS, timeout=30
        )
        if resp.status_code == 200:
            for r in resp.json():
                geojson = r.get('geojson')
                gtype = geojson.get('type', '') if geojson else ''
                display = r.get('display_name', '')[:80]
                osm_type = r.get('osm_type', '')
                osm_id = r.get('osm_id', '')
                print(f"  {osm_type}/{osm_id}: {gtype} - {display}")
                
                if geojson and gtype in ('Polygon', 'MultiPolygon') and 'Алтайский' in r.get('display_name', ''):
                    # Check area
                    coords = geojson.get('coordinates', [])
                    if gtype == 'MultiPolygon':
                        npoints = sum(len(ring) for poly in coords for ring in poly)
                    else:
                        npoints = sum(len(ring) for ring in coords)
                    print(f"    Points: {npoints}")
    except Exception as e:
        print(f"  Error: {e}")
    time.sleep(1.1)
