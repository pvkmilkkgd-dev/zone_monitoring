"""Find and load Troitsk geometry - broader search."""
import sys, time, requests, json

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
TROITSK_ID = 'a695f381-da52-4256-be30-49dc5024b2da'

# Try different Nominatim queries
queries = [
    "Троицк, Московская область",
    "Troitsk, Moscow",
    "Троицк город Москва",
    "Troitsk city Moscow Russia",
]

for q in queries:
    time.sleep(2)
    print(f"\nQuery: '{q}'")
    params = {
        'q': q,
        'format': 'json',
        'polygon_geojson': 1,
        'limit': 5,
        'accept-language': 'ru'
    }
    try:
        resp = requests.get("https://nominatim.openstreetmap.org/search", params=params,
                           headers={'User-Agent': 'ZoneMonitoring/1.0'}, timeout=60)
        results = resp.json()
        for r in results:
            osm_type = r.get('osm_type', '')
            osm_id = r.get('osm_id', '')
            display = r.get('display_name', '')[:150]
            geojson = r.get('geojson', {})
            geom_type = geojson.get('type', 'none')
            print(f"  {osm_type}/{osm_id}: {display}")
            print(f"    geom={geom_type}")
    except Exception as e:
        print(f"  Error: {e}")

# Also try structured search
print("\n\n=== Structured search ===")
time.sleep(2)
params = {
    'city': 'Троицк',
    'country': 'Russia',
    'format': 'json',
    'polygon_geojson': 1,
    'limit': 5,
    'accept-language': 'ru'
}
try:
    resp = requests.get("https://nominatim.openstreetmap.org/search", params=params,
                       headers={'User-Agent': 'ZoneMonitoring/1.0'}, timeout=60)
    results = resp.json()
    for r in results:
        osm_type = r.get('osm_type', '')
        osm_id = r.get('osm_id', '')
        display = r.get('display_name', '')[:150]
        geojson = r.get('geojson', {})
        geom_type = geojson.get('type', 'none')
        lat = r.get('lat', '')
        lon = r.get('lon', '')
        print(f"  {osm_type}/{osm_id} ({lat},{lon}): {display}")
        print(f"    geom={geom_type}")
        
        # Troitsk Moscow is at approximately 37.3 E, 55.5 N
        if geom_type in ('Polygon', 'MultiPolygon') and float(lon) > 37 and float(lon) < 38:
            print(f"    >>> This is Moscow Troitsk! Saving...")
            geojson_str = json.dumps(geojson)
            with ENGINE.begin() as c:
                c.execute(text("""
                    UPDATE districts 
                    SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)))
                    WHERE id = :id
                """), {'geojson': geojson_str, 'id': TROITSK_ID})
                row = c.execute(text("""
                    SELECT name, ST_NPoints(geom), ROUND(ST_Area(geom::geography)/1e6)
                    FROM districts WHERE id = :id
                """), {'id': TROITSK_ID}).fetchone()
                print(f"    Result: {row[0]}, pts={row[1]}, area={row[2]} km2")
            break
except Exception as e:
    print(f"  Error: {e}")

print("\nDone!")
