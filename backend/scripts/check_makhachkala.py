# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    parts = c.execute(text("""
        SELECT (dump).path, ROUND((ST_Area((dump).geom::geography)/1000000)::numeric,2) as km2,
               ROUND(ST_Y(ST_Centroid((dump).geom))::numeric, 4) as lat,
               ROUND(ST_X(ST_Centroid((dump).geom))::numeric, 4) as lon
        FROM districts d JOIN regions r ON d.region_id = r.id,
        LATERAL ST_Dump(d.geom) AS dump
        WHERE r.name = 'Республика Дагестан' AND d.name = 'городской округ г. Махачкала'
        ORDER BY ST_Area((dump).geom::geography) DESC
    """)).fetchall()
    for p in parts:
        print(f"  part {p[0]}: {p[1]} km2, lat={p[2]}, lon={p[3]}")
