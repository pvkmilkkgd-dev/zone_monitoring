"""Check point counts for districts to assess geometry quality."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

e = create_engine(settings.DATABASE_URL)

# Check Arkhangelsk specifically
with e.connect() as c:
    rows = c.execute(text("""
        SELECT d.name, ST_NPoints(d.geom) as pts, ST_NPoints(d.geom_simplified) as pts_s,
               ST_Area(d.geom::geography)/1e6 as area_km2
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Архангельская область'
        ORDER BY ST_NPoints(d.geom)
    """)).fetchall()

print("=== Архангельская область ===")
print(f"{'Name':45s} {'Points':>7s} {'Simplified':>10s} {'Area km2':>10s}")
for name, pts, pts_s, area in rows:
    print(f"{name:45s} {pts:>7d} {pts_s:>10d} {area:>10.0f}")

# Check a few other regions for comparison
print("\n=== Comparison: Average points per district by region ===")
with e.connect() as c:
    rows = c.execute(text("""
        SELECT r.name, 
               COUNT(d.id) as cnt,
               AVG(ST_NPoints(d.geom))::int as avg_pts,
               MIN(ST_NPoints(d.geom)) as min_pts,
               MAX(ST_NPoints(d.geom)) as max_pts
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE d.geom IS NOT NULL
        GROUP BY r.name
        ORDER BY AVG(ST_NPoints(d.geom))
        LIMIT 20
    """)).fetchall()

print(f"{'Region':45s} {'Cnt':>4s} {'Avg pts':>8s} {'Min':>6s} {'Max':>6s}")
for name, cnt, avg, mn, mx in rows:
    print(f"{name:45s} {cnt:>4d} {avg:>8d} {mn:>6d} {mx:>6d}")

# Overall stats
print("\n=== Overall ===")
with e.connect() as c:
    stats = c.execute(text("""
        SELECT AVG(ST_NPoints(geom))::int, MIN(ST_NPoints(geom)), MAX(ST_NPoints(geom)),
               PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ST_NPoints(geom))::int as median
        FROM districts WHERE geom IS NOT NULL
    """)).fetchone()
print(f"Average: {stats[0]}, Min: {stats[1]}, Max: {stats[2]}, Median: {stats[3]}")

# Check specifically the low-point districts
print("\n=== Districts with < 100 points ===")
with e.connect() as c:
    rows = c.execute(text("""
        SELECT r.name as region, d.name, ST_NPoints(d.geom) as pts
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE ST_NPoints(d.geom) < 100 AND d.geom IS NOT NULL
        ORDER BY ST_NPoints(d.geom)
        LIMIT 30
    """)).fetchall()
for reg, name, pts in rows:
    print(f"  {pts:>4d} pts  {reg} / {name}")
