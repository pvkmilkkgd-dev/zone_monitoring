"""Replace Novaya Zemlya district geometry with actual island shapes from archipelago R4263184"""
import sys, json, requests, time
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

# 1. Download archipelago geometry (actual island shapes)
print("Downloading archipelago R4263184 geometry...")
url = "https://nominatim.openstreetmap.org/lookup"
params = {
    'osm_ids': 'R4263184',
    'format': 'geojson',
    'polygon_geojson': 1,
    'polygon_threshold': 0
}
resp = requests.get(url, params=params, headers=HEADERS, timeout=60)
data = resp.json()
feat = data['features'][0]
geom = feat['geometry']

# Ensure MultiPolygon
if geom['type'] == 'Polygon':
    geom = {'type': 'MultiPolygon', 'coordinates': [geom['coordinates']]}

total_pts = sum(sum(len(ring) for ring in poly) for poly in geom['coordinates'])
print(f"Archipelago: {geom['type']}, {len(geom['coordinates'])} polygons, {total_pts} points")

geom_json = json.dumps(geom)

# 2. Update district
print("\nUpdating Novaya Zemlya district with archipelago geometry...")
with e.begin() as c:
    # Find district
    d = c.execute(text("""
        SELECT d.id FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Архангельская область' AND d.name LIKE '%Новая Земля%'
    """)).fetchone()
    
    district_id = d[0]
    print(f"District id: {district_id}")
    
    c.execute(text("""
        UPDATE districts SET
            geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326))),
            geom_simplified = ST_SimplifyPreserveTopology(
                ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326))), 0.005
            )
        WHERE id = :did
    """), {'gj': geom_json, 'did': district_id})
    
    # Verify
    v = c.execute(text("""
        SELECT ST_NPoints(geom), ST_NumGeometries(geom),
               ST_Area(geom::geography)/1e6,
               ST_XMin(geom), ST_YMin(geom), ST_XMax(geom), ST_YMax(geom),
               ST_NPoints(geom_simplified)
        FROM districts WHERE id = :did
    """), {'did': district_id}).fetchone()
    
    print(f"\nResult:")
    print(f"  Points: {v[0]} (was 465)")
    print(f"  Parts: {v[1]} (was 1)")
    print(f"  Area: {v[2]:.0f} km2")
    print(f"  Bbox: lon {v[3]:.2f}-{v[5]:.2f}, lat {v[4]:.2f}-{v[6]:.2f}")
    print(f"  Simplified: {v[7]} pts")

print("\nDone! Novaya Zemlya now shows actual island shapes.")
