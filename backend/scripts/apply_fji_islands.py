"""Replace Franz Josef Land blobs in Primorsky district with real island geometry"""
import sys, json, requests, time
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)
HEADERS = {'User-Agent': 'ZoneMonitoring/1.0'}

# 1. Get current Primorsky geometry and split into mainland vs FJL
with e.connect() as c:
    row = c.execute(text("""
        SELECT d.id, ST_AsGeoJSON(d.geom)::text
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Архангельская область' AND d.name LIKE '%Приморский%'
    """)).fetchone()

district_id = row[0]
geom = json.loads(row[1])

mainland_polys = []
arctic_polys = []
for poly in geom['coordinates']:
    all_coords = [c for ring in poly for c in ring]
    lats = [coord[1] for coord in all_coords]
    max_lat = max(lats)
    if max_lat > 75:  # Arctic islands
        arctic_polys.append(poly)
        pts = sum(len(ring) for ring in poly)
        print(f"  Arctic blob: {pts} pts, lat {min(lats):.1f}-{max_lat:.1f}")
    else:
        mainland_polys.append(poly)
        pts = sum(len(ring) for ring in poly)
        print(f"  Mainland: {pts} pts, lat {min(lats):.1f}-{max_lat:.1f}")

print(f"\nMainland parts: {len(mainland_polys)}, Arctic blobs to replace: {len(arctic_polys)}")

# 2. Download real Franz Josef Land geometry
print("\nDownloading Franz Josef Land archipelago (R3068295)...")
url = "https://nominatim.openstreetmap.org/lookup"
params = {
    'osm_ids': 'R3068295',
    'format': 'geojson',
    'polygon_geojson': 1,
    'polygon_threshold': 0
}
resp = requests.get(url, params=params, headers=HEADERS, timeout=60)
data = resp.json()
feat = data['features'][0]
fji_geom = feat['geometry']

if fji_geom['type'] == 'Polygon':
    fji_polys = [fji_geom['coordinates']]
elif fji_geom['type'] == 'MultiPolygon':
    fji_polys = fji_geom['coordinates']
else:
    print(f"Unexpected type: {fji_geom['type']}")
    sys.exit(1)

fji_total_pts = sum(sum(len(ring) for ring in poly) for poly in fji_polys)
print(f"  FJL: {len(fji_polys)} islands, {fji_total_pts} total points")

# Show some island stats
for i, poly in enumerate(fji_polys):
    pts = sum(len(ring) for ring in poly)
    if pts > 100:
        all_coords = [c for ring in poly for c in ring]
        lons = [coord[0] for coord in all_coords]
        lats = [coord[1] for coord in all_coords]
        print(f"    Island {i}: {pts} pts, lat {min(lats):.2f}-{max(lats):.2f}, lon {min(lons):.2f}-{max(lons):.2f}")

# 3. Combine: mainland parts + real FJL islands
new_coordinates = mainland_polys + fji_polys
new_geom = {'type': 'MultiPolygon', 'coordinates': new_coordinates}
new_total = sum(sum(len(ring) for ring in poly) for poly in new_coordinates)
print(f"\nNew geometry: {len(new_coordinates)} parts, {new_total} total points")

geom_json = json.dumps(new_geom)

# 4. Update district
print(f"\nUpdating Primorsky district (id={district_id})...")
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
               ST_YMin(geom), ST_YMax(geom),
               ST_NPoints(geom_simplified)
        FROM districts WHERE id = :did
    """), {'did': district_id}).fetchone()
    
    print(f"\nResult:")
    print(f"  Points: {v[0]} (was 3628)")
    print(f"  Parts: {v[1]} (was 5)")  
    print(f"  Area: {v[2]:.0f} km2 (was 115569)")
    print(f"  Lat: {v[3]:.1f} - {v[4]:.1f}")
    print(f"  Simplified: {v[5]} pts")

print("\nDone!")
