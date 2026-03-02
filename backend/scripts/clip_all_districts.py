"""
Clip ALL district geometries to their region boundaries.
This fixes districts that extend beyond the region polygon,
which causes visual artifacts on the map.
"""
import sys, os
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)


def main():
    # First, identify all problem regions
    print("=== Regions with district coverage > 105% ===")
    with ENGINE.connect() as c:
        problems = c.execute(text("""
            SELECT r.id, r.name, 
                   ST_Area(r.geom::geography)/1e6 as rarea,
                   SUM(ST_Area(d.geom::geography)/1e6) as darea,
                   COUNT(d.id) as cnt
            FROM regions r 
            JOIN districts d ON d.region_id = r.id AND d.geom IS NOT NULL
            GROUP BY r.id, r.name, r.geom
            HAVING SUM(ST_Area(d.geom::geography)/1e6) > ST_Area(r.geom::geography)/1e6 * 1.05
            ORDER BY SUM(ST_Area(d.geom::geography)/1e6) / ST_Area(r.geom::geography)/1e6 DESC
        """)).fetchall()
    
    print(f"Found {len(problems)} regions to fix:")
    for rid, name, rarea, darea, cnt in problems:
        coverage = darea / rarea * 100
        print(f"  {coverage:>6.1f}%  {name} ({cnt} districts)")
    
    # Clip all districts in problem regions to their region boundaries
    for rid, name, rarea, darea, cnt in problems:
        coverage = darea / rarea * 100
        print(f"\nClipping: {name} ({coverage:.1f}%)...")
        
        with ENGINE.connect() as c:
            # Clip each district to the region polygon
            result = c.execute(text("""
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
                  AND d.geom IS NOT NULL
                RETURNING d.name
            """), {"rid": str(rid)})
            updated = result.fetchall()
            c.commit()
        
        # Check new coverage
        with ENGINE.connect() as c:
            new = c.execute(text("""
                SELECT SUM(ST_Area(d.geom::geography)/1e6)
                FROM districts d WHERE d.region_id = :rid AND d.geom IS NOT NULL
            """), {"rid": str(rid)}).fetchone()[0]
        
        new_coverage = new / rarea * 100
        print(f"  Updated {len(updated)} districts: {coverage:.1f}% -> {new_coverage:.1f}%")
    
    # Final verification
    print(f"\n{'='*60}")
    print("=== Final check: regions with coverage > 105% ===")
    with ENGINE.connect() as c:
        still = c.execute(text("""
            SELECT r.name, 
                   ST_Area(r.geom::geography)/1e6 as rarea,
                   SUM(ST_Area(d.geom::geography)/1e6) as darea
            FROM regions r 
            JOIN districts d ON d.region_id = r.id AND d.geom IS NOT NULL
            GROUP BY r.id, r.name, r.geom
            HAVING SUM(ST_Area(d.geom::geography)/1e6) > ST_Area(r.geom::geography)/1e6 * 1.05
            ORDER BY r.name
        """)).fetchall()
    
    if still:
        print(f"Still {len(still)} regions with issues:")
        for name, rarea, darea in still:
            print(f"  {darea/rarea*100:.1f}%  {name}")
    else:
        print("All regions now have proper coverage!")
    
    # Overall stats
    with ENGINE.connect() as c:
        stats = c.execute(text("SELECT COUNT(id), COUNT(geom) FROM districts")).fetchone()
    print(f"\nOverall: {stats[0]} districts, {stats[1]} with geometry")


if __name__ == "__main__":
    main()
