# -*- coding: utf-8 -*-
"""Проверить диапазон долгот Чукотки — пересекает ли 180-й меридиан."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'c:\Users\Lucky\Documents\zone_monitoring\backend')
from sqlalchemy import create_engine, text
from app.core.config import settings
e = create_engine(settings.DATABASE_URL)
with e.connect() as c:
    rows = c.execute(text("""
        SELECT d.name,
               ST_XMin(d.geom) AS lon_min,
               ST_XMax(d.geom) AS lon_max,
               ST_YMin(d.geom) AS lat_min,
               ST_YMax(d.geom) AS lat_max
        FROM districts d JOIN regions r ON d.region_id = r.id
        WHERE r.name = 'Чукотский автономный округ' AND d.geom IS NOT NULL
        ORDER BY d.name
    """)).fetchall()
    for r in rows:
        crosses = "<<< ПЕРЕСЕКАЕТ 180" if (r[1] < 0 and r[2] > 0 and r[2] > 100) else ""
        if r[1] < -100 and r[2] > 100:
            crosses = "<<< ПЕРЕСЕКАЕТ 180"
        print(f"  {r[0]:<45s}  lon: {r[1]:>10.4f} .. {r[2]:>10.4f}  lat: {r[3]:>8.4f} .. {r[4]:>8.4f}  {crosses}")
