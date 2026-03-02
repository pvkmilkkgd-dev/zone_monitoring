"""Check if DNR districts still have inner rings and what the API returns."""
import sqlalchemy as sa
from sqlalchemy import text
import json

DB_URL = "postgresql://postgres:postgres@localhost:5432/zone_monitoring"
engine = sa.create_engine(DB_URL)

with engine.connect() as conn:
    # 1. Check for remaining inner rings
    print("=== Checking for inner rings in DB ===")
    rows = conn.execute(text("""
        SELECT d.name,
               ST_GeometryType(d.geom) as gtype,
               ST_NumGeometries(d.geom) as num_geoms,
               (SELECT SUM(ST_NumInteriorRings(poly.geom))
                FROM ST_Dump(d.geom) AS poly) as total_holes,
               ROUND(ST_Area(d.geom::geography)/1000000) as area_km2,
               ROUND(ST_Area(
                   ST_SimplifyPreserveTopology(ST_MakeValid(d.geom), 0.001)::geography
               )/1000000) as area_simplified_km2
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%Донецк%'
          AND d.geom IS NOT NULL
        ORDER BY d.name
    """)).fetchall()

    for r in rows:
        holes = int(r[3]) if r[3] else 0
        area_diff = int(r[4]) - int(r[5]) if r[5] else 0
        flag = ""
        if holes > 0:
            flag += f" HOLES={holes}"
        if abs(area_diff) > 10:
            flag += f" SIMPLIFY_DIFF={area_diff}km2"
        print(f"{r[0]:55s} | {r[1]:20s} | geoms={r[2]} | {int(r[4]):6d} km2 | simpl={int(r[5]):6d} km2{flag}")

    # 2. Check coverage - find gaps by comparing total area vs oblast area
    print("\n=== Checking total coverage ===")
    result = conn.execute(text("""
        SELECT
            ROUND(ST_Area(ST_Union(d.geom)::geography)/1000000) as union_area,
            COUNT(*) as count
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%Донецк%'
          AND d.geom IS NOT NULL
    """)).fetchone()
    print(f"Union of all districts: {int(result[0])} km2 ({result[1]} districts)")

    # 3. Check if simplification creates gaps
    print("\n=== Checking simplified coverage ===")
    result2 = conn.execute(text("""
        SELECT
            ROUND(ST_Area(ST_Union(
                ST_SimplifyPreserveTopology(ST_MakeValid(d.geom), 0.001)
            )::geography)/1000000) as union_area_simplified
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%Донецк%'
          AND d.geom IS NOT NULL
    """)).fetchone()
    print(f"Union of simplified districts: {int(result2[0])} km2")

    # 4. Check for geometry validity issues
    print("\n=== Checking validity ===")
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
    else:
        print("  All geometries are valid")
