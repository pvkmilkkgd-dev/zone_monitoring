"""Compare Novaya Zemlya: DB vs fresh Nominatim download"""
import sys, json, requests
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

# 1. Get current DB geometry as GeoJSON
with e.connect() as c:
    row = c.execute(text("""
        SELECT d.id, d.name, 
               ST_AsGeoJSON(d.geom)::text,
               ST_NPoints(d.geom),
               ST_NumGeometries(d.geom),
               ST_GeometryType(d.geom),
               ST_NPoints(d.geom_simplified),
               d.region_id
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Архангельская область' AND d.name LIKE '%Новая Земля%'
    """)).fetchone()

print(f"DB: {row[1]}, id={row[0]}, region_id={row[7]}")
print(f"  Full: {row[3]} pts, {row[4]} parts, type={row[5]}")
print(f"  Simplified: {row[6]} pts")

# Save DB geometry for comparison
db_geom = json.loads(row[2])
print(f"  GeoJSON type: {db_geom['type']}")
if db_geom['type'] == 'MultiPolygon':
    for i, poly in enumerate(db_geom['coordinates']):
        total = sum(len(ring) for ring in poly)
        print(f"    Polygon {i}: {len(poly)} rings, {total} coords")
        # Show extent of each polygon
        all_coords = [c for ring in poly for c in ring]
        lons = [c[0] for c in all_coords]
        lats = [c[1] for c in all_coords]
        print(f"      lon: {min(lons):.2f} - {max(lons):.2f}, lat: {min(lats):.2f} - {max(lats):.2f}")

# 2. Download fresh from Nominatim
print("\n=== Downloading fresh from Nominatim (R1329568) ===")
url = "https://nominatim.openstreetmap.org/lookup"
params = {
    'osm_ids': 'R1329568',
    'format': 'geojson',
    'polygon_geojson': 1,
    'polygon_threshold': 0
}
resp = requests.get(url, params=params, headers=HEADERS, timeout=60)
data = resp.json()
feat = data['features'][0]
nom_geom = feat['geometry']
print(f"  Nominatim type: {nom_geom['type']}")

if nom_geom['type'] == 'MultiPolygon':
    total_pts = 0
    for i, poly in enumerate(nom_geom['coordinates']):
        pts = sum(len(ring) for ring in poly)
        total_pts += pts
        all_coords = [c for ring in poly for c in ring]
        lons = [c[0] for c in all_coords]
        lats = [c[1] for c in all_coords]
        print(f"    Polygon {i}: {len(poly)} rings, {pts} coords, "
              f"lon: {min(lons):.2f}-{max(lons):.2f}, lat: {min(lats):.2f}-{max(lats):.2f}")
    print(f"  Total: {len(nom_geom['coordinates'])} polygons, {total_pts} points")
elif nom_geom['type'] == 'Polygon':
    total_pts = sum(len(ring) for ring in nom_geom['coordinates'])
    print(f"  Polygon: {len(nom_geom['coordinates'])} rings, {total_pts} coords")
    
    # Convert to MultiPolygon for DB
    nom_geom = {'type': 'MultiPolygon', 'coordinates': [nom_geom['coordinates']]}
    print(f"  Converted to MultiPolygon")

# 3. Replace DB geometry with fresh Nominatim geometry
district_id = row[0]
region_id = row[7]
geom_json = json.dumps(nom_geom)

print(f"\n=== Updating district id={district_id} with fresh geometry ===")
with e.begin() as c:
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
    
    print(f"Updated: {v[0]} pts, {v[1]} parts, area={v[2]:.0f} km2")
    print(f"  Bbox: lon {v[3]:.2f}-{v[5]:.2f}, lat {v[4]:.2f}-{v[6]:.2f}")
    print(f"  Simplified: {v[7]} pts")

print("\nDone!")
