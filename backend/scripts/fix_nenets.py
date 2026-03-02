"""
Fix Nenets AO: clip district geometries to region boundary.
The Zapolyarny district geometry extends beyond the region border.
Solution: ST_Intersection of each district with the region boundary.
"""
import sys, os
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)


def main():
    with ENGINE.connect() as c:
        rid = str(c.execute(text(
            "SELECT id FROM regions WHERE name LIKE '%Ненец%'"
        )).fetchone()[0])
    
    print("Before:")
    with ENGINE.connect() as c:
        rows = c.execute(text(
            "SELECT name, ST_Area(geom::geography)/1e6, ST_NPoints(geom) "
            "FROM districts WHERE region_id = :rid ORDER BY name"
        ), {"rid": rid}).fetchall()
        for name, area, pts in rows:
            print(f"  {area:>10.0f} km2  {pts:>6d} pts  {name}")
        
        rarea = c.execute(text(
            "SELECT ST_Area(geom::geography)/1e6 FROM regions WHERE id = :rid"
        ), {"rid": rid}).fetchone()[0]
        total = sum(r[1] for r in rows)
        print(f"  Total: {total:.0f} km2, Region: {rarea:.0f} km2, Coverage: {total/rarea*100:.1f}%")
    
    # Clip districts to region boundary
    print("\nClipping districts to region boundary...")
    with ENGINE.connect() as c:
        c.execute(text("""
            UPDATE districts d SET
                geom = ST_Multi(ST_MakeValid(
                    ST_Intersection(d.geom, r.geom)
                )),
                geom_simplified = ST_SimplifyPreserveTopology(
                    ST_Multi(ST_MakeValid(
                        ST_Intersection(d.geom, r.geom)
                    )), 0.005)
            FROM regions r
            WHERE d.region_id = r.id
              AND d.region_id = :rid
        """), {"rid": rid})
        c.commit()
    
    print("\nAfter:")
    with ENGINE.connect() as c:
        rows = c.execute(text(
            "SELECT name, ST_Area(geom::geography)/1e6, ST_NPoints(geom) "
            "FROM districts WHERE region_id = :rid ORDER BY name"
        ), {"rid": rid}).fetchall()
        total = 0
        for name, area, pts in rows:
            print(f"  {area:>10.0f} km2  {pts:>6d} pts  {name}")
            total += area
        print(f"  Total: {total:.0f} km2, Region: {rarea:.0f} km2, Coverage: {total/rarea*100:.1f}%")
    
    # Now check if this same issue exists in other regions
    print("\n=== Checking ALL regions for coverage > 110% ===")
    with ENGINE.connect() as c:
        problem_regions = c.execute(text("""
            SELECT r.name, 
                   ST_Area(r.geom::geography)/1e6 as rarea,
                   SUM(ST_Area(d.geom::geography)/1e6) as darea,
                   COUNT(d.id) as cnt
            FROM regions r 
            JOIN districts d ON d.region_id = r.id AND d.geom IS NOT NULL
            GROUP BY r.id, r.name, r.geom
            HAVING SUM(ST_Area(d.geom::geography)/1e6) > ST_Area(r.geom::geography)/1e6 * 1.1
            ORDER BY SUM(ST_Area(d.geom::geography)/1e6) / ST_Area(r.geom::geography)/1e6 DESC
        """)).fetchall()
    
    if problem_regions:
        print(f"Found {len(problem_regions)} regions with coverage > 110%:")
        for name, rarea, darea, cnt in problem_regions:
            coverage = darea / rarea * 100
            print(f"  {coverage:>6.1f}%  {name} ({cnt} districts, region={rarea:.0f}, districts={darea:.0f})")
    else:
        print("All regions have reasonable coverage!")


if __name__ == "__main__":
    main()
