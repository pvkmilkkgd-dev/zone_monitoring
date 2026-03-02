"""Load geometry for городской округ Троицк in Moscow."""
import sys, time, requests, json

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)

# Step 1: Find Troitsk OSM relation via Overpass
print("=== Searching Troitsk in OSM ===")

# Try Overpass to find Troitsk relation in Moscow
overpass_url = "https://overpass-api.de/api/interpreter"
query = """
[out:json][timeout:60];
area["name"="Москва"]["admin_level"="4"]->.moscow;
(
  relation["name:ru"~"Троицк"]["admin_level"~"[5-9]"](area.moscow);
  relation["name"~"Троицк"]["admin_level"~"[5-9]"](area.moscow);
);
out tags;
"""
resp = requests.post(overpass_url, data={'data': query}, timeout=120)
data = resp.json()
print(f"  Overpass results: {len(data.get('elements', []))}")
for el in data.get('elements', []):
    tags = el.get('tags', {})
    print(f"  relation/{el['id']}: name={tags.get('name')}, name:ru={tags.get('name:ru')}, admin_level={tags.get('admin_level')}")

# Step 2: Try Nominatim to get geometry
print("\n=== Fetching geometry from Nominatim ===")

# Search for Troitsk Moscow specifically
nominatim_url = "https://nominatim.openstreetmap.org/search"

# Try with different queries
for q in ["городской округ Троицк, Москва", "Troitsk, Moscow"]:
    time.sleep(1.5)
    params = {
        'q': q,
        'format': 'json',
        'polygon_geojson': 1,
        'limit': 5,
        'accept-language': 'ru'
    }
    resp = requests.get(nominatim_url, params=params, 
                       headers={'User-Agent': 'ZoneMonitoring/1.0'}, timeout=60)
    results = resp.json()
    print(f"\n  Query: '{q}' -> {len(results)} results")
    for r in results:
        osm_type = r.get('osm_type', '')
        osm_id = r.get('osm_id', '')
        display = r.get('display_name', '')[:100]
        geojson = r.get('geojson', {})
        geom_type = geojson.get('type', 'none')
        print(f"  {osm_type}/{osm_id}: {display}")
        print(f"    geom_type={geom_type}")
        
        if geom_type in ('Polygon', 'MultiPolygon') and 'Москва' in display:
            print(f"    >>> FOUND GEOMETRY! Saving...")
            geojson_str = json.dumps(geojson)
            
            with ENGINE.begin() as c:
                c.execute(text("""
                    UPDATE districts 
                    SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)))
                    WHERE id = 'a695f381-da52-4256-be30-49dc5024b2da'
                """), {'geojson': geojson_str})
                
                # Verify
                row = c.execute(text("""
                    SELECT name, ST_NPoints(geom), ROUND(ST_Area(geom::geography)/1e6) 
                    FROM districts WHERE id = 'a695f381-da52-4256-be30-49dc5024b2da'
                """)).fetchone()
                print(f"    Updated: {row[0]}, pts={row[1]}, area={row[2]} km2")
            break
    else:
        continue
    break
else:
    # If Nominatim didn't work, try via OSM relation ID directly
    print("\n=== Trying direct relation lookup ===")
    # Troitsk in Moscow is likely relation 1334914 or similar
    for rel_id in [1334914, 13220604, 365437]:
        time.sleep(1.5)
        url = f"https://nominatim.openstreetmap.org/lookup?osm_ids=R{rel_id}&format=json&polygon_geojson=1&accept-language=ru"
        resp = requests.get(url, headers={'User-Agent': 'ZoneMonitoring/1.0'}, timeout=60)
        results = resp.json()
        if results:
            r = results[0]
            display = r.get('display_name', '')[:100]
            geojson = r.get('geojson', {})
            geom_type = geojson.get('type', 'none')
            print(f"  R{rel_id}: {display}")
            print(f"    geom_type={geom_type}")
            if geom_type in ('Polygon', 'MultiPolygon'):
                geojson_str = json.dumps(geojson)
                with ENGINE.begin() as c:
                    c.execute(text("""
                        UPDATE districts 
                        SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)))
                        WHERE id = 'a695f381-da52-4256-be30-49dc5024b2da'
                    """), {'geojson': geojson_str})
                    row = c.execute(text("""
                        SELECT name, ST_NPoints(geom), ROUND(ST_Area(geom::geography)/1e6) 
                        FROM districts WHERE id = 'a695f381-da52-4256-be30-49dc5024b2da'
                    """)).fetchone()
                    print(f"    Updated: {row[0]}, pts={row[1]}, area={row[2]} km2")
                break

print("\nDone!")
