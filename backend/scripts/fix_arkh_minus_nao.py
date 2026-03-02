"""
Fix Arkhangelsk Oblast region geometry:
Subtract Nenets AO polygon from it, since Nenets is a separate region in the DB.
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
        # Get both region IDs
        arkh = c.execute(text(
            "SELECT id, ST_Area(geom::geography)/1e6, ST_NPoints(geom) "
            "FROM regions WHERE name = 'Архангельская область'"
        )).fetchone()
        nen = c.execute(text(
            "SELECT id, ST_Area(geom::geography)/1e6, ST_NPoints(geom) "
            "FROM regions WHERE name LIKE '%Ненец%'"
        )).fetchone()
        
        print(f"Архангельская: {arkh[1]:.0f} km2, {arkh[2]} pts")
        print(f"Ненецкий АО:   {nen[1]:.0f} km2, {nen[2]} pts")
        
        # Check overlap
        overlap = c.execute(text("""
            SELECT ST_Area(ST_Intersection(a.geom, b.geom)::geography)/1e6
            FROM regions a, regions b
            WHERE a.id = :a AND b.id = :b
        """), {"a": str(arkh[0]), "b": str(nen[0])}).fetchone()[0]
        print(f"Overlap: {overlap:.0f} km2")
    
    if overlap < 1000:
        print("\nNo significant overlap - geometries are already separate.")
        print("The issue might be elsewhere. Let me check the region geometry shape...")
        
        # Show bbox and centroid
        with ENGINE.connect() as c:
            info = c.execute(text("""
                SELECT ST_XMin(geom), ST_YMin(geom), ST_XMax(geom), ST_YMax(geom),
                       ST_AsText(ST_Centroid(geom))
                FROM regions WHERE id = :rid
            """), {"rid": str(arkh[0])}).fetchone()
            print(f"Bbox: ({info[0]:.2f}, {info[1]:.2f}) - ({info[2]:.2f}, {info[3]:.2f})")
            print(f"Centroid: {info[4]}")
        return
    
    # Subtract Nenets from Arkhangelsk
    print(f"\nSubtracting Ненецкий АО from Архангельская область...")
    with ENGINE.connect() as c:
        c.execute(text("""
            UPDATE regions SET
                geom = ST_Multi(ST_MakeValid(
                    ST_Difference(
                        (SELECT geom FROM regions WHERE id = :arkh_id),
                        (SELECT geom FROM regions WHERE id = :nen_id)
                    )
                )),
                geom_simplified = ST_SimplifyPreserveTopology(
                    ST_Multi(ST_MakeValid(
                        ST_Difference(
                            (SELECT geom FROM regions WHERE id = :arkh_id),
                            (SELECT geom FROM regions WHERE id = :nen_id)
                        )
                    )), 0.01)
            WHERE id = :arkh_id
        """), {"arkh_id": str(arkh[0]), "nen_id": str(nen[0])})
        c.commit()
    
    # Verify
    with ENGINE.connect() as c:
        new = c.execute(text(
            "SELECT ST_Area(geom::geography)/1e6, ST_NPoints(geom), "
            "ST_XMin(geom), ST_YMin(geom), ST_XMax(geom), ST_YMax(geom) "
            "FROM regions WHERE id = :rid"
        ), {"rid": str(arkh[0])}).fetchone()
        print(f"\nNew Архангельская: {new[0]:.0f} km2, {new[1]} pts")
        print(f"Bbox: ({new[2]:.2f}, {new[3]:.2f}) - ({new[4]:.2f}, {new[5]:.2f})")
        
        # District coverage
        darea = c.execute(text("""
            SELECT SUM(ST_Area(d.geom::geography)/1e6)
            FROM districts d WHERE d.region_id = :rid AND d.geom IS NOT NULL
        """), {"rid": str(arkh[0])}).fetchone()[0]
        print(f"District area: {darea:.0f} km2")
        print(f"Coverage: {darea/new[0]*100:.1f}%")
    
    # Also check if similar issue exists for other "parent" regions
    # Тюменская область includes ХМАО and ЯНАО
    # Архангельская includes НАО  
    print("\n=== Checking other parent-child regions ===")
    pairs = [
        ("Тюменская область", ["Ханты-Мансийский автономный округ%", "Ямало-Ненецкий автономный округ%"]),
    ]
    
    for parent, children in pairs:
        with ENGINE.connect() as c:
            p = c.execute(text(
                "SELECT id, name, ST_Area(geom::geography)/1e6 FROM regions WHERE name = :n"
            ), {"n": parent}).fetchone()
            if not p:
                continue
            
            print(f"\n{p[1]}: {p[2]:.0f} km2")
            for child_pattern in children:
                ch = c.execute(text(
                    "SELECT id, name, ST_Area(geom::geography)/1e6 "
                    "FROM regions WHERE name LIKE :n"
                ), {"n": child_pattern}).fetchone()
                if ch:
                    overlap = c.execute(text("""
                        SELECT ST_Area(ST_Intersection(a.geom, b.geom)::geography)/1e6
                        FROM regions a, regions b
                        WHERE a.id = :a AND b.id = :b
                    """), {"a": str(p[0]), "b": str(ch[0])}).fetchone()[0]
                    print(f"  {ch[1]}: {ch[2]:.0f} km2, overlap: {overlap:.0f} km2")


if __name__ == "__main__":
    main()
