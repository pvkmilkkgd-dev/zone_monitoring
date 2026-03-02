# -*- coding: utf-8 -*-
"""
Исправить границу между ГО г. Кизляр и Кизлярским районом.
Вырезаем территорию ГО из района, чтобы контуры точно совпадали.
"""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
REGION = "Республика Дагестан"

with engine.connect() as conn:
    overlap = conn.execute(text("""
        SELECT ROUND((ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1000000)::numeric, 2)
        FROM districts d1
        JOIN districts d2 ON d1.id != d2.id
        JOIN regions r1 ON d1.region_id = r1.id
        JOIN regions r2 ON d2.region_id = r2.id
        WHERE r1.name = :region AND r2.name = :region
          AND d1.name = 'городской округ г. Кизляр'
          AND d2.name = 'Кизлярский муниципальный район'
          AND ST_Intersects(d1.geom, d2.geom)
    """), {"region": REGION}).scalar()
    print(f"Overlap: {overlap} km2")

with engine.begin() as conn:
    # Вырезаем ГО Кизляр из Кизлярского района
    conn.execute(text("""
        UPDATE districts d SET geom = ST_Multi(ST_MakeValid(
            ST_CollectionExtract(
                ST_Difference(d.geom, city.geom),
                3
            )
        ))
        FROM (
            SELECT d2.geom FROM districts d2
            JOIN regions r ON d2.region_id = r.id
            WHERE r.name = :region AND d2.name = 'городской округ г. Кизляр'
        ) city,
        regions r
        WHERE d.region_id = r.id AND r.name = :region
          AND d.name = 'Кизлярский муниципальный район'
    """), {"region": REGION})

    conn.execute(text("""
        UPDATE districts d SET geom_simplified = ST_SimplifyPreserveTopology(d.geom, 0.005)
        FROM regions r
        WHERE d.region_id = r.id AND r.name = :region
          AND d.name = 'Кизлярский муниципальный район'
    """), {"region": REGION})

with engine.connect() as conn:
    overlap_after = conn.execute(text("""
        SELECT ROUND((ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1000000)::numeric, 4)
        FROM districts d1
        JOIN districts d2 ON d1.id != d2.id
        JOIN regions r1 ON d1.region_id = r1.id
        JOIN regions r2 ON d2.region_id = r2.id
        WHERE r1.name = :region AND r2.name = :region
          AND d1.name = 'городской округ г. Кизляр'
          AND d2.name = 'Кизлярский муниципальный район'
          AND ST_Intersects(d1.geom, d2.geom)
    """), {"region": REGION}).scalar()
    print(f"Overlap after: {overlap_after} km2")
    print("OK")
