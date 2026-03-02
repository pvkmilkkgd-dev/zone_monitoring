# -*- coding: utf-8 -*-
"""Убрать дыру в Ногайском районе — включить её в геометрию (только внешние кольца)."""
from sqlalchemy import create_engine, text

engine = create_engine("postgresql+psycopg://zone_user:zone_password@localhost:5432/zone_monitoring")

with engine.begin() as conn:
    conn.execute(text("""
        UPDATE districts d SET geom = sub.geom
        FROM (
            SELECT d.id,
                   ST_Multi(ST_Union(ST_MakePolygon(ST_ExteriorRing((dump).geom)))) AS geom
            FROM districts d
            JOIN regions r ON d.region_id = r.id,
            LATERAL ST_Dump(d.geom) AS dump
            WHERE r.name = :region AND d.name = :name
            GROUP BY d.id
        ) sub
        WHERE d.id = sub.id
    """), {"region": "Республика Дагестан", "name": "Ногайский муниципальный район"})

print("OK: дыра убрана, геометрия Ногайского района обновлена.")
