# -*- coding: utf-8 -*-
"""Удалить из Бабаюртовского района осколки, которые лежат на территории Ногайского."""
from sqlalchemy import create_engine, text

engine = create_engine("postgresql+psycopg://zone_user:zone_password@localhost:5432/zone_monitoring")
REGION = "Республика Дагестан"

with engine.begin() as conn:
    conn.execute(text("""
        WITH nogay AS (
            SELECT d.geom AS nogay_geom
            FROM districts d
            JOIN regions r ON d.region_id = r.id
            WHERE r.name = :region AND d.name = 'Ногайский муниципальный район'
        ),
        babay_parts AS (
            SELECT d.id, (dump).geom AS part
            FROM districts d
            JOIN regions r ON d.region_id = r.id,
            LATERAL ST_Dump(d.geom) AS dump
            WHERE r.name = :region AND d.name = 'Бабаюртовский муниципальный район'
        ),
        outside_nogay AS (
            SELECT s.id, s.part
            FROM babay_parts s, nogay n
            WHERE NOT ST_Within(s.part, n.nogay_geom)
        ),
        new_geom AS (
            SELECT o.id, ST_Multi(ST_Union(o.part)) AS new_geom
            FROM outside_nogay o
            GROUP BY o.id
        )
        UPDATE districts d SET geom = n.new_geom
        FROM new_geom n
        WHERE d.id = n.id AND n.new_geom IS NOT NULL AND NOT ST_IsEmpty(n.new_geom)
    """), {"region": REGION})

print("OK: осколки Бабаюртовского на территории Ногайского удалены.")
