"""Test Chaikin smoothing effect on district geometry."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)

with e.connect() as c:
    rid = str(c.execute(text(
        "SELECT id FROM regions WHERE name = 'Архангельская область'"
    )).fetchone()[0])
    
    rows = c.execute(text("""
        SELECT name,
               ST_NPoints(geom) as orig_pts,
               ST_NPoints(ST_ChaikinSmoothing(geom, 1)) as smooth1_pts,
               ST_NPoints(ST_ChaikinSmoothing(geom, 2)) as smooth2_pts,
               ST_NPoints(ST_ChaikinSmoothing(geom, 3)) as smooth3_pts,
               length(ST_AsGeoJSON(geom)::text) as orig_size,
               length(ST_AsGeoJSON(ST_ChaikinSmoothing(geom, 2))::text) as smooth2_size
        FROM districts
        WHERE region_id = :rid AND geom IS NOT NULL
        ORDER BY name
    """), {"rid": rid}).fetchall()

print(f"{'Name':45s} {'Orig':>6s} {'S1':>6s} {'S2':>6s} {'S3':>6s} {'Orig KB':>8s} {'S2 KB':>8s}")
for name, orig, s1, s2, s3, orig_sz, s2_sz in rows:
    print(f"{name:45s} {orig:>6d} {s1:>6d} {s2:>6d} {s3:>6d} {orig_sz/1024:>7.1f} {s2_sz/1024:>7.1f}")

# Test topology: check if smoothed adjacent districts have gaps
print("\n=== Topology check ===")
with e.connect() as c:
    # Check original topology: sum of all district areas vs region area
    orig = c.execute(text("""
        SELECT SUM(ST_Area(geom::geography))/1e6 FROM districts WHERE region_id = :rid
    """), {"rid": rid}).fetchone()[0]
    
    smooth = c.execute(text("""
        SELECT SUM(ST_Area(ST_ChaikinSmoothing(geom, 2)::geography))/1e6 
        FROM districts WHERE region_id = :rid
    """), {"rid": rid}).fetchone()[0]
    
    region_area = c.execute(text("""
        SELECT ST_Area(geom::geography)/1e6 FROM regions WHERE id = :rid
    """), {"rid": rid}).fetchone()[0]

print(f"Region area:           {region_area:.0f} km2")
print(f"Original districts:    {orig:.0f} km2")
print(f"Smoothed districts:    {smooth:.0f} km2")
print(f"Area change:           {(smooth-orig)/orig*100:.2f}%")
