"""Check Красноармейский МО geometry in detail."""
import sqlalchemy as sa
from sqlalchemy import text
import json

DB_URL = "postgresql://postgres:postgres@localhost:5432/zone_monitoring"
engine = sa.create_engine(DB_URL)

with engine.connect() as conn:
    row = conn.execute(text("""
        SELECT d.name,
               ST_GeometryType(d.geom),
               ST_NumGeometries(d.geom),
               ST_NPoints(d.geom),
               ST_NumInteriorRings((ST_Dump(d.geom)).geom) as holes,
               ROUND(ST_Area(d.geom::geography)/1000000) as area_km2,
               ST_AsGeoJSON(d.geom)::text as geojson
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%Донецк%'
          AND d.name = 'Красноармейский муниципальный округ'
    """)).fetchone()

    print(f"Name: {row[0]}")
    print(f"Type: {row[1]}")
    print(f"Num geometries: {row[2]}")
    print(f"Num points: {row[3]}")
    print(f"Interior rings (holes): {row[4]}")
    print(f"Area: {int(row[5])} km2")

    geojson = json.loads(row[6])
    if geojson["type"] == "MultiPolygon":
        for i, poly in enumerate(geojson["coordinates"]):
            outer = poly[0]
            inner_count = len(poly) - 1
            # Rough area
            n = len(outer)
            area = 0
            for j in range(n):
                x1, y1 = outer[j]
                x2, y2 = outer[(j+1) % n]
                area += x1*y2 - x2*y1
            area = abs(area)/2
            print(f"\n  Polygon {i}: outer ring={len(outer)} pts, inner rings={inner_count}, rough_area={area:.4f}")
            if inner_count > 0:
                for k in range(1, len(poly)):
                    inner = poly[k]
                    n2 = len(inner)
                    iarea = 0
                    for j in range(n2):
                        x1, y1 = inner[j]
                        x2, y2 = inner[(j+1) % n2]
                        iarea += x1*y2 - x2*y1
                    iarea = abs(iarea)/2
                    print(f"    Inner ring {k}: {len(inner)} pts, rough_area={iarea:.6f}")
    elif geojson["type"] == "Polygon":
        outer = geojson["coordinates"][0]
        inner_count = len(geojson["coordinates"]) - 1
        print(f"\n  Polygon: outer ring={len(outer)} pts, inner rings={inner_count}")
        if inner_count > 0:
            for k in range(1, len(geojson["coordinates"])):
                inner = geojson["coordinates"][k]
                n2 = len(inner)
                iarea = 0
                for j in range(n2):
                    x1, y1 = inner[j]
                    x2, y2 = inner[(j+1) % n2]
                    iarea += x1*y2 - x2*y1
                iarea = abs(iarea)/2
                print(f"    Inner ring {k}: {len(inner)} pts, rough_area={iarea:.6f}")

    # Also check what the API returns after simplification
    print("\n--- After ST_MakeValid + simplification ---")
    row2 = conn.execute(text("""
        SELECT
            ST_NumInteriorRings(
                (ST_Dump(
                    ST_SimplifyPreserveTopology(ST_MakeValid(d.geom), 0.0001)
                )).geom
            ) as holes_simplified
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name LIKE '%Донецк%'
          AND d.name = 'Красноармейский муниципальный округ'
    """)).fetchone()
    print(f"Holes after simplification: {row2[0]}")
