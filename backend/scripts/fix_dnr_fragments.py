"""Remove tiny fragments from multi-part DNR geometries using Python."""
import sqlalchemy as sa
from sqlalchemy import text
import json

DB_URL = "postgresql://postgres:postgres@localhost:5432/zone_monitoring"
engine = sa.create_engine(DB_URL)

with engine.begin() as conn:
    # Get all multi-part DNR districts
    rows = conn.execute(text("""
        SELECT d.id, d.name, ST_NumGeometries(d.geom) as num_parts,
               ST_AsGeoJSON(d.geom)::text as geojson
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%Донецк%'
          AND d.geom IS NOT NULL
          AND ST_NumGeometries(d.geom) > 1
        ORDER BY d.name
    """)).fetchall()

    print(f"Found {len(rows)} multi-part districts to clean up:\n")

    for row in rows:
        did, name, num_parts = row[0], row[1], row[2]
        geojson = json.loads(row[3])

        if geojson["type"] != "MultiPolygon":
            print(f"  {name}: type={geojson['type']}, skipping")
            continue

        # Find the largest polygon and keep only significant ones
        polys_with_area = []
        for i, coords in enumerate(geojson["coordinates"]):
            # Rough area estimate (just for comparison)
            ring = coords[0]  # outer ring
            n = len(ring)
            area = 0
            for j in range(n):
                x1, y1 = ring[j]
                x2, y2 = ring[(j + 1) % n]
                area += x1 * y2 - x2 * y1
            area = abs(area) / 2
            polys_with_area.append((i, area, coords))

        max_area = max(a for _, a, _ in polys_with_area)
        # Keep polygons that are at least 1% of the largest
        threshold = max_area * 0.01
        significant = [(i, a, c) for i, a, c in polys_with_area if a >= threshold]

        removed = num_parts - len(significant)
        if removed > 0:
            # Build new MultiPolygon with only significant parts
            new_coords = [c for _, _, c in significant]
            if len(new_coords) == 1:
                new_geojson = {"type": "Polygon", "coordinates": new_coords[0]}
            else:
                new_geojson = {"type": "MultiPolygon", "coordinates": new_coords}

            new_geojson_str = json.dumps(new_geojson)
            conn.execute(text("""
                UPDATE districts
                SET geom = ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))
                WHERE id = :id
            """), {"geojson": new_geojson_str, "id": did})
            print(f"  {name}: {num_parts} -> {len(significant)} parts (removed {removed} tiny fragments)")
        else:
            print(f"  {name}: {num_parts} parts (all significant, no change)")

    # Final check
    print("\n" + "=" * 70)
    print("Final state:")
    rows2 = conn.execute(text("""
        SELECT d.name, ST_NumGeometries(d.geom),
               ROUND(ST_Area(d.geom::geography)/1000000) as area_km2
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%Донецк%'
          AND d.geom IS NOT NULL
        ORDER BY d.name
    """)).fetchall()
    total = 0
    for r in rows2:
        area = int(r[2])
        total += area
        parts = f" ({r[1]} parts)" if r[1] > 1 else ""
        print(f"  {r[0]:55s} | {area:6d} km2{parts}")
    print(f"  {'TOTAL':55s} | {total:6d} km2")
