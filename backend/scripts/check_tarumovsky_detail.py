# -*- coding: utf-8 -*-
"""Детальная проверка Тарумовского: дыры, self-intersections, тонкие части."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    r = c.execute(text("""
        SELECT d.name,
               ST_NumGeometries(d.geom) as parts,
               ROUND((ST_Area(d.geom::geography)/1000000)::numeric,1) as km2,
               ST_NPoints(d.geom) as pts,
               ST_IsValid(d.geom) as valid,
               ST_IsSimple(d.geom) as simple,
               (SELECT COALESCE(SUM(ST_NumInteriorRings(g.geom)), 0)
                FROM districts d2, LATERAL ST_Dump(d2.geom) AS g WHERE d2.id = d.id) as holes,
               ST_YMin(d.geom) as min_lat, ST_YMax(d.geom) as max_lat,
               ST_XMin(d.geom) as min_lon, ST_XMax(d.geom) as max_lon
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Республика Дагестан' AND d.name ILIKE '%тарумов%'
    """)).fetchone()
    print(f"{r[0]}: {r[1]} parts, {r[2]} km2, {r[3]} pts")
    print(f"  valid={r[4]}, simple={r[5]}, holes={r[6]}")
    print(f"  bbox: lat [{r[7]:.4f}, {r[8]:.4f}], lon [{r[9]:.4f}, {r[10]:.4f}]")

    # Check for narrow parts using negative buffer
    for buf in [10, 50, 100, 500]:
        area = c.execute(text("""
            SELECT ROUND((ST_Area(ST_Buffer(d.geom::geography, :buf)::geography)/1000000)::numeric, 1)
            FROM districts d JOIN regions r ON d.region_id = r.id
            WHERE r.name = 'Республика Дагестан' AND d.name ILIKE '%тарумов%'
        """), {"buf": -buf}).scalar()
        print(f"  buffer -{buf}m: {area} km2")

    # Check if buffer/unbuffer fixes the shape
    print("\n  Trying ST_Buffer(geom, 0.0001) to heal:")
    healed = c.execute(text("""
        SELECT ST_NPoints(ST_Buffer(d.geom, 0.0001)),
               ROUND((ST_Area(ST_Buffer(d.geom, 0.0001)::geography)/1000000)::numeric, 1)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Республика Дагестан' AND d.name ILIKE '%тарумов%'
    """)).fetchone()
    print(f"    pts={healed[0]}, area={healed[1]} km2")

    # Check the southern part of the district (where the red rectangle was)
    print("\n  Southern boundary details (lat < 43.5):")
    south = c.execute(text("""
        SELECT ST_AsText(ST_Intersection(
            d.geom,
            ST_MakeEnvelope(44, 41, 49, 43.5, 4326)
        ))
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Республика Дагестан' AND d.name ILIKE '%тарумов%'
    """)).scalar()
    if south:
        print(f"    type: {south[:80]}...")
