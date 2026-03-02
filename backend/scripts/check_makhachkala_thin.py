# -*- coding: utf-8 -*-
"""Проверка тонких перемычек Махачкалы."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    rid = str(c.execute(text("SELECT id FROM regions WHERE name = 'Республика Дагестан'")).scalar())
    parts = c.execute(text("""
        WITH orig AS (
            SELECT d.geom FROM districts d WHERE d.region_id = :rid AND d.name = 'городской округ г. Махачкала'
        ),
        shrunk AS (
            SELECT ST_CollectionExtract(ST_MakeValid(
                ST_Buffer(geom::geography, -100)::geometry
            ), 3) AS geom FROM orig
        ),
        parts AS (
            SELECT (dump).path,
                   (dump).geom AS gp,
                   ROUND((ST_Area((dump).geom::geography)/1e6)::numeric, 4) AS km2,
                   ROUND(ST_Y(ST_Centroid((dump).geom))::numeric, 4) AS lat,
                   ROUND(ST_X(ST_Centroid((dump).geom))::numeric, 4) AS lon
            FROM shrunk, LATERAL ST_Dump(geom) AS dump
        )
        SELECT path, km2, lat, lon FROM parts ORDER BY km2 DESC
    """), {"rid": rid}).fetchall()
    for p in parts:
        print(f"  part {p[0]}: {p[1]} km2, lat={p[2]}, lon={p[3]}")

    # Also check which districts are nearby each small part
    parts2 = c.execute(text("""
        WITH orig AS (
            SELECT d.geom FROM districts d WHERE d.region_id = :rid AND d.name = 'городской округ г. Махачкала'
        ),
        shrunk AS (
            SELECT ST_CollectionExtract(ST_MakeValid(
                ST_Buffer(geom::geography, -100)::geometry
            ), 3) AS geom FROM orig
        ),
        small_parts AS (
            SELECT (dump).geom AS gp,
                   ROUND((ST_Area((dump).geom::geography)/1e6)::numeric, 4) AS km2,
                   ROW_NUMBER() OVER (ORDER BY ST_Area((dump).geom::geography) DESC) AS rn
            FROM shrunk, LATERAL ST_Dump(geom) AS dump
        )
        SELECT sp.rn, sp.km2,
               ROUND(ST_Y(ST_Centroid(sp.gp))::numeric, 4) AS lat,
               ROUND(ST_X(ST_Centroid(sp.gp))::numeric, 4) AS lon,
               d2.name AS nearest,
               ROUND((ST_Distance(sp.gp::geography, d2.geom::geography))::numeric, 0) AS dist_m
        FROM small_parts sp, districts d2
        WHERE d2.region_id = :rid AND d2.name != 'городской округ г. Махачкала'
        AND sp.rn > 1
        AND ST_DWithin(sp.gp::geography, d2.geom::geography, 5000)
        ORDER BY sp.rn, dist_m
    """), {"rid": rid}).fetchall()
    print("\nSmall parts neighbors:")
    seen = set()
    for p in parts2:
        key = p[0]
        if key not in seen:
            seen.add(key)
            print(f"  part #{p[0]} ({p[1]} km2, lat={p[2]}, lon={p[3]}): nearest={p[4]} ({p[5]}m)")
