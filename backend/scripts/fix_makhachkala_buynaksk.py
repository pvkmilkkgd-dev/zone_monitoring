# -*- coding: utf-8 -*-
"""Передать кусочек ГО Махачкала, находящийся на территории Буйнакского района, Буйнакскому."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
REGION = "Республика Дагестан"
SRC = "городской округ г. Махачкала"
TGT = "Буйнакский муниципальный район"

with engine.begin() as conn:
    # Все части Махачкалы кроме главной
    parts = conn.execute(text("""
        SELECT (dump).path, ROUND((ST_Area((dump).geom::geography)/1000000)::numeric, 2),
               ROUND(ST_Y(ST_Centroid((dump).geom))::numeric, 4),
               ROUND(ST_X(ST_Centroid((dump).geom))::numeric, 4)
        FROM districts d JOIN regions r ON d.region_id = r.id,
        LATERAL ST_Dump(d.geom) AS dump
        WHERE r.name = :region AND d.name = :src
        ORDER BY ST_Area((dump).geom::geography) DESC
    """), {"region": REGION, "src": SRC}).fetchall()
    for p in parts:
        print(f"  part {p[0]}: {p[1]} km2, lat={p[2]}, lon={p[3]}")

    if len(parts) <= 1:
        print("Only 1 part, nothing to transfer")
    else:
        # Передаём все части кроме главной в Буйнакский
        conn.execute(text("""
            WITH ranked AS (
                SELECT d.id as src_id, (dump).geom as piece_geom,
                       ROW_NUMBER() OVER (ORDER BY ST_Area((dump).geom::geography) DESC) as rn
                FROM districts d JOIN regions r ON d.region_id = r.id,
                LATERAL ST_Dump(d.geom) AS dump
                WHERE r.name = :region AND d.name = :src
            ),
            fragments AS (
                SELECT ST_Union(piece_geom) AS geom FROM ranked WHERE rn > 1
            )
            UPDATE districts d SET geom = ST_Multi(ST_MakeValid(ST_Union(d.geom, f.geom)))
            FROM fragments f, regions r
            WHERE d.region_id = r.id AND r.name = :region AND d.name = :tgt
              AND NOT ST_IsEmpty(f.geom)
        """), {"region": REGION, "src": SRC, "tgt": TGT})

        # Оставляем только главную часть у Махачкалы
        conn.execute(text("""
            WITH main AS (
                SELECT d.id, ST_Multi((dump).geom) AS geom
                FROM districts d JOIN regions r ON d.region_id = r.id,
                LATERAL ST_Dump(d.geom) AS dump
                WHERE r.name = :region AND d.name = :src
                ORDER BY ST_Area((dump).geom::geography) DESC
                LIMIT 1
            )
            UPDATE districts d SET geom = m.geom FROM main m WHERE d.id = m.id
        """), {"region": REGION, "src": SRC})

        for name in [SRC, TGT]:
            conn.execute(text("""
                UPDATE districts d SET geom_simplified = ST_SimplifyPreserveTopology(d.geom, 0.005)
                FROM regions r WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
            """), {"region": REGION, "name": name})

        for name in [SRC, TGT]:
            r = conn.execute(text("""
                SELECT ST_NumGeometries(d.geom), ROUND((ST_Area(d.geom::geography)/1000000)::numeric, 1)
                FROM districts d JOIN regions r ON d.region_id = r.id
                WHERE r.name = :region AND d.name = :name
            """), {"region": REGION, "name": name}).fetchone()
            print(f"  {name}: {r[0]} parts, {r[1]} km2")
        print("OK")
