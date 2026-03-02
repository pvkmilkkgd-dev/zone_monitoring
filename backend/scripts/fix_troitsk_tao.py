"""Set городской округ Троицк to Troitsky district geometry (район Троицк) - matches reference map."""
import sys, time, requests, json

sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)
TROITSK_ID = 'a695f381-da52-4256-be30-49dc5024b2da'

# relation/1703093 = "район Троицк" (Troitsky Administrative Okrug territory) ~99 km2 - matches the red area on reference map
time.sleep(1)
resp = requests.get(
    "https://nominatim.openstreetmap.org/lookup",
    params={'osm_ids': 'R1703093', 'format': 'json', 'polygon_geojson': 1},
    headers={'User-Agent': 'ZoneMonitoring/1.0'},
    timeout=60
)
results = resp.json()
if not results:
    print("Nominatim: no result for R1703093")
    sys.exit(1)

r = results[0]
geojson = r.get('geojson', {})
if geojson.get('type') not in ('Polygon', 'MultiPolygon'):
    print("No polygon in result")
    sys.exit(1)

geojson_str = json.dumps(geojson)
with ENGINE.begin() as c:
    c.execute(text("""
        UPDATE districts
        SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326)))
        WHERE id = :id
    """), {'g': geojson_str, 'id': TROITSK_ID})
    row = c.execute(text("""
        SELECT name, ST_NPoints(geom), ROUND(ST_Area(geom::geography)/1e6)
        FROM districts WHERE id = :id
    """), {'id': TROITSK_ID}).fetchone()
    print(f"Обновлено: {row[0]}, pts={row[1]}, area={row[2]} km2")
    print("Геометрия = район Троицк (Троицкий административный округ), как на эталонной карте.")
