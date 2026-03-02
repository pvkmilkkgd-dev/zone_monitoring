# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
REGION = "Республика Дагестан"
NAME = "городской округ г. Кизляр"

with engine.connect() as conn:
    before = conn.execute(text("""
        SELECT ST_NPoints(d.geom), ROUND((ST_Area(d.geom::geography)/1000000)::numeric, 1)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = :region AND d.name = :name
    """), {"region": REGION, "name": NAME}).fetchone()
    print(f"Before: {before[0]} pts, {before[1]} km2")

with engine.begin() as conn:
    conn.execute(text("""
        UPDATE districts d SET
            geom = ST_Multi(ST_SimplifyPreserveTopology(d.geom, 0.002)),
            geom_simplified = ST_SimplifyPreserveTopology(d.geom, 0.005)
        FROM regions r
        WHERE d.region_id = r.id AND r.name = :region AND d.name = :name
    """), {"region": REGION, "name": NAME})

with engine.connect() as conn:
    after = conn.execute(text("""
        SELECT ST_NPoints(d.geom), ROUND((ST_Area(d.geom::geography)/1000000)::numeric, 1)
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = :region AND d.name = :name
    """), {"region": REGION, "name": NAME}).fetchone()
    print(f"After:  {after[0]} pts, {after[1]} km2")
    print("OK")
