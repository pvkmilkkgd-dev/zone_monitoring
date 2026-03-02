# -*- coding: utf-8 -*-
"""Вырезать территорию Буйнакского района из ГО Махачкала (пересечение -> Буйнакскому)."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
REGION = "Республика Дагестан"
SRC = "городской округ г. Махачкала"
TGT = "Буйнакский муниципальный район"

with engine.connect() as conn:
    overlap = conn.execute(text("""
        SELECT ROUND((ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1000000)::numeric, 2)
        FROM districts d1, districts d2, regions r1, regions r2
        WHERE d1.region_id = r1.id AND d2.region_id = r2.id
          AND r1.name = :region AND r2.name = :region
          AND d1.name = :src AND d2.name = :tgt
          AND ST_Intersects(d1.geom, d2.geom)
    """), {"region": REGION, "src": SRC, "tgt": TGT}).scalar()
    print(f"Overlap: {overlap} km2")

if overlap and overlap > 0:
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE districts d SET geom = ST_Multi(ST_MakeValid(
                ST_CollectionExtract(ST_Difference(d.geom, tgt.geom), 3)
            ))
            FROM (
                SELECT d2.geom FROM districts d2 JOIN regions r ON d2.region_id = r.id
                WHERE r.name = :region AND d2.name = :tgt
            ) tgt, regions r
            WHERE d.region_id = r.id AND r.name = :region AND d.name = :src
        """), {"region": REGION, "src": SRC, "tgt": TGT})

        for name in [SRC, TGT]:
            conn.execute(text("""
                UPDATE districts d SET geom_simplified = ST_SimplifyPreserveTopology(d.geom, 0.005)
                FROM regions r WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
            """), {"region": REGION, "name": name})

    with engine.connect() as conn:
        after = conn.execute(text("""
            SELECT ROUND((ST_Area(ST_Intersection(d1.geom, d2.geom)::geography)/1000000)::numeric, 4)
            FROM districts d1, districts d2, regions r1, regions r2
            WHERE d1.region_id = r1.id AND d2.region_id = r2.id
              AND r1.name = :region AND r2.name = :region
              AND d1.name = :src AND d2.name = :tgt
              AND ST_Intersects(d1.geom, d2.geom)
        """), {"region": REGION, "src": SRC, "tgt": TGT}).scalar()
        print(f"Overlap after: {after} km2")
    print("OK")
else:
    print("No overlap")
