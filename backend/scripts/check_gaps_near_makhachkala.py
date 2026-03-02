# -*- coding: utf-8 -*-
"""Найти незанятые области рядом с Махачкалой."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    rid = str(c.execute(text("SELECT id FROM regions WHERE name = 'Республика Дагестан'")).scalar())
    # Все пересечения Махачкалы с другими районами
    overlaps = c.execute(text("""
        SELECT d2.name, ROUND((ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1000000)::numeric, 2)
        FROM districts d1, districts d2
        WHERE d1.region_id = :rid AND d2.region_id = :rid
          AND d1.name = 'городской округ г. Махачкала' AND d2.id != d1.id
          AND d1.geom IS NOT NULL AND d2.geom IS NOT NULL
          AND ST_Intersects(d1.geom, d2.geom)
          AND ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1e6 > 0.01
        ORDER BY 2 DESC
    """), {"rid": rid}).fetchall()
    print("Overlaps with Makhachkala:")
    for o in overlaps:
        print(f"  {o[0]}: {o[1]} km2")
    if not overlaps:
        print("  None")

    # Буферная зона 5км вокруг Махачкалы минус все районы = пустые места
    gaps = c.execute(text("""
        WITH makh AS (
            SELECT d.geom FROM districts d WHERE d.region_id = :rid AND d.name = 'городской округ г. Махачкала'
        ),
        buf AS (SELECT ST_Buffer(geom::geography, 5000)::geometry AS geom FROM makh),
        all_d AS (SELECT ST_Union(d.geom) AS geom FROM districts d WHERE d.region_id = :rid AND d.geom IS NOT NULL),
        gaps AS (SELECT ST_CollectionExtract(ST_Difference(b.geom, ad.geom), 3) AS geom FROM buf b, all_d ad)
        SELECT ROUND((ST_Area(geom::geography)/1000000)::numeric, 2),
               ST_NumGeometries(geom),
               ROUND(ST_Y(ST_Centroid(geom))::numeric, 4),
               ROUND(ST_X(ST_Centroid(geom))::numeric, 4)
        FROM gaps WHERE NOT ST_IsEmpty(geom)
    """), {"rid": rid}).fetchone()
    if gaps:
        print(f"\nGaps near Makhachkala: {gaps[0]} km2, {gaps[1]} pieces, center lat={gaps[2]} lon={gaps[3]}")
    else:
        print("\nNo gaps near Makhachkala")
