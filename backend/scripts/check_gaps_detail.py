# -*- coding: utf-8 -*-
"""Подробная информация о пустых участках рядом с Махачкалой."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    rid = str(c.execute(text("SELECT id FROM regions WHERE name = 'Республика Дагестан'")).scalar())
    gaps = c.execute(text("""
        WITH makh AS (
            SELECT d.geom FROM districts d WHERE d.region_id = :rid AND d.name = 'городской округ г. Махачкала'
        ),
        buf AS (SELECT ST_Buffer(geom::geography, 5000)::geometry AS geom FROM makh),
        all_d AS (SELECT ST_Union(d.geom) AS geom FROM districts d WHERE d.region_id = :rid AND d.geom IS NOT NULL),
        gaps AS (SELECT ST_CollectionExtract(ST_Difference(b.geom, ad.geom), 3) AS geom FROM buf b, all_d ad),
        parts AS (
            SELECT (dump).geom AS gp,
                   ROUND((ST_Area((dump).geom::geography)/1000000)::numeric, 4) AS km2,
                   ROUND(ST_Y(ST_Centroid((dump).geom))::numeric, 4) AS lat,
                   ROUND(ST_X(ST_Centroid((dump).geom))::numeric, 4) AS lon
            FROM gaps, LATERAL ST_Dump(geom) AS dump
        )
        SELECT km2, lat, lon FROM parts ORDER BY km2 DESC
    """), {"rid": rid}).fetchall()
    for g in gaps:
        print(f"  {g[0]} km2, lat={g[1]}, lon={g[2]}")
