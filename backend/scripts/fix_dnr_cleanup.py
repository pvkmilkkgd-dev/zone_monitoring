"""
Clean up DNR geometries:
1. Make all geometries valid with ST_MakeValid + ST_Buffer(0)
2. Remove tiny polygon fragments (< 1 km2)
3. Ensure no self-intersections
"""
import sqlalchemy as sa
from sqlalchemy import text

DB_URL = "postgresql://postgres:postgres@localhost:5432/zone_monitoring"
engine = sa.create_engine(DB_URL)

with engine.begin() as conn:
    # Step 1: Fix validity of all DNR district geometries
    print("Step 1: Fixing geometry validity...")
    result = conn.execute(text("""
        UPDATE districts d
        SET geom = ST_Multi(ST_Buffer(ST_MakeValid(d.geom), 0))
        FROM regions r
        WHERE d.region_id = r.id
          AND r.name LIKE '%Донецк%'
          AND d.geom IS NOT NULL
        RETURNING d.name, ST_IsValid(d.geom) as valid
    """))
    for r in result:
        status = "OK" if r[1] else "STILL INVALID"
        print(f"  {r[0]:55s} | {status}")

    # Step 2: Remove tiny fragments - keep only significant polygons
    print("\nStep 2: Removing tiny fragments (< 0.5 km2)...")
    result2 = conn.execute(text("""
        UPDATE districts d
        SET geom = sub.cleaned_geom
        FROM regions r,
        LATERAL (
            SELECT ST_SetSRID(
                ST_Multi(
                    ST_Collect(poly.geom)
                ),
                4326
            ) as cleaned_geom
            FROM ST_Dump(d.geom) AS poly
            WHERE ST_Area(poly.geom::geography) > 500000  -- > 0.5 km2
        ) sub
        WHERE d.region_id = r.id
          AND r.name LIKE '%Донецк%'
          AND d.geom IS NOT NULL
          AND ST_NumGeometries(d.geom) > 1
        RETURNING d.name,
                  ST_NumGeometries(d.geom) as num_geoms,
                  ROUND(ST_Area(d.geom::geography)/1000000) as area_km2
    """))
    cleaned = list(result2)
    if cleaned:
        for r in cleaned:
            print(f"  {r[0]:55s} | {r[1]} parts | {int(r[2])} km2")
    else:
        print("  No multi-part geometries needed cleaning")

    # Step 3: Final validity check
    print("\nStep 3: Final validity check...")
    invalid = conn.execute(text("""
        SELECT d.name, ST_IsValidReason(d.geom)
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%Донецк%'
          AND d.geom IS NOT NULL
          AND NOT ST_IsValid(d.geom)
    """)).fetchall()
    if invalid:
        for r in invalid:
            print(f"  INVALID: {r[0]} - {r[1]}")
        # Force fix with aggressive approach
        print("  Applying aggressive fix...")
        conn.execute(text("""
            UPDATE districts d
            SET geom = ST_Multi(ST_Buffer(ST_Buffer(ST_MakeValid(d.geom), 0.0001), -0.0001))
            FROM regions r
            WHERE d.region_id = r.id
              AND r.name LIKE '%Донецк%'
              AND d.geom IS NOT NULL
              AND NOT ST_IsValid(d.geom)
        """))
    else:
        print("  All geometries are valid!")

    # Final summary
    print("\n" + "=" * 80)
    rows = conn.execute(text("""
        SELECT d.name,
               ST_NumGeometries(d.geom) as parts,
               ROUND(ST_Area(d.geom::geography)/1000000) as area_km2,
               ST_IsValid(d.geom) as valid
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%Донецк%'
          AND d.geom IS NOT NULL
        ORDER BY d.name
    """)).fetchall()
    total = 0
    for r in rows:
        area = int(r[2])
        total += area
        v = "OK" if r[3] else "BAD"
        print(f"{r[0]:55s} | parts={r[1]} | {area:6d} km2 | {v}")
    print(f"\nTotal: {total} km2")
