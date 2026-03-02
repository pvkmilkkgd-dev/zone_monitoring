import sys, os, json, time, requests
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

# Use the городское поселение Камень-на-Оби (R3458078)
print("Downloading geometry for R3458078 (городское поселение Камень-на-Оби)...")
resp = requests.get(
    "https://nominatim.openstreetmap.org/lookup",
    params={'osm_ids': 'R3458078', 'format': 'json', 'polygon_geojson': 1},
    headers=HEADERS, timeout=30
)
data = resp.json()
geojson = data[0]['geojson']
print(f"  Type: {geojson['type']}")

geojson_str = json.dumps(geojson)

with engine.connect() as conn:
    # Find the district
    row = conn.execute(text("""
        SELECT d.id FROM districts d
        JOIN regions r ON r.id = d.region_id
        WHERE r.name = 'Алтайский край' AND d.name = 'городской округ город Камень-на-Оби'
    """)).fetchone()
    
    if row:
        did = str(row[0])
        conn.execute(text("""
            UPDATE districts SET 
                geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))),
                geom_simplified = ST_SimplifyPreserveTopology(
                    ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))), 0.005)
            WHERE id = :id
        """), {"geojson": geojson_str, "id": did})
        conn.commit()
        
        # Check area
        row2 = conn.execute(text("""
            SELECT ST_Area(geom::geography)/1000000 FROM districts WHERE id = :id
        """), {"id": did}).fetchone()
        print(f"  Updated! Area: {row2[0]:.1f} km²")
    else:
        print("  District not found!")
