# -*- coding: utf-8 -*-
"""Заполнить дыры в Хасавюртовском муниципальном районе."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
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
    """), {"region": "Республика Дагестан", "name": "Хасавюртовский муниципальный район"})
    conn.execute(text("""
        UPDATE districts d SET geom_simplified = ST_SimplifyPreserveTopology(d.geom, 0.005)
        FROM regions r
        WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
    """), {"region": "Республика Дагестан", "name": "Хасавюртовский муниципальный район"})
print("OK: дыры заполнены в Хасавюртовском муниципальном районе")
