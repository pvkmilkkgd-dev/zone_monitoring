# -*- coding: utf-8 -*-
"""Вырезать территорию ГО Махачкала из Бабаюртовского района."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
REGION = "Республика Дагестан"

with engine.connect() as conn:
    overlap = conn.execute(text("""
        SELECT ROUND((ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1000000)::numeric, 2)
        FROM districts d1, districts d2, regions r1, regions r2
        WHERE d1.region_id = r1.id AND d2.region_id = r2.id
          AND r1.name = :region AND r2.name = :region
          AND d1.name = 'Бабаюртовский муниципальный район'
          AND d2.name = 'городской округ г. Махачкала'
          AND ST_Intersects(d1.geom, d2.geom)
    """), {"region": REGION}).scalar()
    print(f"Overlap: {overlap} km2")

with engine.begin() as conn:
    conn.execute(text("""
        UPDATE districts d SET geom = ST_Multi(ST_MakeValid(
            ST_CollectionExtract(
                ST_Difference(d.geom, city.geom), 3
            )
        ))
        FROM (
            SELECT d2.geom FROM districts d2 JOIN regions r ON d2.region_id = r.id
            WHERE r.name = :region AND d2.name = 'городской округ г. Махачкала'
        ) city, regions r
        WHERE d.region_id = r.id AND r.name = :region
          AND d.name = 'Бабаюртовский муниципальный район'
    """), {"region": REGION})
    conn.execute(text("""
        UPDATE districts d SET geom_simplified = ST_SimplifyPreserveTopology(d.geom, 0.005)
        FROM regions r WHERE d.region_id = r.id AND r.name = :region
          AND d.name = 'Бабаюртовский муниципальный район'
    """), {"region": REGION})

with engine.connect() as conn:
    after = conn.execute(text("""
        SELECT ROUND((ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1000000)::numeric, 4)
        FROM districts d1, districts d2, regions r1, regions r2
        WHERE d1.region_id = r1.id AND d2.region_id = r2.id
          AND r1.name = :region AND r2.name = :region
          AND d1.name = 'Бабаюртовский муниципальный район'
          AND d2.name = 'городской округ г. Махачкала'
          AND ST_Intersects(d1.geom, d2.geom)
    """), {"region": REGION}).scalar()
    print(f"Overlap after: {after} km2")
    print("OK")
