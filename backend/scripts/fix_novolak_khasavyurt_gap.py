# -*- coding: utf-8 -*-
"""Отдать дыру между Новолакским и Хасавюртовским районами Хасавюртовскому."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
REGION = "Республика Дагестан"
TARGET = "Хасавюртовский муниципальный район"

with engine.begin() as conn:
    rid = str(conn.execute(text("SELECT id FROM regions WHERE name = :r"), {"r": REGION}).scalar())

    gap = conn.execute(text("""
        WITH d1 AS (
            SELECT d.geom FROM districts d JOIN regions r ON d.region_id = r.id
            WHERE r.name = :region AND d.name = 'Новолакский муниципальный район'
        ),
        d2 AS (
            SELECT d.geom FROM districts d JOIN regions r ON d.region_id = r.id
            WHERE r.name = :region AND d.name = :target
        ),
        buf1 AS (SELECT ST_Buffer(geom::geography, 3000)::geometry AS geom FROM d1),
        buf2 AS (SELECT ST_Buffer(geom::geography, 3000)::geometry AS geom FROM d2),
        buf_overlap AS (
            SELECT ST_Intersection(buf1.geom, buf2.geom) AS geom FROM buf1, buf2
        ),
        all_districts AS (
            SELECT ST_Union(d.geom) AS geom
            FROM districts d WHERE d.region_id = :rid AND d.geom IS NOT NULL
        ),
        gap AS (
            SELECT ST_CollectionExtract(ST_Difference(bo.geom, ad.geom), 3) AS geom
            FROM buf_overlap bo, all_districts ad
        )
        SELECT gap.geom, ROUND((ST_Area(gap.geom::geography)/1000000)::numeric, 2)
        FROM gap WHERE NOT ST_IsEmpty(gap.geom)
    """), {"region": REGION, "target": TARGET, "rid": rid}).fetchone()

    if not gap or not gap[0]:
        print("No gap found")
    else:
        print(f"Gap: {gap[1]} km2")
        conn.execute(text("""
            UPDATE districts d SET geom = ST_Multi(ST_MakeValid(ST_Union(d.geom, :gap)))
            FROM regions r WHERE d.region_id = r.id AND r.name = :region AND d.name = :target
        """), {"gap": gap[0], "region": REGION, "target": TARGET})

        conn.execute(text("""
            UPDATE districts d SET geom = sub.geom
            FROM (
                SELECT d.id, ST_Multi(ST_Union(ST_MakePolygon(ST_ExteriorRing((dump).geom)))) AS geom
                FROM districts d JOIN regions r ON d.region_id = r.id,
                LATERAL ST_Dump(d.geom) AS dump
                WHERE r.name = :region AND d.name = :target
                GROUP BY d.id
            ) sub WHERE d.id = sub.id
        """), {"region": REGION, "target": TARGET})
        conn.execute(text("""
            UPDATE districts d SET geom_simplified = ST_SimplifyPreserveTopology(d.geom, 0.005)
            FROM regions r WHERE d.region_id = r.id AND r.name = :region AND d.name = :target
        """), {"region": REGION, "target": TARGET})

        a = conn.execute(text("""
            SELECT ROUND((ST_Area(d.geom::geography)/1000000)::numeric, 1)
            FROM districts d JOIN regions r ON d.region_id = r.id
            WHERE r.name = :region AND d.name = :target
        """), {"region": REGION, "target": TARGET}).scalar()
        print(f"{TARGET}: {a} km2")
        print("OK")
