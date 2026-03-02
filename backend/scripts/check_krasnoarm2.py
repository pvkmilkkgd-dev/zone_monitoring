"""Deep check of Красноармейский МО - self-intersections, overlaps, topology."""
import sqlalchemy as sa
from sqlalchemy import text

DB_URL = "postgresql://postgres:postgres@localhost:5432/zone_monitoring"
engine = sa.create_engine(DB_URL)

with engine.connect() as conn:
    # 1. Check if polygon is simple (no self-intersections)
    print("=== Self-intersection check ===")
    row = conn.execute(text("""
        SELECT ST_IsSimple(d.geom),
               ST_IsValid(d.geom),
               ST_IsValidReason(d.geom)
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%Донецк%'
          AND d.name = 'Красноармейский муниципальный округ'
    """)).fetchone()
    print(f"  IsSimple: {row[0]}")
    print(f"  IsValid: {row[1]}")
    print(f"  Reason: {row[2]}")

    # 2. Get bbox of Красноармейский
    print("\n=== Bounding box ===")
    bbox = conn.execute(text("""
        SELECT ST_XMin(d.geom), ST_YMin(d.geom), ST_XMax(d.geom), ST_YMax(d.geom),
               ST_AsText(ST_Centroid(d.geom))
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%Донецк%'
          AND d.name = 'Красноармейский муниципальный округ'
    """)).fetchone()
    print(f"  BBox: [{bbox[0]:.4f}, {bbox[1]:.4f}] - [{bbox[2]:.4f}, {bbox[3]:.4f}]")
    print(f"  Centroid: {bbox[4]}")

    # 3. Find ALL other DNR districts that overlap with Красноармейский
    print("\n=== Overlapping districts ===")
    overlaps = conn.execute(text("""
        SELECT d2.name,
               ROUND(ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1000000) as overlap_km2,
               ROUND(ST_Area(d2.geom::geography)/1000000) as d2_area,
               CASE WHEN ST_Contains(d1.geom, d2.geom) THEN 'CONTAINED'
                    WHEN ST_Within(d1.geom, d2.geom) THEN 'WITHIN'
                    ELSE 'PARTIAL'
               END as relation
        FROM districts d1
        JOIN districts d2 ON d1.id != d2.id AND ST_Intersects(d1.geom, d2.geom)
        JOIN regions r1 ON d1.region_id = r1.id
        JOIN regions r2 ON d2.region_id = r2.id
        WHERE r1.name LIKE '%Донецк%'
          AND r2.name LIKE '%Донецк%'
          AND d1.name = 'Красноармейский муниципальный округ'
          AND ST_Area(ST_Intersection(d1.geom, d2.geom)::geography) > 1000
        ORDER BY overlap_km2 DESC
    """)).fetchall()

    if overlaps:
        for r in overlaps:
            print(f"  {r[0]:55s} | overlap={int(r[1]):6d} km2 | total={int(r[2]):6d} km2 | {r[3]}")
    else:
        print("  No overlapping districts found")

    # 4. Check what the simplified GeoJSON looks like for the API
    print("\n=== API output check ===")
    api_check = conn.execute(text("""
        SELECT
            ST_NumGeometries(
                ST_ForceRHR(ST_SimplifyPreserveTopology(ST_MakeValid(d.geom), 0.0001))
            ) as num_geoms,
            ST_NumInteriorRings(
                (ST_Dump(
                    ST_ForceRHR(ST_SimplifyPreserveTopology(ST_MakeValid(d.geom), 0.0001))
                )).geom
            ) as holes,
            ST_NPoints(
                ST_ForceRHR(ST_SimplifyPreserveTopology(ST_MakeValid(d.geom), 0.0001))
            ) as npoints
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%Донецк%'
          AND d.name = 'Красноармейский муниципальный округ'
    """)).fetchone()
    print(f"  After ST_ForceRHR + simplify: {api_check[0]} geoms, {api_check[1]} holes, {api_check[2]} points")

    # 5. Check ALL DNR districts for overlaps that could cause visual holes
    print("\n=== ALL overlapping pairs in DNR ===")
    all_overlaps = conn.execute(text("""
        SELECT d1.name, d2.name,
               ROUND(ST_Area(ST_Intersection(ST_MakeValid(d1.geom), ST_MakeValid(d2.geom))::geography)/1000000) as overlap_km2
        FROM districts d1
        JOIN districts d2 ON d1.id < d2.id AND ST_Intersects(d1.geom, d2.geom)
        JOIN regions r1 ON d1.region_id = r1.id
        JOIN regions r2 ON d2.region_id = r2.id
        WHERE r1.name LIKE '%Донецк%'
          AND r2.name LIKE '%Донецк%'
          AND d1.geom IS NOT NULL
          AND d2.geom IS NOT NULL
          AND ST_Area(ST_Intersection(ST_MakeValid(d1.geom), ST_MakeValid(d2.geom))::geography) > 1000000
        ORDER BY overlap_km2 DESC
    """)).fetchall()

    if all_overlaps:
        print(f"  Found {len(all_overlaps)} overlapping pairs (> 1 km2):")
        for r in all_overlaps:
            print(f"  {r[0]:40s} <-> {r[1]:40s} | {int(r[2]):6d} km2")
    else:
        print("  No significant overlaps found")
