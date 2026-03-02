# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    r = c.execute(text("""
        SELECT d.name, ST_NumGeometries(d.geom) as parts,
               ROUND((ST_Area(d.geom::geography)/1000000)::numeric,1) as km2
        FROM districts d
        JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Республика Дагестан' AND d.name ILIKE '%кизляр%'
    """)).fetchall()
    for row in r:
        print(f"  {row[0]}: {row[1]} parts, {row[2]} km2")
    for row in r:
        name = row[0]
        parts = c.execute(text("""
            SELECT (dump).path, ROUND((ST_Area((dump).geom::geography)/1000000)::numeric,2) as km2
            FROM districts d JOIN regions r ON d.region_id = r.id,
            LATERAL ST_Dump(d.geom) AS dump
            WHERE r.name = 'Республика Дагестан' AND d.name = :name
            ORDER BY ST_Area((dump).geom::geography) DESC
        """), {"name": name}).fetchall()
        print(f"\n{name}:")
        for p in parts:
            print(f"  part {p[0]}: {p[1]} km2")
