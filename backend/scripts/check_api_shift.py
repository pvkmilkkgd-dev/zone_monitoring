"""Check that ST_ShiftLongitude works for antimeridian districts."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy import create_engine, text

engine = create_engine("postgresql://postgres:postgres@localhost:5432/zone_monitoring")

with engine.connect() as conn:
    # Find Chukotka region
    row = conn.execute(text(
        "SELECT id, name FROM regions WHERE name LIKE '%Чукот%'"
    )).fetchone()
    if not row:
        print("Chukotka not found")
        sys.exit(1)
    
    region_id = row[0]
    print(f"Region: {row[1]} (id={region_id})")
    
    # Check raw coordinates
    rows = conn.execute(text("""
        SELECT name, 
               ST_XMin(geom) AS raw_min, ST_XMax(geom) AS raw_max,
               ST_XMin(
                 CASE WHEN ST_XMin(geom) < -170 AND ST_XMax(geom) > 170
                      THEN ST_ShiftLongitude(geom)
                      ELSE geom
                 END
               ) AS shifted_min,
               ST_XMax(
                 CASE WHEN ST_XMin(geom) < -170 AND ST_XMax(geom) > 170
                      THEN ST_ShiftLongitude(geom)
                      ELSE geom
                 END
               ) AS shifted_max
        FROM districts
        WHERE region_id = :rid AND geom IS NOT NULL
        ORDER BY name
    """), {"rid": region_id}).fetchall()
    
    for r in rows:
        print(f"  {r[0]}")
        print(f"    raw:     {r[1]:.4f} .. {r[2]:.4f}")
        print(f"    shifted: {r[3]:.4f} .. {r[4]:.4f}")
