# -*- coding: utf-8 -*-
"""Проверка деталей геометрии Махачкалы - geom и geom_simplified."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    rid = str(c.execute(text("SELECT id FROM regions WHERE name = 'Республика Дагестан'")).scalar())
    r = c.execute(text("""
        SELECT 
            ST_NumGeometries(d.geom) AS num_parts,
            ST_NumGeometries(d.geom_simplified) AS num_parts_simpl,
            ROUND((ST_Area(d.geom::geography)/1e6)::numeric, 2) AS area_km2,
            ROUND((ST_Area(d.geom_simplified::geography)/1e6)::numeric, 2) AS area_simpl_km2,
            ST_NumInteriorRings(ST_GeometryN(d.geom, 1)) AS holes,
            ST_NumInteriorRings(ST_GeometryN(d.geom_simplified, 1)) AS holes_simpl,
            ST_IsValid(d.geom) AS valid,
            ST_IsValid(d.geom_simplified) AS valid_simpl,
            ST_NPoints(d.geom) AS npoints,
            ST_NPoints(d.geom_simplified) AS npoints_simpl
        FROM districts d WHERE d.region_id = :rid AND d.name = 'городской округ г. Махачкала'
    """), {"rid": rid}).fetchone()
    print(f"geom: parts={r[0]}, area={r[2]} km2, holes={r[4]}, valid={r[6]}, points={r[8]}")
    print(f"geom_simplified: parts={r[1]}, area={r[3]} km2, holes={r[5]}, valid={r[7]}, points={r[9]}")

    # geom_simplified parts
    parts_s = c.execute(text("""
        SELECT (dump).path, ROUND((ST_Area((dump).geom::geography)/1e6)::numeric, 4) AS km2,
               ROUND(ST_Y(ST_Centroid((dump).geom))::numeric, 4) AS lat,
               ROUND(ST_X(ST_Centroid((dump).geom))::numeric, 4) AS lon
        FROM districts d, LATERAL ST_Dump(d.geom_simplified) AS dump
        WHERE d.region_id = :rid AND d.name = 'городской округ г. Махачкала'
        ORDER BY ST_Area((dump).geom::geography) DESC
    """), {"rid": rid}).fetchall()
    print("\ngeom_simplified parts:")
    for p in parts_s:
        print(f"  part {p[0]}: {p[1]} km2, lat={p[2]}, lon={p[3]}")

    # Check thin connections using buffer
    thin = c.execute(text("""
        WITH orig AS (
            SELECT d.geom FROM districts d WHERE d.region_id = :rid AND d.name = 'городской округ г. Махачкала'
        ),
        shrunk AS (
            SELECT ST_CollectionExtract(ST_MakeValid(
                ST_Buffer(geom::geography, -100)::geometry
            ), 3) AS geom FROM orig
        )
        SELECT ST_NumGeometries(geom),
               ROUND((ST_Area(geom::geography)/1e6)::numeric, 2)
        FROM shrunk WHERE NOT ST_IsEmpty(geom)
    """), {"rid": rid}).fetchone()
    if thin:
        print(f"\nAfter -100m buffer: {thin[0]} parts, {thin[1]} km2")
    else:
        print("\nAfter -100m buffer: geometry disappears")
