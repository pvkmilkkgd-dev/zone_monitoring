"""Load Troitsk geometry from found OSM relations."""
import sys, time, requests, json

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
TROITSK_ID = 'a695f381-da52-4256-be30-49dc5024b2da'

# Check both relations
for rel_id in [1703093, 184748]:
    time.sleep(2)
    url = "https://nominatim.openstreetmap.org/lookup"
    params = {
        'osm_ids': f'R{rel_id}',
        'format': 'json',
        'polygon_geojson': 1,
        'accept-language': 'ru'
    }
    resp = requests.get(url, params=params,
                       headers={'User-Agent': 'ZoneMonitoring/1.0'}, timeout=60)
    results = resp.json()
    if results:
        r = results[0]
        display = r.get('display_name', '')
        geojson = r.get('geojson', {})
        geom_type = geojson.get('type', 'none')
        # Calculate approximate area from bbox
        bbox = r.get('boundingbox', [])
        print(f"R{rel_id}: {display}")
        print(f"  type={geojson.get('type')} bbox={bbox}")
        
        # Temporarily store to calculate area
        if geom_type in ('Polygon', 'MultiPolygon'):
            geojson_str = json.dumps(geojson)
            with ENGINE.connect() as c:
                row = c.execute(text("""
                    SELECT ROUND(ST_Area(
                        ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))::geography
                    ) / 1e6),
                    ST_NPoints(ST_GeomFromGeoJSON(:g))
                """), {'g': geojson_str}).fetchone()
                print(f"  area={row[0]} km2, pts={row[1]}")
    else:
        print(f"R{rel_id}: no results")

# relation/184748 is the city of Troitsk (~10 km2)
# relation/1703093 is the administrative district "район Троицк" which is likely the larger area
# "городской округ Троицк" = the city territory, so use 184748
print("\n=== Using relation/184748 (город Троицк) ===")
time.sleep(2)
resp = requests.get("https://nominatim.openstreetmap.org/lookup",
                   params={'osm_ids': 'R184748', 'format': 'json', 'polygon_geojson': 1},
                   headers={'User-Agent': 'ZoneMonitoring/1.0'}, timeout=60)
results = resp.json()
if results:
    geojson = results[0].get('geojson', {})
    if geojson.get('type') in ('Polygon', 'MultiPolygon'):
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
            print(f"  Updated: {row[0]}, pts={row[1]}, area={row[2]} km2")

print("\nDone!")
