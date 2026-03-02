"""
Fix Arkhangelsk Oblast display: clip Arctic extremes.

Problem: Приморский МО includes Franz Josef Land (79-82°N) making
the map zoom way out. Новая Земля (70-77°N) also pushes the view north.

Solution:
1. Clip Приморский район to mainland only (below 68°N)
2. Update region geometry to reasonable bounds (below 78°N, keeping Novaya Zemlya)
3. Keep Новая Земля as is
"""
import sys, os, json
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')

from sqlalchemy import create_engine, text
from app.core.config import settings

ENGINE = create_engine(settings.DATABASE_URL)


def main():
    with ENGINE.connect() as c:
        rid = str(c.execute(text(
            "SELECT id FROM regions WHERE name = 'Архангельская область'"
        )).fetchone()[0])
    
    # Step 1: Check current state of Приморский
    print("=== Before ===")
    with ENGINE.connect() as c:
        pr = c.execute(text(
            "SELECT id, name, "
            "ST_Area(geom::geography)/1e6, "
            "ST_YMin(geom), ST_YMax(geom) "
            "FROM districts WHERE region_id = :rid AND name LIKE '%Приморск%'"
        ), {"rid": rid}).fetchone()
        print(f"Приморский: {pr[2]:.0f} km2, lat {pr[3]:.2f} - {pr[4]:.2f}")
        pr_id = str(pr[0])
        
        nz = c.execute(text(
            "SELECT id, name, "
            "ST_Area(geom::geography)/1e6, "
            "ST_YMin(geom), ST_YMax(geom) "
            "FROM districts WHERE region_id = :rid AND name LIKE '%Новая Земля%'"
        ), {"rid": rid}).fetchone()
        if nz:
            print(f"Новая Земля: {nz[2]:.0f} km2, lat {nz[3]:.2f} - {nz[4]:.2f}")
        
        rg = c.execute(text(
            "SELECT ST_Area(geom::geography)/1e6, "
            "ST_YMin(geom), ST_YMax(geom) "
            "FROM regions WHERE id = :rid"
        ), {"rid": rid}).fetchone()
        print(f"Region: {rg[0]:.0f} km2, lat {rg[1]:.2f} - {rg[2]:.2f}")
    
    # Step 2: Clip Приморский район to mainland only (below 68°N)
    # This removes Franz Josef Land (79-82°N) while keeping mainland (63-66°N)
    print("\n=== Clipping Приморский район (below 68°N) ===")
    with ENGINE.connect() as c:
        # Create a clipping box: whole longitude range, latitude up to 68°N
        c.execute(text("""
            UPDATE districts SET
                geom = ST_Multi(ST_MakeValid(
                    ST_Intersection(
                        geom,
                        ST_MakeEnvelope(0, 0, 180, 68, 4326)
                    )
                )),
                geom_simplified = ST_SimplifyPreserveTopology(
                    ST_Multi(ST_MakeValid(
                        ST_Intersection(
                            geom,
                            ST_MakeEnvelope(0, 0, 180, 68, 4326)
                        )
                    )), 0.005)
            WHERE id = :id
        """), {"id": pr_id})
        c.commit()
        
        # Verify
        pr_new = c.execute(text(
            "SELECT ST_Area(geom::geography)/1e6, "
            "ST_YMin(geom), ST_YMax(geom), ST_NPoints(geom) "
            "FROM districts WHERE id = :id"
        ), {"id": pr_id}).fetchone()
        print(f"Приморский after clip: {pr_new[0]:.0f} km2, lat {pr_new[1]:.2f} - {pr_new[2]:.2f}, {pr_new[3]} pts")
    
    # Step 3: Update region geometry - clip to reasonable bounds
    # Keep Novaya Zemlya (up to 77°N) but remove Franz Josef Land (79-82°N)
    print("\n=== Clipping region geometry (below 78°N) ===")
    with ENGINE.connect() as c:
        c.execute(text("""
            UPDATE regions SET
                geom = ST_Multi(ST_MakeValid(
                    ST_Intersection(
                        geom,
                        ST_MakeEnvelope(0, 0, 180, 78, 4326)
                    )
                )),
                geom_simplified = ST_SimplifyPreserveTopology(
                    ST_Multi(ST_MakeValid(
                        ST_Intersection(
                            geom,
                            ST_MakeEnvelope(0, 0, 180, 78, 4326)
                        )
                    )), 0.01)
            WHERE id = :rid
        """), {"rid": rid})
        c.commit()
        
        rg_new = c.execute(text(
            "SELECT ST_Area(geom::geography)/1e6, "
            "ST_YMin(geom), ST_YMax(geom) "
            "FROM regions WHERE id = :rid"
        ), {"rid": rid}).fetchone()
        print(f"Region after clip: {rg_new[0]:.0f} km2, lat {rg_new[1]:.2f} - {rg_new[2]:.2f}")
    
    # Step 4: Final stats
    print(f"\n{'='*60}")
    print("=== After ===")
    with ENGINE.connect() as c:
        rows = c.execute(text(
            "SELECT name, ST_Area(geom::geography)/1e6, "
            "ST_YMin(geom), ST_YMax(geom) "
            "FROM districts WHERE region_id = :rid ORDER BY name"
        ), {"rid": rid}).fetchall()
        
        total = sum(r[1] for r in rows)
        rarea = c.execute(text(
            "SELECT ST_Area(geom::geography)/1e6 FROM regions WHERE id = :rid"
        ), {"rid": rid}).fetchone()[0]
    
    print(f"Region: {rarea:.0f} km2")
    print(f"Districts ({len(rows)}):")
    for name, area, ymin, ymax in rows:
        print(f"  {area:>10.0f} km2  lat {ymin:.1f}-{ymax:.1f}  {name}")
    print(f"\nTotal: {total:.0f} km2")
    print(f"Coverage: {total/rarea*100:.1f}%")
    
    # Overall
    with ENGINE.connect() as c:
        stats = c.execute(text("SELECT COUNT(id), COUNT(geom) FROM districts")).fetchone()
    print(f"\nOverall: {stats[0]} districts, {stats[1]} with geometry")


if __name__ == "__main__":
    main()
