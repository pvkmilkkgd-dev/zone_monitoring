# -*- coding: utf-8 -*-
"""Найти все районы Дагестана с > 1 частью геометрии."""
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    rows = c.execute(text("""
        SELECT d.name, ST_NumGeometries(d.geom) as parts,
               ROUND((ST_Area(d.geom::geography)/1000000)::numeric,1) as total_km2
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Республика Дагестан' AND d.geom IS NOT NULL AND ST_NumGeometries(d.geom) > 1
        ORDER BY parts DESC
    """)).fetchall()
    if not rows:
        print("Все районы имеют по 1 части")
    for row in rows:
        print(f"\n{row[0]}: {row[1]} parts, {row[2]} km2")
        parts = c.execute(text("""
            SELECT (dump).path, ROUND((ST_Area((dump).geom::geography)/1000000)::numeric,2) as km2,
                   ROUND(ST_Y(ST_Centroid((dump).geom))::numeric, 4) as lat,
                   ROUND(ST_X(ST_Centroid((dump).geom))::numeric, 4) as lon
            FROM districts d JOIN regions r ON d.region_id = r.id,
            LATERAL ST_Dump(d.geom) AS dump
            WHERE r.name = 'Республика Дагестан' AND d.name = :name
            ORDER BY ST_Area((dump).geom::geography) DESC
        """), {"name": row[0]}).fetchall()
        for p in parts:
            print(f"  part {p[0]}: {p[1]} km2, lat={p[2]}, lon={p[3]}")
